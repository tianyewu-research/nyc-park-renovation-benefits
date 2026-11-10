"""Round 4, step 1 — geometry audit. Audit first, map later.

Nothing is hard-coded: every count is recomputed from the layers on disk.
"""
import os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
XW = "data/interim/atlas_round2/project_site_crosswalk.csv"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
OUT = "data/interim/atlas_round4"
os.makedirs(OUT, exist_ok=True)

GOV_LAYERS = ["parks_properties", "other_public_open_space", "public_authority_or_trust",
              "state_federal_open_space", "zoning_pops", "restrictive_declaration_sites",
              "waterfront_public_access_areas", "dot_pedestrian_plazas", "community_gardens"]

rows = []
for l in GOV_LAYERS:
    g = gpd.read_file(R2, layer=l)
    gt = g.geom_type.value_counts().to_dict()
    n_poly = int(g.geom_type.isin(["Polygon", "MultiPolygon"]).sum())
    n_pt = int(g.geom_type.isin(["Point", "MultiPoint"]).sum())
    has_poly = n_poly == len(g) and len(g) > 0
    rows.append(dict(
        kind="governance", source_layer=l,
        gov_subtype=g["Governance_Category"].iloc[0] if len(g) else "",
        n_records=len(g),
        n_point=n_pt, n_multipoint=int((g.geom_type == "MultiPoint").sum()),
        n_polygon=int((g.geom_type == "Polygon").sum()),
        n_multipolygon=int((g.geom_type == "MultiPolygon").sum()),
        n_empty=int(g.geometry.is_empty.sum()),
        n_invalid=int((~g.geometry.is_valid).sum()),
        geom_types=";".join(f"{k}={v}" for k, v in gt.items()),
        has_real_site_polygon=bool(has_poly),
        needs_parcel_matching=bool(n_pt > 0),
        crs=str(g.crs)))

# renovation site polygons
sp = gpd.read_file(R2, layer="renovation_site_polygons")
pt = gpd.read_file(R2, layer="unmatched_project_points")
pts = gpd.read_file(R2, layer="renovation_project_locations")
xw = pd.read_csv(XW, dtype={"BBL": str})
pi = pd.read_excel(WB, sheet_name="Project Inventory")

for nm, g in (("renovation_site_polygons", sp), ("unmatched_project_points", pt),
              ("renovation_project_locations", pts)):
    gt = g.geom_type.value_counts().to_dict()
    rows.append(dict(kind="renovation", source_layer=nm, gov_subtype="",
        n_records=len(g), n_point=int(g.geom_type.isin(["Point","MultiPoint"]).sum()),
        n_multipoint=int((g.geom_type=="MultiPoint").sum()),
        n_polygon=int((g.geom_type=="Polygon").sum()),
        n_multipolygon=int((g.geom_type=="MultiPolygon").sum()),
        n_empty=int(g.geometry.is_empty.sum()), n_invalid=int((~g.geometry.is_valid).sum()),
        geom_types=";".join(f"{k}={v}" for k,v in gt.items()),
        has_real_site_polygon=bool(nm=="renovation_site_polygons"),
        needs_parcel_matching=False, crs=str(g.crs)))

for role, sub in xw.groupby("Geometry_Role"):
    rows.append(dict(kind="geometry_role", source_layer="project_site_crosswalk",
        gov_subtype=role, n_records=len(sub), n_point=0, n_multipoint=0,
        n_polygon=0, n_multipolygon=0, n_empty=0, n_invalid=0,
        geom_types="; ".join(f"{k}={v}" for k, v in
                             sub["Geometry_Confidence"].value_counts().items()),
        has_real_site_polygon=bool(role != "point_only"),
        needs_parcel_matching=bool(role == "point_only"), crs="EPSG:2263"))

ident = dict(kind="identity", source_layer="inventory + crosswalk", gov_subtype="",
    n_records=len(pi), n_point=0, n_multipoint=0, n_polygon=0, n_multipolygon=0,
    n_empty=0, n_invalid=0,
    geom_types=(f"unique Tracker_ID={pi['Tracker_ID'].nunique()}; "
                f"unique project-location={len(pi)}; "
                f"mapped project-location={len(pts)}; "
                f"unique Matched_Site_ID={xw['Matched_Site_ID'].nunique()}; "
                f"unique Tracker_ID x Matched_Site_ID="
                f"{xw.dropna(subset=['Matched_Site_ID']).drop_duplicates(['Tracker_ID','Matched_Site_ID']).shape[0]}"),
    has_real_site_polygon=False, needs_parcel_matching=False, crs="EPSG:2263")
rows.append(ident)

aud = pd.DataFrame(rows)
# parcel-match columns are filled by step 2; declared here so the schema is stable
for c in ("parcel_match_ok", "parcel_match_ambiguous", "parcel_match_failed"):
    aud[c] = pd.NA
aud.to_csv(f"{OUT}/geometry_audit.csv", index=False)

print("=== governance layers ===")
for _, r in aud[aud.kind == "governance"].iterrows():
    flag = "POLYGON" if r.has_real_site_polygon else "NEEDS PARCEL MATCH"
    print(f"  {r.source_layer:<32} {r.n_records:>5}  {r.geom_types:<24} {flag}")
print("\n=== renovation ===")
for _, r in aud[aud.kind == "renovation"].iterrows():
    print(f"  {r.source_layer:<32} {r.n_records:>5}  {r.geom_types}")
print("\n=== Geometry_Role ===")
for _, r in aud[aud.kind == "geometry_role"].iterrows():
    print(f"  {r.gov_subtype:<26} {r.n_records:>5}  confidence: {r.geom_types}")
print("\n=== identity ===\n  " + ident["geom_types"].replace("; ", "\n  "))
print(f"\nempty geoms: {int(aud.n_empty.sum())} | invalid: {int(aud.n_invalid.sum())}")
print(f"wrote {OUT}/geometry_audit.csv")
