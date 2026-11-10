"""QA for the atlas round: record-count consistency and the checks that matter."""
import glob, os, warnings
import geopandas as gpd, pandas as pd
warnings.filterwarnings("ignore")

GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
rows = []
def chk(status, area, test, detail):
    rows.append({"status": status, "area": area, "test": test, "detail": detail})

pi = pd.read_excel(WB, sheet_name="Project Inventory")
pts = gpd.read_file(GPKG, layer="renovation_project_locations")
gj = gpd.read_file("outputs/atlas/gis/renovation_project_locations_4326.geojson")

# 1 universe preserved
chk("Passed" if len(pi) == 2758 else "Blocked", "inventory", "universe_preserved",
    f"Project Inventory holds {len(pi)} project-location rows (expected 2,758)")

# 2 excel / gpkg / geojson agreement
mapped = pi["Mapped_In_Atlas_Round1"].eq("Yes").sum()
ok = (mapped == len(pts) == len(gj))
chk("Passed" if ok else "Blocked", "cross-format", "record_count_consistency",
    f"Excel mapped={mapped}, GeoPackage={len(pts)}, GeoJSON={len(gj)}")

# 3 no (0,0) reached any spatial output
b = pts.to_crs(4326).total_bounds
chk("Passed" if b[0] > -75 and b[1] > 40 else "Blocked", "geometry", "no_null_island",
    f"mapped extent lon {b[0]:.4f}..{b[2]:.4f}, lat {b[1]:.4f}..{b[3]:.4f}")

# 4 unmapped rows survive in the inventory
un = pi[pi["Mapped_In_Atlas_Round1"] != "Yes"]
chk("Passed" if len(un) == 284 else "Warning", "inventory", "unmapped_retained",
    f"{len(un)} records with no usable coordinate retained in Excel with null map geometry")

# 5 the repaired longitude is still flagged
rep = pi["Coordinate_QA"].astype(str).str.contains("Repaired", na=False)
raw_pos = pd.to_numeric(pi.loc[rep, "Longitude_Raw"], errors="coerce")
chk("Passed" if rep.sum() == 1 and (raw_pos > 0).all() else "Manual review",
    "geometry", "repaired_longitude_traceable",
    f"{int(rep.sum())} repaired record; raw longitude preserved positive "
    f"({raw_pos.tolist()}), QA status retained")

# 6 CRS declared
crs_ok = str(pts.crs).endswith("2263")
chk("Passed" if crs_ok else "Blocked", "geometry", "analysis_crs",
    f"GeoPackage layers in {pts.crs}; share export in EPSG:4326")

# 7 funding never midpointed
band = pi["Funding_Band"].notna()
num_on_band = pd.to_numeric(pi.loc[band, "Funding_Exact_USD"], errors="coerce").notna().sum()
chk("Passed" if num_on_band == 0 else "Blocked", "inventory", "no_band_midpoint",
    f"{int(band.sum())} banded records; {int(num_on_band)} of them carry a numeric value "
    "(must be 0)")

# 8 site/coordinate gap coincidence -- the finding, recorded as a QA fact
noid = pi["Site_Type"].eq("No Park ID")
chk("Manual review", "inventory", "missing_site_and_location_coincide",
    f"{int((noid & (pi['Mapped_In_Atlas_Round1'] != 'Yes')).sum())} of {int((~pi['Mapped_In_Atlas_Round1'].eq('Yes')).sum())} "
    f"unmapped records also lack a Park ID; {int(noid.sum())} records lack a Park ID overall, "
    f"so only {int((noid & pi['Mapped_In_Atlas_Round1'].eq('Yes')).sum())} appear on Map 3")

# 9 duplicate trackerid+parkid still flagged, not resolved
dup = pi.duplicated(subset=["Tracker_ID", "Park_ID"], keep=False) & pi["Park_ID"].notna()
chk("Manual review", "identifiers", "duplicate_trackerid_parkid_unresolved",
    f"{int(dup.sum())} rows share Tracker_ID+Park_ID; flagged for contract/phase review, "
    "no final IDs invented")

# 10 layer inventory
lay = gpd.list_layers(GPKG) if hasattr(gpd, "list_layers") else None
chk("Passed", "gis", "gpkg_layers",
    ", ".join(f"{n}({len(gpd.read_file(GPKG, layer=n))})"
              for n in ["boroughs","parks_properties","active_passive_recreation",
                        "community_gardens","pops","renovation_project_locations"]))

qa = pd.DataFrame(rows)
os.makedirs("outputs/atlas", exist_ok=True)
qa.to_csv("outputs/atlas/qa_issues_round1.csv", index=False)
print(qa["status"].value_counts().to_string()); print()
for _, r in qa.iterrows():
    print(f"[{r['status']:<13}] {r['area']:<12} {r['test']}")
    print(f"                {r['detail']}")
