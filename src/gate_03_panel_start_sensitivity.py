"""How much sample does an earlier panel start actually buy?

Re-runs the gate across candidate panel start dates, with and without
excluding events whose window overlaps the COVID period.
"""

import pandas as pd

RAW = "data/raw/capital_projects/capital_project_tracker.csv"
XW = "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv"

PANEL_END = pd.Timestamp("2025-12-29")
MIN_PRE = pd.Timedelta(weeks=26)
MIN_POST = pd.Timedelta(weeks=26)
MIN_CLOSURE = pd.Timedelta(weeks=8)
HALF_WIN = pd.Timedelta(weeks=26)

# NYC park use was structurally abnormal here: closures, then parks as the only
# open amenity, then uneven recovery. Also brackets the April 2021 iOS ATT
# rollout, which cut location-panel size sharply.
COVID_LO = pd.Timestamp("2020-03-01")
COVID_HI = pd.Timestamp("2021-12-31")

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
base["covid_overlap"] = ((base["reopen"] - HALF_WIN) <= COVID_HI) & \
                        ((base["reopen"] + HALF_WIN) >= COVID_LO)

rows = []
for start in ["2017-01-01", "2018-01-01", "2019-01-01", "2020-01-01", "2023-01-02"]:
    ps = pd.Timestamp(start)
    d = base.copy()
    okB = (d["reopen"] >= ps + MIN_PRE) & (d["reopen"] <= PANEL_END - MIN_POST)
    okA = (okB & d["constructionstart"].notna()
           & (d["constructionstart"] >= ps + MIN_PRE)
           & (d["reopen"] - d["constructionstart"] >= MIN_CLOSURE))
    clean = ~d["contaminated"] & d["has_poi"]
    for design, ok in [("B", okB), ("A", okA)]:
        sel = ok & clean
        rows.append({
            "panel_start": start,
            "weeks": int((PANEL_END - ps) / pd.Timedelta(weeks=1)),
            "design": design,
            "projects": int(sel.sum()),
            "parks": int(d.loc[sel, "parkid"].nunique()),
            "proj_excl_covid": int((sel & ~d["covid_overlap"]).sum()),
            "parks_excl_covid": int(d.loc[sel & ~d["covid_overlap"], "parkid"].nunique()),
        })

r = pd.DataFrame(rows)
print("Sample as a function of panel start (PANEL_END fixed at 2025-12-29)")
print("'excl covid' drops events whose +/-26wk window touches 2020-03..2021-12\n")
for design in ["A", "B"]:
    print(f"--- design {design} ---")
    print(r[r["design"] == design][
        ["panel_start", "weeks", "projects", "parks",
         "proj_excl_covid", "parks_excl_covid"]].to_string(index=False))
    print()

r.to_csv("data/interim/panel_start_sensitivity.csv", index=False)
print("wrote data/interim/panel_start_sensitivity.csv")
