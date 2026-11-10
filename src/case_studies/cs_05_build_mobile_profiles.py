"""Step 5 — Advan profiles. Vintage 202606, coverage 2023-2025 (post-renovation for all
three cases). Used to describe CURRENT use, never renovation effect."""
import csv, gzip, json, os, re, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
import pandas as pd

D = os.path.join(C.INTERIM, "mobile"); os.makedirs(D, exist_ok=True)
T = os.path.join(C.INTERIM, "tables")
POI = {cid: set(pd.read_csv(f"{T}/{cid}_advan_pois.csv", dtype={"ID_STORE": str})["ID_STORE"])
       for cid in C.CASES}
ALL = {s: cid for cid, ss in POI.items() for s in ss}
print({cid: len(s) for cid, s in POI.items()})

# ---- weekly index from the processed table --------------------------------
pw = pd.read_csv(C.p("poi_week"), dtype={"ID_STORE": str}, low_memory=False)
pw["week"] = pd.to_datetime(pw["week"])
pw["case_id"] = pw["ID_STORE"].map(ALL)
wk = (pw[pw.case_id.notna()].groupby(["case_id", "week"], as_index=False)
      .agg(visits_dq=("visits_dq", "sum"), n_poi=("ID_STORE", "nunique")))
full = pd.MultiIndex.from_product([list(C.CASES), sorted(pw.week.unique())],
                                  names=["case_id", "week"]).to_frame(index=False)
wk = full.merge(wk, on=["case_id", "week"], how="left")
wk["missing_week"] = wk["visits_dq"].isna()
out = []
for cid, g in wk.groupby("case_id"):
    g = g.sort_values("week").copy()
    base = g.loc[g.week.dt.year == 2023, "visits_dq"].median()
    g["index_2023med100"] = g["visits_dq"] / base * 100
    g["index_roll4"] = g["index_2023med100"].rolling(4, center=True, min_periods=2).median()
    g["baseline_2023_median_visits_dq"] = base
    out.append(g)
wk = pd.concat(out, ignore_index=True)
wk.to_csv(f"{D}/weekly_visit_index.csv", index=False)
mo = (wk.assign(month=wk.week.dt.month, year=wk.week.dt.year)
        .groupby(["case_id", "month"], as_index=False)
        .agg(median_index=("index_2023med100", "median"),
             n_weeks=("index_2023med100", "count")))
mo.to_csv(f"{D}/seasonal_profile_month.csv", index=False)
print(f"weekly index: {len(wk)} rows | missing weeks: "
      f"{wk.groupby('case_id').missing_week.sum().to_dict()}")

# ---- visitor-home origins, streamed and filtered before JSON parsing -------
def load_geoid_to_nta():
    cbg = pd.read_csv(C.p("acs"), dtype={"GEOID": str})[["GEOID"]]
    nta = None
    try:
        import geopandas as gpd
        n = gpd.read_file(C.p("atlas_r4"), layer="boroughs")   # fallback label only
    except Exception:
        pass
    return cbg
acc = {cid: {} for cid in C.CASES}
files = sorted([f for f in os.listdir(C.p("advan_dir")) if f.endswith(".csv.gz")])
print(f"streaming {len(files)} weekly Advan files (filtering to case POIs first) ...")
for i, fn in enumerate(files, 1):
    with gzip.open(os.path.join(C.p("advan_dir"), fn), "rt") as fh:
        for row in csv.DictReader(fh):
            sid = row.get("ID_STORE")
            cid = ALL.get(sid)
            if cid is None:
                continue                      # filter BEFORE touching JSON
            raw = row.get("VISITOR_HOME_CBGS") or ""
            if not raw.strip():
                continue
            try:
                d = json.loads(raw)
            except Exception:
                continue
            for geoid, n in d.items():
                if isinstance(n, (int, float)):
                    acc[cid][geoid] = acc[cid].get(geoid, 0) + float(n)
    if i % 40 == 0: print(f"  {i}/{len(files)}", flush=True)

rows = [dict(case_id=cid, home_geoid=g, provider_home_count=v)
        for cid, d in acc.items() for g, v in d.items()]
org = pd.DataFrame(rows)
org.to_csv(f"{D}/visitor_home_cbg_raw.csv", index=False)
print(f"origin rows: {len(org)} | per case: {org.groupby('case_id').size().to_dict()}")

# aggregate to borough for public figures; keep CBG file internal only
acs = pd.read_csv(C.p("acs"), dtype={"GEOID": str}, low_memory=False)
org["GEOID"] = org["home_geoid"].astype(str).str.zfill(12)
m = org.merge(acs, on="GEOID", how="left")
BORO = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}
m["boro"] = m["GEOID"].str[2:5].map(BORO).fillna("Outside NYC / unmatched")
bor = (m.groupby(["case_id", "boro"], as_index=False)["provider_home_count"].sum())
bor["share"] = bor.groupby("case_id")["provider_home_count"].transform(lambda s: s / s.sum() * 100)
bor.to_csv(f"{D}/visitor_origin_by_borough.csv", index=False)

# ACS composition of visitor-origin areas, weighted by provider home counts
comp = []
for cid, g in m.groupby("case_id"):
    g = g[g["pct_white_nh"].notna()]
    w = g["provider_home_count"]
    comp.append(dict(case_id=cid, matched_home_count=float(w.sum()),
                     n_origin_cbg=int(g["GEOID"].nunique()),
                     **{c: round(float((g[c] * w).sum() / w.sum()) * 100, 1)
                        for c in ("pct_white_nh", "pct_black", "pct_asian", "pct_hispanic")}))
pd.DataFrame(comp).to_csv(f"{D}/origin_area_acs_composition.csv", index=False)
print(pd.DataFrame(comp).to_string(index=False))
print("\nNOTE: this is the ACS composition of visitor-ORIGIN AREAS, weighted by "
      "provider-estimated home-CBG counts. It is not the race of visitors.")
