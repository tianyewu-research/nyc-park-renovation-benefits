"""Round 2 Chart 1 — completions by year, administrative vs verified public opening."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style_round2 as S

START, END, SNAP_Y = 2010, 2026, 2026
G = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
pi = pd.read_excel("outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx",
                   sheet_name="Project Inventory")
pts = gpd.read_file(G, layer="renovation_project_locations")
boro = gpd.read_file(G, layer="boroughs")[["boroname","geometry"]]
j = gpd.sjoin(pts, boro, how="left", predicate="within")
j = j[~j.index.duplicated(keep="first")]
mb = dict(zip(j["Map_ID"], j["boroname"]))

adm = pd.to_datetime(pi["Administrative_Completion_Date"], errors="coerce").dt.year
ver = pd.to_datetime(pi["Verified_Public_Opening_Date"], errors="coerce").dt.year
pi["_boro"] = pi["Map_ID"].map(mb)
YEARS = list(range(START, END + 1))
BOR = ["Bronx","Brooklyn","Manhattan","Queens","Staten Island"]

n_adm = int(adm.between(START, END).sum())
n_ver = int(ver.between(START, END).sum())
n_adm_missing = int(len(pi) - adm.notna().sum())

fig, axes = plt.subplots(1, 5, figsize=(17.5, 5.9), sharey=True)
fig.subplots_adjust(left=.045, right=.985, top=.72, bottom=.235, wspace=.13)
ymax = 0
series = {}
for b in BOR:
    s = pi[pi["_boro"] == b]
    v = [int(((pd.to_datetime(s["Administrative_Completion_Date"], errors="coerce")
               .dt.year) == y).sum()) for y in YEARS]
    series[b] = v; ymax = max(ymax, max(v) if v else 0)

for ax, b in zip(axes, BOR):
    v = series[b]
    ax.bar(YEARS, v, width=.72, color=S.ST_COMPLETED, edgecolor=S.TEAL_M,
           linewidth=.7, zorder=3, label="Administrative completion")
    if SNAP_Y in YEARS:
        i = YEARS.index(SNAP_Y)
        ax.bar([SNAP_Y], [v[i]], width=.72, facecolor="none", edgecolor=S.RUST_D,
               linewidth=1.0, hatch="//", zorder=4)
        ax.axvline(SNAP_Y - .5, color=S.INK_2, lw=.9, ls=(0, (4, 3)), zorder=5)
    ax.set_title(f"{b}\n{sum(v):,} administrative completions", fontsize=9.8,
                 color=S.INK, pad=7)
    ax.set_xticks([y for y in YEARS if y % 2 == 0])
    ax.set_xticklabels([y for y in YEARS if y % 2 == 0], rotation=45, ha="right", fontsize=8)
    ax.tick_params(colors=S.INK_2, length=0, labelsize=8.5)
    ax.grid(axis="y", color=S.MUTED, alpha=.22, lw=.6, zorder=0); ax.set_axisbelow(True)
    for sp in ("top","right","left"): ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(S.MUTED)
axes[0].set_ylabel("Project locations", fontsize=9.5, color=S.INK_2)
axes[0].set_ylim(0, ymax * 1.18)
axes[0].yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))

fig.text(.045, .965, "Projects completed or opened by year", fontsize=18,
         weight="bold", color=S.INK, va="top")
fig.text(.045, .925,
         "Two different dates, reported separately. Bars show ADMINISTRATIVE completion; "
         "verified public opening is a distinct field and is charted only where sourced.",
         fontsize=10.5, color=S.INK_2, va="top")
fig.text(.045, .878,
         f"Administrative completions {START}–{END}:  n = {n_adm:,}          "
         f"Verified public openings {START}–{END}:  n = {n_ver:,}",
         fontsize=11, color=S.RUST_D if n_ver == 0 else S.INK, weight="bold", va="top")

NOTES = [
 f"Verified_Public_Opening_Date has n = {n_ver} sourced values, so no opening-date series "
 "can be drawn. In round 1 this field held a verbatim copy of the administrative "
 "completion date; that copy was cleared in round 2 rather than carried forward.",
 f"{n_adm_missing:,} of {len(pi):,} inventory rows carry no administrative completion date. "
 "Missing dates are excluded and never imputed.",
 f"{SNAP_Y} is a partial year at the {S.SNAPSHOT} snapshot date (hatched, right of the "
 "dashed rule).",
 "Borough is assigned by spatial join to borough polygons, not from the raw Borough string.",
]
y = .175
for t in NOTES:
    fig.text(.045, y, "•  " + t, fontsize=8.3, color=S.INK_2, va="top", wrap=True)
    y -= .033
fig.text(.045, .022, "Source: NYC Parks Capital Project Tracker (4hcv-tc5r); Borough "
         f"Boundaries (gthc-hcne). Snapshot {S.SNAPSHOT}.", fontsize=7.2,
         color=S.MUTED, va="top")
S.save(fig, "chart_projects_completed_or_opened_by_year")
print(f"  administrative n={n_adm} | verified opening n={n_ver} | no adm date {n_adm_missing}")
print("  per borough:", {b: sum(v) for b, v in series.items()})
