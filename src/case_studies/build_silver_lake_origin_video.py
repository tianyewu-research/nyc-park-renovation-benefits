"""Silver Lake Park weekly visitor home-CBG origin animation.

    python3 src/case_studies/build_silver_lake_origin_video.py            # full run
    python3 src/case_studies/build_silver_lake_origin_video.py --render-only
    python3 src/case_studies/build_silver_lake_origin_video.py --metric count --render-only

--metric share (default) maps each CBG's share of the week's home-CBG visitors;
--metric count maps the smoothed recorded home-CBG visitor count itself and writes to
outputs/silver_lake_origin_video_count/. Both read the same tables in DATA_DIR.

Project: Silver Lake Park Pathway Reconstruction, tracker 1514111, Parks property R022.
A visual feasibility demonstration of how the *composition* of recorded visitor
home CBGs changes week to week. It is not a causal estimate.

Steps
  1. crosswalk -> the six analytic-eligible POIs matched to R022 (hard stop otherwise)
  2. stream every weekly raw Advan gzip in chunks, keep only those POIs, parse
     VISITOR_HOME_CBGS, aggregate week x home_CBG across the six POIs
  3. join 12-digit home CBG to TIGER 2023 block-group GEOID (five boroughs only)
  4. 4-week centered rolling mean of within-week shares, one fixed color scale
  5. key-frame PNGs + MP4 (1920x1080, when an ffmpeg binary is found) + GIF + QA report

--render-only reuses the two CSVs from a previous run and redraws the figures.
Raw files are read only; nothing under data/raw is written.
"""
import argparse, glob, gzip, json, os, re, shutil, sys, warnings
from collections import defaultdict
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import geopandas as gpd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src/atlas/round4"))
import r4_04_style as R4          # sets rcParams (fonts, background) for the thesis look

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.lines import Line2D
from PIL import Image

# ---------------------------------------------------------------- inputs
ADVAN_GLOB = "data/raw/advan_vintage_202606/*.csv.gz"
CROSSWALK = "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv"
BG_SHP = "data/raw/census_geo_2020/tl_2023_36_bg/tl_2023_36_bg.shp"
POI_WEEK = "data/interim/poi_week.csv.gz"                   # QA only
INVENTORY = "outputs/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
ATLAS_GPKG = "outputs/atlas/gis/nyc_green_space_atlas_round4.gpkg"  # park polygon + boroughs
DATA_DIR = "outputs/silver_lake_origin_video"             # extraction tables (shared)
OUT = DATA_DIR                                            # render outputs; set per metric in main()

TRACKER_ID, PARK_ID, N_POI_EXPECTED = 1514111, "R022", 6
PROJECT = "Silver Lake Park Pathway Reconstruction"
WEEK_FIRST, WEEK_LAST, N_WEEKS = "2023-01-02", "2025-12-29", 157
CONSTR_START, CONSTR_END = pd.Timestamp("2023-07-01"), pd.Timestamp("2024-03-01")
NYC_COUNTIES = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan",
                "081": "Queens", "085": "Staten Island"}
FPS, ROLL = 5, 4
FRAME_PX, GIF_PX, KEY_DPI = (1920, 1080), (1600, 900), 200
KEY_FRAMES = [("pre", "2023-05-01"), ("construction_a", "2023-09-04"),
              ("construction_b", "2023-12-04"), ("post", "2024-04-29")]
USECOLS = ["ID_STORE", "DATE_RANGE_START", "VISIT_COUNTS", "VISITOR_COUNTS",
           "VISITOR_HOME_CBGS"]

TITLE = "Silver Lake Park — weekly visitor home-CBG origins"
CAVEAT = ("Shows the changing composition of recorded visitor home CBGs — not individual "
          "demographics, park attendance, or a causal renovation effect. Raw visits rise "
          "archive-wide from 2023 to 2025 (panel growth); read the map as within-week shares, "
          "not raw counts.")
SOURCE = ("Source: Advan weekly patterns (vintage 202606), 6 POIs matched to NYC Parks "
          "property R022; TIGER 2023 block groups; NYC Parks Capital Project Tracker "
          "(tracker 1514111). Construction band = administrative dates.")

METRICS = {
    "share": dict(
        col="origin_share", out=DATA_DIR, stem="silver_lake_weekly_origins",
        title=TITLE,
        subtitle="share of each week's recorded visitor home CBGs, 4-week centered mean",
        caveat=CAVEAT,
        legend="Share of week's home-CBG visitors\n(fixed scale, capped at 99th pct.)",
        tick=lambda t: f"{t*100:.2f}%" if t else "0",
        unit="smoothed CBG-week shares", vfmt=lambda v: f"{v:.4%}"),
    "count": dict(
        col="origin_visitors", out="outputs/silver_lake_origin_video_count",
        stem="silver_lake_weekly_origins_count",
        title=TITLE + " (counts)",
        subtitle="recorded home-CBG visitors, 4-week centered mean",
        caveat=("Smoothed count of recorded visitors by inferred home CBG (Advan device panel) "
                "\u2014 not unique people, park attendance, individual demographics, or a causal "
                "renovation effect. Counts are influenced by Advan panel coverage growth across "
                "2023\u20132025, so apparent growth must not be interpreted as equivalent to park "
                "attendance growth."),
        legend="Recorded home-CBG visitors\n(4-week mean; fixed scale, capped at 99th pct.)",
        tick=lambda t: f"{t:,.0f}",
        unit="smoothed CBG-week visitor counts", vfmt=lambda v: f"{v:,.1f} visitors"),
}
M = METRICS["share"]

TEAL, TEAL_LIGHT = R4.GOV["NYC Parks"], "#CFE0DA"
ORANGE, ORANGE_DARK = R4.GOV["Privately owned public access"], R4.PHASE["Procurement"]
BG, LAND, EDGE, INK, INK_2, MUTED = R4.BG, R4.LAND, R4.EDGE, R4.INK, R4.INK_2, R4.MUTED
CMAP = LinearSegmentedColormap.from_list(
    "thesis_teal", ["#DCE9E4", "#9CC3B8", "#5E9C8D", TEAL, "#1F4A40"])


def log(msg):
    print(msg, flush=True)


def phase_of(week):
    """A Monday-start week that overlaps the administrative interval is 'construction'."""
    w0, w1 = week, week + pd.Timedelta(days=6)
    if w1 < CONSTR_START:
        return "pre-construction"
    if w0 < CONSTR_END:
        return "construction (administrative)"
    return "after administrative completion"


# ---------------------------------------------------------------- 1. POIs
def matched_pois():
    cw = pd.read_csv(CROSSWALK, dtype={"ID_STORE": str, "matched_pid": str})
    elig = cw["analytic_eligible"].astype(str).str.strip().str.lower() == "true"
    sel = cw[(cw["matched_pid"] == PARK_ID) & elig]
    ids = sorted(sel["ID_STORE"].str.strip().unique())
    log(f"matched ID_STORE for {PARK_ID} (analytic_eligible): {ids}")
    if len(ids) != N_POI_EXPECTED:
        sys.exit(f"ERROR: expected {N_POI_EXPECTED} matched POIs for {PARK_ID}, found "
                 f"{len(ids)}: {ids}. Stopping; check the crosswalk before rendering.")
    return ids, sel


# ---------------------------------------------------------------- 2. stream raw
def parse_cbgs(raw):
    """-> (dict | None, status). status in ok / empty / missing / malformed."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None, "missing"
    s = str(raw).strip()
    if s == "" or s.lower() in ("nan", "null", "none"):
        return None, "missing"
    try:
        d = json.loads(s)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, "malformed"
    if not isinstance(d, dict):
        return None, "malformed"
    clean = {}
    for k, v in d.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
            return None, "malformed"
        clean[str(k).strip()] = float(v)
    return clean, ("ok" if clean else "empty")


def stream_raw(ids):
    files = sorted(glob.glob(ADVAN_GLOB))
    wre = re.compile(r"(\d{4}-\d{2}-\d{2})--")
    ids = set(ids)
    origin = defaultdict(float)                      # (week, cbg) -> visitors
    rows, issues = [], []
    for i, f in enumerate(files, 1):
        m = wre.search(os.path.basename(f))
        fweek = m.group(1) if m else None
        seen = []
        with gzip.open(f, "rt", newline="") as fh:
            for chunk in pd.read_csv(fh, usecols=USECOLS, dtype=str, chunksize=100_000):
                hit = chunk[chunk["ID_STORE"].str.strip().isin(ids)]
                if len(hit):
                    seen.append(hit)
        hit = pd.concat(seen) if seen else pd.DataFrame(columns=USECOLS)
        hit["ID_STORE"] = hit["ID_STORE"].str.strip()
        dweeks = sorted(hit["DATE_RANGE_START"].str[:10].unique()) if len(hit) else []
        week = dweeks[0] if len(dweeks) == 1 else fweek
        if len(dweeks) > 1 or (dweeks and dweeks[0] != fweek):
            issues.append(dict(week=week, file=os.path.basename(f), issue="date_mismatch",
                               detail=f"filename {fweek}, DATE_RANGE_START {dweeks}"))
        dup = hit["ID_STORE"].duplicated(keep="first")
        for sid in hit.loc[dup, "ID_STORE"]:
            issues.append(dict(week=week, file=os.path.basename(f), issue="duplicate_poi_row",
                               detail=f"ID_STORE {sid}: extra row dropped (first kept)"))
        hit = hit[~dup]
        visits = pd.to_numeric(hit["VISIT_COUNTS"], errors="coerce")
        visitors = pd.to_numeric(hit["VISITOR_COUNTS"], errors="coerce")
        n_status = defaultdict(int)
        week_cbgs = set()
        for sid, raw in zip(hit["ID_STORE"], hit["VISITOR_HOME_CBGS"]):
            d, status = parse_cbgs(raw)
            n_status[status] += 1
            if status in ("missing", "malformed"):
                issues.append(dict(week=week, file=os.path.basename(f),
                                   issue=f"json_{status}",
                                   detail=f"ID_STORE {sid}: {str(raw)[:120]!r}"))
            for cbg, v in (d or {}).items():
                origin[(week, cbg)] += v
                week_cbgs.add(cbg)
        missing_pois = sorted(ids - set(hit["ID_STORE"]))
        if missing_pois:
            issues.append(dict(week=week, file=os.path.basename(f), issue="poi_missing",
                               detail=",".join(missing_pois)))
        rows.append(dict(week=week, file=os.path.basename(f),
                         visits_raw=visits.sum(min_count=1), visitors_raw=visitors.sum(min_count=1),
                         n_poi_present=len(hit), missing_poi_ids=",".join(missing_pois),
                         n_source_cbgs=len(week_cbgs), json_ok=n_status["ok"],
                         json_empty=n_status["empty"], json_missing=n_status["missing"],
                         json_malformed=n_status["malformed"]))
        if i % 20 == 0 or i == len(files):
            log(f"  streamed {i}/{len(files)} files ({week}: {len(hit)} POIs)")
    od = pd.DataFrame([dict(week=w, home_cbg=c, origin_visitors=v)
                       for (w, c), v in origin.items()])
    return od, pd.DataFrame(rows), pd.DataFrame(issues, columns=["week", "file", "issue", "detail"])


# ---------------------------------------------------------------- 3. geometry
def load_geo():
    bg = gpd.read_file(BG_SHP)[["GEOID", "COUNTYFP", "ALAND", "geometry"]]
    bg = bg[bg["COUNTYFP"].isin(NYC_COUNTIES)].to_crs(R4_CRS)
    boros = gpd.read_file(ATLAS_GPKG, layer="boroughs").to_crs(R4_CRS)
    park = gpd.read_file(ATLAS_GPKG, layer="governance_display_polygons")
    park = park[park["Site_Key"] == PARK_ID].to_crs(R4_CRS)
    return bg, boros, park


R4_CRS = "EPSG:2263"


def build_tables(od, summ, nyc_geoids):
    od["home_cbg"] = od["home_cbg"].astype(str)
    tot = od.groupby("week")["origin_visitors"].transform("sum")
    od["origin_share"] = od["origin_visitors"] / tot
    od["in_nyc"] = od["home_cbg"].isin(nyc_geoids)
    od = od.sort_values(["week", "origin_visitors"], ascending=[True, False])
    g = od.groupby("week")
    s = pd.DataFrame({"origin_visitors_total": g["origin_visitors"].sum(),
                      "origin_visitors_nyc_mapped": od[od.in_nyc].groupby("week")["origin_visitors"].sum(),
                      "origin_visitors_nyc_county_unmatched": od[
                          ~od.in_nyc & od.home_cbg.str[:5].isin({"36" + c for c in NYC_COUNTIES})
                      ].groupby("week")["origin_visitors"].sum()}).fillna(0)
    summ = summ.merge(s, left_on="week", right_index=True, how="left")
    summ[["origin_visitors_total", "origin_visitors_nyc_mapped",
          "origin_visitors_nyc_county_unmatched"]] = summ[[
        "origin_visitors_total", "origin_visitors_nyc_mapped",
        "origin_visitors_nyc_county_unmatched"]].fillna(0)
    summ["share_nyc_mapped"] = summ.origin_visitors_nyc_mapped / summ.origin_visitors_total.replace(0, np.nan)
    summ["share_outside_nyc_or_unmatched"] = 1 - summ["share_nyc_mapped"]
    summ["phase"] = pd.to_datetime(summ.week).map(phase_of)
    return od, summ.sort_values("week").reset_index(drop=True)


def smoothed_matrix(od, weeks, geoids, col="origin_share"):
    """week x NYC CBG matrix of `col` (share or count), 4-week centered rolling mean
    (missing weeks skipped)."""
    nyc = od[od.in_nyc].pivot_table(index="week", columns="home_cbg",
                                    values=col, aggfunc="sum")
    has_data = od.groupby("week")["origin_visitors"].sum() > 0
    m = nyc.reindex(index=weeks, columns=geoids)
    for w in weeks:                                   # observed week -> absent CBG = 0
        if has_data.get(w, False):
            m.loc[w] = m.loc[w].fillna(0)
    # rolling mean with center=True over an even window uses rows t-2..t+1
    return m.rolling(ROLL, center=True, min_periods=1).mean()


# ---------------------------------------------------------------- 4. figure
class Frame:
    def __init__(self, bg, boros, park, summ, vmax):
        self.summ = summ
        self.weeks = pd.to_datetime(summ.week)
        self.fig = fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        fig.patch.set_facecolor(BG)
        fig.text(.03, .945, M["title"], fontsize=22, fontweight="bold", color=INK, va="bottom")
        fig.text(.03, .915, f"{PROJECT} (tracker {TRACKER_ID}, property {PARK_ID}) · "
                 + M["subtitle"],
                 fontsize=11, color=INK_2, va="bottom")

        ax = self.ax_map = fig.add_axes([.02, .1, .53, .79])
        R4.blank(ax)
        bg.plot(ax=ax, color=LAND, edgecolor="none")
        self.coll = ax.collections[-1]
        self.coll.set_cmap(CMAP)
        self.coll.set_norm(PowerNorm(0.5, vmin=0, vmax=vmax))
        self.coll.set_array(np.full(len(bg), np.nan))
        self.coll.cmap.set_bad(LAND)
        self.coll.cmap.set_under(LAND)
        boros.boundary.plot(ax=ax, color=EDGE, linewidth=.6)
        park.plot(ax=ax, facecolor="none", edgecolor=ORANGE_DARK, linewidth=1.4, zorder=5)
        c = park.geometry.unary_union.representative_point()
        ax.plot(c.x, c.y, marker="*", markersize=17, color=ORANGE, mec=INK, mew=.6, zorder=6)
        ax.annotate("Silver Lake Park", xy=(c.x, c.y), xytext=(c.x - 23000, c.y + 16000),
                    fontsize=10.5, color=INK, ha="center",
                    arrowprops=dict(arrowstyle="-", color=INK_2, lw=.7), zorder=6)
        x0, y0, x1, y1 = boros.total_bounds
        pad = .02 * (x1 - x0)
        ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad)
        R4.north_arrow(ax, x=.06, y=.93)
        R4.scale_bar(ax, length_mi=2, x=.62, y=.03)
        for name, (bx, by) in {"Bronx": (.72, .9), "Manhattan": (.47, .72),
                               "Brooklyn": (.5, .3), "Queens": (.8, .55),
                               "Staten Island": (.14, .3)}.items():
            ax.text(bx, by, name, transform=ax.transAxes, fontsize=9.5, color=MUTED,
                    ha="center", style="italic")
        cax = fig.add_axes([.07, .745, .19, .014])
        cb = fig.colorbar(self.coll, cax=cax, orientation="horizontal", extend="max")
        cb.outline.set_edgecolor(EDGE)
        if M["col"] == "origin_visitors":     # whole-number ticks placed at their true values
            ticks = [0, float(max(1, round(vmax / 4))), float(np.floor(vmax))]
        else:
            ticks = [0, vmax * .25, vmax]
        cb.set_ticks(ticks)
        cb.set_ticklabels([M["tick"](t) for t in ticks])
        cb.ax.tick_params(labelsize=8, colors=INK_2, length=2)
        cax.set_title(M["legend"],
                      fontsize=8.5, color=INK_2, loc="left")
        self.cax = cax

        # time series
        ts = self.ax_ts = fig.add_axes([.6, .5, .37, .38])
        ts.set_facecolor(BG)
        ts.axvspan(CONSTR_START, CONSTR_END, color=ORANGE, alpha=.18, lw=0)
        ymax = np.nanmax(summ.visits_raw) * 1.12
        ts.text(CONSTR_START + (CONSTR_END - CONSTR_START) / 2, ymax * .965,
                "Construction\n(administrative dates)", ha="center", va="top",
                fontsize=8.5, color=ORANGE_DARK)
        ts.plot(self.weeks, summ.visits_raw, color=TEAL, lw=1.6)
        self.vline = ts.axvline(self.weeks.iloc[0], color=INK, lw=1.1)
        self.dot, = ts.plot([], [], "o", color=TEAL, mec=INK, mew=.8, ms=6.5, zorder=5)
        ts.set_ylim(0, ymax)
        ts.set_xlim(self.weeks.iloc[0] - pd.Timedelta(days=7), self.weeks.iloc[-1] + pd.Timedelta(days=7))
        ts.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ts.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ts.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        for sp in ("top", "right"):
            ts.spines[sp].set_visible(False)
        ts.tick_params(labelsize=9, colors=INK_2)
        ts.grid(axis="y", color=EDGE, lw=.4, alpha=.6)
        ts.set_title("Weekly raw visits, sum of 6 matched POIs (157 weeks)", fontsize=11.5,
                     color=INK, loc="left", pad=8)

        # info panel
        ip = self.ax_info = fig.add_axes([.6, .13, .37, .29])
        ip.set_xticks([]); ip.set_yticks([]); ip.set_facecolor("#F8F9F5")
        for sp in ip.spines.values():
            sp.set_edgecolor(EDGE); sp.set_linewidth(.7)
        labels = ["Week of", "Project phase", "Matched POIs reporting",
                  "Total raw visits", "NYC-mapped origin share"]
        self.vals = []
        for k, lab in enumerate(labels):
            y = .84 - k * .17
            ip.text(.05, y, lab, fontsize=11, color=INK_2, va="center", transform=ip.transAxes)
            self.vals.append(ip.text(.95, y, "", fontsize=14 if k < 2 else 12.5, ha="right",
                                     va="center", color=INK, fontweight="bold",
                                     transform=ip.transAxes))

        fig.text(.03, .055, M["caveat"], fontsize=9, color=INK_2, va="bottom", wrap=True)
        fig.text(.03, .025, SOURCE, fontsize=7.8, color=MUTED, va="bottom")

    def draw(self, i, values):
        r = self.summ.iloc[i]
        w = self.weeks.iloc[i]
        self.coll.set_array(np.where(values > 0, values, np.nan))  # 0 or no data -> base gray
        self.vline.set_xdata([w, w])
        self.dot.set_data([w], [r.visits_raw])
        ph = r.phase
        self.vals[0].set_text(f"{w:%b %-d, %Y}")
        self.vals[1].set_text(ph[0].upper() + ph[1:])
        self.vals[1].set_color(ORANGE_DARK if ph.startswith("construction") else INK)
        self.vals[2].set_text(f"{int(r.n_poi_present)} of {N_POI_EXPECTED}")
        self.vals[3].set_text(f"{r.visits_raw:,.0f}" if pd.notna(r.visits_raw) else "no data")
        self.vals[4].set_text(f"{r.share_nyc_mapped:.0%}" if pd.notna(r.share_nyc_mapped) else "n/a")
        return self.fig


def fig_to_image(fig):
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB")


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe, "system ffmpeg on PATH"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe(), "imageio-ffmpeg bundled binary"
    except Exception:
        return None, ("no `ffmpeg` executable on PATH and the Python package `imageio-ffmpeg` "
                      "is not installed")


# ---------------------------------------------------------------- 5. QA
def qa_vs_poi_week(ids, summ):
    try:
        pw = pd.read_csv(POI_WEEK, dtype={"ID_STORE": str})
    except Exception as e:
        return None, f"could not read {POI_WEEK}: {e}"
    pw = pw[pw.ID_STORE.isin(ids)].groupby("week", as_index=False)[["visits_raw", "visitors_raw"]].sum()
    m = summ[["week", "visits_raw", "visitors_raw"]].merge(pw, on="week", how="outer",
                                                           suffixes=("", "_poi_week"))
    m["d_visits"] = m.visits_raw - m.visits_raw_poi_week
    m["d_visitors"] = m.visitors_raw - m.visitors_raw_poi_week
    return m, None


def write_qa(ids, sel, summ, od, issues, vmax, key_paths, video, qa_cmp, qa_err, n_bg):
    w = pd.to_datetime(summ.week)
    exp = pd.date_range(WEEK_FIRST, WEEK_LAST, freq="7D")
    missing_weeks = sorted(set(exp.strftime("%Y-%m-%d")) - set(summ.week))
    extra_weeks = sorted(set(summ.week) - set(exp.strftime("%Y-%m-%d")))
    parse_fail = issues[issues.issue.isin(["json_missing", "json_malformed"])]
    wk_missing_poi = summ[summ.n_poi_present < N_POI_EXPECTED]
    other = issues[~issues.issue.isin(["json_missing", "json_malformed", "poi_missing"])]
    ph = summ.groupby("phase", sort=False).agg(
        weeks=("week", "size"), mean_visits=("visits_raw", "mean"),
        mean_share_nyc=("share_nyc_mapped", "mean"))
    si = od[od.home_cbg.str.startswith("36085") & od.in_nyc].groupby("week").origin_share.sum()
    summ2 = summ.assign(share_si=summ.week.map(si).fillna(0))
    ph["mean_share_staten_island"] = summ2.groupby("phase", sort=False).share_si.mean()
    L = []
    a = L.append
    a(f"# QA report \u2014 {M['title']}\n")
    a(f"Generated by `src/case_studies/build_silver_lake_origin_video.py` on "
      f"{pd.Timestamp.now():%Y-%m-%d %H:%M}.\n")
    a(f"Project: **{PROJECT}** · tracker `{TRACKER_ID}` · Parks property `{PARK_ID}`.\n")
    a("## Caveat\n")
    a(M["caveat"] + " This is a visual feasibility demonstration, not causal evidence.\n")
    if M["col"] == "origin_visitors":
        a("## Share map vs count map\n")
        a("The share map asks whether the spatial composition of recorded origins changes. "
          "The count map asks whether the observed panel count from each origin changes. "
          "Because the data panel grows over the archive, a brighter count map does not by "
          "itself establish increased park use.\n")
        a(f"Tables are read from `{DATA_DIR}/` (`weekly_origin_cbg.csv`, `weekly_summary.csv`); "
          f"the share-based deliverables in that directory are not modified by this run.\n")
    a("## Dates\n")
    a(f"- Weekly files found: **{len(summ)}** (expected {N_WEEKS}); first `{summ.week.min()}`, "
      f"last `{summ.week.max()}`.")
    a(f"- Missing expected weeks: {', '.join(missing_weeks) or 'none'}. "
      f"Unexpected weeks: {', '.join(extra_weeks) or 'none'}.")
    a(f"- Administrative construction interval (Capital Project Tracker): "
      f"{CONSTR_START:%Y-%m-%d} to {CONSTR_END:%Y-%m-%d}. The inventory's `Public_Reopen_Date` "
      "equals the administrative construction completion and is flagged there as *not* "
      "independently verified; the animation therefore labels weeks after 2024-03-01 "
      "\"after administrative completion\", not \"reopened\".")
    a("- Phase rule: a Monday-start week is *construction* if any of its 7 days falls in "
      "[2023-07-01, 2024-03-01); earlier weeks are pre-construction, later weeks post.\n")
    a("| phase | weeks | mean raw visits | mean NYC-mapped share | mean Staten Island share |")
    a("|---|---:|---:|---:|---:|")
    for p, r in ph.iterrows():
        a(f"| {p} | {int(r.weeks)} | {r.mean_visits:,.0f} | {r.mean_share_nyc:.1%} | "
          f"{r.mean_share_staten_island:.1%} |")
    a("\n## Matched POIs\n")
    a(f"- Crosswalk rows with `matched_pid == \"{PARK_ID}\"` and `analytic_eligible == True`: "
      f"**{len(ids)}** (required {N_POI_EXPECTED}).")
    a("- ID_STORE: " + ", ".join(f"`{i}`" for i in ids))
    a(f"- Match method(s): {', '.join(sorted(sel.match_method.unique()))}; "
      f"distance_ft max {sel.distance_ft.max()}.\n")
    a("## JSON parsing (`VISITOR_HOME_CBGS`)\n")
    a(f"- POI-weeks parsed OK: {int(summ.json_ok.sum())}; empty object `{{}}`: "
      f"{int(summ.json_empty.sum())}; missing: {int(summ.json_missing.sum())}; "
      f"malformed: {int(summ.json_malformed.sum())}.")
    if len(parse_fail):
        pf = parse_fail.assign(poi=parse_fail.detail.str.extract(r"ID_STORE (\d+)")[0])
        a("- Every missing/malformed POI-week is logged in `row_issues.csv` (week, file, "
          "ID_STORE, raw value). These POI-weeks still count toward raw visits but "
          "contribute no home CBGs. By POI:\n")
        a("| ID_STORE | issue | POI-weeks | first week | last week |")
        a("|---|---|---:|---|---|")
        for (poi, iss), g in pf.groupby(["poi", "issue"]):
            a(f"| {poi} | {iss} | {len(g)} | {g.week.min()} | {g.week.max()} |")
    a("")
    a("## Weeks with missing POIs\n")
    if len(wk_missing_poi):
        a(f"{len(wk_missing_poi)} week(s) have fewer than {N_POI_EXPECTED} matched POIs:\n")
        a("| week | POIs present | missing ID_STORE |")
        a("|---|---:|---|")
        for _, r in wk_missing_poi.iterrows():
            a(f"| {r.week} | {r.n_poi_present} | {r.missing_poi_ids} |")
    else:
        a("None: all six POIs appear in every week.")
    if len(other):
        a("\nOther row-level issues:\n")
        for _, r in other.iterrows():
            a(f"- {r.week} {r.issue}: {r.detail}")
    a("\n## Coverage of home CBGs\n")
    a(f"- Distinct source home CBGs across all weeks: {od.home_cbg.nunique():,}; "
      f"of which matched to 2023 NYC block-group geometry: {od[od.in_nyc].home_cbg.nunique():,} "
      f"(of {n_bg:,} NYC block groups).")
    a(f"- Weekly share of home-CBG visitors outside NYC or unmatched: median "
      f"{summ.share_outside_nyc_or_unmatched.median():.1%}, range "
      f"{summ.share_outside_nyc_or_unmatched.min():.1%}–"
      f"{summ.share_outside_nyc_or_unmatched.max():.1%} (max in week "
      f"{summ.loc[summ.share_outside_nyc_or_unmatched.idxmax(), 'week']}).")
    a(f"- Home CBGs with an NYC county prefix but no 2023 TIGER GEOID match: "
      f"{od[~od.in_nyc & od.home_cbg.str[:5].isin({'36'+c for c in NYC_COUNTIES})].home_cbg.nunique()} "
      f"distinct codes, {summ.origin_visitors_nyc_county_unmatched.sum():,.0f} visitor-weeks.")
    a(f"- Home-CBG visitors sum vs `VISITOR_COUNTS`: median ratio "
      f"{(summ.origin_visitors_total / summ.visitors_raw).median():.2f} "
      "(range {:.2f}-{:.2f}). Advan drops very small home CBGs and reports 2-4 as 4, "
      "so the home-CBG table is not an exact partition of `VISITOR_COUNTS`.\n".format(
          (summ.origin_visitors_total / summ.visitors_raw).min(),
          (summ.origin_visitors_total / summ.visitors_raw).max()))
    leg = summ.origin_visitors_nyc_county_unmatched / summ.origin_visitors_total
    lw = summ.loc[leg > 0, "week"]
    a("## Geography-vintage anomaly (legacy 2010 CBG codes)\n")
    if len(lw):
        a(f"- {len(lw)} week(s), {lw.min()} to {lw.max()}, report some NYC home CBGs under "
          "2010-census codes that do not exist in 2020/2023 TIGER geography (e.g. "
          "`360850059001`, the park's own tract 59 before its 2020 split into 59.01/59.02). "
          f"In those weeks they are {leg[leg > 0].median():.1%} (median) and up to "
          f"{leg.max():.1%} of home-CBG visitors.")
        a("- They are kept in `weekly_origin_cbg.csv` (`in_nyc = False`) and counted in "
          "`origin_visitors_nyc_county_unmatched`, but are not drawn: no 2010-to-2020 block-group "
          "crosswalk is in the repository and the script does not guess one. This share is "
          "reported here and in `weekly_summary.csv`; it is not drawn on the frames.")
        a("- Consequence: in these weeks the map under-draws visitors from the park's own "
          "neighborhood. Do not read the mid-2025 lightening near the park as a composition "
          "change. Fix path: apply the Census 2010-to-2020 block-group relationship file.\n")
    else:
        a("- None found.\n")
    a("## Cross-check against `data/interim/poi_week.csv.gz`\n")
    if qa_err:
        a(f"- {qa_err}")
    else:
        both = qa_cmp.dropna(subset=["visits_raw", "visits_raw_poi_week"])
        a(f"- Weeks compared: {len(both)} (only in raw stream: "
          f"{qa_cmp.visits_raw_poi_week.isna().sum()}, only in poi_week: {qa_cmp.visits_raw.isna().sum()}).")
        a(f"- Max |difference| in summed raw visits: {both.d_visits.abs().max():,.0f}; "
          f"raw visitors: {both.d_visitors.abs().max():,.0f}. "
          + ("Totals agree exactly." if both.d_visits.abs().max() == 0 and both.d_visitors.abs().max() == 0
             else "See weekly_summary.csv for the weeks that differ."))
    a("\n## Rendering choices\n")
    if M["col"] == "origin_visitors":
        a("- Map value: `origin_visitors` = recorded visitors from a home CBG, summed over the six "
          "matched POIs, as parsed from `VISITOR_HOME_CBGS` (not `VISIT_COUNTS`; not unique "
          "people or attendance).")
        what = "weekly counts"
    else:
        a(f"- `origin_share` = CBG visitors / all home-CBG visitors that week (NYC and non-NYC).")
        what = "weekly shares"
    a(f"- Map values: {ROLL}-week centered rolling mean of {what} (pandas "
      "`rolling(4, center=True)`, i.e. weeks t\u22122..t+1, fewer at the series ends); an "
      "observed week with no visitors from a CBG counts as 0. Frame labels are the actual week.")
    a(f"- One fixed color scale for all frames: 0 to {M['vfmt'](vmax)} (99th percentile of all "
      f"non-zero {M['unit']}); values above are drawn at the top color (`extend=max`). A "
      "square-root (power 0.5) color stretch keeps small values visible; the scale never changes.")
    a("- Five boroughs only (TIGER 2023 `tl_2023_36_bg`, counties 005/047/061/081/085), EPSG:2263, "
      "joined on 12-digit `GEOID`. Non-NYC and unmatched origins are not drawn. The "
      "lower-left \"Not mapped\" callout is intentionally omitted from frames; the unsmoothed "
      "weekly unmapped-origin values remain in `weekly_summary.csv` "
      "(`share_outside_nyc_or_unmatched`, `origin_visitors_nyc_county_unmatched`) and in this report. "
      "The right panel still shows the NYC-mapped origin share.")
    a(f"- Animation: {len(summ)} frames at {FPS} fps (~{len(summ)/FPS:.0f} s); frames "
      f"rendered at {FRAME_PX[0]}\u00d7{FRAME_PX[1]} px (MP4), GIF downscaled to "
      f"{GIF_PX[0]}\u00d7{GIF_PX[1]} px, 256 colors. Key-frame PNGs at dpi {KEY_DPI}.\n")
    a("## Outputs\n")
    for p in [f"{DATA_DIR}/weekly_origin_cbg.csv", f"{DATA_DIR}/weekly_summary.csv",
              f"{OUT}/qa_report.md"] + [f"{OUT}/{os.path.basename(p)}" for p in key_paths]:
        a(f"- `{p}`")
    for p in video["files"]:
        a(f"- `{OUT}/{os.path.basename(p)}`")
    a("")
    a("## Video format\n")
    if video["mp4"]:
        a(f"- MP4: H.264, yuv420p, crf 18, {FPS} fps, {FRAME_PX[0]}\u00d7{FRAME_PX[1]}, "
          f"written with {video['how']}.")
    else:
        a(f"- **MP4 unavailable**: {video['why']}. Install `imageio-ffmpeg` in this Python "
          "environment and re-run with `--render-only` to produce it.")
    a(f"- GIF: {GIF_PX[0]}\u00d7{GIF_PX[1]}, 256 colors, {FPS} fps, written on every run "
      "(not only as an MP4 fallback).")
    a("\n## Limitations\n")
    for t in [
        "Composition, not people: home CBGs are Advan's inferred device home locations, "
        "aggregated; they say nothing about individual visitors' demographics.",
        "Not attendance: Advan counts are a device panel sample. The archive panel grows about "
        "+53% from 2023 to 2025, so rising raw visits are partly panel growth; the map uses "
        "within-week shares for that reason.",
        "Privacy suppression: Advan drops home CBGs with very few visitors and rounds small "
        "counts (2–4 reported as 4), so small-share CBGs are noisy and some weeks' tails are "
        "censored.",
        "Geofence: six POIs inside a 206-acre park; the pathway project is local to parts of the "
        "park, so whole-park geofences dilute any project-specific change.",
        "Dates are administrative (Capital Project Tracker). Actual closure and public access "
        "dates are not independently verified; completion is not treated as reopening.",
        "The 4-week centered mean blurs abrupt changes by roughly ±2 weeks, including "
        "around the construction boundaries.",
        "No counterfactual or comparison park: this is descriptive and not a causal renovation "
        "effect.",
    ]:
        a(f"- {t}")
    with open(os.path.join(OUT, "qa_report.md"), "w") as f:
        f.write("\n".join(L) + "\n")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--metric", choices=sorted(METRICS), default="share",
                    help="map value: within-week share (default) or smoothed visitor count")
    args = ap.parse_args()
    global M, OUT
    M = METRICS[args.metric]
    OUT = M["out"]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    log(f"metric: {args.metric} -> {OUT}")

    ids, sel = matched_pois()
    bg, boros, park = load_geo()
    nyc_geoids = set(bg.GEOID)
    log(f"NYC block groups: {len(bg):,}; park polygon rows: {len(park)}")

    p_od = os.path.join(DATA_DIR, "weekly_origin_cbg.csv")
    p_sm = os.path.join(DATA_DIR, "weekly_summary.csv")
    p_iss = os.path.join(DATA_DIR, "row_issues.csv")
    if args.render_only:
        od = pd.read_csv(p_od, dtype={"home_cbg": str, "week": str})
        summ = pd.read_csv(p_sm, dtype={"week": str, "missing_poi_ids": str}).fillna({"missing_poi_ids": ""})
        issues = pd.read_csv(p_iss, dtype=str) if os.path.exists(p_iss) else \
            pd.DataFrame(columns=["week", "file", "issue", "detail"])
    else:
        log("streaming raw weekly files ...")
        od, summ, issues = stream_raw(ids)
        od, summ = build_tables(od, summ, nyc_geoids)
        od[["week", "home_cbg", "origin_visitors", "origin_share", "in_nyc"]].to_csv(p_od, index=False)
        cols = ["week", "phase", "visits_raw", "visitors_raw", "n_poi_present", "missing_poi_ids",
                "n_source_cbgs", "origin_visitors_total", "origin_visitors_nyc_mapped",
                "origin_visitors_nyc_county_unmatched", "share_nyc_mapped",
                "share_outside_nyc_or_unmatched", "json_ok", "json_empty", "json_missing",
                "json_malformed", "file"]
        summ = summ[cols]
        summ.to_csv(p_sm, index=False)
        issues.to_csv(p_iss, index=False)
        log(f"wrote {p_od} ({len(od):,} rows) and {p_sm} ({len(summ)} weeks)")
    if len(summ) != N_WEEKS:
        log(f"WARNING: {len(summ)} weeks found, expected {N_WEEKS}")

    weeks = list(summ.week)
    geoids = list(bg.GEOID)
    sm = smoothed_matrix(od, weeks, geoids, M["col"])
    nz = sm.values[np.isfinite(sm.values) & (sm.values > 0)]
    vmax = float(np.percentile(nz, 99))
    log(f"fixed color scale vmax (p99 of non-zero {M['unit']}) = {vmax:.5f}")

    fr = Frame(bg, boros, park, summ, vmax)
    key_paths = []
    key_idx = {}
    for label, d in KEY_FRAMES:
        i = int(np.argmin(np.abs((pd.to_datetime(summ.week) - pd.Timestamp(d)).dt.days)))
        key_idx[i] = label
    ffmpeg, why = find_ffmpeg()
    video = dict(mp4=False, files=[], how="", why=why)
    mp4 = os.path.join(OUT, M["stem"] + ".mp4")
    gif = os.path.join(OUT, M["stem"] + ".gif")
    enc = None
    if ffmpeg:
        import subprocess
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{FRAME_PX[0]}x{FRAME_PX[1]}", "-r", str(FPS), "-i", "-",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", str(FPS), mp4]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    # full-size frames stream straight to ffmpeg; only the smaller GIF frames stay in memory
    gif_frames = []
    for i, w in enumerate(weeks):
        fig = fr.draw(i, sm.loc[w].values.astype(float))
        if i in key_idx:
            p = os.path.join(OUT, f"keyframe_{list(key_idx).index(i)+1}_{key_idx[i]}_{w}.png")
            fig.savefig(p, dpi=KEY_DPI, facecolor=BG)
            key_paths.append(p)
        im = fig_to_image(fig)
        if im.size != FRAME_PX:
            sys.exit(f"ERROR: frame is {im.size}, expected {FRAME_PX}")
        if enc is not None:
            try:
                enc.stdin.write(im.tobytes())
            except BrokenPipeError:
                video["why"] = f"ffmpeg ({why}) closed its input: " + \
                    enc.stderr.read().decode(errors="replace").strip()[:300]
                enc = None
        gif_frames.append(im.resize(GIF_PX, Image.LANCZOS).quantize(colors=256, method=2))
    log(f"rendered {len(gif_frames)} frames at {FRAME_PX[0]}x{FRAME_PX[1]}; key frames: "
        f"{[os.path.basename(p) for p in key_paths]}")

    if enc is not None:
        enc.stdin.close()
        err = enc.stderr.read().decode(errors="replace").strip()
        if enc.wait() == 0:
            video.update(mp4=True, how=why)
            video["files"].append(mp4)
            log(f"wrote {mp4}")
        else:
            video["why"] = f"ffmpeg ({why}) exited with an error: {err[:300]}"
    if not video["mp4"]:
        log(f"WARNING: MP4 not written \u2014 {video['why']}. GIF is still written.")
    gif_frames[0].save(gif, save_all=True, append_images=gif_frames[1:],
                       duration=int(1000 / FPS), loop=0, optimize=False)
    video["files"].append(gif)
    log(f"wrote {gif}")

    qa_cmp, qa_err = qa_vs_poi_week(ids, summ)
    write_qa(ids, sel, summ, od, issues, vmax, key_paths, video, qa_cmp, qa_err, len(bg))
    log(f"wrote {OUT}/qa_report.md")


if __name__ == "__main__":
    main()
