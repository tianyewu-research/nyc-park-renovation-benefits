"""Eyeball the visit series behind gate_05's closure_depth.

gate_05 says 84% of projects show no visitation drop during the stated closure.
Before believing that, look at the series: the alternative explanations are a
whole-park POI geofence diluting a partial-site closure, residual seasonality
the citywide deflator does not remove, or simply a noisy denominator.

Top row  : lowest closure_depth  (detector says the park really closed)
Bottom   : closure_depth near 1  (detector says nothing happened)

Usage:  python3 src/gate_05b_plot_series.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import lib_advan as la

VAL = "outputs/tables/date_validation.csv"
OUT = "outputs/figures/closure_series_examples.png"
N = 6


def main():
    v = pd.read_csv(VAL, low_memory=False)
    v = v[v["closure_depth"].notna()].copy()
    for c in ["constructionstart", "admin_reopen", "reopen_empirical"]:
        v[c] = pd.to_datetime(v[c], errors="coerce")

    # prefer long closures — those are where a real interruption should be visible
    v["clen"] = (v["admin_reopen"] - v["constructionstart"]).dt.days / 7
    pool = v[v["clen"] >= 26]

    closed = pool.nsmallest(N, "closure_depth")
    open_ = (pool.assign(d=(pool["closure_depth"] - 1.0).abs())
             .nsmallest(N, "d"))

    pw, _ = la.park_week(la.load_poi_week())
    series = {k: g.set_index("week")["visits_defl"].sort_index()
              for k, g in pw.groupby("parkid")}

    fig, axes = plt.subplots(2, N, figsize=(4.0 * N, 7.5), sharex=False)
    for row, (df, label) in enumerate([(closed, "closure detected"),
                                       (open_, "no drop detected")]):
        for col, (_, r) in enumerate(df.iterrows()):
            ax = axes[row, col]
            s = series.get(r["parkid"])
            if s is None or s.empty:
                ax.set_visible(False)
                continue
            ax.plot(s.index, s.values, lw=0.9, color="#3b6ea5")
            ax.axvspan(r["constructionstart"], r["admin_reopen"],
                       color="#d9534f", alpha=0.13, lw=0)
            ax.axvline(r["admin_reopen"], color="#d9534f", lw=1.2, ls="--")
            if pd.notna(r.get("reopen_empirical")):
                ax.axvline(r["reopen_empirical"], color="#4c9a4c", lw=1.2, ls=":")
            name = str(r["name"])[:26]
            ax.set_title(f"{name}\ndepth={r['closure_depth']:.2f}  "
                         f"closure={r['clen']:.0f}wk  off={r['offset_weeks']:+.0f}wk",
                         fontsize=8)
            ax.tick_params(labelsize=6)
            for lab in ax.get_xticklabels():
                lab.set_rotation(45)
                lab.set_ha("right")
            if col == 0:
                ax.set_ylabel(f"{label}\ndeflated visits", fontsize=8)

    fig.suptitle("Red band = stated construction period · dashed red = admin reopening · "
                 "dotted green = detected break", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130)
    print(f"wrote {OUT}")

    print("\ntop row (lowest depth):")
    print(closed[["name", "closure_depth", "clen", "offset_weeks"]]
          .round(2).to_string(index=False))
    print("\nbottom row (depth ~ 1):")
    print(open_[["name", "closure_depth", "clen", "offset_weeks"]]
          .round(2).to_string(index=False))


if __name__ == "__main__":
    main()
