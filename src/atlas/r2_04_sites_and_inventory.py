"""Round 2, stage 4 — site polygons, enriched inventory, key-case candidates."""
import glob, os, re, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2, OUT = "data/raw/atlas_round2", "data/interim/atlas_round2"
WB_IN  = "outputs/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
WB_OUT = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
CRS = "EPSG:2263"
START_YEAR, END_YEAR = 2010, 2026

def prep(g):
    g = g[~(g.geometry.is_empty | g.geometry.isna())].copy()
    bad = ~g.geometry.is_valid
    if bad.any(): g.loc[bad, "geometry"] = g.loc[bad, "geometry"].buffer(0)
    return g.to_crs(CRS)

xw   = pd.read_csv(f"{OUT}/project_site_crosswalk.csv", dtype={"BBL": str})
pts  = gpd.read_file("outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg",
                     layer="renovation_project_locations")
parks= prep(gpd.read_file(sorted(glob.glob("data/raw/park_boundaries/parks_properties_20260623/*.shp"))[-1]))
cpdb = prep(gpd.read_file(f"{R2}/cpdb_project_polygons.geojson"))
pipp = prep(gpd.read_file(f"{R2}/pip_all_sites_mapped.geojson"))
cpdb["cp_pj"] = cpdb["projectid"].astype(str).str.upper().str.replace(" ","",regex=False)

# ---- assemble one polygon per project location where one exists -----------
geo = []
pk = parks.assign(_k=parks["gispropnum"].astype(str)).drop_duplicates("_k").set_index("_k")["geometry"]
cp = cpdb.drop_duplicates("cp_pj").set_index("cp_pj")["geometry"]
pp = pipp.assign(_k=pipp["prop_id"].astype(str)).drop_duplicates("_k").set_index("_k")["geometry"]
for _, r in xw.iterrows():
    g = None
    if r.Geometry_Role == "cpdb_project_polygon":   g = cp.get(str(r.Cand_B_cpdb))
    elif r.Geometry_Role == "pip_subsite_polygon":  g = pp.get(str(r.Cand_C_pip))
    elif r.Geometry_Role == "park_property_polygon":g = pk.get(str(r.Cand_A_park))
    geo.append(g)
sp = gpd.GeoDataFrame(xw.copy(), geometry=geo, crs=CRS)
site_poly = sp[sp.geometry.notna()].copy()
pt_only   = sp[sp.geometry.isna()].copy()
pt_only = gpd.GeoDataFrame(pt_only.drop(columns="geometry"),
                           geometry=pts.set_index("Map_ID").loc[pt_only["Map_ID"], "geometry"].values,
                           crs=CRS)
site_poly.to_file(f"{OUT}/renovation_site_polygons.gpkg", layer="renovation_site_polygons", driver="GPKG")
pt_only.to_file(f"{OUT}/unmatched_project_points.gpkg", layer="unmatched_project_points", driver="GPKG")
print(f"site polygons {len(site_poly)} | point-only {len(pt_only)}")

# ---- enrich the single master inventory -----------------------------------
pi = pd.read_excel(WB_IN, sheet_name="Project Inventory")
m = xw.set_index("Map_ID")
def take(col): return pi["Map_ID"].map(m[col]) if col in m.columns else pd.NA

gov = pd.concat([gpd.read_file(f"{OUT}/gov_{k}.gpkg", layer=k)
                 for k in ("parks_properties","other_public_open_space",
                           "public_authority_or_trust")], ignore_index=True)
gov_by_id = gov.assign(_k=gov["Site_Key"].astype(str)).drop_duplicates("_k").set_index("_k")

NEW = {
 "Ownership_Model": pi["Park_ID"].astype(str).map(gov_by_id["Governance_Category"]),
 "Jurisdiction_Owner": pi["Park_ID"].astype(str).map(gov_by_id["Jurisdiction_Owner"]),
 "Operator_Manager": pd.NA, "Maintenance_Entity": pd.NA,
 "Open_Space_Subtype": pi["Park_ID"].astype(str).map(gov_by_id["Open_Space_Subtype"]),
 "Project_Type": pd.NA, "Before_Condition": pd.NA,
 "Designer_or_Firm": pd.NA, "Architect": pd.NA,
 "Client_Lead_Agency": pi.get("Owning_Agency"),
 "Verified_Public_Opening_Date": pd.NA,
 "Opening_Date_Source": pd.NA,
 "Administrative_Completion_Date": pi["Construction_Actual_Completion"],
 "BBL": take("BBL"), "CPDB_MAPROJID": take("Cand_B_cpdb"),
 "Geometry_Role": take("Geometry_Role"), "Geometry_Source": take("Geometry_Source"),
 "Geometry_Method": take("Geometry_Method"), "Geometry_Confidence": take("Geometry_Confidence"),
 "Geometry_QA": take("Geometry_QA"), "Matched_Site_ID": take("Matched_Site_ID"),
 "Match_Distance_Ft": take("Match_Distance_Ft"),
 "Match_Ambiguity_Count": take("Match_Ambiguity_Count"),
 "Primary_Official_URL": pi.get("Official_Project_URL"),
 "Design_Firm_URL": pd.NA, "Award_URL": pd.NA, "Media_URL": pd.NA,
 "Key_Case_Flag": "", "Profile_Rationale": "", "Map_Label_No": pd.NA,
 "Name_QA": "", "Last_Verified_Date": pd.NA,
}
for k, v in NEW.items(): pi[k] = v
pi["Ownership_Model"] = pi["Ownership_Model"].fillna(
    pi["Site_Type"].map({"Non-Parks public green-space site":"Other NYC agency public open space",
                         "No Park ID":pd.NA,"Unmatched or legacy property code":pd.NA}))
# the rule the brief insists on
pi["Public_Reopen_Date"] = pd.NA
pi["Public_Reopen_Date_QA"] = ("Cleared in round 2: the round-1 value was a verbatim copy of "
    "Construction_Actual_Completion. Administrative completion is not a public opening date. "
    "Repopulate only from an independent source recorded in Opening_Date_Source.")

# ---- key-case CANDIDATES (transparent filter, not a hidden score) ---------
cs = pd.to_datetime(pi["Construction_Start"], errors="coerce").dt.year
cc = pd.to_datetime(pi["Administrative_Completion_Date"], errors="coerce").dt.year
inwin = ((cs.between(START_YEAR, END_YEAR)) | (cc.between(START_YEAR, END_YEAR)))
fund = pd.to_numeric(pi["Funding_Exact_USD"], errors="coerce")
elig = pi[inwin & pi["Mapped_In_Atlas_Round1"].eq("Yes")].copy()
elig["_fund"] = fund[elig.index]
elig["_boro"] = elig["Borough"].astype(str).str.split(r"[,/]").str[0].str.strip()
elig["_gov"]  = elig["Ownership_Model"].fillna("Unclassified")

picks, n = [], 0
for boro in ["Bronx","Brooklyn","Manhattan","Queens","Staten Island"]:
    sub = elig[elig["_boro"] == boro]
    for gv in sub["_gov"].value_counts().index[:2]:
        cand = sub[sub["_gov"] == gv].nlargest(2, "_fund")
        for idx, r in cand.iterrows():
            if pd.isna(r["_fund"]) or n >= 25: continue
            n += 1
            picks.append((idx, n,
                f"Borough-balanced candidate: largest recorded exact funding "
                f"(${r['_fund']:,.0f}) among {boro} locations with governance "
                f"'{gv}' inside {START_YEAR}-{END_YEAR}. NOT yet verified against "
                f"awards, PDC records or design publications — Enrichment_Status "
                f"remains open."))
for idx, lab, why in picks:
    pi.loc[idx, "Key_Case_Flag"] = "Candidate — unverified"
    pi.loc[idx, "Map_Label_No"] = lab
    pi.loc[idx, "Profile_Rationale"] = why
print(f"key-case candidates: {len(picks)} (target 15-25)")

# ---- write workbook: all sheets preserved, one master table ---------------
xl = pd.ExcelFile(WB_IN)
sheets = {s: (xl.parse(s, header=None) if s == "Overview" else xl.parse(s))
          for s in xl.sheet_names}
sheets["Project Inventory"] = pi
kv = pi[pi["Key_Case_Flag"].ne("")][
    ["Map_Label_No","Project_Title","Park_Name","Borough","Ownership_Model",
     "Open_Space_Subtype","Administrative_Completion_Date","Funding_Exact_USD",
     "Designer_or_Firm","Geometry_Role","Geometry_Confidence","Key_Case_Flag",
     "Profile_Rationale","Primary_Official_URL"]].sort_values("Map_Label_No")
sheets["Key Cases View"] = kv
sheets["Governance_Categories"] = pd.DataFrame({
    "Category": ["NYC Parks property","Other NYC agency public open space",
        "State or federal park","Public authority or trust","Zoning POPS",
        "Restrictive-declaration public space",
        "Privately owned public-access park, non-POPS",
        "DOT pedestrian plaza / BID-managed space","Community garden"],
    "Source": ["parks_properties.jurisdiction=DPR","parks_properties.jurisdiction non-DPR city agency",
        "facilities_database overlevel=State/Federal, facgroup=PARKS AND PLAZAS",
        "parks_properties.jurisdiction contains an authority (e.g. TBTA)",
        "DCP Zoning POPS qeta-4kqg","NYC Parks Restrictive Declaration Sites igsj-fxac",
        "DCP WPAA jakx-zd39 (non-POPS private public-access); other such parks are NOT auto-assigned",
        "NYC DOT Pedestrian Plazas fnkv-pyhj","GreenThumb p78i-pat6"]})
with pd.ExcelWriter(WB_OUT, engine="openpyxl") as w:
    for nm, df in sheets.items():
        df.to_excel(w, sheet_name=nm[:31], index=False, header=(nm != "Overview"))
print(f"wrote {WB_OUT}")
for nm, df in sheets.items(): print(f"  {nm:<26} {len(df):>5} x {df.shape[1]:>3}")
