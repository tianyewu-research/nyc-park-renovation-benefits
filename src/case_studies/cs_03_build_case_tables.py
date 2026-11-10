"""Step 3 — per-case structured tables from the existing atlas data. Read-only."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
import pandas as pd

D = os.path.join(C.INTERIM, "tables"); os.makedirs(D, exist_ok=True)
qa = []
def q(check, expect, observed, note=""):
    st = "Passed" if str(expect) == str(observed) else "Discrepancy"
    qa.append(dict(area="coverage", check=check, expected=expect, observed=observed,
                   status=st, note=note))

trk = pd.read_csv(C.p("tracker"), low_memory=False)
pip_i = pd.read_csv(C.p("pip_insp"), low_memory=False)
pip_v = pd.read_csv(C.p("pip_inv"), low_memory=False)
spev = pd.read_csv(C.p("sp_events"), low_memory=False)
xw = pd.read_csv(C.p("crosswalk"), dtype={"ID_STORE": str}, low_memory=False)

EXPECT = {"BP": dict(trk=0, inv=31, insp=51, poi=1, ev=0),
          "WSP": dict(trk=1, inv=85, insp=248, poi=6, ev=44),
          "MCP": dict(trk=10, inv=153, insp=458, poi=9, ev=322)}

def sel(df, col, pid, how):
    s = df[col].astype(str)
    return df[s == pid] if how == "exact" else df[s.str.startswith(pid)]

for cid, cfg in C.CASES.items():
    pid, how = cfg["park_id"], cfg["pip_match"]
    e = EXPECT[cid]

    t = trk[trk["parkid"].astype(str) == pid].copy()
    t.to_csv(f"{D}/{cid}_tracker.csv", index=False)
    q(f"{cid} tracker records (exact parkid)", e["trk"], len(t))

    iv = sel(pip_v, "prop_id", pid, how); iv.to_csv(f"{D}/{cid}_pip_inventory.csv", index=False)
    q(f"{cid} PIP inventory ({how})", e["inv"], len(iv))

    ii = sel(pip_i, "prop_id", pid, how).copy()
    ii["date"] = pd.to_datetime(ii["date"], errors="coerce")
    ii = ii.sort_values("date"); ii.to_csv(f"{D}/{cid}_pip_inspections.csv", index=False)
    q(f"{cid} PIP inspections ({how})", e["insp"], len(ii))

    col = "matched_pid"
    pois = xw[(xw[col].astype(str) == pid) & (xw["analytic_eligible"] == True)]
    pois[["ID_STORE", col]].to_csv(f"{D}/{cid}_advan_pois.csv", index=False)
    q(f"{cid} Advan matched POIs", e["poi"], len(pois))

    # events: match on free-text location, then report so the match can be audited
    key = {"BP": "bryant", "WSP": "washington square", "MCP": "mccarren"}[cid]
    ev = spev[spev.astype(str).apply(
        lambda r: key in " ".join(r.values).lower(), axis=1)].copy()
    ev.to_csv(f"{D}/{cid}_special_events.csv", index=False)
    q(f"{cid} Parks special events (text match '{key}')", e["ev"], len(ev),
      "free-text match; audit before use")

pw = pd.read_csv(C.p("poi_week"), dtype={"ID_STORE": str}, low_memory=False)
pw["week"] = pd.to_datetime(pw["week"])
q("Advan processed weeks", 157, pw["week"].nunique())
q("Advan coverage start", "2023-01-02", pw["week"].min().strftime("%Y-%m-%d"))
q("Advan coverage end", "2025-12-29", pw["week"].max().strftime("%Y-%m-%d"))

for key, lbl, exp in (("mcp_att_old", "jvwx-xnsr", 378), ("mcp_att_new", "82jf-bykm", 620)):
    d = pd.read_csv(C.p(key), low_memory=False)
    d.to_csv(f"{D}/MCP_attendance_{lbl}.csv", index=False)
    q(f"McCarren {lbl}.csv rows", exp, len(d))

pd.DataFrame(qa).to_csv(f"{D}/coverage_qa.csv", index=False)
d = pd.DataFrame(qa)
print(d[["check", "expected", "observed", "status"]].to_string(index=False))
print(f"\n{int((d.status=='Passed').sum())}/{len(d)} coverage checks match expectation")
