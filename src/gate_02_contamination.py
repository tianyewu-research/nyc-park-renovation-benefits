"""Refine the gate: gate_01's multi_project_park flag is over-strict — it fires
on any other project at the park across 2013-2026. What actually contaminates a
design is another project whose CONSTRUCTION overlaps the event window.

Also profiles funding size and scope text for the surviving sample.
"""

import pandas as pd

RAW = "data/raw/capital_projects/capital_project_tracker.csv"
CAND = "data/interim/candidate_projects.csv"
OUT = "data/interim/candidate_projects_clean.csv"

EVENT_HALF_WINDOW = pd.Timedelta(weeks=26)

allp = pd.read_csv(RAW, low_memory=False)
for c in ["constructionstart", "constructionactualcompletion"]:
    allp[c] = pd.to_datetime(allp[c], errors="coerce")
# a project occupies its park whenever it is under construction; for projects
# still in progress treat the occupation as open-ended from the start date
allp = allp[allp["constructionstart"].notna() & allp["parkid"].notna()].copy()
allp["occ_end"] = allp["constructionactualcompletion"].fillna(pd.Timestamp("2030-01-01"))

cand = pd.read_csv(CAND, low_memory=False)
for c in ["constructionstart", "reopen"]:
    cand[c] = pd.to_datetime(cand[c], errors="coerce")

by_park = {k: v for k, v in allp.groupby("parkid")}


def contaminated(row):
    """Another project at the same park under construction inside the event window."""
    others = by_park.get(row["parkid"])
    if others is None:
        return False
    others = others[others["trackerid"] != row["trackerid"]]
    if others.empty:
        return False
    lo = row["reopen"] - EVENT_HALF_WINDOW
    hi = row["reopen"] + EVENT_HALF_WINDOW
    return bool(((others["constructionstart"] <= hi) & (others["occ_end"] >= lo)).any())


cand["contaminated"] = cand.apply(contaminated, axis=1)
cand["clean_B"] = cand["pass_B"] & ~cand["contaminated"]
cand["clean_A"] = cand["pass_A"] & ~cand["contaminated"]

print("=" * 62)
print("REFINED FUNNEL  (contamination = concurrent construction, same park)")
print("=" * 62)
for lab, raw_col, clean_col in [("B", "pass_B", "clean_B"), ("A", "pass_A", "clean_A")]:
    n_raw, n_cl = cand[raw_col].sum(), cand[clean_col].sum()
    parks = cand.loc[cand[clean_col], "parkid"].nunique()
    print(f"design {lab}:  {n_raw:>4} projects -> {n_cl:>4} uncontaminated  "
          f"({parks} unique parks)")

print("\nfunding size, uncontaminated design A")
print(cand.loc[cand["clean_A"], "totalfunding"].value_counts().to_string())

print("\nborough, uncontaminated design A")
print(cand.loc[cand["clean_A"], "borough"].value_counts().to_string())

print("\nclosure length (weeks), uncontaminated design A")
print(cand.loc[cand["clean_A"], "closure_weeks"].describe().round(1).to_string())

print("\nscope keywords in title, uncontaminated design A")
titles = cand.loc[cand["clean_A"], "title"].fillna("").str.lower()
for kw in ["playground", "reconstruction", "renovation", "field", "court",
           "track", "pool", "comfort station", "path", "greenstreet",
           "building", "roof", "fence", "lighting", "tree", "seawall"]:
    n = titles.str.contains(kw).sum()
    if n:
        print(f"  {kw:<16} {n:>4}")

cand.to_csv(OUT, index=False)
print(f"\nwrote {OUT}")
