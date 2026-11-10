"""Map 1 — Citywide green-space and renovation landscape."""
import warnings; warnings.filterwarnings("ignore")
import geopandas as gpd, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style as S

GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
rd = lambda l: gpd.read_file(GPKG, layer=l)

boro, parks = rd("boroughs"), rd("parks_properties")
ap, gt, pops = rd("active_passive_recreation"), rd("community_gardens"), rd("pops")
pts = rd("renovation_project_locations")

fig, ax = plt.subplots(figsize=(11.5, 12.4))
fig.subplots_adjust(left=.03, right=.985, top=.895, bottom=.085)

boro.plot(ax=ax, facecolor=S.LAND, edgecolor="white", lw=1.4, zorder=1)
parks.plot(ax=ax, facecolor=S.PARK_PALE, edgecolor="none", zorder=2)
ap[ap.recreation_category == "Passive"].plot(ax=ax, facecolor=S.PARK_MID,
                                             edgecolor="none", zorder=3)
ap[ap.recreation_category == "Active"].plot(ax=ax, facecolor=S.PARK_DEEP,
                                            edgecolor="none", zorder=4)
# gardens are small MultiPolygons; at citywide scale they are drawn as
# representative points so they remain visible (noted in the caption)
gt_pt = gt.copy(); gt_pt["geometry"] = gt_pt.geometry.representative_point()
gt_pt.plot(ax=ax, color=S.AQUA, markersize=15, alpha=.95,
           edgecolor="white", linewidth=.5, zorder=5)
pops.plot(ax=ax, color=S.ORANGE, marker="s", markersize=9, alpha=.9,
          edgecolor="white", linewidth=.3, zorder=6)
pts.plot(ax=ax, color=S.BLUE, markersize=9, alpha=.45,
         edgecolor="white", linewidth=.25, zorder=7)

boro.boundary.plot(ax=ax, color="white", lw=1.4, zorder=8)
S.blank(ax); S.north_arrow(ax); S.scale_bar(ax)

for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r["boroname"], (c.x, c.y), fontsize=9.5, weight="bold",
                color=S.INK_2, ha="center", zorder=10,
                path_effects=None, alpha=.75)

handles = [
    Patch(facecolor=S.PARK_DEEP, edgecolor="none", label="Park land — active recreation"),
    Patch(facecolor=S.PARK_MID, edgecolor="none", label="Park land — passive recreation"),
    Patch(facecolor=S.PARK_PALE, edgecolor="none", label="Other Parks property"),
    Line2D([], [], ls="", marker="o", ms=6.5, color=S.AQUA,
           mec="white", mew=.8,
           label=f"GreenThumb community garden (n={len(gt)})"),
    Line2D([], [], ls="", marker="s", ms=5, color=S.ORANGE,
           label=f"Privately owned public space (n={len(pops)})"),
    Line2D([], [], ls="", marker="o", ms=5.5, color=S.BLUE, alpha=.6,
           label=f"Capital project location (n={len(pts):,})"),
]
ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=.94,
          edgecolor=S.MUTED, fontsize=8.4, borderpad=.85, labelspacing=.62,
          bbox_to_anchor=(.005, .995))

S.frame(fig,
        "New York City green space and capital renovation activity",
        "Every mapped Parks capital project location, shown against the city's park, "
        "community-garden and privately owned public space network.",
        "Project points are administrative project locations from the Capital Project "
        "Tracker, not verified construction footprints; 284 of 2,758 records carry no "
        "usable coordinate and are retained in the Excel inventory only. Community "
        "gardens and POPS are drawn at representative points, not to area.")
S.save(fig, "map1_green_space_and_renovation_landscape")
