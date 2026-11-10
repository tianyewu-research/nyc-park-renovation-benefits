"""Validate treatment dates against the visit series.

The tracker's constructionactualcompletion is an administrative milestone, not
the day the gates reopened. This finds, for each candidate project:

  reopen_empirical   the week where deflated visits step from a low to a high
                     regime, scanned within +/-26 weeks of the admin date
  closure_depth      median deflated visits during the stated closure, divided
                     by the pre-construction baseline. ~1.0 means the park never
                     actually closed.
  offset_weeks       reopen_empirical - constructionactualcompletion

Decision rules (pre-specified in notes/03_research_design.md):
  - admin date is the main-analysis treatment date; empirical date is a
    robustness check
  - |offset| > 8 weeks  -> drop from the main sample, log for manual review
  - closure_depth > 0.7 -> "no real closure", moved to a separate stratum

Series are deflated by citywide dwell-qualified park visits, which removes both
panel-size drift and the citywide seasonal cycle. Without that, a spring
reopening looks like a treatment effect.

Usage:
  python3 src/gate_05_validate_dates.py [--rebuild]
"""

import os
import sys

import numpy as np
import pandas as pd

import lib_advan as la

CAND = "data/interim/candidate_projects_clean.csv"
POI_WEEK = "data/interim/poi_week.csv.gz"
OUT = "outputs/tables/date_validation.csv"

MIN_SIDE = 6       # need at least this many observed weeks on each side
BASELINE = 26      # pre-construction baseline length, weeks
DEPTH_CUTOFF = 0.7   # above this, the park did not meaningfully close
OFFSET_CUTOFF = 8    # weeks; beyond this the admin date is not trustworthy
RECOVER_FRAC = 0.5   # "reopened" = back above this share of pre-construction level
CONFIRM_OF = (3, 4)  # ...for 3 of the next 4 weeks, so a spike does not count
MIN_BASELINE_DQ = 50   # weekly dwell-qualified visits; below this the series is
                       # noise-dominated and closure_depth is not interpretable


def detect_recovery(s, cs, admin_week, baseline_level):
    """Find where the series climbs back out of the closure trough.

    Visit series during a real closure collapse to a floor and then step back up,
    so a max-t scan is the wrong tool: it chases noise spikes and pins itself to
    the edge of the scan window. Instead walk forward from the deepest week of
    the stated closure and take the first week that recovers to RECOVER_FRAC of
    the pre-construction level and stays there.

    Returns (recovery_week, trough_week) or (None, trough_week).
    """
    if not np.isfinite(baseline_level) or baseline_level <= 0:
        return None, None
    during = s[(s.index >= cs) & (s.index < admin_week)]
    if len(during) < MIN_SIDE:
        return None, None
    trough = during.idxmin()

    thr = RECOVER_FRAC * baseline_level
    need, of = CONFIRM_OF
    after = s[s.index >= trough]
    vals = after.values
    for i, w in enumerate(after.index):
        window = vals[i:i + of]
        if len(window) < of:
            break
        if vals[i] >= thr and (window >= thr).sum() >= need:
            return w, trough
    return None, trough


def main():
    if "--rebuild" in sys.argv or not os.path.exists(POI_WEEK):
        print("building POI x week table from weekly extracts...")
        la.build_poi_week(POI_WEEK)

    pw, city = la.park_week(la.load_poi_week(POI_WEEK))
    covered = (pw["week"].min(), pw["week"].max())
    print(f"panel covers {covered[0]:%Y-%m-%d} .. {covered[1]:%Y-%m-%d} "
          f"({pw['week'].nunique()} weeks, {pw['parkid'].nunique()} parks)")

    cand = pd.read_csv(CAND, low_memory=False)
    for c in ["constructionstart", "reopen"]:
        cand[c] = pd.to_datetime(cand[c], errors="coerce")

    series = {k: v.set_index("week")["visits_defl"].sort_index()
              for k, v in pw.groupby("parkid")}
    raw_series = {k: v.set_index("week")["visits_dq"].sort_index()
                  for k, v in pw.groupby("parkid")}

    rows = []
    for _, r in cand.iterrows():
        s = series.get(r["parkid"])
        rec = {"trackerid": r["trackerid"], "parkid": r["parkid"],
               "name": r["name"], "title": r["title"],
               "constructionstart": r["constructionstart"],
               "admin_reopen": r["reopen"],
               "clean_A": r.get("clean_A"), "clean_B": r.get("clean_B")}

        if s is None or s.empty:
            rec["status"] = "no_series"
            rows.append(rec)
            continue

        # is the event window actually inside the weeks we hold?
        if not (s.index.min() <= r["reopen"] <= s.index.max()):
            rec["status"] = "outside_panel"
            rec["n_weeks"] = len(s)
            rows.append(rec)
            continue

        # closure depth relative to a pre-construction baseline
        cs = r["constructionstart"]
        base_level = np.nan
        if pd.notna(cs):
            base = s[(s.index >= cs - pd.Timedelta(weeks=BASELINE)) & (s.index < cs)]
            during = s[(s.index >= cs) & (s.index < r["reopen"])]
            if len(base) >= MIN_SIDE and len(during) >= MIN_SIDE:
                base_level = base.median()
                rec["baseline_defl"] = base_level
                rec["closure_defl"] = during.median()
                rec["closure_depth"] = (float(during.median() / base_level)
                                        if base_level > 0 else np.nan)
            rec["n_baseline_weeks"] = len(base)
            rec["n_closure_weeks"] = len(during)

        # raw volume floor: below this the series is noise and depth is meaningless
        raw = raw_series.get(r["parkid"])
        if raw is not None and pd.notna(cs):
            rb = raw[(raw.index >= cs - pd.Timedelta(weeks=BASELINE)) & (raw.index < cs)]
            rec["baseline_dq"] = rb.median() if len(rb) else np.nan

        if pd.notna(cs) and np.isfinite(base_level):
            rw, trough = detect_recovery(s, cs, r["reopen"], base_level)
            rec["trough_week"] = trough
            rec["reopen_empirical"] = rw
            rec["offset_weeks"] = ((rw - r["reopen"]).days / 7) if rw is not None else np.nan

        rec["status"] = "ok"
        rows.append(rec)

    out = pd.DataFrame(rows)
    out["low_volume"] = out.get("baseline_dq", pd.Series(dtype=float)) < MIN_BASELINE_DQ
    out["date_ok"] = out["offset_weeks"].abs() <= OFFSET_CUTOFF
    out["real_closure"] = (out["closure_depth"] <= DEPTH_CUTOFF) & ~out["low_volume"]
    out["no_real_closure"] = ~out["real_closure"]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False)

    print(f"\nstatus\n{out['status'].value_counts().to_string()}")
    ok = out[(out["status"] == "ok") & out["closure_depth"].notna()]
    if len(ok):
        print(f"\n{len(ok)} projects with an evaluable closure window")
        print(f"  low volume (baseline < {MIN_BASELINE_DQ} dq visits/wk): "
              f"{int(ok['low_volume'].sum())}  -> depth not interpretable")
        ev = ok[~ok["low_volume"]]
        print(f"  interpretable: {len(ev)}")
        print("\n  closure_depth")
        print("  " + ev["closure_depth"].describe().round(2)
              .to_string().replace("\n", "\n  "))
        real = ev[ev["real_closure"]]
        print(f"\n  REAL CLOSURE (depth <= {DEPTH_CUTOFF}): {len(real)}  "
              f"({len(real) / max(len(ev), 1):.0%} of interpretable)")
        if len(real):
            got = real["reopen_empirical"].notna()
            print(f"    recovery week detected for {int(got.sum())}/{len(real)}")
            if got.any():
                o = real.loc[got, "offset_weeks"]
                print(f"    |offset| <= {OFFSET_CUTOFF}wk: {int((o.abs() <= OFFSET_CUTOFF).sum())}"
                      f"  ({(o.abs() <= OFFSET_CUTOFF).mean():.0%})")
                print("    offset_weeks (empirical recovery - admin date)")
                print("    " + o.describe().round(1).to_string().replace("\n", "\n    "))
    print(f"\nwrote {OUT}")
    print("\nNEXT: manually review rows with real_closure == True and "
          "date_ok == False; log a keep/drop/re-date reason for each.")


if __name__ == "__main__":
    main()
