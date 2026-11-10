"""Figure A — one large citywide map of capital project locations by current phase.

Replaces the map half of the old combined figure. Nothing about the data,
cleaning rules, GeoPackage or sample changes here; this is presentation only.

Colour note
-----------
The brief asked for red-orange / purple / blue / orange-yellow. The literal
pair (orange #eb6834 for construction, yellow #eda100 for proposed) collapses
under deuteranopia -- OKLab dE 3.7, far under the 8 floor -- so both warm hues
were re-stepped for lightness separation and the purple was moved off blue.
Final set scores worst-pair CVD dE 12.9 and normal-vision dE 16.8, clearing the
8 / 15 floors. Marker shape and size vary by phase as secondary encoding.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style as S

GPKG = "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"

boro = gpd.read_file(GPKG, layer="boroughs")
parks = gpd.read_file(GPKG, layer="parks_properties")
g = gpd.read_file(GPKG, layer="renovation_project_locations")

PH = {"completed": "Completed", "construction": "In construction",
      "procurement": "In procurement", "design": "In design",
      "design-procurement": "In design", "proposed": "Proposed"}
g["phase_group"] = g["Current_Phase"].map(PH).fillna("Other / unknown")

# draw order is deliberate: completed underneath, active work on top
# (name, colour, marker, size, alpha, white edge)
SPEC = [
    ("Completed",       "#a8bccf", "o", 13.0, .42, False),
    ("Proposed",        "#f5c84c", "D", 40.0, .88, True),
    ("In design",       "#2a78d6", "o", 44.0, .88, True),
    ("In procurement",  "#9c31a5", "^", 52.0, .90, True),
    ("In construction", "#a01b12", "s", 46.0, .92, True),
    ("Other / unknown", "#52514e", "X", 46.0, .92, True),
]

n_total = len(g)
counts = {k: int((g["phase_group"] == k).sum()) for k, *_ in SPEC}
present = [s for s in SPEC if counts[s[0]] > 0]
n_completed = counts["Completed"]
n_active = n_total - n_completed

pi = pd.read_excel(WB, sheet_name="Project Inventory")
n_placeholder = int(pi["Coordinate_QA"].astype(str)
                    .str.contains("Invalid placeholder", na=False).sum())

fig, ax = plt.subplots(figsize=(16.5, 17.5))
fig.subplots_adjust(left=.025, right=.99, top=.905, bottom=.10)

boro.plot(ax=ax, facecolor="#f5f4f1", edgecolor="white", lw=1.6, zorder=1)
parks.plot(ax=ax, facecolor="#d7e8cf", edgecolor="none", zorder=2)
boro.boundary.plot(ax=ax, color="#d9d7d2", lw=1.2, zorder=3)

for z, (name, colour, marker, size, alpha, edge) in enumerate(SPEC, start=5):
    sel = g[g["phase_group"] == name]
    if sel.empty:
        continue
    sel.plot(ax=ax, color=colour, marker=marker, markersize=size, alpha=alpha,
             edgecolor="white" if edge else "none",
             linewidth=.7 if edge else 0, zorder=z)

S.blank(ax)
S.north_arrow(ax, x=.955, y=.90, size=.045)
S.scale_bar(ax, length_mi=2, x=.055, y=.035)   # bottom-left, now clear

for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r["boroname"], (c.x, c.y), fontsize=11, weight="bold",
                color="#8a8781", ha="center", zorder=4, alpha=.9)

handles = [Line2D([], [], ls="", marker=m, ms=max((sz ** .5) * 1.75, 8.0), color=col,
                  mec="white" if e else "none", mew=.6,
                  label=f"{nm} — {counts[nm]:,} locations "
                        f"({counts[nm]/n_total:.1%})")
           for nm, col, m, sz, a, e in present]
leg = ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=.96,
                edgecolor=S.MUTED, fontsize=10.5, borderpad=1.0,
                labelspacing=.75, bbox_to_anchor=(.005, .995),
                title="Current phase", title_fontsize=11)
leg.get_title().set_fontweight("bold")

info = (f"Mapped project locations:  {n_total:,}\n"
        f"Completed:  {n_completed:,}\n"
        f"Active / not completed:  {n_active:,}\n"
        f"Excluded coordinate placeholders:  {n_placeholder:,}")
# sits directly under the legend in the empty upper-left block, so it never
# covers project points (the bottom-left corner holds Staten Island's tip)
ax.text(.005, .805, info, transform=ax.transAxes, fontsize=10.2,
        va="top", ha="left", color=S.INK, linespacing=1.65,
        bbox=dict(boxstyle="round,pad=0.75", facecolor="white",
                  edgecolor=S.MUTED, alpha=.96))

fig.text(.025, .968,
         "Where renovation stands: NYC green-space capital projects by current phase",
         fontsize=20, weight="bold", color=S.INK, va="top")
fig.text(.025, .936,
         "Each point is a Capital Project Tracker location, not necessarily a unique "
         "project or verified construction footprint.",
         fontsize=11.5, color=S.INK_2, va="top")

LIMS = [
    "Phase represents the Tracker's current administrative status at the 2026-09-08 "
    "snapshot date, not a verified on-site condition.",
    "One project may contain multiple project-location records.",
    f"{n_placeholder} records with literal (0,0) coordinates are retained in the "
    "inventory but excluded from the map.",
    "Point density is not adjusted for borough population, land area, park acreage, "
    "or number of parks.",
]
y = .075
for t in LIMS:
    fig.text(.025, y, "•  " + t, fontsize=8.6, color=S.INK_2, va="top")
    y -= .0145
fig.text(.025, .0135, f"{S.SOURCE}  Snapshot {S.SNAPSHOT}. "
         "Projection EPSG:2263 (NAD83 / New York Long Island, US ft).",
         fontsize=7.4, color=S.MUTED, va="top")

os.makedirs("maps", exist_ok=True)
for ext in ("png", "pdf"):
    p = f"maps/map2_phase_status.{ext}"
    fig.savefig(p, dpi=300 if ext == "png" else None,
                bbox_inches="tight", facecolor="white")
    print(f"  wrote {p}")
plt.close(fig)

print("\n--- QA: phase counts ---")
for nm, *_ in SPEC:
    print(f"  {nm:<18} {counts[nm]:>6,}")
print(f"  {'SUM':<18} {sum(counts.values()):>6,}   "
      f"({'matches' if sum(counts.values()) == n_total else 'MISMATCH vs'} "
      f"{n_total:,} mapped locations)")
