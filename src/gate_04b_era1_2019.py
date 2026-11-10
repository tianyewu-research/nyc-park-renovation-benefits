"""Earliest available Advan week is 2019. What survives?

era 1 (2019-01 .. 2020-02) is only 60 weeks, so a +/-26wk event window leaves an
8-week reopening band. This asks: (a) what era 1 can still support at narrower
windows, (b) whether era 2 can be split in half for an internal replication
instead, and (c) whether buying 2019-2021 is worth it at all.
"""

import pandas as pd

RAW = "data/raw/capital_projects/capital_project_tracker.csv"
XW = "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv"

MIN_CLOSURE = pd.Timedelta(weeks=8)
CONTAM_WIN = pd.Timedelta(weeks=26)

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
    lo, hi = row["reopen"] - CONTAM_WIN, row["reopen"] + CONTAM_WIN
    return bool(((others["constructionstart"] <= hi) & (others["occ_end"] >= lo)).any())


base["contaminated"] = base.apply(contaminated, axis=1)
base["has_poi"] = base["parkid"].isin(poi_parks)
clean = ~base["contaminated"] & base["has_poi"]


def count(lo, hi, pre_w, post_w):
    pre, post = pd.Timedelta(weeks=pre_w), pd.Timedelta(weeks=post_w)
    okB = (base["reopen"] >= lo + pre) & (base["reopen"] <= hi - post)
    okA = (okB & base["constructionstart"].notna()
           & (base["constructionstart"] >= lo + pre)
           & (base["reopen"] - base["constructionstart"] >= MIN_CLOSURE))
    out = {}
    for d, ok in [("A", okA), ("B", okB)]:
        sel = ok & clean
        out[d] = (int(sel.sum()), int(base.loc[sel, "parkid"].nunique()))
    bl, bh = lo + pre, hi - post
    out["band"] = f"{bl:%Y-%m}..{bh:%Y-%m}" if bh > bl else "EMPTY"
    return out


E1 = (pd.Timestamp("2019-01-07"), pd.Timestamp("2020-02-24"))
E2 = (pd.Timestamp("2022-01-03"), pd.Timestamp("2025-12-29"))

print("=" * 78)
print("(a) ERA 1  2019-01-07 .. 2020-02-24   (60 weeks)")
print("=" * 78)
for pre, post in [(26, 26), (26, 13), (13, 13), (13, 8), (8, 8)]:
    r = count(*E1, pre, post)
    print(f"  pre {pre:>2}wk / post {post:>2}wk | band {r['band']:<18} | "
          f"A {r['A'][0]:>3}/{r['A'][1]:>3} parks | B {r['B'][0]:>3}/{r['B'][1]:>3}")

print()
print("=" * 78)
print("(b) ERA 2  2022-01-03 .. 2025-12-29   (208 weeks)  -- primary")
print("=" * 78)
for pre, post in [(26, 52), (26, 26), (26, 13)]:
    r = count(*E2, pre, post)
    print(f"  pre {pre:>2}wk / post {post:>2}wk | band {r['band']:<18} | "
          f"A {r['A'][0]:>3}/{r['A'][1]:>3} parks | B {r['B'][0]:>3}/{r['B'][1]:>3}")

print()
print("=" * 78)
print("(c) ERA 2 SPLIT-HALF  -- internal replication in place of a lost era 1")
print("=" * 78)
halves = [("H1", pd.Timestamp("2022-01-03"), pd.Timestamp("2023-12-25")),
          ("H2", pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-29"))]
for lab, lo, hi in halves:
    wks = int((hi - lo) / pd.Timedelta(weeks=1))
    for pre, post in [(26, 26), (26, 13)]:
        r = count(lo, hi, pre, post)
        print(f"  {lab} ({wks}wk) pre {pre}/post {post:>2} | band {r['band']:<18} | "
              f"A {r['A'][0]:>3}/{r['A'][1]:>3} parks | B {r['B'][0]:>3}/{r['B'][1]:>3}")

print()
print("=" * 78)
print("(d) Would 2019 data help era 2 by allowing LONGER closures?")
print("    (pre-construction baseline in 2019, reopening in era 2 --")
print("     but such closures straddle COVID, so the closure event is confounded)")
print("=" * 78)
lo2, hi2 = E2
okB = (base["reopen"] >= lo2 + pd.Timedelta(weeks=26)) & \
      (base["reopen"] <= hi2 - pd.Timedelta(weeks=26))
long_closure = (okB & clean & base["constructionstart"].notna()
                & (base["constructionstart"] < lo2 + pd.Timedelta(weeks=26))
                & (base["constructionstart"] >= pd.Timestamp("2019-07-01")))
print(f"  extra design-A-eligible reopenings if pre-2022 baseline allowed: "
      f"{int(long_closure.sum())} projects / {base.loc[long_closure,'parkid'].nunique()} parks")
straddle = long_closure & (base["constructionstart"] <= pd.Timestamp("2021-12-31"))
print(f"    of which the closure straddles the COVID hole (confounded): "
      f"{int(straddle.sum())}")
