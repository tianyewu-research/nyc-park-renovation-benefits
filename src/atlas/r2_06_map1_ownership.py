"""Round 2 Map 1 — NYC Green Spaces by Ownership and Governance."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, matplotlib.pyplot as plt
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style_round2 as S

G = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
rd = lambda l: gpd.read_file(G, layer=l)
boro = rd("boroughs")

# fill = governance FAMILY (3 validated colours); hatch = SUBTYPE
SPEC = [
    ("parks_properties",              "NYC Parks property",                        S.GOV_PUBLIC,      ""),
    ("other_public_open_space",       "Other NYC agency public open space",        S.GOV_PUBLIC,      ".."),
    ("state_federal_open_space",      "State or federal park",                     S.GOV_PUBLIC,      "//"),
    ("public_authority_or_trust",     "Public authority or trust",                 S.GOV_PUBLIC,      "\\\\"),
    ("zoning_pops",                   "Zoning POPS",                               S.GOV_PRIVATE_PUB, ""),
    ("restrictive_declaration_sites", "Restrictive-declaration public space",      S.GOV_PRIVATE_PUB, "//"),
    ("waterfront_public_access_areas","Privately owned public-access, non-POPS",   S.GOV_PRIVATE_PUB, ".."),
    ("dot_pedestrian_plazas",         "DOT pedestrian plaza / BID-managed",        S.GOV_PRIVATE_PUB, "xx"),
    ("community_gardens",             "Community garden",                          S.GOV_COMMUNITY,   ""),
]

fig, ax = plt.subplots(figsize=(16.5, 17.4))
fig.subplots_adjust(left=.025, right=.99, top=.90, bottom=.105)
boro.plot(ax=ax, facecolor=S.LAND, edgecolor="white", lw=1.8, zorder=1)
boro.boundary.plot(ax=ax, color=S.SHORE, lw=1.0, zorder=2)

counts, handles = {}, []
for z, (lyr, label, fill, hatch) in enumerate(SPEC, start=3):
    g = rd(lyr); counts[label] = len(g)
    pts = g.geom_type.isin(["Point", "MultiPoint"]).all()
    if pts:
        g.plot(ax=ax, color=fill, markersize=26, alpha=.95, marker="^",
               edgecolor=S.INK, linewidth=.45, zorder=z + 20)
    else:
        g.plot(ax=ax, facecolor=fill, edgecolor=S.INK, linewidth=.28,
               hatch=hatch or None, alpha=.95, zorder=z)
        # small polygons need a visible edge to register at citywide scale
        if lyr in ("community_gardens", "zoning_pops", "dot_pedestrian_plazas",
                   "restrictive_declaration_sites", "waterfront_public_access_areas"):
            c = g.copy(); c["geometry"] = c.geometry.representative_point()
            c.plot(ax=ax, color=fill, markersize=11, alpha=.95,
                   edgecolor=S.INK, linewidth=.4, zorder=z + 20)
    handles.append(Patch(facecolor=fill, edgecolor=S.INK, lw=.5, hatch=hatch or None,
                         label=f"{label} — {len(g):,}"))

S.blank(ax); S.north_arrow(ax); S.scale_bar(ax, 2, x=.045, y=.035)
for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r["boroname"], (c.x, c.y), fontsize=11, weight="bold",
                color="#878984", ha="center", zorder=60)

leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(.004, .996),
                frameon=True, framealpha=.97, edgecolor=S.MUTED, fontsize=9.8,
                borderpad=1.0, labelspacing=.7, title="Governance category",
                title_fontsize=11)
leg.get_title().set_fontweight("bold")
ax.text(.004, .705, "Fill colour = governance family\n"
        "   teal  public owner        rust  private-public arrangement\n"
        "   cream  community-managed\n"
        "Hatch = subtype within the family, so colour alone never carries identity.\n"
        "Small polygons also drawn at a representative point for citywide\n"
        "visibility — the point is a visibility symbol, not the real area.",
        transform=ax.transAxes, fontsize=9.0, va="top", color=S.INK_2, linespacing=1.6,
        bbox=dict(boxstyle="round,pad=.7", facecolor="white", edgecolor=S.MUTED, alpha=.96))

S.title_block(fig, "NYC Green Spaces by Ownership and Governance",
    "Nine governance categories from official registers. Zoning POPS, "
    "restrictive-declaration space, privately owned public-access parks and "
    "DOT/BID plazas are coded separately, not merged into one 'POPS' class.")
S.footer(fig,
    "Governance is read from official register fields, not inferred. State and "
    "federal parks are shown as points because the Facilities Database carries no "
    "polygons. A privately owned public-access park that is neither a zoning POPS, "
    "a restrictive-declaration site nor a WPAA cannot be derived from any open "
    "dataset and is therefore absent here rather than guessed.", y0=.070)
S.save(fig, "map1_green_space_ownership_governance")
print("  counts:", {k: v for k, v in counts.items()})
