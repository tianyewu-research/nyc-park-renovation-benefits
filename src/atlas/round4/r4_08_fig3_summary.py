"""Round 4 Figure 3 — three summary panels. Descriptive only."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MaxNLocator
sys.path.insert(0, os.path.dirname(__file__))
import r4_04_style as S

R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
I3, I4 = "data/interim/atlas_round3", "data/interim/atlas_round4"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
SNAP_Y, Y0 = 2026, 2008

pi = pd.read_excel(WB, sheet_name="Project Inventory")
pts = gpd.read_file(R2, layer="renovation_project_locations")
boro = gpd.read_file(f"{I3}/boroughs.gpkg", layer="boroughs")[["boroname", "geometry"]]
j = gpd.sjoin(pts, boro, how="left", predicate="within")
j = j[~j.index.duplicated(keep="first")]
pts["Mapped_Borough"] = j["boroname"].fillna("Unknown / unmatched").values

# ---------- A: construction starts by year and borough (round 3 logic reused) ----
cs = pd.to_datetime(pts["Construction_Start"], errors="coerce").dt.year
valid = cs.notna() & cs.between(Y0, 2040)
dA = pd.DataFrame({"year": cs[valid].astype(int), "boro": pts.loc[valid, "Mapped_Borough"]})
YEARS = list(range(Y0, int(dA.year.max()) + 1))
pvA = (dA.groupby(["year", "boro"]).size().unstack(fill_value=0)
       .reindex(index=YEARS, fill_value=0).reindex(columns=S.BORO_ORDER, fill_value=0))
totA = pvA.sum(axis=1)
nA, nMiss = int(valid.sum()), int(len(pts) - valid.sum())

# ---------- B: active phase by borough, unique Tracker_ID x Borough -------------
PH = {"construction": "Construction", "procurement": "Procurement",
      "design": "Design", "design-procurement": "Design"}
pts["ph"] = pts["Map_ID"].map(pi.set_index("Map_ID")["Current_Phase"]).map(PH)
actB = pts[pts["ph"].notna()].drop_duplicates(["Tracker_ID", "Mapped_Borough", "ph"])
pvB = (actB.groupby(["Mapped_Borough", "ph"]).size().unstack(fill_value=0)
       .reindex(index=[b for b in S.BORO_ORDER if b in actB.Mapped_Borough.unique()],
                fill_value=0)
       .reindex(columns=["Design", "Procurement", "Construction"], fill_value=0))

# ---------- C: governance family x active phase, unique Tracker_ID x site -------
site = pd.read_csv(f"{I4}/renovation_site_status.csv")
gov = gpd.read_file(f"{I4}/governance_display_polygons.gpkg",
                    layer="governance_display_polygons")
sg = gpd.read_file(f"{I4}/renovation_site_status.gpkg", layer="renovation_site_status")
rep = sg.copy(); rep["geometry"] = rep.geometry.representative_point()
jj = gpd.sjoin(rep, gov[["display_family", "geometry"]], how="left", predicate="within")
jj = jj[~jj.index.duplicated(keep="first")]
sg["display_family"] = jj["display_family"].values
# each project is attributed to ITS OWN phase, not to the site's most advanced
# phase, so a completed project at a construction site is not counted as construction
ph_by_map = pts.set_index("Map_ID")["ph"]
xw = pd.read_csv("data/interim/atlas_round2/project_site_crosswalk.csv", dtype={"BBL": str})
fam_by_site = dict(zip(sg["display_site_key"], sg["display_family"]))
key = xw["Matched_Site_ID"].fillna("") + "|" + xw["Geometry_Role"].fillna("")
rec = pd.DataFrame({"tracker": xw["Tracker_ID"], "site": xw["Matched_Site_ID"],
                    "family": key.map(fam_by_site),
                    "phase": xw["Map_ID"].map(ph_by_map)})
rec = rec[rec["phase"].notna() & rec["site"].notna()].drop_duplicates(["tracker", "site"])
dC = rec
n_incl = len(dC); n_nofam = int(dC["family"].isna().sum())
pvC = (dC.dropna(subset=["family"]).groupby(["family", "phase"]).size().unstack(fill_value=0)
       .reindex(index=S.GOV_ORDER, fill_value=0)
       .reindex(columns=["Design", "Procurement", "Construction"], fill_value=0))

# ---------- render -------------------------------------------------------------
fig = plt.figure(figsize=(19.5, 13.4))
gs = GridSpec(2, 2, figure=fig, height_ratios=[1.0, .92], width_ratios=[1.0, .78],
              hspace=.52, wspace=.26, left=.085, right=.975, top=.800, bottom=.095)

axA = fig.add_subplot(gs[0, :])
bot = np.zeros(len(YEARS))
for b in S.BORO_ORDER:
    v = pvA[b].values
    if v.sum() == 0: continue
    axA.bar(YEARS, v, bottom=bot, width=.74, label=b, color=S.BORO_STACK[b],
            edgecolor=S.BG, linewidth=.7, zorder=3); bot += v
if SNAP_Y in YEARS:
    i = YEARS.index(SNAP_Y)
    axA.bar([SNAP_Y], [totA[SNAP_Y]], width=.74, facecolor="none", edgecolor=S.INK,
            lw=.9, hatch="//", zorder=4)
    axA.axvline(SNAP_Y - .5, color=S.INK_2, lw=1.0, ls=(0, (4, 3)), zorder=5)
for y in YEARS:
    if totA[y] > 0:
        axA.text(y, totA[y] + totA.max() * .03, f"{int(totA[y])}", ha="center",
                 va="bottom", fontsize=7.6, color=S.INK)
axA.set_xticks(YEARS); axA.set_xticklabels(YEARS, rotation=45, ha="right", fontsize=8.4)
axA.set_ylabel("Project-location records", fontsize=9, color=S.INK_2)
axA.set_ylim(0, totA.max() * 1.16); axA.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
axA.tick_params(colors=S.INK_2, length=0, labelsize=8.6)
axA.grid(axis="y", color=S.MUTED, alpha=.22, lw=.6, zorder=0); axA.set_axisbelow(True)
for sp in ("top","right","left"): axA.spines[sp].set_visible(False)
axA.spines["bottom"].set_color(S.MUTED)
# panel A's title and note are placed in FIGURE coordinates so they cannot
# collide with the legend, which lives in axes coordinates
axA.legend(loc="upper left", bbox_to_anchor=(0, 1.115), ncol=6, frameon=False,
           fontsize=S.LEGEND, columnspacing=1.5, handlelength=1.1, handleheight=1.1)
fig.text(.085, .893, "A. Recorded Construction Starts by Year and Borough",
         fontsize=S.PANEL, color=S.INK, va="top", weight="bold")
fig.text(.085, .872, f"Unit: project-location records (n = {nA:,} with a valid "
         f"Construction_Start). {nMiss:,} mapped locations without a start date are excluded. "
         f"{SNAP_Y} is a partial year at the snapshot date and is hatched.",
         fontsize=8.2, color=S.INK_2, va="top")

axB = fig.add_subplot(gs[1, 0])
ys = np.arange(len(pvB)); left = np.zeros(len(pvB))
for ph in ["Design", "Procurement", "Construction"]:
    v = pvB[ph].values
    axB.barh(ys, v, left=left, height=.62, color=S.PHASE[ph], edgecolor=S.BG,
             linewidth=.8, label=ph, zorder=3); left += v
for i, t in enumerate(left):
    axB.text(t + left.max() * .015, i, f"{int(t)}", va="center", fontsize=8.2, color=S.INK)
axB.set_yticks(ys); axB.set_yticklabels(pvB.index, fontsize=8.8)
axB.invert_yaxis(); axB.set_xlim(0, left.max() * 1.14); axB.set_xticks([])
axB.tick_params(colors=S.INK_2, length=0)
for sp in ("top","right","bottom","left"): axB.spines[sp].set_visible(False)
axB.legend(loc="lower right", frameon=False, fontsize=S.LEGEND)
axB.set_title("B. Current Project Phase by Borough", fontsize=S.PANEL, color=S.INK,
              loc="left", pad=34, weight="bold")
axB.text(0, 1.045, "Unit: unique Tracker_ID by borough. Each project is counted once per borough. "
         "Completed and proposed projects are excluded.",
         transform=axB.transAxes, fontsize=8.2, color=S.INK_2, va="bottom")

axC = fig.add_subplot(gs[1, 1])
M = pvC.values
im = axC.imshow(M, cmap="YlOrBr", vmin=0, vmax=max(M.max(), 1), aspect="auto", alpha=.85)
axC.set_xticks(range(M.shape[1])); axC.set_xticklabels(pvC.columns, fontsize=8.8)
axC.set_yticks(range(M.shape[0]))
axC.set_yticklabels([f if len(f) <= 28 else f[:26] + "…" for f in pvC.index], fontsize=8.4)
for i in range(M.shape[0]):
    for k in range(M.shape[1]):
        axC.text(k, i, str(M[i, k]), ha="center", va="center", fontsize=9.2,
                 color=S.INK if M[i, k] < M.max() * .6 else "white", weight="bold")
axC.tick_params(colors=S.INK_2, length=0)
for sp in axC.spines.values(): sp.set_visible(False)
axC.set_title("C. Current Project Phase by Governance Category", fontsize=S.PANEL,
              color=S.INK, loc="left", pad=62, weight="bold")
axC.text(0, 1.045, f"Unit: unique Tracker_ID by Matched_Site_ID (n = {n_incl:,}). Each\n"
         f"project is counted under its current phase. Projects without a matched site\n"
         f"polygon are excluded; {n_nofam} matched pairs outside the mapped governance\n"
         "categories are also excluded.",
         transform=axC.transAxes, fontsize=8.0, color=S.INK_2, va="bottom", linespacing=1.5)

fig.text(.05, .975, "Park Renovation by Year, Borough, and Governance Category",
         fontsize=S.TITLE, weight="bold", color=S.INK, va="top")
fig.text(.05, .940, "Counts use the unit of analysis specified for each panel.",
         fontsize=S.SUBTITLE,
         color=S.INK_2, va="top")
fig.text(.05, .034, f"{S.SRC_REN}  Snapshot {S.SNAPSHOT}. Borough assigned by spatial join, "
         "not the raw Borough string.", fontsize=7.5, color=S.MUTED, va="top")
S.save(fig, "fig3_renovation_summary_panels")
pvA.to_csv(f"{I4}/fig3_panelA.csv"); pvB.to_csv(f"{I4}/fig3_panelB.csv")
pvC.to_csv(f"{I4}/fig3_panelC.csv")
print(f"  A total {int(totA.sum())} == valid {nA} | B total {int(pvB.values.sum())} | "
      f"C total {int(pvC.values.sum())} (n_incl {n_incl}, no-family {n_nofam})")
