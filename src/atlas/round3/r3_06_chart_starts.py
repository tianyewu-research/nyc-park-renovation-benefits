"""Round 3 Figure 2 — recorded construction starts by year and borough.

Layout and data logic follow the earliest accepted composition
(src/atlas/p3_chart_construction_starts_annual.py). ONLY the colour system and
minor spacing change. Rebuilt from the round 2 project-location layer.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
sys.path.insert(0, os.path.dirname(__file__))
import r3_style as S

R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
SNAP_Y, Y0, YMAXP = 2026, 2008, 2040
qa = []

g = gpd.read_file(R2, layer="renovation_project_locations")
boro = gpd.read_file(R2, layer="boroughs")[["boroname", "geometry"]]
j = gpd.sjoin(g, boro, how="left", predicate="within")
j = j[~j.index.duplicated(keep="first")]
g["Mapped_Borough"] = j["boroname"].fillna("Unknown / unmatched").values
n_unmatched = int((g["Mapped_Borough"] == "Unknown / unmatched").sum())

cs = pd.to_datetime(g["Construction_Start"], errors="coerce")
yr = cs.dt.year
valid = yr.notna() & yr.between(Y0, YMAXP)
n_valid, n_missing = int(valid.sum()), int(len(g) - valid.sum())

d = pd.DataFrame({"year": yr[valid].astype(int), "boro": g.loc[valid, "Mapped_Borough"]})
YEARS = list(range(Y0, int(d["year"].max()) + 1))
pivot = (d.groupby(["year", "boro"]).size().unstack(fill_value=0)
         .reindex(index=YEARS, fill_value=0)
         .reindex(columns=S.BORO_ORDER, fill_value=0))
totals = pivot.sum(axis=1)

fig, ax = plt.subplots(figsize=(15.0, 7.6))
fig.subplots_adjust(left=.055, right=.985, top=.80, bottom=.205)
bottom = np.zeros(len(YEARS))
for b in S.BORO_ORDER:
    v = pivot[b].values
    if v.sum() == 0:
        continue
    ax.bar(YEARS, v, bottom=bottom, width=.74, label=b, color=S.BORO_COL[b],
           edgecolor=S.OFFWHITE, linewidth=.7, zorder=3)   # thin off-white separators
    bottom += v

for y, hatch in ((SNAP_Y, "//"), (SNAP_Y + 1, "xx")):
    if y in YEARS:
        ax.bar([y], [totals[y]], width=.74, facecolor="none", edgecolor=S.INK,
               linewidth=.9, hatch=hatch, zorder=4)
if SNAP_Y in YEARS:
    ax.axvline(SNAP_Y - .5, color=S.INK_2, lw=1.1, ls=(0, (4, 3)), zorder=5)

for y in YEARS:
    if totals[y] > 0:
        ax.text(y, totals[y] + totals.max() * .028, f"{int(totals[y])}", ha="center",
                va="bottom", fontsize=8.2, color=S.INK, zorder=6)

ax.set_xticks(YEARS); ax.set_xticklabels(YEARS, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("Project locations", fontsize=10, color=S.INK_2)
ax.set_ylim(0, totals.max() * 1.16)
ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
ax.tick_params(colors=S.INK_2, length=0, labelsize=9)
ax.grid(axis="y", color=S.MUTED, alpha=.24, lw=.6, zorder=0); ax.set_axisbelow(True)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(S.MUTED)
ax.legend(loc="upper left", bbox_to_anchor=(0, 1.135), ncol=6, frameon=False,
          fontsize=9.5, columnspacing=1.6, handlelength=1.1, handleheight=1.1)

n26, n27 = int(totals.get(SNAP_Y, 0)), int(totals.get(SNAP_Y + 1, 0))
ax.text(YEARS[0] - .35, totals.max() * 1.055,
        f"Hatched bars sit to the right of the dashed line:\n"
        f"   {SNAP_Y}  partial year through the snapshot date (n={n26})\n"
        f"   {SNAP_Y+1}  future-dated administrative records (n={n27})",
        fontsize=8.8, color=S.INK_2, va="top", ha="left", linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.6", facecolor=S.BG, edgecolor=S.MUTED,
                  alpha=.95, linewidth=.7))

fig.text(.055, .965, "Recorded construction starts by year and borough",
         fontsize=18, weight="bold", color=S.INK, va="top")
fig.text(.055, .922, "Mapped project locations with a valid Construction_Start date; "
         "borough is assigned from point location.", fontsize=10.5, color=S.INK_2, va="top")
NOTES = [
    f"Included locations with a valid Construction_Start date: n = {n_valid:,}",
    f"Missing Construction_Start date: n = {n_missing:,}. Missing dates are excluded "
    "and never imputed.",
    f"{SNAP_Y} is an incomplete observation year at the {S.SNAPSHOT} snapshot date.",
    "Future-dated records are administrative records and should not be interpreted as "
    "completed starts.",
    f"Borough assigned by spatial join to borough polygons, not the raw Borough string; "
    f"{n_unmatched} of {len(g):,} mapped locations fell outside every polygon.",
]
y = .145
for t in NOTES:
    fig.text(.055, y, "•  " + t, fontsize=8.3, color=S.INK_2, va="top"); y -= .0225
fig.text(.055, .022, "Source: NYC Parks Capital Project Tracker (4hcv-tc5r); Borough "
         f"Boundaries (gthc-hcne).  Snapshot {S.SNAPSHOT}.  Points projected in EPSG:2263.",
         fontsize=7.4, color=S.MUTED, va="top")

S.save(fig, "chart_recorded_construction_starts_by_year_and_borough")
qa = dict(n_mapped=len(g), n_valid_start=n_valid, n_missing_start=n_missing,
          bar_total=int(totals.sum()), n_2026=n26, n_2027=n27,
          n_unmatched_borough=n_unmatched,
          **{f"boro_{b}": int(pivot[b].sum()) for b in S.BORO_ORDER})
pd.DataFrame([qa]).to_csv("data/interim/atlas_round3/chart_starts_qa.csv", index=False)
print("  ", qa)
