"""Acceptance checks to run the moment new Advan weeks land.

Five checks, in the order failures are cheapest to fix:

  1 week completeness   no missing weeks; every gap exactly 7 days
  2 expected blocks     the purchased date ranges are actually present
  3 key stability       ID_STORE <-> PERSISTENT_ID_STORE is 1:1 and stable
  4 POI churn           per-week POI counts; size of the balanced set
  5 panel totals        citywide weekly deflator written out, with break scan

A missing week is the expensive one: it puts a spurious step in every park's
series in that week, which an event study will read as a treatment effect.

Usage:
  python3 src/gate_06_download_qa.py [--rebuild]
"""

import argparse
import csv
import gzip
import os
import sys

import numpy as np
import pandas as pd

import lib_advan as la

POI_WEEK = "data/interim/poi_week.csv.gz"
TOTALS = "data/interim/panel_totals_weekly.csv"

# Blocks the design needs; see notes/04_data_acquisition.md
EXPECTED_BLOCKS = {
    "era1 (secondary, design B)": ("2019-01-07", "2020-02-24"),
    "era2 (primary, design A)":   ("2021-07-05", "2025-12-29"),
}

CURRENT_VINTAGE_DIR = "data/raw/advan"


def check_weeks(files):
    weeks = pd.to_datetime(sorted(files))
    print(f"  {len(weeks)} weeks: {weeks.min():%Y-%m-%d} .. {weeks.max():%Y-%m-%d}")
    gaps = pd.Series(weeks).diff().dt.days.dropna()
    bad = gaps[gaps != 7]
    if len(bad) == 0:
        print("  PASS  no gaps, all intervals 7 days")
        return True
    print(f"  FAIL  {len(bad)} non-7-day intervals:")
    for i, g in bad.items():
        print(f"        after {weeks[i - 1]:%Y-%m-%d}: {int(g)} days "
              f"({int(g / 7) - 1} week(s) missing)")
    return False


def check_blocks(files, expected_blocks):
    have = set(files)
    allok = True
    for label, (lo, hi) in expected_blocks.items():
        want = {d.strftime("%Y-%m-%d") for d in pd.date_range(lo, hi, freq="W-MON")}
        missing = sorted(want - have)
        mark = "PASS" if not missing else "FAIL"
        print(f"  {mark}  {label}: {len(want) - len(missing)}/{len(want)} weeks")
        if missing:
            allok = False
            head = ", ".join(missing[:6])
            print(f"        missing {len(missing)}: {head}"
                  f"{' ...' if len(missing) > 6 else ''}")
    return allok


def check_single_vintage_current_dir(expected_blocks):
    """Production weeks must all be present in the current-vintage folder.

    lib_advan may use the archived 2023-2025 pull as a development fallback,
    so coverage alone cannot detect a mixed-vintage panel. This check prevents
    the archive from silently making the production acceptance gate pass.
    """
    current = la.week_files([CURRENT_VINTAGE_DIR])
    expected = set()
    for lo, hi in expected_blocks.values():
        expected.update(d.strftime("%Y-%m-%d")
                        for d in pd.date_range(lo, hi, freq="W-MON"))
    missing = sorted(expected - set(current))
    if missing:
        print(f"  FAIL  current-vintage folder contains "
              f"{len(expected) - len(missing)}/{len(expected)} required weeks")
        print(f"        {len(missing)} required weeks are coming from the archive "
              "or are absent")
        print("        first missing: " + ", ".join(missing[:6]) +
              (" ..." if len(missing) > 6 else ""))
        return False
    print(f"  PASS  all {len(expected)} required weeks are physically present in "
          f"{CURRENT_VINTAGE_DIR}")
    return True


def check_keys(files, sample_n=6):
    """ID_STORE -> PERSISTENT_ID_STORE must be a stable 1:1 map."""
    picks = list(files.values())
    step = max(1, len(picks) // sample_n)
    picks = picks[::step][:sample_n]
    mapping, conflicts, rev = {}, 0, {}
    rev_conflicts = 0
    for path in picks:
        with gzip.open(path, "rt") as f:
            for row in csv.DictReader(f):
                i = row.get("ID_STORE")
                p = row.get("PERSISTENT_ID_STORE") or row.get("PERSISTENT_ID")
                if not i or not p:
                    continue
                if i in mapping and mapping[i] != p:
                    conflicts += 1
                mapping[i] = p
                if p in rev and rev[p] != i:
                    rev_conflicts += 1
                rev[p] = i
    print(f"  sampled {len(picks)} weeks, {len(mapping):,} distinct ID_STORE")
    ok = conflicts == 0 and rev_conflicts == 0
    print(f"  {'PASS' if ok else 'FAIL'}  ID_STORE->PERSISTENT conflicts: {conflicts}; "
          f"reverse conflicts: {rev_conflicts}")
    if not ok:
        print("        -> key on PERSISTENT_ID_STORE, and rebuild the crosswalk")
    return ok


def check_churn(poi_week):
    per_week, balanced = la.poi_churn(poi_week)
    n_weeks = poi_week["week"].nunique()
    total = poi_week["ID_STORE"].nunique()
    cov = len(balanced) / total if total else 0
    print(f"  POIs per week: min {per_week.min():,}  max {per_week.max():,}  "
          f"median {int(per_week.median()):,}")
    print(f"  distinct POIs across panel: {total:,}")
    print(f"  balanced set (present all {n_weeks} weeks): {len(balanced):,} "
          f"({cov:.0%})")
    print(f"  {'PASS' if cov >= 0.90 else 'WARN'}  balanced coverage "
          f"{'>=' if cov >= 0.90 else '<'} 90%")
    print("\n  POIs per week, by year")
    yr = per_week.groupby(per_week.index.year).agg(["min", "max", "mean"]).round(0)
    print("  " + yr.to_string().replace("\n", "\n  "))
    pd.Series(sorted(balanced), name="ID_STORE").to_csv(
        "data/interim/balanced_poi_set.csv", index=False)
    print("\n  wrote data/interim/balanced_poi_set.csv")
    return cov >= 0.90


def check_totals(poi_week):
    city = (poi_week.groupby("week", as_index=False)
            .agg(citywide_dq=("visits_dq", "sum"),
                 citywide_raw=("visits_raw", "sum"),
                 n_poi=("ID_STORE", "nunique"))
            .sort_values("week"))
    city.to_csv(TOTALS, index=False)
    print(f"  wrote {TOTALS}")
    # week-on-week jumps large enough to look like a panel break
    lr = np.log(city["citywide_dq"].clip(lower=1)).diff()
    thr = 0.35   # ~ +42% / -30% in a single week
    big = city.loc[lr.abs() > thr, "week"]
    if len(big):
        print(f"  WARN  {len(big)} week-on-week jumps > {thr} in log citywide "
              f"volume — candidate panel breaks:")
        for w, v in zip(big, lr[lr.abs() > thr]):
            print(f"        {w:%Y-%m-%d}  {v:+.2f} log points")
        print("        seasonal turns can do this; a step that never reverts "
              "is a panel break and must not straddle an era boundary")
    else:
        print(f"  PASS  no week-on-week log jump > {thr}")
    print("\n  citywide dwell-qualified visits, annual mean")
    print("  " + city.assign(y=city["week"].dt.year).groupby("y")["citywide_dq"]
          .mean().round(0).to_string().replace("\n", "\n  "))
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true",
                        help="rebuild POI-week intermediate from weekly extracts")
    parser.add_argument("--scope", choices=["main", "full"], default="main",
                        help=("main checks the 2021-07 to 2025-12 primary panel; "
                              "full also requires the optional 2019 replication"))
    args = parser.parse_args(argv)
    expected_blocks = ({"era2 (primary, design A)":
                        EXPECTED_BLOCKS["era2 (primary, design A)"]}
                       if args.scope == "main" else EXPECTED_BLOCKS)

    files = la.week_files()
    if not files:
        raise SystemExit("no weekly files found; check lib_advan.WEEK_DIRS")

    results = {}
    print("=" * 70)
    print("1. WEEK COMPLETENESS")
    print("=" * 70)
    results["weeks"] = check_weeks(list(files))

    print("\n" + "=" * 70)
    print("2. EXPECTED BLOCKS")
    print("=" * 70)
    results["blocks"] = check_blocks(list(files), expected_blocks)

    print("\n" + "=" * 70)
    print("2B. SINGLE-VINTAGE PRODUCTION FOLDER")
    print("=" * 70)
    results["single_vintage"] = check_single_vintage_current_dir(expected_blocks)

    print("\n" + "=" * 70)
    print("3. POI KEY STABILITY")
    print("=" * 70)
    results["keys"] = check_keys(files)

    if args.rebuild or not os.path.exists(POI_WEEK):
        print("\nbuilding POI x week table...")
        la.build_poi_week(POI_WEEK)
    poi_week = la.load_poi_week(POI_WEEK)

    print("\n" + "=" * 70)
    print("4. POI CHURN")
    print("=" * 70)
    results["churn"] = check_churn(poi_week)

    print("\n" + "=" * 70)
    print("5. PANEL TOTALS / DEFLATOR")
    print("=" * 70)
    results["totals"] = check_totals(poi_week)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    if not all(results.values()):
        print("\nDo not proceed to Phase 2 until every check passes "
              "(see notes/05_workplan.md step 0.7).")


if __name__ == "__main__":
    main()
