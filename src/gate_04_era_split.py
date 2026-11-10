"""Two-era design: how long does era 1 need to be?

Each era is its own panel. A design needs MIN_PRE before and MIN_POST after the
reopening, both inside that era. A short era therefore admits only a narrow band
of reopening dates, regardless of how many projects completed in it.
"""

import pandas as pd

RAW = "data/raw/capital_projects/capital_project_tracker.csv"
XW = "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv"

MIN_CLOSURE = pd.Timedelta(weeks=8)
HALF_WIN = pd.Timedelta(weeks=26)

ERA1_END = pd.Timestamp("2020-02-29")   # last clean pre-COVID week
ERA2 = (pd.Timestamp("2022-01-01"), pd.Timestamp("2025-12-29"))  # post-ATT

allp = pd.read_csv(RAW, low_memory=False)
for c in ["constructionstart", "constructionactualcompletion"]:
    allp[c] = pd.to_datetime(allp[c], errors="coerce")
allp = allp[allp["parkid"].notna()].copy()

occ = allp[allp["constructionstart"].notna()].copy()
occ["occ_end"] = occ["constructionactualcompletion"].fillna(pd.Timestamp("2030-01-01"))
by_park = {k: v for k, v in occ.groupby("parkid")}

xw = pd.read_csv(XW, low_memory=False)
poi_parks = set(xw.loc[xw["matched_pid"].notna(), "matched_pid"].unique())

base = allp[allp["constructionactualcompletion"].notna()].copy()
base["reopen"] = base["constructionactualcompletion"]


def contaminated(row):
    others = by_park.get(row["parkid"])
    if others is None:
        return False
    others = others[others["trackerid"] != row["trackerid"]]
    if others.empty:
        return False
    lo, hi = row["reopen"] - HALF_WIN, row["reopen"] + HALF_WIN
    return bool(((others["constructionstart"] <= hi) & (others["occ_end"] >= lo)).any())


base["contaminated"] = base.apply(contaminated, axis=1)
base["has_poi"] = base["parkid"].isin(poi_parks)
clean = ~base["contaminated"] & base["has_poi"]


def count(lo, hi, half_win_weeks):
    """Projects usable inside a single era with a +/-half_win event window."""
    w = pd.Timedelta(weeks=half_win_weeks)
    okB = (base["reopen"] >= lo + w) & (base["reopen"] <= hi - w)
    okA = (okB & base["constructionstart"].notna()
           & (base["constructionstart"] >= lo + w)
           & (base["reopen"] - base["constructionstart"] >= MIN_CLOSURE))
    out = {}
    for design, ok in [("A", okA), ("B", okB)]:
        sel = ok & clean
        out[design] = (int(sel.sum()), int(base.loc[sel, "parkid"].nunique()))
    band_lo, band_hi = lo + w, hi - w
    out["band"] = f"{band_lo:%Y-%m} .. {band_hi:%Y-%m}" if band_hi > band_lo else "EMPTY"
    return out


print("=" * 74)
print("ERA 2  (post-ATT, 2022-01-01 .. 2025-12-29, 208 weeks)")
print("=" * 74)
for hw in [26, 13]:
    r = count(*ERA2, hw)
    print(f"  +/-{hw:>2}wk window | reopen band {r['band']} | "
          f"design A {r['A'][0]:>3} proj / {r['A'][1]:>3} parks | "
          f"design B {r['B'][0]:>3} / {r['B'][1]:>3}")

print()
print("=" * 74)
print(f"ERA 1  (pre-COVID, START .. {ERA1_END:%Y-%m-%d}) -- length depends on data purchase")
print("=" * 74)
for start in ["2017-01-01", "2018-01-01", "2019-01-01"]:
    lo = pd.Timestamp(start)
    wks = int((ERA1_END - lo) / pd.Timedelta(weeks=1))
    print(f"\n  start {start}  ({wks} weeks)")
    for hw in [26, 13]:
        r = count(lo, ERA1_END, hw)
        print(f"    +/-{hw:>2}wk window | reopen band {r['band']:<22} | "
              f"design A {r['A'][0]:>3} proj / {r['A'][1]:>3} parks | "
              f"design B {r['B'][0]:>3} / {r['B'][1]:>3}")

print("\n" + "=" * 74)
print("READ: era 1 must be long enough that the reopening band is not a sliver.")
print("A +/-26wk window burns one full year of era length before any project qualifies.")
