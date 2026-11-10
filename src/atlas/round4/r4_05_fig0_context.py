"""Round 4 Figure 0 — NYC context: population, transport, built form. No thematic data."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm, Normalize
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(__file__))
import r4_04_style as S

I3 = "data/interim/atlas_round3"
rd = lambda f, l: gpd.read_file(f"{I3}/{f}.gpkg", layer=l)
boro, pop = rd("boroughs", "boroughs"), rd("population_bg_2023", "population_bg_2023")
bld = rd("buildings_cartographic", "buildings_cartographic")
stp = rd("streets_principal", "streets_principal")
sr, ss = rd("subway_routes", "subway_routes"), rd("subway_stations", "subway_stations")

valid = pop[pop["pop_state"] == "valid"]
q = sorted(set(round(float(valid["density_display"].quantile(x))) for x in (0,.25,.5,.75,1.0)))
cmap = LinearSegmentedColormap.from_list("pop", S.POP_RAMP, N=len(q)-1)
norm = BoundaryNorm(q, cmap.N)
bcm = LinearSegmentedColormap.from_list("b", ["#DDE0DA", "#AEB2AB"], N=48)
bn = Normalize(0, float(bld["built_coverage"].quantile(.95)))

fig = plt.figure(figsize=(14.5, 15.2))
gs = GridSpec(1, 1, figure=fig, left=.025, right=.985, top=.895, bottom=.10)
ax = fig.add_subplot(gs[0, 0])
boro.plot(ax=ax, facecolor=S.LAND, edgecolor="none", zorder=1)
valid.plot(ax=ax, column="density_display", cmap=cmap, norm=norm, edgecolor="none", zorder=2)
pop[pop["pop_state"] != "valid"].plot(ax=ax, facecolor=S.POP_ZERO, edgecolor="none", zorder=2)
bld.plot(ax=ax, column="built_coverage", cmap=bcm, norm=bn, edgecolor="none",
         alpha=.22, zorder=3)
stp.plot(ax=ax, color=S.ST_PRINCIPAL, linewidth=.45, zorder=5)
sr.plot(ax=ax, color=S.SUBWAY, linewidth=.95, alpha=.95, zorder=6)
ss.plot(ax=ax, color=S.STATION, markersize=2.0, alpha=.85, zorder=7)
boro.boundary.plot(ax=ax, color=S.EDGE, linewidth=1.0, zorder=8)
S.blank(ax); S.north_arrow(ax); S.scale_bar(ax, 2, x=.045, y=.03)
for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r["boroname"], (c.x, c.y), fontsize=S.BORO_LBL, weight="bold",
                color=S.INK_2, ha="center", zorder=20, alpha=.85)

h = [Patch(facecolor=cmap(i), edgecolor="none",
           label=f"{int(q[i]):,} - {int(q[i+1]):,}") for i in range(len(q)-1)]
h += [Patch(facecolor=S.POP_ZERO, edgecolor="none", label="zero population"),
      Patch(facecolor="#AEB2AB", edgecolor="none", label="built form (500 ft grid)"),
      Line2D([], [], color=S.ST_PRINCIPAL, lw=1.2, label="principal street"),
      Line2D([], [], color=S.SUBWAY, lw=1.2, label="subway route"),
      Line2D([], [], ls="", marker="o", ms=2.8, color=S.STATION, label="subway station")]
lg = ax.legend(handles=h, loc="upper left", bbox_to_anchor=(.004, .996), frameon=True,
               framealpha=.95, edgecolor=S.MUTED, fontsize=S.LEGEND, borderpad=.8,
               labelspacing=.5, title="Population per square mile of land\n"
               "(ACS 2023 5-year, block group)", title_fontsize=9.0)
lg.get_title().set_fontweight("bold")

fig.text(.025, .972, "Population, Transport, and Built Form in New York City",
         fontsize=S.TITLE, weight="bold", color=S.INK, va="top")
fig.text(.025, .935, "Population density, principal streets, subway routes, and generalized built form",
         fontsize=S.SUBTITLE, color=S.INK_2, va="top")
fig.text(.025, .068, "Population density is calculated per square mile of TIGER land area (ALAND). "
         "The four classes are quartiles of values clipped to the 2nd-98th percentile; raw "
         "values are retained. Minor streets are omitted. Built form is generalized to a "
         "500 ft grid for citywide display.", fontsize=S.NOTE, color=S.INK_2, va="top", style="italic")
fig.text(.025, .028, f"{S.SRC_BASE}  Snapshot {S.SNAPSHOT}. EPSG:2263. No online basemap.",
         fontsize=7.5, color=S.MUTED, va="top")
S.save(fig, "fig0_nyc_context_population_transport")
print(f"  pop classes {q}")
