"""Round 3 Figure 1 — green-space ownership/governance + renovation status.

Same base layers and frame as Figure 0, at lower opacity so the thematic layers
dominate. Ownership uses FILL for the family and HATCH for the subtype;
renovation phase uses a separate ordered warm sequence on project-location
POINTS, so ownership and status never share a visual variable and a whole-park
polygon can never overstate a small intervention.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(__file__))
import r3_style as S
import r3_05_fig0_base as B

INT = "data/interim/atlas_round3"
gov = gpd.read_file(f"{INT}/green_space_governance.gpkg", layer="green_space_governance")
pts = gpd.read_file(f"{INT}/renovation_project_locations.gpkg",
                    layer="renovation_project_locations")
boro = B.boro

FAM_COL = {"public": S.FAM_PUBLIC, "private_public": S.FAM_PRIVPUB,
           "community": S.FAM_COMMUNITY}
SUBTYPE = [
    ("NYC Parks property", "public", ""),
    ("Other NYC agency public open space", "public", ".."),
    ("State or federal park", "public", "//"),
    ("Public authority or trust", "public", "xx"),
    ("Zoning POPS", "private_public", ""),
    ("Restrictive-declaration public space", "private_public", "//"),
    ("Privately owned public-access park, non-POPS", "private_public", ".."),
    ("DOT pedestrian plaza / BID-managed space", "private_public", "xx"),
    ("Community garden", "community", ""),
]

def theme(ax, lw=1.0, pt_scale=1.0, tiny_points=True):
    for name, fam, hatch in SUBTYPE:
        g = gov[gov["gov_subtype"] == name]
        if g.empty: continue
        col = FAM_COL[fam]
        if g.geom_type.isin(["Point", "MultiPoint"]).all():
            g.plot(ax=ax, color=col, marker="^", markersize=22 * pt_scale,
                   edgecolor=S.INK, linewidth=.4, zorder=12)
        else:
            g.plot(ax=ax, facecolor=col, edgecolor=S.INK, linewidth=.22 * lw,
                   hatch=hatch or None, alpha=.92, zorder=11)
            if tiny_points and name in ("Community garden", "Zoning POPS",
                    "DOT pedestrian plaza / BID-managed space",
                    "Restrictive-declaration public space",
                    "Privately owned public-access park, non-POPS"):
                c = g.copy(); c["geometry"] = c.geometry.representative_point()
                c.plot(ax=ax, color=col, markersize=9 * pt_scale, edgecolor=S.INK,
                       linewidth=.35, zorder=13)
    for z, ph in enumerate(S.PHASE_ORDER, start=20):
        sel = pts[pts["phase_display"] == ph]
        if sel.empty: continue
        small = ph == "Completed"
        sel.plot(ax=ax, color=S.PHASE[ph], marker="o",
                 markersize=(7 if small else 26) * pt_scale,
                 alpha=.75 if small else .95,
                 edgecolor="white", linewidth=.0 if small else .5, zorder=z)

def legend_handles():
    h = [Patch(facecolor=FAM_COL[f], edgecolor=S.INK, lw=.4, hatch=ha or None,
               label=f"{n} — {int((gov.gov_subtype==n).sum()):,}")
         for n, f, ha in SUBTYPE]
    p = [Line2D([], [], ls="", marker="o", ms=4.5 if ph == "Completed" else 8,
                color=S.PHASE[ph], mec="white", mew=.6,
                label=f"{ph} — {int((pts.phase_display==ph).sum()):,}")
         for ph in S.PHASE_ORDER]
    return h, p

CAPTION = ("Limitation: ownership polygons are official register geometry; renovation "
           "status is shown on administrative project-location POINTS, not on site "
           "polygons, because a PIP subsite or whole park-property polygon is a matched "
           "SITE and not a verified construction footprint. One project may hold several "
           "project-location records. 284 inventory records carry (0,0) placeholder "
           "coordinates and are excluded from every map while remaining in the inventory.")

def render(stem, extent=None, title=None, sub=None, figsize=(15.5, 15.4),
           lw=1.0, pt=1.0, legend=True, mi=2):
    fig, ax = plt.subplots(figsize=figsize)
    fig.subplots_adjust(left=.025, right=.99, top=.905, bottom=.095)
    B.draw(ax, extent=extent, lw_scale=lw, bld_alpha=.13, pop_alpha=.42,
           stations=extent is not None)
    theme(ax, lw=lw, pt_scale=pt, tiny_points=extent is None)
    S.north_arrow(ax); S.scale_bar(ax, mi, x=.045, y=.03)
    if extent is None:
        for _, r in boro.iterrows():
            c = r.geometry.representative_point()
            ax.annotate(r["boroname"], (c.x, c.y), fontsize=10, weight="bold",
                        color=S.INK_2, ha="center", zorder=40, alpha=.8)
    if legend:
        hg, hp = legend_handles()
        l1 = ax.legend(handles=hg, loc="upper left", bbox_to_anchor=(.004, .996),
                       frameon=True, framealpha=.96, edgecolor=S.MUTED, fontsize=8.2,
                       borderpad=.8, labelspacing=.5,
                       title="Green space — ownership / governance\n"
                             "fill = family · hatch = subtype", title_fontsize=8.8)
        l1.get_title().set_fontweight("bold"); ax.add_artist(l1)
        ax.legend(handles=hp, loc="upper left", bbox_to_anchor=(.004, .700),
                  frameon=True, framealpha=.96, edgecolor=S.MUTED, fontsize=8.2,
                  borderpad=.8, labelspacing=.5,
                  title="Capital project location — current phase", title_fontsize=8.8
                  ).get_title().set_fontweight("bold")
    fig.text(.025, .968, title, fontsize=18.5, weight="bold", color=S.INK, va="top")
    fig.text(.025, .938, sub, fontsize=10.2, color=S.INK_2, va="top")
    fig.text(.025, .062, CAPTION, fontsize=7.4, color=S.INK_2, va="top", style="italic",
             wrap=True)
    fig.text(.025, .022, f"{S.SRC_THEME}  Base: {S.SRC_BASE}  Snapshot {S.SNAPSHOT}. "
             "EPSG:2263. No online basemap.", fontsize=6.2, color=S.MUTED, va="top",
             wrap=True)
    return S.save(fig, stem)

if __name__ == "__main__":
    render("map1_green_space_ownership_and_renovation_status", None,
           "Green space ownership and renovation status",
           "Nine governance categories grouped into three cartographic families; "
           "capital project locations coloured by current phase.")
    BOR = [("map1a_bronx_green_space_detail", "Bronx"),
           ("map1b_brooklyn_green_space_detail", "Brooklyn"),
           ("map1c_manhattan_green_space_detail", "Manhattan"),
           ("map1d_queens_green_space_detail", "Queens"),
           ("map1e_staten_island_green_space_detail", "Staten Island")]
    for stem, name in BOR:
        b = boro[boro["boroname"] == name]
        x0, y0, x1, y1 = b.total_bounds
        pad = max(x1 - x0, y1 - y0) * .04
        ext = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        asp = (y1 - y0 + 2*pad) / (x1 - x0 + 2*pad)
        w = 13.5; fsz = (w, min(max(w * asp * 1.16, 9.5), 17.5))
        render(stem, ext, f"{name}: green space ownership and renovation status",
               "Same legend, colours and symbology as the citywide figure — a detailed "
               "view, not a separately styled map.", figsize=fsz, lw=2.2, pt=2.6, mi=1)
    print("\ndone")
