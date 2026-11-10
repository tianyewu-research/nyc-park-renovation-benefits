"""Round 3 Figure 0 — five-borough contextual base map."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
sys.path.insert(0, os.path.dirname(__file__))
import r3_style as S

INT = "data/interim/atlas_round3"
rd = lambda f, l: gpd.read_file(f"{INT}/{f}.gpkg", layer=l)

boro   = rd("boroughs", "boroughs")
pop    = rd("population_bg_2023", "population_bg_2023")
bld    = rd("buildings_cartographic", "buildings_cartographic")
st_all = rd("streets_all", "streets_all")
st_pri = rd("streets_principal", "streets_principal")
sub_r  = rd("subway_routes", "subway_routes")
sub_s  = rd("subway_stations", "subway_stations")

valid = pop[pop["pop_state"] == "valid"]
q = [valid["density_display"].quantile(x) for x in (0, .2, .4, .6, .8, 1.0)]
q = sorted(set(round(float(v)) for v in q))
cmap = LinearSegmentedColormap.from_list("popteal", S.POP_RAMP, N=len(q) - 1)
BLD_CMAP = LinearSegmentedColormap.from_list("bld", ["#BFC3BC", "#6E736C"], N=64)
from matplotlib.colors import Normalize
BLD_NORM = Normalize(vmin=0.0, vmax=float(bld["built_coverage"].quantile(.95)))
norm = BoundaryNorm(q, cmap.N)

def draw(ax, extent=None, lw_scale=1.0, bld_alpha=.24, pop_alpha=1.0, stations=True):
    boro.plot(ax=ax, facecolor=S.LAND, edgecolor="none", zorder=1)
    valid.plot(ax=ax, column="density_display", cmap=cmap, norm=norm,
               edgecolor="none", alpha=pop_alpha, zorder=2)
    pop[pop["pop_state"] != "valid"].plot(ax=ax, facecolor=S.POP_ZERO,
                                          edgecolor="none", alpha=pop_alpha, zorder=2)
    # built mass reads as urban grain: darker where coverage is higher
    bld.plot(ax=ax, column="built_coverage", cmap=BLD_CMAP, norm=BLD_NORM,
             edgecolor="none", alpha=float(np.clip(bld_alpha, 0, 1)), zorder=3)
    st_all.plot(ax=ax, color=S.ST_MINOR, linewidth=.09 * lw_scale, alpha=.75, zorder=4)
    st_pri.plot(ax=ax, color=S.ST_PRINCIPAL, linewidth=.45 * lw_scale, zorder=5)
    sub_r.plot(ax=ax, color=S.SUBWAY, linewidth=.95 * lw_scale, alpha=.95, zorder=6)
    if stations:
        sub_s.plot(ax=ax, color=S.STATION, markersize=2.2 * lw_scale**2,
                   alpha=.85, zorder=7)
    boro.boundary.plot(ax=ax, color=S.SHORE, linewidth=.9 * lw_scale, zorder=8)
    S.blank(ax)
    if extent: ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])

if __name__ == "__main__":
    fig, ax = plt.subplots(figsize=(15.5, 15.4))
    fig.subplots_adjust(left=.025, right=.99, top=.905, bottom=.095)
    draw(ax)
    S.north_arrow(ax); S.scale_bar(ax, 2, x=.045, y=.03)
    for _, r in boro.iterrows():
        c = r.geometry.representative_point()
        ax.annotate(r["boroname"], (c.x, c.y), fontsize=10.5, weight="bold",
                    color=S.INK_2, ha="center", zorder=20, alpha=.85)

    lab = [f"{int(q[i]):,} – {int(q[i+1]):,}" for i in range(len(q) - 1)]
    h = [Patch(facecolor=cmap(i), edgecolor="none", label=lab[i]) for i in range(len(q) - 1)]
    h += [Patch(facecolor=S.POP_ZERO, edgecolor="none",
                label=f"zero population ({int((pop.pop_state=='zero_population').sum())} BGs)"),
          Patch(facecolor=S.BLDG, edgecolor="none", label="built mass (500 ft grid)"),
          Line2D([], [], color=S.ST_PRINCIPAL, lw=1.1, label="principal road"),
          Line2D([], [], color=S.ST_MINOR, lw=.8, label="other street"),
          Line2D([], [], color=S.SUBWAY, lw=1.1, label="subway route"),
          Line2D([], [], ls="", marker="o", ms=2.6, color=S.STATION, label="subway station")]
    lg = ax.legend(handles=h, loc="upper left", bbox_to_anchor=(.004, .996), frameon=True,
                   framealpha=.95, edgecolor=S.MUTED, fontsize=8.6, borderpad=.85,
                   labelspacing=.5,
                   title="Population per square mile of land\n(ACS 2023 5-yr, block group)",
                   title_fontsize=9.0)
    lg.get_title().set_fontweight("bold")

    fig.text(.025, .968, "New York City contextual base", fontsize=19, weight="bold",
             color=S.INK, va="top")
    fig.text(.025, .938, "Population density, built mass, street fabric and rapid transit "
             "across the five boroughs.", fontsize=10.5, color=S.INK_2, va="top")
    fig.text(.025, .062,
             "Limitation: density uses ACS 2023 5-year total population over TIGER land "
             "area (ALAND), so water is excluded; classes are quintiles of values clipped "
             "to the 2nd–98th percentile for display while raw values are retained; zero "
             "and missing population are kept as separate states, not shaded as low density.",
             fontsize=7.8, color=S.INK_2, va="top", style="italic")
    fig.text(.025, .026, f"{S.SRC_BASE}  Snapshot {S.SNAPSHOT}. Analysis CRS EPSG:2263 "
             "(NAD83 / New York Long Island, US ft). No online basemap.",
             fontsize=6.6, color=S.MUTED, va="top")
    S.save(fig, "map0_nyc_context_base")
    print(f"  pop classes {q} | zero {int((pop.pop_state=='zero_population').sum())} | "
          f"bld cells {len(bld):,} | streets {len(st_all):,} (principal {len(st_pri):,}) | "
          f"subway {len(sub_r)} routes / {len(sub_s)} stations")
