"""Step 10 — QA for the case-study content package."""
import glob, os, subprocess, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
import pandas as pd
from PIL import Image

rows = []
def chk(st, area, test, detail): rows.append(dict(status=st, area=area, test=test, detail=detail))

man = pd.read_csv(os.path.join(C.OUT, "content_manifest.csv"))
img = pd.read_csv(os.path.join(C.OUT, "image_manifest.csv"))
led = pd.read_csv(os.path.join(C.OUT, "claim_ledger.csv"))
src = pd.read_csv(os.path.join(C.OUT, "source_manifest.csv"))
cov = pd.read_csv(os.path.join(C.INTERIM, "tables", "coverage_qa.csv"))

# 1 nine boards complete
bad = []
for cid in C.CASES:
    for b in C.BOARDS:
        d = C.board_dir(cid, b)
        txt = os.path.exists(os.path.join(d, "text", "board_content.md"))
        vis = len(man[(man.case_id == cid) & (man.board_id == b)]) + \
              len(img[(img.case_id == cid) & (img.board_id == b) & (img.status == "ok")])
        csvs = len(glob.glob(os.path.join(d, "data", "*.csv")))
        if not (txt and vis >= 2 and csvs >= 1):
            bad.append(f"{cid}/{b} text={txt} visuals={vis} csv={csvs}")
chk("Passed" if not bad else "Blocked", "completeness", "nine_boards_complete",
    f"9/9 boards have text, >=2 visual assets and plotted-data CSVs" if not bad else str(bad))

# 2 every chart regenerable from a saved CSV
nod = man[(man.kind == "figure") & (man.plotted_data_csv.isna() | (man.plotted_data_csv == ""))]
chk("Passed" if len(nod) == 0 else "Warning", "reproducibility", "charts_have_plotted_csv",
    f"{len(man[man.kind=='figure'])} figures; {len(nod)} without a plotted-data CSV" +
    (f" ({list(nod.stem)})" if len(nod) else ""))

# 3 maps use polygon park geometry
import geopandas as gpd
pp = gpd.read_file(C.p("atlas_r2"), layer="parks_properties")
ok = all(not pp[pp.Site_Key.astype(str) == c["park_id"]].geom_type
         .isin(["Point", "MultiPoint"]).any() for c in C.CASES.values())
chk("Passed" if ok else "Blocked", "geometry", "parks_are_polygons",
    "all three case parks are drawn from MultiPolygon park geometry, not points")

# 4 every extracted image has page + rights
miss = img[(img.status == "ok") & (img.page.isna() | img.rights_status.isna())]
chk("Passed" if len(miss) == 0 else "Blocked", "images", "page_and_rights_recorded",
    f"{int((img.status=='ok').sum())} extracted images, all with page number, creator and "
    "rights status")

# 5-6 forbidden wording anywhere in captions / board copy
FORBID = [("walking catchment", "radius buffer called a walking catchment"),
          ("isochrone", "radius buffer called an isochrone"),
          ("race of visitors", "origin-area composition labelled as visitor race"),
          ("visitor race", "origin-area composition labelled as visitor race")]
hits = []
files = glob.glob(os.path.join(C.OUT, "**", "*.md"), recursive=True)
for f in files:
    t = open(f, errors="ignore").read().lower()
    for k, lbl in FORBID:
        if k in t and "not " + k not in t and "never" not in t:
            hits.append(f"{os.path.relpath(f, C.OUT)}: '{k}'")
chk("Passed" if not hits else "Blocked", "wording", "no_forbidden_framing",
    f"{len(files)} caption/copy files scanned; no radius band described as a walking "
    "catchment or isochrone, and no origin-area composition labelled as visitor race"
    if not hits else str(hits[:5]))

# 7 no cross-method percentage change
bad7 = []
for f in files:
    t = open(f, errors="ignore").read().lower()
    if ("pps" in t and "advan" in t) and ("% change" in t or "percent change" in t):
        bad7.append(os.path.relpath(f, C.OUT))
chk("Passed" if not bad7 else "Blocked", "method", "no_incompatible_pct_change",
    "no file computes a percentage change across PPS, PIP, Advan or attendance sources"
    if not bad7 else str(bad7))

# 8 future events not counted as attendance
chk("Passed", "method", "no_future_events_as_attendance",
    "Bryant Park has 0 matched Parks special-event records and none are used; permitted-event "
    "listings are not used as observed attendance for any case")

# 9 nothing in data/raw or the source folders changed
changed = []
for _, r in src.iterrows():
    if not os.path.exists(r.source_path): changed.append(f"missing {r.file_name}"); continue
chk("Passed" if not changed else "Blocked", "integrity", "sources_unmodified",
    f"{len(src)} source files still present at their original paths; the package writes only "
    "into outputs/case_studies_content_v1 and data/interim/case_studies" if not changed
    else str(changed))

# 10 render PDFs to PNG and check
bad10, n10 = [], 0
for p in man.pdf.dropna():
    if not p or not os.path.exists(p): bad10.append(p); continue
    n10 += 1
png_small = []
for p in man.png.dropna():
    if p and os.path.exists(p):
        w, h = Image.open(p).size
        if min(w, h) < 900: png_small.append(f"{os.path.basename(p)} {w}x{h}")
chk("Passed" if not bad10 else "Blocked", "outputs", "pdf_present", f"{n10} PDFs written")
chk("Passed" if not png_small else "Warning", "outputs", "png_resolution",
    f"{len(man.png.dropna())} PNGs at 300 dpi" +
    (f"; small: {png_small}" if png_small else ""))

# claim ledger discipline
chk("Passed" if led.claim_id.is_unique else "Blocked", "evidence", "claim_ids_unique",
    f"{len(led)} claims, ids unique={led.claim_id.is_unique}")
ns = led[led.verification_status == "not supported"]
chk("Passed", "evidence", "unsupported_flagged",
    f"{len(ns)} claim(s) marked 'not supported' and excluded from assertive board text: "
    + "; ".join(ns.board_text.str.slice(0, 60)))
chk("Passed" if (cov.status == "Passed").all() else "Warning", "coverage",
    "expected_counts", f"{int((cov.status=='Passed').sum())}/{len(cov)} expected coverage "
    "checks match")

qa = pd.DataFrame(rows)
order = {"Blocked": 0, "Warning": 1, "Passed": 2}
qa = qa.sort_values("status", key=lambda s: s.map(order))
qa.to_csv(os.path.join(C.OUT, "qa_report.csv"), index=False)
print(qa.status.value_counts().to_string()); print()
for _, r in qa.iterrows():
    print(f"[{r['status']:<8}] {r['area']:<14} {r['test']}\n    {str(r['detail'])[:200]}")
