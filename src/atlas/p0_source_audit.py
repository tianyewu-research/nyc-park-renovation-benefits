"""Phase 0 — environment and source-data audit.

Scans every input under data/ and records what it actually is, then runs the
integrity checks the atlas depends on.

Two outputs:
  data/interim/atlas/source_audit.csv        one row per input file (or file group)
  data/interim/atlas/qa_issues_p0.csv        one row per detected problem

Design notes
------------
Advan weekly extracts are 157 near-identical files; they are audited as ONE
group (sampled) rather than 157 rows, so the audit stays readable.

The Capital Project Tracker is project-LOCATION granularity. A repeated
trackerid is therefore expected and is NOT an error; it is recorded so Phase 2
can split projects from project_locations correctly.

Usage:  python3 src/atlas/p0_source_audit.py
"""

import glob
import gzip
import hashlib
import os
import re
import sys
import warnings
from datetime import datetime, timezone

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = "."
OUT_AUDIT = "data/interim/atlas/source_audit.csv"
OUT_QA = "data/interim/atlas/qa_issues_p0.csv"

# generous bounding box for the five boroughs
NYC_BBOX = (-74.30, 40.47, -73.68, 40.93)

DATE_HINT = re.compile(r"date|start|completion|updated|inspect|time", re.I)
LON_HINT = re.compile(r"^(longitude|lon|x|long)$", re.I)
LAT_HINT = re.compile(r"^(latitude|lat|y)$", re.I)

# what we know about each input; purpose is deliberately short
KNOWN = {
    "capital_project_tracker.csv": ("NYC Open Data 4hcv-tc5r", "Parks capital projects; project-location grain"),
    "cpdb_projects.csv": ("NYC Open Data fi59-268w", "OMB capital projects; independent date/budget source"),
    "parks_properties.csv": ("NYC Open Data enfh-gkve", "Park property attributes (tabular)"),
    "pip_inspections.csv": ("NYC Open Data yg3y-7juh", "Park condition ratings over time"),
    "pip_inventory.csv": ("NYC Open Data 86a8-pqby", "Park feature inventory"),
    "nyc_permitted_events.csv": ("NYC Open Data tvpp-9vvx", "Permitted events; current subset only"),
    "parks_special_events.csv": ("NYC Open Data 6v4b-5gp4", "Public Programs special events"),
    "candidate_projects.csv": ("derived, src/gate_01", "PILOT: initial project screen"),
    "candidate_projects_clean.csv": ("derived, src/gate_02", "PILOT: previously_screened_candidate flag only"),
    "poi_property_crosswalk_canonical_100ft.csv": ("derived, LPUR paper", "Advan ID_STORE -> Parks parkid"),
    "Borough_Boundaries_20260623.geojson": ("NYC Open Data", "Borough polygons"),
    "tab20_blkgrp20_blkgrp10_st36.txt": ("Census rel2020", "2010<->2020 block group relationship"),
    "bg_crosswalk_2010_2020_nyc.csv": ("derived, src/fetch_02_geo", "NYC subset of the BG relationship file"),
}

issues = []
unrecorded = []


def flag(sev, source, check, detail, action=""):
    issues.append({"severity": sev, "source": source, "check": check,
                   "detail": detail, "recommended_action": action})


def file_hash(path, limit=64 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        read = 0
        while read < limit:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
            read += len(b)
    return h.hexdigest()[:16]


def date_range(df):
    los, his = [], []
    for c in df.columns:
        if not DATE_HINT.search(str(c)):
            continue
        s = pd.to_datetime(df[c], errors="coerce", utc=True)
        if s.notna().sum() == 0:
            continue
        los.append(s.min().tz_convert(None))
        his.append(s.max().tz_convert(None))
    if not los:
        return "", ""
    return f"{min(los):%Y-%m-%d}", f"{max(his):%Y-%m-%d}"


def audit_table(path, df, source, purpose, crs="", extent=""):
    lo, hi = date_range(df)
    return {
        "rel_path": os.path.relpath(path, ROOT),
        "format": os.path.splitext(path)[1].lstrip("."),
        "size_mb": round(os.path.getsize(path) / 1e6, 2),
        "sha256_16": file_hash(path),
        "n_records": len(df),
        "n_fields": df.shape[1],
        "fields": "|".join(map(str, df.columns[:60])),
        "date_min": lo, "date_max": hi,
        "crs": crs, "spatial_extent": extent,
        "file_mtime": datetime.fromtimestamp(
            os.path.getmtime(path), timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": source, "purpose": purpose,
    }


def read_any(path):
    """Return (df, crs, extent) or (None, ...) if unreadable/not tabular."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".geojson", ".shp", ".gpkg"):
            import geopandas as gpd
            g = gpd.read_file(path)
            b = g.total_bounds
            return (pd.DataFrame(g.drop(columns=g.geometry.name)),
                    str(g.crs), f"{b[0]:.4f},{b[1]:.4f},{b[2]:.4f},{b[3]:.4f}")
        if ext == ".csv":
            return pd.read_csv(path, low_memory=False), "", ""
        if ext == ".gz":
            return pd.read_csv(path, low_memory=False, nrows=200000), "", ""
        if ext == ".txt":
            sep = "|" if "tab20" in os.path.basename(path) else None
            if sep:
                return pd.read_csv(path, sep=sep, dtype=str, low_memory=False), "", ""
            return pd.DataFrame({"line": open(path).read().splitlines()}), "", ""
        if ext == ".xlsx":
            return pd.read_excel(path), "", ""
    except Exception as e:
        flag("Warning", os.path.relpath(path, ROOT), "unreadable",
             f"{type(e).__name__}: {e}", "inspect manually")
    return None, "", ""


# ---------------------------------------------------------------- scan
rows = []
skip_dirs = {"advan_vintage_202606"}
paths = []
for dirpath, dirnames, filenames in os.walk("data"):
    dirnames[:] = [d for d in dirnames if d not in skip_dirs]
    for fn in filenames:
        if fn.startswith(".") or fn.endswith(".zip"):
            continue
        paths.append(os.path.join(dirpath, fn))

print(f"scanning {len(paths)} files (advan weekly audited as one group)...")
for p in sorted(paths):
    base = os.path.basename(p)
    src, purp = KNOWN.get(base, ("unrecorded", "unrecorded"))
    if src == "unrecorded":
        unrecorded.append(os.path.relpath(p, ROOT))
    df, crs, ext = read_any(p)
    if df is None:
        rows.append({"rel_path": os.path.relpath(p, ROOT),
                     "format": os.path.splitext(p)[1].lstrip("."),
                     "size_mb": round(os.path.getsize(p) / 1e6, 2),
                     "sha256_16": file_hash(p), "n_records": pd.NA,
                     "n_fields": pd.NA, "fields": "", "date_min": "", "date_max": "",
                     "crs": "", "spatial_extent": "",
                     "file_mtime": datetime.fromtimestamp(
                         os.path.getmtime(p), timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                     "source": src, "purpose": purp})
        continue
    rows.append(audit_table(p, df, src, purp, crs, ext))

# advan weekly group
wk = sorted(glob.glob("data/raw/advan_vintage_202606/*.csv.gz"))
if wk:
    sample = pd.read_csv(wk[0], low_memory=False, nrows=5000)
    weeks = sorted(re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(f)).group(1) for f in wk)
    rows.append({
        "rel_path": "data/raw/advan_vintage_202606/ (GROUP of %d weekly files)" % len(wk),
        "format": "csv.gz", "size_mb": round(sum(os.path.getsize(f) for f in wk) / 1e6, 2),
        "sha256_16": file_hash(wk[0]) + " (first file)",
        "n_records": pd.NA, "n_fields": sample.shape[1],
        "fields": "|".join(map(str, sample.columns)),
        "date_min": weeks[0], "date_max": weeks[-1], "crs": "EPSG:4326 (point lat/lon)",
        "spatial_extent": "NYC park POIs",
        "file_mtime": datetime.fromtimestamp(
            os.path.getmtime(wk[0]), timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Dewey Data / Advan Weekly Patterns, 2026-06 vintage",
        "purpose": "PILOT/prototype only; NOT the production single-vintage panel",
    })

audit = pd.DataFrame(rows).sort_values("rel_path")
os.makedirs(os.path.dirname(OUT_AUDIT), exist_ok=True)
audit.to_csv(OUT_AUDIT, index=False)
print(f"wrote {OUT_AUDIT}  ({len(audit)} rows)")

# ------------------------------------------------------- integrity checks
print("\nrunning integrity checks...")
TRK = "data/raw/capital_projects/capital_project_tracker.csv"
PPROP = "data/raw/capital_projects/parks_properties.csv"

if os.path.exists(TRK):
    t = pd.read_csv(TRK, low_memory=False)
    n = len(t)

    # -- coordinates -----------------------------------------------------
    if {"latitude", "longitude"}.issubset(t.columns):
        lat = pd.to_numeric(t["latitude"], errors="coerce")
        lon = pd.to_numeric(t["longitude"], errors="coerce")
        miss = int((lat.isna() | lon.isna()).sum())
        if miss:
            flag("Warning", "capital_project_tracker", "missing_coordinates",
                 f"{miss}/{n} rows ({miss/n:.1%}) lack usable lat/lon",
                 "geocode from park_id or address in Phase 4; keep NA meanwhile")
        null_island = int(((lat == 0) & (lon == 0)).sum())
        if null_island:
            flag("Warning", "capital_project_tracker", "coords_encoded_zero_not_null",
                 f"{null_island}/{n} rows carry literal (0, 0) coordinates; the "
                 "lat/lon columns are never NA, so missingness is encoded as zero",
                 "convert (0,0) to NA BEFORE any mapping or spatial join -- otherwise "
                 "these projects plot in the Gulf of Guinea and silently pass a "
                 "not-null test")
        inb = (lon.between(NYC_BBOX[0], NYC_BBOX[2]) & lat.between(NYC_BBOX[1], NYC_BBOX[3]))
        other_out = t[~inb & lat.notna() & lon.notna() & ~((lat == 0) & (lon == 0))]
        if len(other_out):
            ex = [f"({a:.4f}, {b:.4f})" for a, b in
                  zip(lat[other_out.index], lon[other_out.index])][:5]
            flag("Manual review", "capital_project_tracker", "coords_outside_nyc",
                 f"{len(other_out)} rows outside the NYC bbox and not (0,0): {ex}",
                 "check for a dropped minus sign on longitude before discarding")

    # -- tracker id grain -------------------------------------------------
    if "trackerid" in t.columns:
        dup = t["trackerid"].duplicated(keep=False)
        n_dup_ids = t.loc[dup, "trackerid"].nunique()
        if n_dup_ids:
            flag("Passed", "capital_project_tracker", "duplicate_trackerid_expected",
                 f"{n_dup_ids} trackerids appear on >1 row ({int(dup.sum())} rows total) "
                 "-- consistent with project-LOCATION grain, not an error",
                 "Phase 2: split into projects (unique trackerid) and project_locations")
        if {"trackerid", "parkid"}.issubset(t.columns):
            d2 = t.duplicated(subset=["trackerid", "parkid"], keep=False)
            if d2.any():
                flag("Manual review", "capital_project_tracker",
                     "duplicate_trackerid_plus_parkid",
                     f"{int(d2.sum())} rows share the same trackerid+parkid pair",
                     "these are NOT distinguished by location; check whether they are "
                     "separate contracts/phases before assigning project_location_id")

    # -- dates -------------------------------------------------------------
    dcols = [c for c in t.columns if DATE_HINT.search(c)]
    for c in dcols:
        s = pd.to_datetime(t[c], errors="coerce")
        if s.notna().sum() == 0:
            continue
        bad = s[(s < pd.Timestamp("1980-01-01")) | (s > pd.Timestamp("2050-01-01"))]
        if len(bad):
            flag("Manual review", "capital_project_tracker", "implausible_date",
                 f"{c}: {len(bad)} values outside 1980-2050, e.g. "
                 f"{sorted(bad.dt.strftime('%Y-%m-%d').unique())[:5]}",
                 "set to NA and record original in a *_raw column")
    # ordering
    if {"constructionstart", "constructionactualcompletion"}.issubset(t.columns):
        a = pd.to_datetime(t["constructionstart"], errors="coerce")
        b = pd.to_datetime(t["constructionactualcompletion"], errors="coerce")
        rev = int((b < a).sum())
        if rev:
            flag("Manual review", "capital_project_tracker", "date_order_violation",
                 f"{rev} rows have construction completion BEFORE construction start",
                 "flag in qa_flags; do not silently swap")

    # -- borough -----------------------------------------------------------
    if "borough" in t.columns:
        VALID = {"Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"}
        vals = t["borough"].dropna().unique()
        weird = [v for v in vals if v not in VALID]
        if weird:
            flag("Manual review", "capital_project_tracker", "nonstandard_borough",
                 f"{len(weird)} non-standard borough values, e.g. {sorted(weird)[:6]}",
                 "concatenated multi-borough strings; parse into a borough list in "
                 "Phase 2, keep the raw string")

    # -- funding -----------------------------------------------------------
    if "totalfunding" in t.columns:
        f = t["totalfunding"].dropna().astype(str)
        band = f.str.contains("Between|between", regex=True)
        exact = f.str.match(r"^\$[\d,]+$")
        other = ~(band | exact)
        flag("Passed", "capital_project_tracker", "funding_format_mix",
             f"exact ${int(exact.sum())} rows / band {int(band.sum())} rows / "
             f"other {int(other.sum())} rows; {n - len(f)} rows NA",
             "Phase 2: keep funding_raw, funding_numeric (NA for bands), "
             "funding_band; never coerce a band to a midpoint silently")
        if other.any():
            flag("Manual review", "capital_project_tracker", "funding_unparsed_format",
                 f"{int(other.sum())} funding strings match neither pattern, e.g. "
                 f"{sorted(f[other].unique())[:5]}", "extend the parser or leave NA")

    # -- cross-source field conflict ---------------------------------------
    if os.path.exists(PPROP) and "parkid" in t.columns:
        pp = pd.read_csv(PPROP, low_memory=False)
        idcol = next((c for c in ("gispropnum", "GISPROPNUM", "propnum")
                      if c in pp.columns), None)
        if idcol:
            known = set(pp[idcol].dropna().astype(str))
            tp = t["parkid"].dropna().astype(str)
            orphan = sorted(set(tp) - known)
            AGENCY = {"DEP", "DOE", "DOT", "HPD", "EDC", "SCA", "NYCHA"}
            agency = sorted(set(orphan) & AGENCY)
            rest = sorted(set(orphan) - AGENCY)
            if agency:
                nrow = int(t["parkid"].astype(str).isin(agency).sum())
                flag("Manual review", "capital_project_tracker", "site_is_not_a_parks_property",
                     f"{len(agency)} parkid values are AGENCY codes, not park properties "
                     f"({agency}), covering {nrow} rows -- e.g. DOE school playgrounds, "
                     "DOT medians/greenways, DEP sites",
                     "these are real green-space projects on non-Parks land and must be "
                     "KEPT in the universe; sites table needs a site_type / owning_agency "
                     "field rather than assuming every project sits on a Parks property")
            if rest:
                nrow = int(t["parkid"].astype(str).isin(rest).sum())
                flag("Manual review", "tracker x parks_properties", "parkid_not_in_properties",
                     f"{len(rest)} distinct parkids absent from parks_properties "
                     f"({nrow} rows), e.g. {rest[:8]}",
                     "sub-property suffixes, retired ids, or a second property-code series "
                     "(MZ*/QZ*/BZ*); build an explicit site crosswalk in Phase 3, do not drop")
        else:
            flag("Manual review", "parks_properties", "no_property_id_column",
                 f"columns are {list(pp.columns)[:12]}", "identify the property id field")

# blockers ---------------------------------------------------------------
flag("Blocked", "NYC_Green_Space_Renovation_Inventory.xlsx", "workbook_not_found",
     "Phase 1's GIS Layer Index (Official_Page / Direct_Download_URL / Priority / "
     "Local_Status) is unavailable; full-disk search of the local machine found no "
     ".xlsx/.xlsm with this name",
     "user to supply the workbook, OR authorise building a GIS Layer Index from "
     "NYC Open Data + Census official pages and treat it as evidence grade B")

if unrecorded:
    from collections import Counter
    by_dir = Counter(os.path.dirname(u) for u in unrecorded)
    flag("Manual review", "data/ (multiple)", "provenance_missing",
         f"{len(unrecorded)} files across {len(by_dir)} directories have no recorded "
         f"source/purpose; largest: " +
         ", ".join(f"{d} ({c})" for d, c in by_dir.most_common(5)),
         "Phase 2 sources table must carry source URL, dataset id, access timestamp, "
         "hash, record count, CRS and licence for every input")
    pd.DataFrame({"rel_path": sorted(unrecorded)}).to_csv(
        "data/interim/atlas/provenance_missing_files.csv", index=False)

qa = pd.DataFrame(issues)
order = {"Blocked": 0, "Manual review": 1, "Warning": 2, "Passed": 3}
qa = qa.sort_values("severity", key=lambda s: s.map(order))
qa.to_csv(OUT_QA, index=False)
qa[qa["severity"] == "Blocked"].to_csv(
    "data/interim/atlas/manual_review_blockers.csv", index=False)

print(f"wrote {OUT_QA}  ({len(qa)} issues)")
print("\nseverity counts:")
print(qa["severity"].value_counts().to_string())
print("\n" + "=" * 74)
for _, r in qa.iterrows():
    print(f"[{r['severity']}] {r['source']} :: {r['check']}")
    print(f"    {r['detail']}")
    if r["recommended_action"]:
        print(f"    -> {r['recommended_action']}")
