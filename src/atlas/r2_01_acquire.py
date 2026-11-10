"""Round 2, stage 1 — acquire the ownership/parcel layers.

Reads data/raw/atlas_round2/ first; only fetches what is missing. Every fetch
records source_url, dataset_id, download_timestamp, source_version, source_crs,
local_path, row_count, geometry_type and license/limitation.

MapPLUTO is NOT bulk-downloaded. The full layer is 858k tax lots; this atlas
needs a few hundred, so lots are pulled by BBL from the DCP feature service in
stage 3, where the BBL list is known.
"""
import hashlib, json, os, urllib.request
from datetime import datetime, timezone
import pandas as pd

DEST = "data/raw/atlas_round2"
PROV = "outputs/atlas/source_provenance_round2.csv"
SOCRATA = "https://data.cityofnewyork.us/api/v3/views/{id}/query.geojson?accessType=DOWNLOAD"
LIC = ("NYC Open Data Terms of Use — public domain for most datasets; attribute "
       "the agency and note the snapshot date.")

LAYERS = [
    # slug, dataset_id, kind, purpose/limitation
    ("cpdb_project_polygons", "9jkp-n57r", "geojson",
     "CPDB project polygons. DCP states some geometries come from manual or fuzzy "
     "matching; keep source and confidence, never treat as surveyed footprint."),
    ("pip_all_sites_mapped", "buk3-3qpr", "geojson",
     "PIP sub-property polygons; finer than a Parks property, used for sub-site match."),
    ("waterfront_public_access_areas", "jakx-zd39", "geojson",
     "WPAA — privately built, publicly accessible waterfront space."),
    ("restrictive_declaration_sites", "igsj-fxac", "geojson",
     "Public space secured by restrictive declaration, NOT zoning POPS."),
    ("dot_pedestrian_plazas", "fnkv-pyhj", "geojson",
     "DOT pedestrian plazas, frequently BID-managed."),
    ("publicly_owned_waterfront", "jr73-mxkz", "geojson",
     "Publicly owned waterfront parcels."),
    ("planimetric_open_space", "g84h-jbjm", "geojson",
     "Planimetric open space; physical surface, not a governance category."),
    ("planimetric_public_plazas", "ue2e-9jm2", "geojson",
     "Planimetric public plazas; physical surface, not a governance category."),
    ("nta2020", "9nt8-h7nd", "geojson", "2020 Neighborhood Tabulation Areas."),
    ("facilities_database", "ji82-xba5", "geojson",
     "Facilities Database — used only to corroborate state/federal ownership."),
    ("colp_gdb", "c2g8-ercv", "blobzip",
     "City Owned and Leased Property geodatabase; agency-level ownership of city lots."),
]


def sha(p, limit=64 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        n = 0
        while n < limit:
            b = f.read(1 << 20)
            if not b: break
            h.update(b); n += len(b)
    return h.hexdigest()[:16]


def version_of(dsid):
    try:
        with urllib.request.urlopen(
                f"https://data.cityofnewyork.us/api/views/{dsid}.json", timeout=30) as r:
            d = json.load(r)
        ts = d.get("rowsUpdatedAt") or d.get("viewLastModified")
        return (datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                if ts else ""), d.get("name", "")
    except Exception:
        return "", ""


rows = []
os.makedirs(DEST, exist_ok=True)
for slug, dsid, kind, note in LAYERS:
    ext = "geojson" if kind == "geojson" else "zip"
    dest = os.path.join(DEST, f"{slug}.{ext}")
    url = (SOCRATA.format(id=dsid) if kind == "geojson"
           else f"https://data.cityofnewyork.us/download/{dsid}/application/zip")
    src_ver, src_name = version_of(dsid)

    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  {slug:<32} already present, not re-fetched")
    else:
        print(f"  {slug:<32} GET {dsid} ...", flush=True)
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "nyc-green-space-atlas-round2/research"})
            with urllib.request.urlopen(req, timeout=600) as r:
                data = r.read()
            with open(dest, "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"     FAILED {type(e).__name__}: {e}")
            rows.append(dict(layer_slug=slug, dataset_id=dsid, source_url=url,
                             local_path="", status=f"FAILED {type(e).__name__}",
                             download_timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             source_version=src_ver, source_name=src_name,
                             source_crs="", row_count=pd.NA, geometry_type="",
                             size_mb=pd.NA, sha256_16="", license_limitation=LIC + " | " + note))
            continue

    # inspect what actually arrived
    n, crs, gt = pd.NA, "", ""
    try:
        if kind == "geojson":
            import geopandas as gpd
            g = gpd.read_file(dest)
            n, crs = len(g), str(g.crs)
            gt = ",".join(sorted(map(str, g.geom_type.dropna().unique())))
        else:
            import zipfile
            with zipfile.ZipFile(dest) as z:
                names = z.namelist()
            gt = f"zip archive, {len(names)} entries"
            crs = "see gdb layers"
    except Exception as e:
        gt = f"unreadable: {type(e).__name__}"

    print(f"     -> {dest}  n={n}  crs={crs}  {gt[:40]}")
    rows.append(dict(layer_slug=slug, dataset_id=dsid, source_url=url,
                     local_path=dest, status="OK",
                     download_timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     source_version=src_ver, source_name=src_name,
                     source_crs=crs, row_count=n, geometry_type=gt,
                     size_mb=round(os.path.getsize(dest) / 1e6, 2), sha256_16=sha(dest),
                     license_limitation=LIC + " | " + note))

# reused round-1 assets, recorded so provenance is complete
REUSED = [
    ("boroughs", "gthc-hcne", "data/raw/geography/Borough_Boundaries_20260623.geojson"),
    ("parks_properties", "enfh-gkve", "data/raw/park_boundaries/parks_properties_20260623/"),
    ("capital_project_tracker", "4hcv-tc5r", "data/raw/capital_projects/capital_project_tracker.csv"),
    ("greenthumb_gardens", "p78i-pat6", "data/raw/external_downloads/"),
    ("zoning_pops", "qeta-4kqg", "data/raw/external_downloads/"),
    ("active_passive_recreation", "kcqe-vnci", "data/raw/external_downloads/"),
    ("pip_inventory", "86a8-pqby", "data/raw/park_quality_pip/pip_inventory.csv"),
    ("pip_inspections", "yg3y-7juh", "data/raw/park_quality_pip/pip_inspections.csv"),
]
for slug, dsid, path in REUSED:
    rows.append(dict(layer_slug=slug, dataset_id=dsid, source_url="(round 1)",
                     local_path=path, status="REUSED from round 1",
                     download_timestamp="", source_version="", source_name="",
                     source_crs="", row_count=pd.NA, geometry_type="",
                     size_mb=pd.NA, sha256_16="",
                     license_limitation=LIC + " | reused, not re-downloaded"))

prov = pd.DataFrame(rows)
os.makedirs(os.path.dirname(PROV), exist_ok=True)
prov.to_csv(PROV, index=False)
print(f"\nwrote {PROV}  ({len(prov)} rows: "
      f"{int((prov.status=='OK').sum())} fetched, "
      f"{int((prov.status.str.startswith('REUSED')).sum())} reused, "
      f"{int((prov.status.str.startswith('FAILED')).sum())} failed)")
