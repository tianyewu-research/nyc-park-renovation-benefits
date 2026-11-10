"""Shared chart builders used by the three case asset scripts."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C, cs_fig as F
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

MOB = os.path.join(C.INTERIM, "mobile"); TAB = os.path.join(C.INTERIM, "tables")
SRC_ADVAN = (f"Advan weekly patterns, vintage {C.ADVAN_VINTAGE}, coverage "
             f"{C.ADVAN_COVERAGE}; POIs matched via canonical 100 ft crosswalk.")
ADVAN_CAVEAT = ("Advan coverage begins in 2023, after all three focal renovations. "
                "These series describe current use, not renovation effects.")

def _ax(ax):
    ax.tick_params(colors=F.INK_2, length=0, labelsize=8)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(F.MUTED)
    ax.grid(axis="y", color=F.MUTED, alpha=.22, lw=.6); ax.set_axisbelow(True)

def advan_index(cid, board):
    w = pd.read_csv(f"{MOB}/weekly_visit_index.csv", parse_dates=["week"])
    w = w[w.case_id == cid].sort_values("week")
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    ax.plot(w.week, w.index_2023med100, color=F.TEAL_M, lw=.8, alpha=.55, label="weekly")
    ax.plot(w.week, w.index_roll4, color=F.RUST, lw=1.9, label="4-week rolling median")
    ax.axhline(100, color=F.MUTED, lw=.8, ls="--")
    ax.set_ylabel("Index (2023 median = 100)", fontsize=9, color=F.INK_2)
    _ax(ax); ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title(f"{C.CASES[cid]['name']}: weekly visit index, 2023–2025",
                 fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, SRC_ADVAN + " " + ADVAN_CAVEAT)
    fig.tight_layout(rect=(0, .06, 1, 1))
    F.export(fig, os.path.join(C.board_dir(cid, board), "figures"),
             f"{cid}_F01_advan_weekly_index",
             f"{C.CASES[cid]['name']}: weekly visit index, 2023–2025",
             "Dwell-qualified weekly visits summed across matched POIs, indexed to the "
             "2023 median. Within-case index only; absolute totals are not comparable "
             "between cases because each has a different number of matched POIs.",
             "visits_dq summed by week across matched POIs; index = value / 2023 median x 100; "
             "4-week centred rolling median overlaid.",
             "index (2023 median = 100)", SRC_ADVAN,
             w[["week","visits_dq","n_poi","index_2023med100","index_roll4","missing_week"]],
             case_id=cid, board=board)

def advan_season(cid, board):
    m = pd.read_csv(f"{MOB}/seasonal_profile_month.csv")
    m = m[m.case_id == cid].sort_values("month")
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    ax.bar(m.month, m.median_index, color=F.TEAL, width=.66)
    for _, r in m.iterrows():
        ax.text(r.month, r.median_index + 2, f"{r.median_index:.0f}", ha="center",
                fontsize=7.5, color=F.INK)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"], fontsize=8)
    ax.set_ylabel("Median weekly index", fontsize=9, color=F.INK_2); _ax(ax)
    ax.set_title(f"{C.CASES[cid]['name']}: seasonal profile, 2023–2025",
                 fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, SRC_ADVAN + " " + ADVAN_CAVEAT)
    fig.tight_layout(rect=(0, .06, 1, 1))
    F.export(fig, os.path.join(C.board_dir(cid, board), "figures"),
             f"{cid}_F02_advan_seasonal",
             f"{C.CASES[cid]['name']}: seasonal profile, 2023–2025",
             "Median weekly visit index by calendar month across the three observed years.",
             "Median of the weekly 2023-indexed series, grouped by calendar month.",
             "median weekly index", SRC_ADVAN, m, case_id=cid, board=board)

def pip_timelines(cid, board):
    d = pd.read_csv(f"{TAB}/{cid}_pip_inspections.csv", low_memory=False)
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d[d.date.notna()].sort_values("date")
    m = {"A": 1, "U": 0, "N": np.nan}
    for c in ("overall_condition", "cleanliness"):
        if c in d.columns: d[c + "_num"] = d[c].map(m)
    yr = d.assign(y=d.date.dt.year).groupby("y").agg(
        n_inspections=("date", "size"),
        pct_acceptable_overall=("overall_condition_num", lambda s: 100 * s.mean(skipna=True)),
        pct_acceptable_clean=("cleanliness_num", lambda s: 100 * s.mean(skipna=True))
    ).reset_index()
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    ax.plot(yr.y, yr.pct_acceptable_overall, color=F.TEAL, lw=1.8, marker="o", ms=3.2,
            label="overall condition")
    if yr.pct_acceptable_clean.notna().any():
        ax.plot(yr.y, yr.pct_acceptable_clean, color=F.ORANGE, lw=1.6, marker="s", ms=3.0,
                label="cleanliness")
    ax.set_ylim(0, 105); ax.set_ylabel("% of inspections rated Acceptable", fontsize=9,
                                       color=F.INK_2)
    _ax(ax); ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title(f"{C.CASES[cid]['name']}: PIP condition ratings by year",
                 fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, f"NYC Parks Parks Inspection Program (yg3y-7juh), prop_id "
                  f"{'exact' if C.CASES[cid]['pip_match']=='exact' else 'prefix'} "
                  f"{C.CASES[cid]['park_id']}. Ratings are inspector judgements at "
                  "inspection time, not continuous monitoring.")
    fig.tight_layout(rect=(0, .07, 1, 1))
    F.export(fig, os.path.join(C.board_dir(cid, board), "figures"),
             f"{cid}_F03_pip_condition",
             f"{C.CASES[cid]['name']}: PIP condition ratings by year",
             "Share of Parks Inspection Program inspections rated Acceptable, by year.",
             "Acceptable=1, Unacceptable=0, N/A excluded; annual mean x 100.",
             "% of inspections rated Acceptable",
             "NYC Parks PIP inspections yg3y-7juh", yr, case_id=cid, board=board)

    if "visitorcount" in d.columns and d["visitorcount"].notna().any():
        v = d[["date", "visitorcount"]].dropna().copy()
        v["visitorcount"] = pd.to_numeric(v["visitorcount"], errors="coerce")
        v = v.dropna()
        fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
        ax.scatter(v.date, v.visitorcount, s=14, color=F.ORANGE, alpha=.8)
        ax.set_ylabel("Visitors counted at inspection", fontsize=9, color=F.INK_2); _ax(ax)
        ax.set_title(f"{C.CASES[cid]['name']}: PIP inspection-time visitor counts",
                     fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
        F.source_line(fig, "Each point is one inspection visit. PIP visitorcount is a "
                      "snapshot observation at the moment of inspection; it is NOT "
                      "continuous attendance and must not be summed as a total. "
                      "Source: NYC Parks PIP inspections yg3y-7juh.")
        fig.tight_layout(rect=(0, .08, 1, 1))
        F.export(fig, os.path.join(C.board_dir(cid, board), "figures"),
                 f"{cid}_F04_pip_visitorcount",
                 f"{C.CASES[cid]['name']}: PIP inspection-time visitor counts",
                 "Observed visitor count recorded at each inspection.",
                 "Plotted as individual observations; never aggregated into attendance.",
                 "visitors present at inspection", "NYC Parks PIP inspections yg3y-7juh",
                 v, case_id=cid, board=board)

def origin_and_composition(cid, board):
    b = pd.read_csv(f"{MOB}/visitor_origin_by_borough.csv")
    b = b[b.case_id == cid].sort_values("provider_home_count", ascending=False)
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    ax.barh(b.boro, b.share, color=F.TEAL_M, height=.62)
    for i, (_, r) in enumerate(b.iterrows()):
        ax.text(r.share + .8, i, f"{r.share:.1f}%", va="center", fontsize=8, color=F.INK)
    ax.invert_yaxis(); ax.set_xlim(0, max(b.share) * 1.2); ax.set_xticks([])
    ax.tick_params(colors=F.INK_2, length=0, labelsize=8.4)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.set_title(f"{C.CASES[cid]['name']}: visitor-origin geography, 2023–2025",
                 fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, "Provider-estimated home block groups aggregated to borough for "
                  "privacy. No individual device or exact home location is published. "
                  + SRC_ADVAN)
    fig.tight_layout(rect=(0, .08, 1, 1))
    F.export(fig, os.path.join(C.board_dir(cid, board), "figures"),
             f"{cid}_F05_visitor_origin_borough",
             f"{C.CASES[cid]['name']}: visitor-origin geography, 2023–2025",
             "Share of provider-estimated visitor home block groups by borough.",
             "VISITOR_HOME_CBGS summed across matched POIs and all weeks, aggregated to borough.",
             "% of provider-estimated home-CBG counts", SRC_ADVAN, b, case_id=cid, board=board)

    dem = pd.read_csv(os.path.join(C.SHARED, "data", "S03_800m_demographic_profiles.csv"))
    comp = pd.read_csv(f"{MOB}/origin_area_acs_composition.csv")
    d1 = dem[dem.case_id == cid].iloc[0]; d2 = comp[comp.case_id == cid].iloc[0]
    CATS = [("pct_white_nh", "White NH", F.TEAL), ("pct_black", "Black", F.TEAL_M),
            ("pct_asian", "Asian", F.ORANGE), ("pct_hispanic", "Hispanic", "#C9A227")]
    rows = [dict(series="800 m radius study area (residents)", **{l: d1[c] for c,l,_ in CATS}),
            dict(series="ACS composition of visitor-origin areas", **{l: d2[c] for c,l,_ in CATS})]
    t = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    left = np.zeros(2)
    for c, l, col in CATS:
        v = t[l].values
        ax.barh([0, 1], v, left=left, color=col, height=.5, label=l, edgecolor=F.BG, lw=.8)
        for i in range(2):
            if v[i] > 5:
                ax.text(left[i] + v[i]/2, i, f"{v[i]:.0f}", ha="center", va="center",
                        fontsize=8, color="white" if col in (F.TEAL,) else F.INK)
        left += v
    ax.set_yticks([0, 1]); ax.set_yticklabels(t.series, fontsize=8.6)
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("% of population", fontsize=9,
                                                          color=F.INK_2)
    ax.tick_params(colors=F.INK_2, length=0, labelsize=8)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(.5, 1.18))
    ax.set_title(f"{C.CASES[cid]['name']}: surrounding residents vs visitor-origin areas",
                 fontsize=11, color=F.INK, loc="left", pad=26, weight="bold")
    F.source_line(fig, "The lower bar is an ECOLOGICAL estimate of the ACS composition of "
                  "the areas visitors come from, weighted by provider-estimated home-CBG "
                  "counts. It is NOT the race or ethnicity of visitors. Sources: ACS "
                  "(acs_cbg.csv); " + SRC_ADVAN)
    fig.tight_layout(rect=(0, .10, 1, 1))
    F.export(fig, os.path.join(C.board_dir(cid, board), "figures"),
             f"{cid}_F06_surrounding_vs_origin_composition",
             f"{C.CASES[cid]['name']}: surrounding residents vs visitor-origin areas",
             "Two different populations, shown side by side: residents within 800 m, and "
             "the ACS composition of the areas visitors travel from. The second is an "
             "ecological estimate of origin-area composition, not visitor race.",
             "Top bar: overlap-weighted ACS within the 800 m ring. Bottom bar: ACS shares "
             "of origin block groups weighted by provider-estimated home counts.",
             "% of population", "ACS acs_cbg.csv; " + SRC_ADVAN, t, case_id=cid, board=board)
