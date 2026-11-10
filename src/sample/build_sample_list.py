"""Sample list v1 (2026-10-05). Rules: >=26wk mobility coverage before construction start and after
completion (Tracker admin dates), no other DPR project in same park within +/-26wk, not infrastructure-only
(title keywords), park matched to a balanced Advan POI. 52wk flag for robustness. No funding threshold.
status: confirmed = passes with current 2023-2025 panel; pending = passes only if 2019-2022 data arrive."""
import pandas as pd, pathlib, datetime as dt
R = pathlib.Path(__file__).resolve().parents[2]
t = pd.read_csv(R/"data/raw/capital_projects/capital_project_tracker.csv", dtype=str)
t["cs"] = pd.to_datetime(t.constructionstart)
t["ce"] = pd.to_datetime(t.constructionactualcompletion.fillna(t.constructionadjustedcompletion))
u = t.drop_duplicates("trackerid").dropna(subset=["cs", "ce"]).copy()
INFRA = r"Roof|Filtration|Filter|Electrical|Plumbing|Boiler|HVAC|Condenser|Citywide|General Site Work|Seawall|Retaining Wall|Water Service|Generator|Elevator|Office|Garage|Expansion Joint|Structural|Sewer|Tower|Bridge"
u = u[~u.title.str.contains(INFRA, case=False)]
xw = pd.read_csv(R/"data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv", dtype=str)
bal = set(pd.read_csv(R/"data/interim/balanced_poi_set.csv", dtype=str).ID_STORE)
xw = xw[(xw.match_status == "matched") & xw.ID_STORE.isin(bal)]
npoi = xw.groupby("matched_pid").ID_STORE.nunique()
u["n_poi"] = u.parkid.map(npoi).fillna(0).astype(int)
tt = t.dropna(subset=["cs"])
P = lambda *a: [(pd.Timestamp(x), pd.Timestamp(y)) for x, y in a]
NOW = P(("2023-01-02", "2025-12-29"))
EXP = P(("2019-01-07", "2020-03-01"), ("2021-07-05", "2025-12-29"))
cov = lambda a, b, S: any(a >= s and b <= e for s, e in S)
def flags(wk, S):
    W = pd.Timedelta(weeks=wk)
    def ok(r):
        o = tt[(tt.parkid == r.parkid) & (tt.trackerid != r.trackerid)]
        clean = not ((o.cs <= r.ce + W) & (o.ce.fillna(pd.Timestamp("2030")) >= r.cs - W)).any()
        return clean and cov(r.cs - W, r.cs, S) and cov(r.ce, r.ce + W, S)
    return u.apply(ok, axis=1)
u["ok26_now"], u["ok26_exp"] = flags(26, NOW), flags(26, EXP)
u["ok52_now"], u["ok52_exp"] = flags(52, NOW), flags(52, EXP)
u["status"] = "out"
u.loc[u.ok26_exp, "status"] = "pending"
u.loc[u.ok26_now & (u.n_poi > 0), "status"] = "confirmed"
s = u[u.status != "out"].copy()
s["funding_usd"] = pd.to_numeric(s.totalfunding.str.replace(r"[\$,]", "", regex=True), errors="coerce")
s["robust52"] = s.ok52_now | s.ok52_exp
s["url"] = "https://www.nycgovparks.org/planning-and-building/capital-project-tracker/project/" + s.trackerid
cols = ["status","trackerid","fmsid","title","parkid","name","borough","cs","ce","totalfunding","funding_usd","fundingsource","n_poi","robust52","summary","url"]
s = s.sort_values(["status","borough","ce"])[cols].rename(columns={"cs":"construction_start","ce":"construction_completion_admin","name":"location_name"})
s["built"] = dt.date.today().isoformat(); s["tracker_snapshot"] = t.lastupdated.max()[:10]
s.to_csv(R/"data/interim/sample/sample_list_v1.csv", index=False)
print(s.status.value_counts().to_dict(), "| robust52 confirmed:", int((s.robust52 & (s.status=="confirmed")).sum()))
