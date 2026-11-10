"""SUPERSEDED 2026-09-09 -- retained for provenance, do not run for deliverables.

This produced the combined phase-map + period-chart figure, now archived at
maps/archive/map2_phase_and_timing_pre_split_20260909.png / .pdf

It was split because putting a current-phase map and a construction-start chart
on one canvas implied a one-to-one relationship between them. Current phase is a
2026-09-08 snapshot and cannot describe a project's status in its start year.

Replaced by:
  src/atlas/p3_map2_phase_status.py               -> maps/map2_phase_status.*
  src/atlas/p3_chart_construction_starts_annual.py -> maps/chart_construction_starts_by_year.*
"""

"""Map 2 — Renovation activity by current phase and by construction period.

Faceted rather than one multi-colour map: a categorical point map is an
all-pairs form, and the reference palette caps all-pairs categorical series at
three. Five phases therefore become five small multiples, each carrying one
accent against grey context, so no CVD-unsafe pair is ever on screen.
"""
import warnings; warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd, numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style as S

GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
boro = gpd.read_file(GPKG, layer="boroughs")
parks = gpd.read_file(GPKG, layer="parks_properties")
g = gpd.read_file(GPKG, layer="renovation_project_locations")

# fold six raw phases into five reader-facing groups
PH = {"completed": "Completed", "construction": "In construction",
      "procurement": "In procurement", "design": "In design",
      "design-procurement": "In design", "proposed": "Proposed"}
g["phase_group"] = g["Current_Phase"].map(PH).fillna("Other / unknown")
ORDER = ["Completed", "In construction", "In procurement", "In design", "Proposed"]
counts = g["phase_group"].value_counts()

fig = plt.figure(figsize=(15.5, 8.9))
gs = GridSpec(2, 5, figure=fig, height_ratios=[1.12, 1.0],
              hspace=.22, wspace=.045,
              left=.035, right=.982, top=.845, bottom=.125)

for i, ph in enumerate(ORDER):
    ax = fig.add_subplot(gs[0, i])
    boro.plot(ax=ax, facecolor=S.LAND, edgecolor="white", lw=.7)
    parks.plot(ax=ax, facecolor=S.PARK_MID, edgecolor="none", alpha=.75)
    sel = g[g["phase_group"] == ph]
    sel.plot(ax=ax, color=S.BLUE, markersize=4.2, alpha=.62,
             edgecolor="none", zorder=5)
    S.blank(ax)
    ax.set_title(f"{ph}\n{len(sel):,} project locations", fontsize=9.6,
                 color=S.INK, pad=7, weight="bold" if i == 0 else "normal")
    if i == 0:
        S.scale_bar(ax, length_mi=5, x=.04, y=.03)
        S.north_arrow(ax, x=.93, y=.93, size=.07)

# ---- timing panel -------------------------------------------------------
axb = fig.add_subplot(gs[1, :])
cs = pd.to_datetime(g["Construction_Start"], errors="coerce")
yr = cs.dt.year
BINS = [(2008, 2012), (2013, 2016), (2017, 2020), (2021, 2023), (2024, 2027)]
labs = [f"{a}–{b}" for a, b in BINS]
vals = [int(((yr >= a) & (yr <= b)).sum()) for a, b in BINS]
n_missing = int(yr.isna().sum())

bars = axb.bar(labs, vals, color=S.BLUE, width=.62, zorder=3)
for b, v in zip(bars, vals):
    axb.text(b.get_x() + b.get_width() / 2, v + max(vals) * .03, f"{v:,}",
             ha="center", va="bottom", fontsize=9, color=S.INK)
axb.set_ylim(0, max(vals) * 1.22)
axb.set_ylabel("Project locations", fontsize=8.5, color=S.INK_2)
axb.tick_params(labelsize=9, colors=S.INK_2, length=0)
axb.grid(axis="y", color=S.MUTED, alpha=.22, lw=.6, zorder=0)
axb.set_axisbelow(True)
for sp in ("top", "right", "left"):
    axb.spines[sp].set_visible(False)
axb.spines["bottom"].set_color(S.MUTED)
axb.set_title("Construction start period — mapped project locations with a "
              f"recorded construction start date (n={int(yr.notna().sum()):,})",
              fontsize=10, color=S.INK, pad=8, loc="left")
axb.text(1.0, 1.06, f"{n_missing:,} mapped locations have no construction start date "
         "and are not counted here", transform=axb.transAxes, ha="right",
         fontsize=8, color=S.MUTED)

S.frame(fig,
        "Where renovation stands: capital project locations by phase and period",
        "Five small multiples share one scale and extent. Grey shows the city; green "
        "shows Parks property; each panel plots only the project locations in that phase.",
        "Phase is the Tracker's current administrative status at the snapshot date, not "
        f"a verified site condition. {n_missing:,} of {len(g):,} mapped locations lack a "
        f"construction start date and 694 lack an actual completion date; missing dates "
        "are excluded from the period chart, never imputed.")
S.save(fig, "map2_phase_and_timing")
