"""Round 3, step 1 — audit local data, then acquire only the missing base layers.

Acquires exactly four things and nothing else: street centerlines, building
footprints, subway service lines, subway stations. No bus routes, trees,
parcels, rasters, sidewalks, POIs or extra demographics. No OSM, no basemap.

Every fetch records source_url, dataset_id, retrieval timestamp, local path,
CRS, feature count and any filtering/generalisation.
"""
import hashlib, json, os, sys, urllib.request
from datetime import datetime, timezone
import pandas as pd

RAW = "data/raw/atlas_round3"
INT = "data/interim/atlas_round3"
PROV = "outputs/atlas/source_provenance_round3.csv"
for d in (RAW, INT, "outputs/atlas"):
    os.makedirs(d, exist_ok=True)

SRC = [
    # slug, host, dataset_id, title, note
    ("streets_centerline", "data.cityofnewyork.us", "inkn-q76z",
     "NYC Street Centerline (CSCL)",
     "All centerline segments; principal-road filter applied later from documented fields."),
    ("subway_routes", "data.ny.gov", "vtcn-vhd8",
     "MTA Subway Service Lines Map",
     "Official MTA service-line geometry. MTA service colours deliberately NOT used."),
    ("subway_stations", "data.ny.gov", "39hk-dx4f",
     "MTA Subway Stations",
     "Official MTA station points."),
    ("buildings", "data.cityofnewyork.us", "5zhs-2jue",
     "NYC Building Footprints",
     "~1.08M polygons. Full raw file preserved; a documented cartographic "
     "derivative is built separately for citywide rendering."),
]

def sha(p, limit=32 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        n = 0
        while n < limit:
            b = f.read(1 << 20)
            if not b: break
            h.update(b); n += len(b)
    return h.hexdigest()[:16]

def fetch(slug, host, dsid, title, note, only=None):
    if only and slug != only:
        return None
    dest = f"{RAW}/{slug}.geojson"
    url = f"https://{host}/api/v3/views/{dsid}/query.geojson?accessType=DOWNLOAD"
    if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
        print(f"  {slug:<20} cached ({os.path.getsize(dest)/1e6:.0f} MB)")
    else:
        print(f"  {slug:<20} GET {dsid} ...", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "nyc-atlas-round3/research"})
        with urllib.request.urlopen(req, timeout=3600) as r, open(dest, "wb") as f:
            while True:
                b = r.read(1 << 22)
                if not b: break
                f.write(b)
        print(f"     -> {os.path.getsize(dest)/1e6:.0f} MB", flush=True)
    try:
        import geopandas as gpd
        g = gpd.read_file(dest, rows=1)
        crs = str(g.crs)
        gt = ",".join(sorted(map(str, g.geom_type.dropna().unique())))
        import fiona
        with fiona.open(dest) as src:
            n = len(src)
    except Exception as e:
        crs, gt, n = "", f"unread:{type(e).__name__}", pd.NA
    return dict(layer_slug=slug, dataset_id=dsid, source_title=title,
                source_url=url, local_path=dest, status="OK",
                retrieved_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                source_crs=crs, feature_count=n, geometry_type=gt,
                size_mb=round(os.path.getsize(dest)/1e6, 2), sha256_16=sha(dest),
                filtering_generalisation=note,
                license="NYC Open Data / NY State Open Data terms; attribute agency + snapshot date")

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rows = [r for r in (fetch(*s, only=only) for s in SRC) if r]
    # reused local inputs, recorded so provenance is complete
    REUSED = [
        ("acs_b01003_2023_bg", "ACSDT5Y2023.B01003",
         "data/raw/acs_panel/from_walkability/b01003_2023_bg/",
         "ACS 2023 5-year total population, block group"),
        ("tiger_bg_2020vintage", "TIGER2023 BG",
         "data/raw/census_geo_2020/tl_2023_36_bg/",
         "2020-vintage block-group geometry incl. ALAND land area"),
        ("round2_atlas_gpkg", "(derived round 2)",
         "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg",
         "boroughs, governance layers, renovation points/polygons"),
        ("round2_inventory", "(derived round 2)",
         "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx",
         "project inventory incl. Current_Phase, Construction_Start, Geometry_Role"),
    ]
    for slug, dsid, path, note in REUSED:
        rows.append(dict(layer_slug=slug, dataset_id=dsid, source_title=note,
                         source_url="(local, reused)", local_path=path,
                         status="REUSED", retrieved_utc="", source_crs="",
                         feature_count=pd.NA, geometry_type="", size_mb=pd.NA,
                         sha256_16="", filtering_generalisation="reused unchanged",
                         license="see round 1/2 provenance"))
    prov = pd.DataFrame(rows)
    if os.path.exists(PROV) and only:
        old = pd.read_csv(PROV)
        prov = pd.concat([old[~old.layer_slug.isin(prov.layer_slug)], prov], ignore_index=True)
    prov.to_csv(PROV, index=False)
    print(f"\nwrote {PROV} ({len(prov)} rows)")
