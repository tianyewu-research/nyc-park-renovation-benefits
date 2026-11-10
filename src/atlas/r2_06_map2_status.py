"""Round 2 Map 2 — Renovation Status on Matched Sites and Parcels."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style_round2 as S

G = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
rd = lambda l: gpd.read_file(G, layer=l)
boro, parks = rd("boroughs"), rd("parks_properties")
poly, ptonly = rd("renovation_site_polygons"), rd("unmatched_project_points")
pi = pd.read_excel("outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx",
                   sheet_name="Project Inventory")
PH = {"completed":"Completed","construction":"In construction","procurement":"In procurement",
      "design":"In design","design-procurement":"In design","proposed":"Proposed"}
ph = pi.set_index("Map_ID")["Current_Phase"].map(PH).fillna("Other / unknown")
poly["phase"] = poly["Map_ID"].map(ph); ptonly["phase"] = ptonly["Map_ID"].map(ph)

ORDER = [("Completed", S.ST_COMPLETED), ("Proposed", S.ST_PROPOSED),
         ("In design", S.ST_DESIGN), ("In procurement", S.ST_PROCUREMENT),
         ("In construction", S.ST_CONSTRUCTION)]

fig, ax = plt.subplots(figsize=(16.5, 17.4))
fig.subplots_adjust(left=.025, right=.99, top=.90, bottom=.105)
boro.plot(ax=ax, facecolor=S.LAND, edgecolor="white", lw=1.8, zorder=1)
parks.plot(ax=ax, facecolor="#eef2ec", edgecolor="none", zorder=2)
boro.boundary.plot(ax=ax, color=S.SHORE, lw=1.0, zorder=3)

pc = {}
for z, (nm, col) in enumerate(ORDER, start=5):
    sel = poly[poly["phase"] == nm]; pc[nm] = len(sel)
    if len(sel):
        sel.plot(ax=ax, facecolor=col, edgecolor=S.INK, linewidth=.25, alpha=.95, zorder=z)
        c = sel.copy(); c["geometry"] = c.geometry.representative_point()
        c.plot(ax=ax, color=col, markersize=9 if nm == "Completed" else 26,
               edgecolor="white", linewidth=.4, alpha=.9, zorder=z + 30)
ptonly.plot(ax=ax, color=S.ST_POINT_ONLY, marker="X", markersize=70,
            edgecolor="white", linewidth=.8, zorder=45)

S.blank(ax); S.north_arrow(ax); S.scale_bar(ax, 2, x=.045, y=.035)
for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r["boroname"], (c.x, c.y), fontsize=11, weight="bold",
                color="#878984", ha="center", zorder=60)

h_poly = [Patch(facecolor=c, edgecolor=S.INK, lw=.4, label=f"{n} — {pc.get(n,0):,}")
          for n, c in ORDER]
h_pt = [Line2D([], [], ls="", marker="X", ms=10, color=S.ST_POINT_ONLY, mec="white",
               label=f"Point only, no site polygon — {len(ptonly)}")]
l1 = ax.legend(handles=h_poly, loc="upper left", bbox_to_anchor=(.004, .996),
               frameon=True, framealpha=.97, edgecolor=S.MUTED, fontsize=10,
               borderpad=.95, labelspacing=.65,
               title="Matched site polygons — renovation status", title_fontsize=10.5)
l1.get_title().set_fontweight("bold")
ax.add_artist(l1)
ax.legend(handles=h_pt, loc="upper left", bbox_to_anchor=(.004, .775),
          frameon=True, framealpha=.97, edgecolor=S.MUTED, fontsize=10,
          borderpad=.8, title="Unmatched", title_fontsize=10.5)

roles = poly["Geometry_Role"].value_counts()
ax.text(.004, .70, "Polygon precision, most precise first\n" +
        "\n".join(f"   {k.replace('_',' ')} — {v:,}" for k, v in roles.items()) +
        f"\n   point only — {len(ptonly)}\n"
        "A whole Parks property is NOT a construction footprint.",
        transform=ax.transAxes, fontsize=9.0, va="top", color=S.INK_2, linespacing=1.55,
        bbox=dict(boxstyle="round,pad=.7", facecolor="white", edgecolor=S.MUTED, alpha=.96))

S.title_block(fig, "Renovation Status on Matched Sites and Parcels",
    "Each project location is drawn on the most precise site geometry that could be "
    "matched to it; locations with no match keep their administrative point.")
S.footer(fig,
    f"One project may contain several project-location records: {len(poly)+len(ptonly):,} "
    f"locations resolve to {pi['Tracker_ID'].nunique():,} unique Tracker IDs. "
    f"{len(poly):,} locations carry a site polygon, {len(ptonly)} are point-only, and "
    f"{len(pi)-len(poly)-len(ptonly):,} inventory rows have no usable coordinate at all. "
    "Polygon precision varies: CPDB project polygons are project-scale but DCP notes some "
    "come from manual or fuzzy matching; PIP sub-sites are finer than a park but not the "
    "works area; a park-property polygon is the WHOLE property.", y0=.070)
S.save(fig, "map2_renovation_status_site_polygons")
print("  polygons", len(poly), "| point-only", len(ptonly))
print("  by role:", roles.to_dict())
