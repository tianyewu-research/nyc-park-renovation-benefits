"""Map 3 — Where the administrative site model does not fit neatly.

Four site-relationship categories, faceted. Each panel carries the full mapped
universe as faint grey context and highlights one category, so the exceptions
are visible without being coloured as errors.
"""
import warnings; warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style as S

GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
boro = gpd.read_file(GPKG, layer="boroughs")
parks = gpd.read_file(GPKG, layer="parks_properties")
g = gpd.read_file(GPKG, layer="renovation_project_locations")

CATS = [
    ("NYC Parks property", S.MUTED,
     "Project location sits on a Parks property that matches the\n"
     "Parks Properties register by Park ID."),
    ("Non-Parks public green-space site", S.ORANGE,
     "Park ID is an agency code (DEP, DOE, DOT). These are real\n"
     "green-space projects on land another agency owns."),
    ("Unmatched or legacy property code", S.BLUE,
     "Park ID is present but absent from the current register —\n"
     "sub-property suffixes, retired codes, or a second code series."),
    ("No Park ID", S.AQUA,
     "No Park ID in the Tracker. Only 15 of 298 such records carry\n"
     "a usable coordinate, so this panel shows 5% of the category."),
]

fig = plt.figure(figsize=(15.0, 6.9))
gs = GridSpec(1, 4, figure=fig, wspace=.045,
              left=.03, right=.985, top=.815, bottom=.235)

for i, (cat, colour, blurb) in enumerate(CATS):
    ax = fig.add_subplot(gs[0, i])
    boro.plot(ax=ax, facecolor=S.LAND, edgecolor="white", lw=.7)
    parks.plot(ax=ax, facecolor=S.PARK_MID, edgecolor="none", alpha=.55)
    g.plot(ax=ax, color=S.MUTED, markersize=1.6, alpha=.20, zorder=4)
    sel = g[g["Site_Type"] == cat]
    big = cat != "NYC Parks property"
    sel.plot(ax=ax, color=colour, markersize=26 if big else 3.0,
             alpha=.95 if big else .5,
             edgecolor="white" if big else "none",
             linewidth=.6 if big else 0, zorder=6)
    S.blank(ax)
    ax.set_title(f"{cat}\n{len(sel):,} mapped project locations",
                 fontsize=9.8, color=S.INK, pad=7, weight="bold")
    ax.text(.5, -.055, blurb, transform=ax.transAxes, ha="center", va="top",
            fontsize=7.8, color=S.INK_2, linespacing=1.45)
    if i == 0:
        S.scale_bar(ax, length_mi=5, x=.04, y=.03)
        S.north_arrow(ax, x=.93, y=.93, size=.07)

# agency breakdown for the exception panel
ag = (g[g["Site_Type"] == "Non-Parks public green-space site"]["Owning_Agency"]
      .value_counts())
ag_txt = "  ·  ".join(f"{k} {v}" for k, v in ag.items()) if len(ag) else "n/a"
fig.text(.03, .105, f"Owning agency among non-Parks sites:  {ag_txt}",
         fontsize=8.2, color=S.INK_2)

n_exc = int((g["Site_Type"] != "NYC Parks property").sum())
fig.text(.03, .088,
         f"{n_exc} of {len(g):,} mapped project locations ({n_exc/len(g):.1%}) do not "
         "resolve to a Parks property. They are kept in the inventory, not dropped — "
         "this is why the atlas models 'site' and 'project' as separate entities.",
         fontsize=8.2, color=S.INK)
fig.text(.03, .062,
         "Missing site identity and missing location are the SAME gap: 283 of the 284 "
         "project locations without a usable coordinate are also the records with no "
         "Park ID. They are mostly finished work (223 completed, 259 with a construction "
         "start date), so the gap is not confined to early-stage projects.",
         fontsize=8.2, color=S.ORANGE)

S.frame(fig,
        "One project, one site? Where the administrative model does not fit",
        "The Capital Project Tracker assumes a project sits on a Parks property. "
        "For most locations it does. These four panels show every case where it does not.",
        "Categories describe how a Tracker record relates to the Parks Properties "
        "register at the snapshot date. They are data-model mismatches to review, not "
        "errors in the underlying projects, and none has been corrected or removed. "
        "The 'No Park ID' panel is severely under-mapped — see the note above.")
S.save(fig, "map3_site_model_mismatch")
