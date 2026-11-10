"""Feasibility gate: how many NYC Parks capital projects have usable
pre/closure/post windows inside the Advan panel (2023-01-02 .. 2025-12-29)?

Outputs data/interim/candidate_projects.csv and prints the funnel.
See notes/02_feasibility_gate.md for the decision rule.
"""

import pandas as pd

RAW = "data/raw/capital_projects/capital_project_tracker.csv"
OUT = "data/interim/candidate_projects.csv"

PANEL_START = pd.Timestamp("2023-01-02")
PANEL_END = pd.Timestamp("2025-12-29")
MIN_PRE = pd.Timedelta(weeks=26)
MIN_POST = pd.Timedelta(weeks=26)
MIN_CLOSURE = pd.Timedelta(weeks=8)

df = pd.read_csv(RAW, low_memory=False)
for c in ["constructionstart", "constructionactualcompletion",
          "constructionadjustedcompletion", "designactualcompletion"]:
    df[c] = pd.to_datetime(df[c], errors="coerce")

print(f"total projects in tracker                     {len(df):>6}")
print(f"  with parkid                                 {df['parkid'].notna().sum():>6}")
print(f"  with construction actual completion         {df['constructionactualcompletion'].notna().sum():>6}")
print(f"  with construction start                     {df['constructionstart'].notna().sum():>6}")
print(f"  with both start and actual completion       "
      f"{(df['constructionstart'].notna() & df['constructionactualcompletion'].notna()).sum():>6}")

print("\ncompletion-date distribution by year")
print(df["constructionactualcompletion"].dt.year.value_counts().sort_index().to_string())

print("\ncurrentphase")
print(df["currentphase"].value_counts(dropna=False).to_string())

# ---- funnel -------------------------------------------------------------
d = df[df["constructionactualcompletion"].notna() & df["parkid"].notna()].copy()
n0 = len(d)

# one park may host several projects; overlapping treatments are ambiguous
proj_per_park = d.groupby("parkid")["trackerid"].transform("size")
d["multi_project_park"] = proj_per_park > 1

d["reopen"] = d["constructionactualcompletion"]
d["pre_weeks"] = (d["reopen"] - PANEL_START) / pd.Timedelta(weeks=1)
d["post_weeks"] = (PANEL_END - d["reopen"]) / pd.Timedelta(weeks=1)
d["closure_weeks"] = (d["reopen"] - d["constructionstart"]) / pd.Timedelta(weeks=1)
d["pre_construction_weeks"] = (d["constructionstart"] - PANEL_START) / pd.Timedelta(weeks=1)

# Design B: >=26wk before reopening and >=26wk after, both inside the panel
d["pass_B"] = (d["reopen"] >= PANEL_START + MIN_PRE) & (d["reopen"] <= PANEL_END - MIN_POST)

# Design A: additionally needs a clean pre-CONSTRUCTION baseline and an
# observable closure of at least 8 weeks
d["pass_A"] = (
    d["pass_B"]
    & d["constructionstart"].notna()
    & (d["constructionstart"] >= PANEL_START + MIN_PRE)
    & (d["reopen"] - d["constructionstart"] >= MIN_CLOSURE)
)

print("\n" + "=" * 60)
print("FUNNEL")
print("=" * 60)
print(f"projects with completion date + parkid        {n0:>6}")
print(f"  reopening inside panel with 26wk pre/post   {d['pass_B'].sum():>6}   <- N_B (design B)")
print(f"    of which park has only this one project   {(d['pass_B'] & ~d['multi_project_park']).sum():>6}")
print(f"  + construction start inside panel, >=8wk    {d['pass_A'].sum():>6}   <- N_A (design A)")
print(f"    of which park has only this one project   {(d['pass_A'] & ~d['multi_project_park']).sum():>6}")

print(f"\nunique parks  N_B: {d.loc[d['pass_B'], 'parkid'].nunique():>4}"
      f"   N_A: {d.loc[d['pass_A'], 'parkid'].nunique():>4}")

if d["pass_A"].any():
    print("\nclosure length among N_A (weeks)")
    print(d.loc[d["pass_A"], "closure_weeks"].describe().round(1).to_string())

cols = ["trackerid", "parkid", "name", "title", "summary", "borough",
        "constructionstart", "reopen", "pre_weeks", "post_weeks",
        "closure_weeks", "pre_construction_weeks", "multi_project_park",
        "pass_B", "pass_A", "totalfunding", "fundingsource",
        "latitude", "longitude"]
d[cols].sort_values("reopen").to_csv(OUT, index=False)
print(f"\nwrote {OUT}  ({len(d)} rows)")
