"""Step 4 — shared spatial assets: locator, context maps, 800 m demographic profiles."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C, cs_fig as F
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

R4G, R3 = C.p("atlas_r4"), C.p("round3")
boro = gpd.read_file(R4G, layer="boroughs")
gov = gpd.read_file(R4G, layer="governance_display_polygons")
bld = gpd.read_file(R4G, layer="buildings_cartographic")
stp = gpd.read_file(R4G, layer="streets_principal")
sub = gpd.read_file(R4G, layer="subway_routes")
sta = gpd.read_file(R4G, layer="subway_stations")
parks = gpd.read_file(C.p("atlas_r2"), layer="parks_properties")
cbg = gpd.read_file(C.p("cbg"))
acs = pd.read_csv(C.p("acs"), dtype={"GEOID": str}, low_memory=False)
cbg["GEOID"] = cbg["GEOID"].astype(str)
cbg = cbg.merge(acs, on="GEOID", how="left")

SITES = {}
for cid, cfg in C.CASES.items():
    g = parks[parks["Site_Key"].astype(str) == cfg["park_id"]]
    if g.empty:
        raise SystemExit(f"{cid}: no park polygon for {cfg['park_id']}")
    SITES[cid] = g.dissolve().reset_index(drop=True)
    SITES[cid]["case_id"] = cid

# ---- S01 citywide locator --------------------------------------------------
fig, ax = plt.subplots(figsize=C.ASPECTS["1:1"])
boro.plot(ax=ax, facecolor=F.LAND, edgecolor="none", zorder=1)
gov.plot(ax=ax, facecolor="#DFE6DF", edgecolor="none", zorder=2)
boro.boundary.plot(ax=ax, color=F.EDGE, lw=.9, zorder=3)
rows = []
for cid, g in SITES.items():
    g.plot(ax=ax, facecolor=F.RUST, edgecolor=F.RUST, lw=1.0, zorder=6)
    c = g.geometry.iloc[0].representative_point()
    ax.annotate(cid, (c.x, c.y), xytext=(0, 26), textcoords="offset points",
                fontsize=10, weight="bold", color=F.INK, ha="center", zorder=8,
                bbox=dict(boxstyle="round,pad=.28", fc=F.BG, ec=F.RUST, lw=.9))
    rows.append(dict(case_id=cid, name=C.CASES[cid]["name"],
                     park_id=C.CASES[cid]["park_id"],
                     acres=round(float(g.geometry.area.iloc[0]) / 43560, 2)))
F.blank(ax); F.north_arrow(ax); F.scale_bar(ax, 2, x=.05, y=.03)
for _, r in boro.iterrows():
    p = r.geometry.representative_point()
    ax.annotate(r["boroname"], (p.x, p.y), fontsize=7.5, color=F.MUTED,
                ha="center", zorder=4)
ax.set_title("Three case parks in New York City", fontsize=12, color=F.INK,
             loc="left", pad=8, weight="bold")
F.source_line(fig, "Park polygons: NYC Parks Properties (enfh-gkve). Open space: "
              "round 4 governance layer. EPSG:2263.")
F.export(fig, os.path.join(C.SHARED, "maps"), "S01_three_case_locations_nyc",
         "Three case parks in New York City",
         "BP Bryant Park (M008), WSP Washington Square Park (M098), MCP McCarren Park (B058), "
         "shown as park polygons against the citywide open-space network.",
         "Park polygons dissolved from NYC Parks Properties by park_id.",
         "park site", "NYC Parks Properties enfh-gkve; round 4 atlas GeoPackage",
         pd.DataFrame(rows), kind="map")

# ---- per-case context + demographics --------------------------------------
dem_rows = []
for cid, cfg in C.CASES.items():
    site = SITES[cid]
    rings = {}
    for m in C.BUFFERS_M:
        rings[m] = gpd.GeoDataFrame(
            geometry=[site.geometry.iloc[0].buffer(m * C.FT_PER_M)], crs=C.CRS_ANALYSIS)
    ext = rings[800].total_bounds
    pad = (ext[2] - ext[0]) * .06
    fig, ax = plt.subplots(figsize=C.ASPECTS["4:3"])
    boro.plot(ax=ax, facecolor=F.LAND, edgecolor="none", zorder=1)
    bld.plot(ax=ax, color=F.BLDG, alpha=.18, edgecolor="none", zorder=2)
    gov.plot(ax=ax, facecolor="#DCE7DF", edgecolor="none", zorder=3)
    stp.plot(ax=ax, color=F.ST, lw=.7, zorder=4)
    sub.plot(ax=ax, color=F.SUB, lw=1.2, zorder=5)
    sta.plot(ax=ax, color=F.STA, markersize=9, zorder=6)
    for m, col in ((800, "#B9A08C"), (400, "#8E6F57")):
        rings[m].boundary.plot(ax=ax, color=col, lw=1.2, linestyle="--", zorder=7)
    site.plot(ax=ax, facecolor=F.RUST, edgecolor=F.RUST, lw=1.2, alpha=.92, zorder=9)
    F.blank(ax)
    ax.set_xlim(ext[0] - pad, ext[2] + pad); ax.set_ylim(ext[1] - pad, ext[3] + pad)
    F.north_arrow(ax, x=.94); F.scale_bar(ax, 1, x=.05, y=.03)
    h = [Patch(facecolor=F.RUST, edgecolor=F.RUST, label=f"{cfg['name']} (park polygon)"),
         Patch(facecolor="#DCE7DF", edgecolor="none", label="other mapped open space"),
         Line2D([], [], color="#8E6F57", lw=1.4, ls="--", label="400 m radius study area"),
         Line2D([], [], color="#B9A08C", lw=1.4, ls="--", label="800 m radius study area"),
         Line2D([], [], color=F.SUB, lw=1.4, label="subway route"),
         Line2D([], [], ls="", marker="o", ms=4, color=F.STA, label="subway station"),
         Line2D([], [], color=F.ST, lw=1.2, label="principal street")]
    ax.legend(handles=h, loc="upper left", fontsize=6.6, frameon=True, framealpha=.95,
              edgecolor=F.MUTED, borderpad=.6, labelspacing=.42)
    ax.set_title(f"{cfg['name']}: site and surrounding context", fontsize=11.5,
                 color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, "Radius bands are straight-line distance from the park boundary. "
                  "They are NOT walking catchments or network isochrones. "
                  "Sources: NYC Parks Properties; round 3/4 atlas base layers. EPSG:2263.")
    F.export(fig, os.path.join(C.SHARED, "maps"), f"S02_{cid}_context",
             f"{cfg['name']}: site and surrounding context",
             f"Park polygon with 400 m and 800 m radius study areas, principal streets, "
             f"subway routes and stations, and other mapped open space.",
             "Buffers computed in EPSG:2263 (US ft) from the dissolved park polygon.",
             "park site; radius band", "NYC Parks Properties enfh-gkve; atlas base layers",
             kind="map", case_id=cid)

    # overlap-weighted demographic profile in the 800 m band
    ring = rings[800]
    inter = gpd.overlay(cbg, ring, how="intersection")
    inter["frac"] = inter.geometry.area / inter["GEOID"].map(
        cbg.set_index("GEOID").geometry.area)
    inter["pop_w"] = inter["total_pop"] * inter["frac"]
    tot = float(inter["pop_w"].sum())
    prof = dict(case_id=cid, park_id=cfg["park_id"], name=cfg["name"],
                study_area="800 m radius study area",
                n_cbg_intersecting=int(inter["GEOID"].nunique()),
                population_overlap_weighted=round(tot),
                median_hh_income_pop_weighted=round(float(
                    np.nansum(inter["median_hh_income"] * inter["pop_w"]) / tot)) if tot else np.nan)
    for c, lbl in (("pct_white_nh", "pct_white_nh"), ("pct_black", "pct_black"),
                   ("pct_asian", "pct_asian"), ("pct_hispanic", "pct_hispanic")):
        # source columns are fractions (0-1); stored as percent for display
        prof[lbl] = round(float(np.nansum(inter[c] * inter["pop_w"]) / tot) * 100, 1) if tot else np.nan
    dem_rows.append(prof)

dem = pd.DataFrame(dem_rows)
dem.to_csv(os.path.join(C.SHARED, "data", "S03_800m_demographic_profiles.csv"), index=False)
fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.2), sharey=True)
CATS = [("pct_white_nh", "White NH", F.TEAL), ("pct_black", "Black", F.TEAL_M),
        ("pct_asian", "Asian", F.ORANGE), ("pct_hispanic", "Hispanic", R4_H := "#C9A227")]
for ax, (_, r) in zip(axes, dem.iterrows()):
    vals = [r[c] for c, _, _ in CATS]
    ax.bar([l for _, l, _ in CATS], vals, color=[c for _, _, c in CATS], width=.64)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.2, f"{v:.0f}", ha="center", fontsize=8, color=F.INK)
    ax.set_title(f"{r['case_id']} · {r['name'].split(' /')[0]}\n"
                 f"pop {int(r['population_overlap_weighted']):,}",
                 fontsize=9.5, color=F.INK, loc="left", pad=6)
    ax.tick_params(labelsize=8, colors=F.INK_2, length=0)
    ax.set_ylim(0, 100)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color=F.MUTED, alpha=.2, lw=.5); ax.set_axisbelow(True)
axes[0].set_ylabel("% of population", fontsize=9, color=F.INK_2)
fig.suptitle("Current population composition, 800 m radius study area", fontsize=12,
             color=F.INK, x=.02, ha="left", weight="bold", y=.99)
F.source_line(fig, "ACS composition of residents within an 800 m straight-line radius, "
              "overlap-weighted assuming population is uniform within each block group. "
              "Current context only — not a renovation outcome. Source: ACS via "
              "data/interim/reused_walkability/acs_cbg.csv.", y=.005, size=6.6)
fig.tight_layout(rect=(0, .07, 1, .96))
F.export(fig, os.path.join(C.SHARED, "figures"), "S03_800m_demographic_profiles",
         "Current population composition, 800 m radius study area",
         "Overlap-weighted ACS composition of residents within 800 m of each park. "
         "Present-day context, not an outcome of renovation.",
         "CBG polygons intersected with the 800 m ring; population apportioned by area "
         "share under a uniform-within-CBG assumption.",
         "% of overlap-weighted resident population", "ACS via reused_walkability/acs_cbg.csv",
         dem, kind="figure")
n = F.flush_manifest()
print(f"\ncontent_manifest.csv: {n} assets")
print(dem.to_string(index=False))
