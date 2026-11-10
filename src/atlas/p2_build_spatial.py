"""Phase 2 (this round) — assemble the map layers and the GeoPackage.

Rules honoured here:
  * raw files are read, never written back to
  * Latitude_Map / Longitude_Map drive the point layer; (0,0) records never map
  * records without usable geometry stay in the Excel inventory, not here
  * everything is reprojected EXPLICITLY to EPSG:2263; a 4326 copy is exported
  * invalid geometries are repaired, and the repair is logged

Outputs:
  outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg   (EPSG:2263)
  outputs/atlas/gis/renovation_project_locations_4326.geojson
  logs/geometry_repair_log.csv
"""

import glob
import os
import warnings

import geopandas as gpd
import pandas as pd

warnings.filterwarnings("ignore")

WB = "data/interim/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
ANALYSIS_CRS = "EPSG:2263"
SHARE_CRS = "EPSG:4326"

repairs = []


def latest(pattern):
    hits = sorted(glob.glob(pattern))
    return hits[-1] if hits else None


def prep(gdf, name, keep=None):
    """Repair invalid geometry, drop empties, reproject to the analysis CRS."""
    n0 = len(gdf)
    bad = ~gdf.geometry.is_valid
    n_bad = int(bad.sum())
    if n_bad:
        gdf.loc[bad, "geometry"] = gdf.loc[bad, "geometry"].buffer(0)
    empty = gdf.geometry.is_empty | gdf.geometry.isna()
    n_empty = int(empty.sum())
    gdf = gdf[~empty].copy()
    still_bad = int((~gdf.geometry.is_valid).sum())
    if gdf.crs is None:
        raise SystemExit(f"{name}: source has no CRS; refusing to guess")
    src_crs = str(gdf.crs)
    gdf = gdf.to_crs(ANALYSIS_CRS)
    repairs.append({"layer": name, "n_input": n0, "invalid_repaired": n_bad,
                    "empty_dropped": n_empty, "still_invalid_after_repair": still_bad,
                    "source_crs": src_crs, "output_crs": ANALYSIS_CRS,
                    "n_output": len(gdf)})
    if keep:
        cols = [c for c in keep if c in gdf.columns] + ["geometry"]
        gdf = gdf[cols]
    print(f"  {name:<34} {len(gdf):>6} feat  {src_crs} -> {ANALYSIS_CRS}"
          f"{'  (repaired %d)' % n_bad if n_bad else ''}")
    return gdf


print("building layers...")
layers = {}

# --- boroughs -----------------------------------------------------------
b = gpd.read_file("data/raw/geography/Borough_Boundaries_20260623.geojson")
layers["boroughs"] = prep(b, "boroughs", ["boroname", "borocode", "shape_area"])

# --- parks properties ---------------------------------------------------
shp = latest("data/raw/park_boundaries/parks_properties_20260623/*.shp")
p = gpd.read_file(shp)
layers["parks_properties"] = prep(
    p, "parks_properties",
    ["gispropnum", "signname", "typecategory", "borough", "acres", "class"])

# --- active / passive recreation ---------------------------------------
ap = gpd.read_file(latest("data/raw/external_downloads/active_passive_recreation_*.geojson"))
layers["active_passive_recreation"] = prep(
    ap, "active_passive_recreation",
    ["gispropnum", "public_open_space_name", "recreation_category",
     "acres", "type_category", "borough"])

# --- community gardens --------------------------------------------------
gt = gpd.read_file(latest("data/raw/external_downloads/greenthumb_gardens_*.geojson"))
layers["community_gardens"] = prep(
    gt, "community_gardens",
    [c for c in gt.columns if c != "geometry" and not c.startswith(":")])

# --- POPS ---------------------------------------------------------------
pops = gpd.read_file(latest("data/raw/external_downloads/pops_*.geojson"))
layers["pops"] = prep(
    pops, "pops",
    [c for c in pops.columns if c != "geometry" and not c.startswith(":")])

# --- renovation project locations --------------------------------------
pi = pd.read_excel(WB, sheet_name="Project Inventory")
lat = pd.to_numeric(pi["Latitude_Map"], errors="coerce")
lon = pd.to_numeric(pi["Longitude_Map"], errors="coerce")
mappable = lat.notna() & lon.notna()
print(f"\n  project-location rows in inventory : {len(pi)}")
print(f"  map-ready (Latitude_Map/Longitude_Map non-null) : {int(mappable.sum())}")
print(f"  retained in Excel only (no map geometry)        : {int((~mappable).sum())}")
assert not ((lat == 0) & (lon == 0)).any(), "(0,0) leaked into Latitude_Map"

KEEP = ["Map_ID", "Project_Location_ID", "Tracker_ID", "FMS_ID", "Park_ID",
        "Park_Name", "Park_Type", "Site_Type", "Owning_Agency", "Borough",
        "Borough_QA", "Project_Title", "Current_Phase", "Construction_Start",
        "Construction_Actual_Completion", "Total_Funding_Raw",
        "Funding_Exact_USD", "Funding_Band", "Funding_QA", "Coordinate_QA",
        "Date_QA", "Evidence_Grade", "Enrichment_Status", "Official_Project_URL"]
sub = pi.loc[mappable, [c for c in KEEP if c in pi.columns]].copy()
pts = gpd.GeoDataFrame(
    sub, geometry=gpd.points_from_xy(lon[mappable], lat[mappable]), crs=SHARE_CRS)

os.makedirs("outputs/atlas/gis", exist_ok=True)
pts.to_file("outputs/atlas/gis/renovation_project_locations_4326.geojson",
            driver="GeoJSON")
print("  wrote renovation_project_locations_4326.geojson (EPSG:4326 share copy)")

layers["renovation_project_locations"] = prep(pts, "renovation_project_locations")

# --- write GeoPackage ---------------------------------------------------
if os.path.exists(GPKG):
    os.remove(GPKG)
for name, g in layers.items():
    for c in g.columns:
        if c != "geometry" and g[c].dtype == "object":
            g[c] = g[c].astype(str).replace({"nan": None, "NaT": None})
    g.to_file(GPKG, layer=name, driver="GPKG")
print(f"\nwrote {GPKG}")
for name, g in layers.items():
    print(f"  layer {name:<34} {len(g):>6} features")

pd.DataFrame(repairs).to_csv("logs/geometry_repair_log.csv", index=False)
print("\nwrote logs/geometry_repair_log.csv")
