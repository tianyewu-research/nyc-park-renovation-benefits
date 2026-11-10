"""Shared Advan weekly-patterns loader.

The dwell rule here is copied from the LPUR paper's pipeline
(../paper_walkability/src/14_process_mobile_visits.py) so the two papers use the
same visit definition: keep the share of visit-time in >=5-minute dwell buckets
and scale VISIT_COUNTS/VISITOR_COUNTS by it. Sub-5-minute traffic is geofence
pass-through, not park use.

No pyarrow in this environment, so intermediates are gzipped CSV.
"""

import glob
import gzip
import json
import os
import re
from collections import defaultdict

import pandas as pd

# Weekly extracts live in two local project folders. Newly purchased/current-
# vintage files take precedence; the copied 2023-2025 archive is only a
# provisional fallback for pipeline development and must never be mistaken for
# the final single-vintage production panel.
WEEK_DIRS = [
    "data/raw/advan",
    "data/raw/advan_vintage_202606",
]

DWELL_KEEP = ("5-20", "21-60", "61-240", ">240")
WEEK_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

CROSSWALK = "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv"


def dwell_qualified_fraction(bucket_json):
    """Share of a POI-week's visit-time in >=5-min buckets. 1.0 if unparseable."""
    if not bucket_json or not isinstance(bucket_json, str):
        return 1.0
    try:
        b = json.loads(bucket_json)
    except (json.JSONDecodeError, TypeError):
        return 1.0
    if not isinstance(b, dict):
        return 1.0
    total = sum(v for v in b.values() if isinstance(v, (int, float)))
    if total <= 0:
        return 1.0
    return sum(b.get(k, 0) for k in DWELL_KEEP) / total


def week_files(dirs=None):
    """Map week-start date string -> file path, across all extract directories.

    Later directories lose to earlier ones on collision, so put the current
    vintage first in WEEK_DIRS.
    """
    dirs = dirs or WEEK_DIRS
    found = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, "*.csv.gz"))):
            m = WEEK_RE.search(os.path.basename(path))
            if m and m.group(1) not in found:
                found[m.group(1)] = path
    return dict(sorted(found.items()))


def load_week(path):
    """One week -> DataFrame[ID_STORE, visits_raw, visitors_raw, visits_dq]."""
    rows = []
    with gzip.open(path, "rt") as f:
        import csv
        for row in csv.DictReader(f):
            sid = row.get("ID_STORE")
            if not sid:
                continue
            try:
                v = float(row.get("VISIT_COUNTS") or 0)
                n = float(row.get("VISITOR_COUNTS") or 0)
            except ValueError:
                continue
            q = dwell_qualified_fraction(row.get("BUCKETED_DWELL_TIMES"))
            rows.append((sid, v, n, v * q))
    return pd.DataFrame(rows, columns=["ID_STORE", "visits_raw",
                                       "visitors_raw", "visits_dq"])


def build_poi_week(out="data/interim/poi_week.csv.gz", dirs=None, verbose=True):
    """Collapse every weekly file to a POI x week table. Idempotent: rebuilds."""
    files = week_files(dirs)
    if not files:
        raise SystemExit("no weekly files found; check WEEK_DIRS")
    parts = []
    for i, (week, path) in enumerate(files.items(), 1):
        df = load_week(path)
        df["week"] = week
        parts.append(df)
        if verbose and (i % 25 == 0 or i == len(files)):
            print(f"  {i}/{len(files)} weeks", flush=True)
    out_df = pd.concat(parts, ignore_index=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    out_df.to_csv(out, index=False, compression="gzip")
    if verbose:
        print(f"wrote {out}  ({len(out_df):,} POI-weeks, "
              f"{out_df['ID_STORE'].nunique():,} POIs, {len(files)} weeks)")
    return out_df


def load_poi_week(path="data/interim/poi_week.csv.gz"):
    df = pd.read_csv(path, dtype={"ID_STORE": str}, low_memory=False)
    df["week"] = pd.to_datetime(df["week"])
    return df


def load_crosswalk(path=CROSSWALK, radius="100ft"):
    """ID_STORE -> parkid (Parks property id), analytic-eligible POIs only."""
    col = "matched_pid" if radius == "100ft" else "matched_pid_328ft"
    xw = pd.read_csv(path, dtype={"ID_STORE": str}, low_memory=False)
    xw = xw[xw[col].notna() & (xw["analytic_eligible"] == True)]  # noqa: E712
    return xw[["ID_STORE", col]].rename(columns={col: "parkid"})


def park_week(poi_week=None, xw=None):
    """POI x week -> park x week, plus the citywide weekly deflator.

    citywide_dq is computed over ALL park POIs in the extract, not just the
    analysis sample, so it stays a stable panel-volume denominator.
    """
    poi_week = load_poi_week() if poi_week is None else poi_week
    city = (poi_week.groupby("week", as_index=False)["visits_dq"]
            .sum().rename(columns={"visits_dq": "citywide_dq"}))
    xw = load_crosswalk() if xw is None else xw
    m = poi_week.merge(xw, on="ID_STORE", how="inner")
    pw = (m.groupby(["parkid", "week"], as_index=False)
          .agg(visits_dq=("visits_dq", "sum"),
               visits_raw=("visits_raw", "sum"),
               n_poi=("ID_STORE", "nunique")))
    pw = pw.merge(city, on="week", how="left")
    # deflated series: removes panel-size drift AND the citywide seasonal cycle,
    # both of which otherwise masquerade as treatment effects
    pw["visits_defl"] = pw["visits_dq"] / pw["citywide_dq"] * 1e6
    return pw, city


def poi_churn(poi_week=None):
    """Per-week POI counts and the balanced set (present every week)."""
    poi_week = load_poi_week() if poi_week is None else poi_week
    per_week = poi_week.groupby("week")["ID_STORE"].nunique()
    seen = poi_week.groupby("ID_STORE")["week"].nunique()
    balanced = set(seen[seen == poi_week["week"].nunique()].index)
    return per_week, balanced
