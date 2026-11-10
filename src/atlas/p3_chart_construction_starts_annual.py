"""Figure B — recorded construction starts by year and borough.

Split out of the old combined figure so the yearly record is not read as if it
maps one-to-one onto the phase map. Presentation only: no data, cleaning rule,
GeoPackage or sample changes.

Borough comes from a spatial join against the borough polygons, NOT from the raw
Borough string, which contains multi-borough and concatenated values
("Bronx, Queens", "BronxManhattan"). Missing dates are excluded, never imputed.

Stack order is fixed; the borough colours are the reference palette slots 1-5 in
slot order, checked on the stacked (adjacent) pairlist: worst adjacent CVD dE
8.0, worst normal-vision dE 17.0, against floors of 8 and 15.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style as S

GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
SNAPSHOT_YEAR = 2026
YEAR_MIN, YEAR_MAX_PLAUSIBLE = 2008, 2040

BORO_ORDER = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island",
              "Unknown / unmatched"]
BORO_COL = {"Bronx": "#2a78d6", "Brooklyn": "#eb6834", "Manhattan": "#1baf7a",
            "Queens": "#eda100", "Staten Island": "#e87ba4",
            "Unknown / unmatched": "#898781"}

g = gpd.read_file(GPKG, layer="renovation_project_locations")
boro = gpd.read_file(GPKG, layer="boroughs")[["boroname", "geometry"]]

# --- spatial join: assign borough from the point, not the raw string ---------
j = gpd.sjoin(g, boro, how="left", predicate="within")
j = j[~j.index.duplicated(keep="first")]          # a point on a shared edge
g["Mapped_Borough"] = j["boroname"].fillna("Unknown / unmatched").values
n_unmatched = int((g["Mapped_Borough"] == "Unknown / unmatched").sum())

# --- dates -------------------------------------------------------------------
cs = pd.to_datetime(g["Construction_Start"], errors="coerce")
yr = cs.dt.year
valid = yr.notna() & yr.between(YEAR_MIN, YEAR_MAX_PLAUSIBLE)
n_valid, n_missing = int(valid.sum()), int(len(g) - valid.sum())

d = pd.DataFrame({"year": yr[valid].astype(int),
                  "boro": g.loc[valid, "Mapped_Borough"]})
YEARS = list(range(YEAR_MIN, int(d["year"].max()) + 1))
pivot = (d.groupby(["year", "boro"]).size().unstack(fill_value=0)
         .reindex(index=YEARS, fill_value=0)
         .reindex(columns=BORO_ORDER, fill_value=0))
totals = pivot.sum(axis=1)

# --- plot --------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(15.0, 7.6))
fig.subplots_adjust(left=.055, right=.985, top=.80, bottom=.205)

bottom = np.zeros(len(YEARS))
for b in BORO_ORDER:
    v = pivot[b].values
    if v.sum() == 0:
        continue
    ax.bar(YEARS, v, bottom=bottom, width=.74, label=b, color=BORO_COL[b],
           edgecolor="white", linewidth=.55, zorder=3)
    bottom += v

# partial / future-dated years get a texture and a lighter outline
for y, hatch in ((SNAPSHOT_YEAR, "//"), (SNAPSHOT_YEAR + 1, "xx")):
    if y in YEARS:
        ax.bar([y], [totals[y]], width=.74, facecolor="none",
               edgecolor="#3a3a38", linewidth=.9, hatch=hatch, zorder=4)

if SNAPSHOT_YEAR in YEARS:
    ax.axvline(SNAPSHOT_YEAR - .5, color=S.INK_2, lw=1.1, ls=(0, (4, 3)), zorder=5)

for y in YEARS:
    if totals[y] > 0:
        ax.text(y, totals[y] + totals.max() * .028, f"{int(totals[y])}",
                ha="center", va="bottom", fontsize=8.2, color=S.INK, zorder=6)

ax.set_xticks(YEARS)
ax.set_xticklabels(YEARS, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("Project locations", fontsize=10, color=S.INK_2)
ax.set_ylim(0, totals.max() * 1.16)
ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
ax.tick_params(colors=S.INK_2, length=0, labelsize=9)
ax.grid(axis="y", color=S.MUTED, alpha=.22, lw=.6, zorder=0)
ax.set_axisbelow(True)
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(S.MUTED)

leg = ax.legend(loc="upper left", bbox_to_anchor=(0, 1.135), ncol=6,
                frameon=False, fontsize=9.5, columnspacing=1.6,
                handlelength=1.1, handleheight=1.1)

n26 = int(totals.get(SNAPSHOT_YEAR, 0))
n27 = int(totals.get(SNAPSHOT_YEAR + 1, 0))
# placed in the empty upper-left block above the short early years, with no
# leader lines: arrows to 2026/2027 would have to cross the tallest bars
note = (f"Hatched bars sit to the right of the dashed line:\n"
        f"   {SNAPSHOT_YEAR}  partial year through the snapshot date (n={n26})\n"
        f"   {SNAPSHOT_YEAR+1}  future-dated administrative records (n={n27})")
ax.text(YEARS[0] - .35, totals.max() * 1.055, note, fontsize=8.8,
        color=S.INK_2, va="top", ha="left", linespacing=1.6,
        bbox=dict(boxstyle="round,pad=0.6", facecolor="white",
                  edgecolor=S.MUTED, alpha=.95, linewidth=.7))

fig.text(.055, .965, "Recorded construction starts by year and borough",
         fontsize=18, weight="bold", color=S.INK, va="top")
fig.text(.055, .922,
         "Mapped project locations with a valid Construction_Start date; "
         "borough is assigned from point location.",
         fontsize=10.5, color=S.INK_2, va="top")

NOTES = [
    f"Included locations with a valid Construction_Start date: n = {n_valid:,}",
    f"Missing Construction_Start date: n = {n_missing:,}. Missing dates are excluded "
    "and never imputed.",
    f"{SNAPSHOT_YEAR} is an incomplete observation year at the {S.SNAPSHOT} snapshot date.",
    "Future-dated records are administrative records and should not be interpreted "
    "as completed starts.",
    f"Borough assigned by spatial join to borough polygons. {n_unmatched} of the "
    f"{len(g):,} mapped locations fell outside every polygon; "
    f"{int(pivot['Unknown / unmatched'].sum())} of those also carry a valid date and "
    "appear in the Unknown / unmatched segment.",
]
y = .145
for t in NOTES:
    fig.text(.055, y, "•  " + t, fontsize=8.3, color=S.INK_2, va="top")
    y -= .0225
fig.text(.055, .022,
         "Source: NYC Parks Capital Project Tracker (4hcv-tc5r); Borough Boundaries "
         f"(gthc-hcne).  Snapshot {S.SNAPSHOT}.  Points projected in EPSG:2263.",
         fontsize=7.4, color=S.MUTED, va="top")

for ext in ("png", "pdf"):
    p = f"maps/chart_construction_starts_by_year.{ext}"
    fig.savefig(p, dpi=300 if ext == "png" else None,
                bbox_inches="tight", facecolor="white")
    print(f"  wrote {p}")
plt.close(fig)

print("\n--- QA: annual construction starts ---")
print(f"  mapped locations              {len(g):,}")
print(f"  valid Construction_Start      {n_valid:,}")
print(f"  missing Construction_Start    {n_missing:,}")
print(f"  bar total across all years    {int(totals.sum()):,}   "
      f"({'matches' if int(totals.sum()) == n_valid else 'MISMATCH vs'} valid)")
print(f"  {SNAPSHOT_YEAR}: {n26}    {SNAPSHOT_YEAR+1}: {n27}")
print("\n  borough after spatial join:")
for b in BORO_ORDER:
    print(f"    {b:<22} {int(pivot[b].sum()):>6,}")
print(f"    {'unmatched (all rows)':<22} {n_unmatched:>6,}")
