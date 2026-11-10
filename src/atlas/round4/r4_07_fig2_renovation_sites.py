"""Round 4 Figure 2 — renovation on matched SITE POLYGONS. No project points."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(__file__))
import r4_04_style as S

I3, I4 = "data/interim/atlas_round3", "data/interim/atlas_round4"
site = gpd.read_file(f"{I4}/renovation_site_status.gpkg", layer="renovation_site_status")
gov = gpd.read_file(f"{I4}/governance_display_polygons.gpkg", layer="governance_display_polygons")
boro = gpd.read_file(f"{I3}/boroughs.gpkg", layer="boroughs")
assert int(site.geom_type.isin(["Point", "MultiPoint"]).sum()) == 0, "points leaked into fig 2"

comp = site[site["has_completed"] == 1]
active = site[site["active_phase_display"].notna() &
              site["active_phase_display"].ne("None")]
n_unmatched = len(gpd.read_file(
    "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg",
    layer="unmatched_project_points"))

fig = plt.figure(figsize=(20.5, 12.4))
gs = GridSpec(1, 2, figure=fig, wspace=.035, left=.02, right=.985, top=.855, bottom=.135)
ext = boro.total_bounds

def base(ax):
    boro.plot(ax=ax, facecolor=S.LAND, edgecolor="none", zorder=1)
    gov.plot(ax=ax, facecolor="#E3E7E0", edgecolor="none", alpha=.85, zorder=2)
    boro.boundary.plot(ax=ax, color=S.EDGE, linewidth=1.0, zorder=8)
    S.blank(ax); ax.set_xlim(ext[0], ext[2]); ax.set_ylim(ext[1], ext[3])
    for _, r in boro.iterrows():
        c = r.geometry.representative_point()
        ax.annotate(r["boroname"], (c.x, c.y), fontsize=S.BORO_LBL - 1, weight="bold",
                    color=S.INK_2, ha="center", zorder=20, alpha=.8)

axL = fig.add_subplot(gs[0, 0]); base(axL)
comp.plot(ax=axL, facecolor=S.COMPLETED, edgecolor=S.COMPLETED, linewidth=.7,
          alpha=.42, zorder=6)
S.north_arrow(axL); S.scale_bar(axL, 2, x=.045, y=.03)
axL.set_title(f"Sites associated with completed projects\n"
              f"{len(comp):,} matched sites", fontsize=S.PANEL, color=S.INK,
              loc="left", pad=8, weight="bold")
axL.legend(handles=[Patch(facecolor=S.COMPLETED, edgecolor=S.COMPLETED, alpha=.55,
           label=f"Completed-project sites - {len(comp):,}")],
           loc="lower right", frameon=False, fontsize=S.LEGEND)

axR = fig.add_subplot(gs[0, 1]); base(axR)
for ph in S.PHASE_ORDER:
    sub = active[active["active_phase_display"] == ph]
    if sub.empty: continue
    if ph == "Proposed/unknown":
        sub.plot(ax=axR, facecolor="none", edgecolor=S.PHASE[ph], linewidth=.85,
                 linestyle=(0, (2.5, 1.8)), zorder=6)
    else:
        sub.plot(ax=axR, facecolor=S.PHASE[ph], edgecolor=S.PHASE[ph], linewidth=.9,
                 alpha=.38, zorder=7)
S.scale_bar(axR, 2, x=.045, y=.03)
axR.set_title(f"Sites with active or proposed projects\n{len(active):,} matched sites",
              fontsize=S.PANEL, color=S.INK,
              loc="left", pad=8, weight="bold")
h = []
for ph in S.PHASE_ORDER:
    n = int((active["active_phase_display"] == ph).sum())
    if ph == "Proposed/unknown":
        h.append(Line2D([], [], color=S.PHASE[ph], lw=1.4, ls=(0, (2.5, 1.8)),
                        label=f"{ph} - {n}"))
    else:
        h.append(Patch(facecolor=S.PHASE[ph], edgecolor=S.PHASE[ph], alpha=.55,
                       label=f"{ph} - {n}"))
axR.legend(handles=h, loc="lower right", frameon=False, fontsize=S.LEGEND,
           labelspacing=.55, title="Most advanced active phase",
           title_fontsize=9).get_title().set_fontweight("bold")

fig.text(.02, .972, "Park Renovation Sites: Completed Projects and Current Phases",
         fontsize=S.TITLE, weight="bold", color=S.INK, va="top")
fig.text(.02, .932, "Matched site polygons are dissolved by site. A site may appear in both panels.",
         fontsize=S.SUBTITLE, color=S.INK_2, va="top")
fig.text(.02, .105, S.NOT_FOOTPRINT, fontsize=S.NOTE + .4, color=S.INK, va="top",
         weight="bold")
fig.text(.02, .078,
         f"The map excludes {n_unmatched} point-only project-location records, which remain in the "
         "inventory and QA file. The completed-project panel records presence or absence at each "
         "site, not project totals. The current-phase panel assigns each site its most advanced "
         "active phase; completed-only sites are excluded from that panel.",
         fontsize=S.NOTE, color=S.INK_2, va="top", style="italic")
fig.text(.02, .024, f"{S.SRC_REN}  Snapshot {S.SNAPSHOT}. EPSG:2263. No online basemap.",
         fontsize=7.5, color=S.MUTED, va="top")
S.save(fig, "fig2_renovation_status_site_polygons")
print(f"  completed sites {len(comp)} | active sites {len(active)} | unmatched points {n_unmatched}")
print("  active mix:", active["active_phase_display"].value_counts().to_dict())
