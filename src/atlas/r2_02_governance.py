"""Round 2, stage 2 — governance-classified open-space polygons.

Nine categories. Fill colour on the maps carries the family; hatch carries the
subtype. Nothing is inferred: each record's category is derived from an official
field, and the field used is written into Governance_Evidence.

Not all POPS are treated as one thing. Zoning POPS (qeta-4kqg),
restrictive-declaration space (igsj-fxac), WPAA (jakx-zd39) and DOT/BID plazas
(fnkv-pyhj) are separate official layers and stay separate. A privately owned
public-access park that is none of those (Domino, Little Island) cannot be
derived from any open dataset and is NOT auto-assigned; the category exists in
the schema and is populated only by manual, sourced entry.
"""
import glob, os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2 = "data/raw/atlas_round2"
OUT = "data/interim/atlas_round2"
CRS = "EPSG:2263"
os.makedirs(OUT, exist_ok=True)

CITY_AGENCIES = {"DOE","CDOT","SDOT","DEP","HPD","NYCHA","DCAS","DSNY","DOT","EDC","SCA","DOHMH","ACS","DOC"}
AUTHORITIES   = {"TBTA","PANYNJ","MTA","BPCA","HRPT","BBP","TRUST","PA"}

def prep(g, crs=CRS):
    g = g[~(g.geometry.is_empty | g.geometry.isna())].copy()
    bad = ~g.geometry.is_valid
    if bad.any():
        g.loc[bad, "geometry"] = g.loc[bad, "geometry"].buffer(0)
    return g.to_crs(crs)

def classify_park(j):
    """Governance category for one Parks-register jurisdiction string."""
    if not isinstance(j, str) or not j.strip():
        return "NYC Parks property", "jurisdiction blank; defaulted to Parks register membership"
    parts = {p.strip().upper() for p in j.replace("/", " ").split()}
    if parts & AUTHORITIES:
        return "Public authority or trust", f"parks_properties.jurisdiction='{j}'"
    if parts == {"DPR"}:
        return "NYC Parks property", f"parks_properties.jurisdiction='{j}'"
    if parts & CITY_AGENCIES:
        return "Other NYC agency public open space", f"parks_properties.jurisdiction='{j}'"
    return "NYC Parks property", f"parks_properties.jurisdiction='{j}' (unrecognised token)"

rows = []
layers = {}

# 1-4  Parks register, split by jurisdiction -------------------------------
pp = prep(gpd.read_file(sorted(glob.glob("data/raw/park_boundaries/parks_properties_20260623/*.shp"))[-1]))
cls = pp["jurisdicti"].apply(classify_park)
pp["Governance_Category"] = [c[0] for c in cls]
pp["Governance_Evidence"] = [c[1] for c in cls]
pp["Jurisdiction_Owner"] = pp["jurisdicti"]
pp["Open_Space_Subtype"] = pp["typecatego"]
pp["Site_Name"] = pp["signname"]
pp["Site_Key"] = pp["gispropnum"]
KEEP = ["Site_Key","Site_Name","Governance_Category","Governance_Evidence",
        "Jurisdiction_Owner","Open_Space_Subtype","acres","borough","geometry"]
pp = pp[KEEP]

layers["parks_properties"] = pp[pp.Governance_Category == "NYC Parks property"]
layers["other_public_open_space"] = pp[pp.Governance_Category == "Other NYC agency public open space"]
layers["public_authority_or_trust"] = pp[pp.Governance_Category == "Public authority or trust"]

# 5  state / federal — Facilities DB is POINTS, so it corroborates ownership
#    level; it is kept as a point layer and never presented as a footprint.
# The Socrata GeoJSON export of the Facilities Database carries NO geometry
# (all 34,446 rows null), so points are rebuilt from its own latitude/longitude
# columns. facgroup is used, not facdomain: the PARKS, GARDENS AND HISTORICAL
# SITES domain also contains historic districts and museums.
fac = pd.read_csv(f"{R2}/facilities_database.geojson", nrows=0)  # placeholder
import json
with open(f"{R2}/facilities_database.geojson") as fh:
    fj = json.load(fh)
fac = pd.DataFrame([f["properties"] for f in fj["features"]])
for c in ("latitude", "longitude"):
    fac[c] = pd.to_numeric(fac[c], errors="coerce")
sf = fac[(fac["overlevel"].isin(["State", "Federal"])) &
         (fac["facgroup"] == "PARKS AND PLAZAS") &
         fac["latitude"].notna() & fac["longitude"].notna()].copy()
sf = gpd.GeoDataFrame(sf, geometry=gpd.points_from_xy(sf["longitude"], sf["latitude"]),
                      crs="EPSG:4326")
sf = prep(sf)
sf["Governance_Category"] = "State or federal park"
sf["Governance_Evidence"] = ("facilities_database.overlevel=" + sf["overlevel"] +
                             "; facgroup=PARKS AND PLAZAS; point rebuilt from "
                             "source latitude/longitude (export geometry was null)")
sf["Jurisdiction_Owner"] = sf["opabbrev"]; sf["Open_Space_Subtype"] = sf["facsubgrp"]
sf["Site_Name"] = sf["facname"]; sf["Site_Key"] = sf["uid"].astype(str)
sf["acres"] = pd.NA
sf["borough"] = sf["boro"] if "boro" in sf.columns else pd.NA
layers["state_federal_open_space"] = sf[KEEP]

# 6-9  the private-public and community families ---------------------------
def simple(path, cat, name_col, key_col, evidence, subtype=None, owner=None):
    g = prep(gpd.read_file(path))
    g["Governance_Category"] = cat
    g["Governance_Evidence"] = evidence
    g["Site_Name"] = g[name_col] if name_col in g.columns else pd.NA
    g["Site_Key"] = g[key_col].astype(str) if key_col in g.columns else g.index.astype(str)
    g["Open_Space_Subtype"] = g[subtype] if subtype and subtype in g.columns else pd.NA
    g["Jurisdiction_Owner"] = g[owner] if owner and owner in g.columns else pd.NA
    if "acres" not in g.columns:
        g["acres"] = (g.geometry.area / 43560).round(3)
    if "borough" not in g.columns:
        g["borough"] = pd.NA
    return g[KEEP]

gt = sorted(glob.glob("data/raw/external_downloads/greenthumb_gardens_*.geojson"))[-1]
layers["community_gardens"] = simple(gt, "Community garden", "gardenname", "gardenname",
                                     "GreenThumb register (p78i-pat6)", owner="juris")
pops_f = sorted(glob.glob("data/raw/external_downloads/pops_*.geojson"))[-1]
layers["zoning_pops"] = simple(pops_f, "Zoning POPS", "building_name", "pops_number",
                               "DCP Zoning POPS register (qeta-4kqg)",
                               subtype="public_space_type")
layers["restrictive_declaration_sites"] = simple(
    f"{R2}/restrictive_declaration_sites.geojson", "Restrictive-declaration public space",
    "location", "gispropnum", "NYC Parks Restrictive Declaration Sites (igsj-fxac)",
    owner="jurisdicti")
layers["dot_pedestrian_plazas"] = simple(
    f"{R2}/dot_pedestrian_plazas.geojson", "DOT pedestrian plaza / BID-managed space",
    "plazaname", "plazaname", "NYC DOT Pedestrian Plazas (fnkv-pyhj); "
    "'partner' names the managing BID or partner where present", owner="partner")
layers["waterfront_public_access_areas"] = simple(
    f"{R2}/waterfront_public_access_areas.geojson",
    "Privately owned public-access park, non-POPS", "name", "wpaa_id",
    "DCP Waterfront Public Access Areas (jakx-zd39): privately built, publicly "
    "accessible waterfront space secured outside the zoning-POPS programme",
    owner="maintenanc")

# context layers, no governance claim
layers["boroughs"] = prep(gpd.read_file("data/raw/geography/Borough_Boundaries_20260623.geojson"))[["boroname","borocode","geometry"]]
nta = prep(gpd.read_file(f"{R2}/nta2020.geojson"))
layers["nta2020"] = nta[[c for c in ("ntaname","nta2020","boroname") if c in nta.columns] + ["geometry"]]

# --- name ambiguity flag ----------------------------------------------------
gov = pd.concat([g.assign(_layer=k) for k, g in layers.items()
                 if "Governance_Category" in g.columns], ignore_index=True)
dup = gov[gov["Site_Name"].notna()].duplicated(subset=["Site_Name"], keep=False)
amb = gov.loc[dup & gov["Site_Name"].notna(), ["Site_Name","Governance_Category","_layer"]]
amb = amb.groupby("Site_Name").filter(lambda d: d["Governance_Category"].nunique() > 1)
amb.to_csv(f"{OUT}/name_qa_ambiguous.csv", index=False)

for k, g in layers.items():
    g.to_file(f"{OUT}/gov_{k}.gpkg", layer=k, driver="GPKG")

print("=== governance layers ===")
tot = 0
for k, g in layers.items():
    cat = g["Governance_Category"].iloc[0] if "Governance_Category" in g.columns and len(g) else "(context)"
    print(f"  {k:<34} {len(g):>6}  {cat}")
    tot += len(g) if "Governance_Category" in g.columns else 0
print(f"  {'TOTAL governance-classified':<34} {tot:>6}")
print(f"\n  name ambiguity rows flagged: {len(amb)} -> {OUT}/name_qa_ambiguous.csv")
print("\n  NOTE: 'Privately owned public-access park, non-POPS' is populated only by "
      "WPAA.\n  Sites such as Domino Park or Little Island have no open dataset and are "
      "NOT auto-assigned.")
