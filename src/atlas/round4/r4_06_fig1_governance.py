"""Round 4 Figure 1 — who governs NYC's green and public open space. Polygons only."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(__file__))
import r4_04_style as S

I3, I4 = "data/interim/atlas_round3", "data/interim/atlas_round4"
gov = gpd.read_file(f"{I4}/governance_display_polygons.gpkg",
                    layer="governance_display_polygons")
boro = gpd.read_file(f"{I3}/boroughs.gpkg", layer="boroughs")
assert int(gov.geom_type.isin(["Point", "MultiPoint"]).sum()) == 0

fig = plt.figure(figsize=(19.5, 14.6))
gs = GridSpec(3, 2, figure=fig, width_ratios=[1.0, .42], height_ratios=[.30, .30, .40],
              wspace=.045, hspace=.16, left=.022, right=.985, top=.885, bottom=.085)
axm = fig.add_subplot(gs[:, 0])
boro.plot(ax=axm, facecolor=S.LAND, edgecolor="none", zorder=1)
for fam in S.GOV_ORDER:                      # citywide: five families, no hatching
    sub = gov[gov.display_family == fam]
    if sub.empty: continue
    col = S.GOV[fam]
    sub.plot(ax=axm, facecolor=col, edgecolor=col, linewidth=.22, alpha=.96, zorder=3)
boro.boundary.plot(ax=axm, color=S.EDGE, linewidth=1.1, zorder=8)
S.blank(axm); S.north_arrow(axm); S.scale_bar(axm, 2, x=.045, y=.03)
for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    axm.annotate(r["boroname"], (c.x, c.y), fontsize=S.BORO_LBL, weight="bold",
                 color=S.INK_2, ha="center", zorder=20, alpha=.85)

# legend, five families only
axl = fig.add_subplot(gs[0, 1]); axl.axis("off")
h = [Patch(facecolor=S.GOV[f], edgecolor=S.GOV[f], label=f) for f in S.GOV_ORDER]
axl.legend(handles=h, loc="upper left", frameon=False, fontsize=S.LEGEND + .4,
           labelspacing=.72, handlelength=1.5, handleheight=1.15,
           title="Governance category", title_fontsize=10
           ).get_title().set_fontweight("bold")

# bar chart of the nine source subtypes
axb = fig.add_subplot(gs[1, 1])
cnt = gov["gov_subtype"].value_counts().sort_values()
cols = [S.GOV[gov.loc[gov.gov_subtype == k, "display_family"].iloc[0]] for k in cnt.index]
axb.barh(range(len(cnt)), cnt.values, color=cols, height=.68, zorder=3)
for i, v in enumerate(cnt.values):
    axb.text(v + cnt.max() * .02, i, f"{v:,}", va="center", fontsize=7.8, color=S.INK)
axb.set_yticks(range(len(cnt)))
SUBTYPE_LABEL = {
    "NYC Parks property": "NYC Parks property",
    "Community garden": "Community gardens",
    "Zoning POPS": "Zoning POPS",
    "Other NYC agency public open space": "Other NYC agencies",
    "DOT pedestrian plaza / BID-managed space": "DOT/BID plazas",
    "Privately owned public-access park, non-POPS": "Private public-access parks",
    "Restrictive-declaration public space": "Restrictive declarations",
    "Public authority or trust": "Public authorities/trusts",
    "State or federal park": "State/federal parks",
}
axb.set_yticklabels([SUBTYPE_LABEL.get(k, k) for k in cnt.index], fontsize=7.6)
axb.set_xlim(0, cnt.max() * 1.18); axb.set_xticks([])
axb.tick_params(colors=S.INK_2, length=0)
for sp in ("top", "right", "bottom", "left"): axb.spines[sp].set_visible(False)
axb.set_title("Mapped spaces by source subtype", fontsize=9.6, color=S.INK,
              loc="left", pad=6, weight="bold")

# Manhattan inset, nine subtypes, at most three hatches
axi = fig.add_subplot(gs[2, 1])
man = boro[boro.boroname == "Manhattan"]
x0, y0, x1, y1 = man.total_bounds; pad = (y1 - y0) * .02
man.plot(ax=axi, facecolor=S.LAND, edgecolor="none", zorder=1)
HATCH = {"Other NYC agency public open space": "..",
         "Restrictive-declaration public space": "//",
         "DOT pedestrian plaza / BID-managed space": "xx"}
for st in gov["gov_subtype"].unique():
    sub = gov[gov.gov_subtype == st]
    if sub.empty: continue
    fam = sub["display_family"].iloc[0]; col = S.GOV[fam]
    sub.plot(ax=axi, facecolor=col, edgecolor=col, linewidth=.3,
             hatch=HATCH.get(st), alpha=.96, zorder=3)
man.boundary.plot(ax=axi, color=S.EDGE, linewidth=.9, zorder=8)
S.blank(axi); axi.set_xlim(x0 - pad, x1 + pad); axi.set_ylim(y0 - pad, y1 + pad)
axi.set_title("Manhattan inset: nine source subtypes\n"
              "Hatching: NYC agency (dots); declaration (//); DOT/BID (xx)",
              fontsize=9.0, color=S.INK, loc="left", pad=6)

fig.text(.022, .972, "Governance of Green and Public Open Space in New York City",
         fontsize=S.TITLE, weight="bold", color=S.INK, va="top")
fig.text(.022, .935, "Five citywide governance categories; nine source subtypes are shown in the Manhattan inset.",
         fontsize=S.SUBTITLE,
         color=S.INK_2, va="top")
n_pops_parcel = int((gov.geometry_role == "tax_lot_proxy").sum())
fig.text(.022, .058,
         f"The map contains {len(gov):,} polygon records. {n_pops_parcel} zoning POPS are represented "
         "by their MapPLUTO owning parcels; these parcel proxies do not delineate the surveyed "
         "public-access areas. Records without resolved polygon geometry are excluded and listed "
         "in the QA file.", fontsize=S.NOTE, color=S.INK_2, va="top", style="italic")
fig.text(.022, .022, f"{S.SRC_GOV}  Snapshot {S.SNAPSHOT}. EPSG:2263. No online basemap.",
         fontsize=7.5, color=S.MUTED, va="top")
S.save(fig, "fig1_open_space_governance_polygons")
print("  families:", gov.display_family.value_counts().to_dict())
