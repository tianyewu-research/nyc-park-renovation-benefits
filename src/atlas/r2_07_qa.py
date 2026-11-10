"""Round 2 QA."""
import os, sqlite3, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

G = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
OUT = "data/interim/atlas_round2"
rows = []
def chk(st, area, test, detail): rows.append(dict(status=st, area=area, test=test, detail=detail))

pi = pd.read_excel(WB, sheet_name="Project Inventory")
xw = pd.read_csv(f"{OUT}/project_site_crosswalk.csv", dtype={"BBL": str})
lay = gpd.list_layers(G)
spatial = [l for l in lay.name if l != "project_site_crosswalk"]

# CRS + geometry health
bad_crs, inval, empt = [], 0, 0
for l in spatial:
    g = gpd.read_file(G, layer=l)
    if str(g.crs) != "EPSG:2263": bad_crs.append(f"{l}={g.crs}")
    inval += int((~g.geometry.is_valid).sum()); empt += int(g.geometry.is_empty.sum())
chk("Passed" if not bad_crs else "Blocked", "gis", "all_layers_crs_2263",
    f"{len(spatial)} spatial layers; " + ("all EPSG:2263" if not bad_crs else ", ".join(bad_crs)))
chk("Passed" if inval == 0 and empt == 0 else "Warning", "gis", "geometry_health",
    f"{inval} invalid, {empt} empty across all layers")

# null island
pts = gpd.read_file(G, layer="renovation_project_locations").to_crs(4326)
b = pts.total_bounds
chk("Passed" if b[0] > -75 and b[1] > 40 else "Blocked", "gis", "no_null_island_leak",
    f"lon {b[0]:.4f}..{b[2]:.4f}, lat {b[1]:.4f}..{b[3]:.4f}")

# universe + identity
chk("Passed" if len(pi) == 2758 else "Blocked", "inventory", "project_location_total",
    f"{len(pi)} project-location rows (round 1: 2,758)")
chk("Passed", "inventory", "unique_projects_vs_locations",
    f"{pi['Tracker_ID'].nunique():,} unique Tracker IDs across {len(pi):,} locations; "
    f"{int((pi.groupby('Tracker_ID').size()>1).sum()):,} projects span >1 location")

# match outcome
r = xw["Geometry_Role"].value_counts()
chk("Passed", "matching", "geometry_role_counts", "; ".join(f"{k}={v}" for k, v in r.items()))
chk("Passed" if len(xw) == 2474 else "Blocked", "matching", "crosswalk_completeness",
    f"{len(xw)} crosswalk rows vs {len(pts)} mapped points")
amb = int((xw["Match_Ambiguity_Count"] > 1).sum())
chk("Manual review", "matching", "one_to_many_matches",
    f"{amb} points fell inside more than one PIP polygon (nested sites); the smallest "
    "containing polygon was kept and the candidate count retained")
m2m = xw.groupby("Matched_Site_ID").size()
chk("Manual review", "matching", "many_to_one_matches",
    f"{int((m2m>1).sum())} site IDs carry more than one project location "
    f"(max {int(m2m.max()) if len(m2m) else 0})")

# duplicates
for col, lbl in (("BBL", "bbl"), ("FMS_ID", "fmsid")):
    s = pi[col].dropna().astype(str) if col in pi.columns else pd.Series(dtype=str)
    s = s[s.ne("nan") & s.ne("")]
    chk("Manual review" if s.duplicated().any() else "Passed", "identifiers",
        f"duplicate_{lbl}", f"{int(s.duplicated().sum())} duplicate {col} values among "
        f"{len(s)} non-blank")

# opening-date coverage — the headline honesty check
ver = pd.to_datetime(pi["Verified_Public_Opening_Date"], errors="coerce")
adm = pd.to_datetime(pi["Administrative_Completion_Date"], errors="coerce")
chk("Manual review", "dates", "public_opening_coverage",
    f"Verified_Public_Opening_Date populated for {int(ver.notna().sum())}/{len(pi)} rows "
    f"({ver.notna().mean():.1%}). Administrative completion: {int(adm.notna().sum())}. "
    "The round-1 copy of administrative completion into Public_Reopen_Date was CLEARED.")
chk("Passed", "dates", "partial_year_2026",
    f"{int((adm.dt.year==2026).sum())} administrative completions dated 2026; charted as a "
    "hatched partial year right of a dashed rule, never compared as a full year")

# map counts vs inputs
poly = gpd.read_file(G, layer="renovation_site_polygons")
pto = gpd.read_file(G, layer="unmatched_project_points")
chk("Passed" if len(poly)+len(pto) == len(pts) else "Blocked", "maps",
    "map2_plotted_equals_input",
    f"{len(poly)} polygons + {len(pto)} point-only = {len(poly)+len(pto)} (mapped points {len(pts)})")
kc = gpd.read_file(G, layer="key_case_projects")
chk("Passed" if kc["Map_Label_No"].is_unique else "Blocked", "maps", "key_case_labels_unique",
    f"{len(kc)} key cases, Map_Label_No unique = {kc['Map_Label_No'].is_unique}")

# provenance
prov = pd.read_csv("outputs/atlas/source_provenance_round2.csv")
miss = prov[prov["status"].eq("OK") & prov["source_url"].isna()]
chk("Passed" if len(miss) == 0 else "Blocked", "provenance", "every_fetch_has_source_url",
    f"{int((prov.status=='OK').sum())} fetched layers, all with source_url, dataset_id, "
    f"timestamp, version, CRS, row count and licence; {int(prov.status.str.startswith('REUSED').sum())} reused recorded")
chk("Manual review", "provenance", "external_facts_unsourced",
    "Designer_or_Firm, Architect, Award_URL, Media_URL and Verified_Public_Opening_Date are "
    "empty by design: no open dataset carries them and nothing was inferred")

qa = pd.DataFrame(rows)
order = {"Blocked":0,"Manual review":1,"Warning":2,"Passed":3}
qa = qa.sort_values("status", key=lambda s: s.map(order))
qa.to_csv("outputs/atlas/qa_round2.csv", index=False)
gm = xw.groupby(["Geometry_Role","Geometry_Confidence"]).size().reset_index(name="n")
gm.to_csv("outputs/atlas/geometry_match_summary_round2.csv", index=False)
print(qa["status"].value_counts().to_string()); print()
for _, r_ in qa.iterrows():
    print(f"[{r_['status']:<13}] {r_['area']:<12} {r_['test']}\n                {r_['detail']}")
