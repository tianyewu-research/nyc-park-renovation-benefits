"""Add sample-status + pilot coding fields to casestudy/Case_Inventory.xlsx (in place, styles kept).
Backup: casestudy/Case_Inventory_backup_2026-10-07.xlsx. Re-runnable: rewrites columns M+ and S-rows."""
import sys
sys.exit("SUPERSEDED 2026-10-16: Case IDs renumbered (see renumber_case_ids.py). Do not rerun; it keys on old S-codes.")
import openpyxl, pandas as pd, pathlib, re
from copy import copy
R = pathlib.Path(__file__).resolve().parents[2]
F = R/"casestudy/Case_Inventory.xlsx"
t = pd.read_csv(R/"data/raw/capital_projects/capital_project_tracker.csv", dtype=str)
t["cs"] = pd.to_datetime(t.constructionstart); t["ce"] = pd.to_datetime(t.constructionactualcompletion.fillna(t.constructionadjustedcompletion))
tt = t.dropna(subset=["cs"]); u = t.drop_duplicates("trackerid").set_index("trackerid")
smp = pd.read_csv(R/"data/interim/sample/sample_list_v1.csv", dtype=str).set_index("trackerid")
pil = pd.read_excel(R/"casestudy/codebook/pilot_coding_v0.xlsx", sheet_name="projects", dtype=str).set_index("trackerid")
ev = pd.read_excel(R/"casestudy/codebook/pilot_coding_v0.xlsx", sheet_name="evidence", dtype=str)
INFRA = r"Roof|Filtration|Filter|Electrical|Plumbing|Boiler|HVAC|Condenser|Citywide|General Site Work|Seawall|Retaining Wall|Water Service|Generator|Elevator|Office|Garage|Expansion Joint|Structural|Sewer|Tower|Bridge"
W = pd.Timedelta(weeks=26)
EXP = [(pd.Timestamp("2019-01-07"), pd.Timestamp("2020-03-01")), (pd.Timestamp("2021-07-05"), pd.Timestamp("2025-12-29"))]
cov = lambda a, b: any(a >= s and b <= e for s, e in EXP)
def status(tid):
    if not tid: return "non-DPR (not in Tracker)", ""
    if tid in smp.index:
        r = smp.loc[tid]; return f"{r.status} (sample v1)", "yes" if r.robust52 == "True" else "no"
    if tid not in u.index: return "not in Tracker snapshot", ""
    r = u.loc[tid]; why = []
    if pd.isna(r.cs) or pd.isna(r.ce): why.append("missing dates")
    else:
        if not (cov(r.cs - W, r.cs) and cov(r.ce, r.ce + W)): why.append("no 26wk mobility before/after")
        o = tt[(tt.parkid == r.parkid) & (tt.trackerid != tid)]
        if ((o.cs <= r.ce + W) & (o.ce.fillna(pd.Timestamp("2030")) >= r.cs - W)).any(): why.append("other project same park")
    if re.search(INFRA, r.title, re.I): why.append("infrastructure-only")
    return "out: " + "; ".join(why or ["no matched POI"]), ""
AM = ["am_play","am_spray","am_sports_surface","am_courts","am_track","am_fitness","am_seating","am_shade_trees","am_lighting",
      "am_paths_entrances","am_accessibility","am_restroom_building","am_planting_gi","am_fencing"]
CODE = ["eligible","multi_site","non_dpr_overlap","scope_extent","area_share","title_verb","primary_type"] + AM + \
       ["am_other","layout_change","entrance_change","target_users","community_request","funding_sources_named",
        "reopening_date_reported","co_works","evidence_status"]
NEW = ["Tracker ID","Park ID","Sample status (v1, 2026-10-07)","52wk robustness","Pilot coding v0","Study area"] + CODE + \
      ["relocated","displaced_use","Key sources (full list: codebook/pilot_coding_v0.xlsx > evidence)","Coder","Verified by TW","TW notes"]
NEWROWS = [("S01","8872","Playground full reconstruction"),("S02","7277","Playground + African Burial Ground commemorative area"),
           ("S03","1482111","Synthetic turf field reconstruction"),("S04","1534111","Path reconstruction"),
           # Queens sample v1 confirmed (added 2026-10-16)
           ("S05","1484111","Synthetic turf field reconstruction"),("S06","1400111","Ballfield lighting (LED) reconstruction"),
           ("S07","1379111","Ballfield lighting (LED) reconstruction"),("S08","1398111","Ballfield lighting (LED) reconstruction"),
           ("S09","10061","Staircase reconstruction"),("S10","1736111","Synthetic turf field reconstruction"),
           ("S11","6840","Basketball courts reconstruction"),("S12","9552","Playground reconstruction"),
           ("S13","7289","Playground reconstruction"),("S14","9550","Baseball fields (natural turf) reconstruction"),
           ("S15","8547","Marina docks/pier reconstruction (Sandy)"),("S16","7269","Asphalt ballfield reconstruction")]
wb = openpyxl.load_workbook(F); ws = wb["Case Inventory"]
# keep manual edits: existing non-empty coding/TW cells win over generated drafts
KEEP = {}
hdrs = [c.value for c in ws[1]]
for r in range(2, ws.max_row + 1):
    cid = ws.cell(r, 1).value
    for j, h in enumerate(hdrs, 1):
        if j > 12 and h not in ("Tracker ID","Park ID","Sample status (v1, 2026-10-07)","52wk robustness"):
            v = ws.cell(r, j).value
            if v not in (None, ""): KEEP[(cid, h)] = v
# drop previous run's S-rows and columns M+
for r in range(ws.max_row, 1, -1):
    if str(ws.cell(r, 1).value or "").startswith("S"): ws.delete_rows(r)
if ws.max_column > 12: ws.delete_cols(13, ws.max_column - 12)
last = ws.max_row
for cid, tid, itype in NEWROWS:
    r = u.loc[tid]; s = smp.loc[tid]; ws.append([None]*12); n = ws.max_row
    for c in range(1, 13):
        src = ws.cell(last, c); dst = ws.cell(n, c)
        dst.font, dst.alignment, dst.border, dst.fill, dst.number_format = copy(src.font), copy(src.alignment), copy(src.border), copy(src.fill), src.number_format
    vals = [cid, r.title, r.borough, itype,
            f"Construction: {r.cs:%b %Y}–{r.ce:%b %Y} (administrative)", s.location_name if isinstance(s.location_name, str) else "",
            f"{r.totalfunding}; park acreage to add", "NYC Parks (DPR)",
            "https://www.nycgovparks.org/planning-and-building/capital-project-tracker/project/" + tid,
            "Pilot coding project (codebook v0). Passes sample v1 threshold (26wk before/after, no other DPR project, matched POI). Pilot",
            float(r.latitude), float(r.longitude)]
    for c, v in enumerate(vals, 1): ws.cell(n, c, v)
hdr = ws.cell(1, 12)
for j, name in enumerate(NEW):
    c = ws.cell(1, 13 + j, name)
    c.font, c.fill, c.alignment, c.border = copy(hdr.font), copy(hdr.fill), copy(hdr.alignment), copy(hdr.border)
    ws.column_dimensions[openpyxl.utils.get_column_letter(13 + j)].width = 40 if name.startswith("Key") else (28 if name in ("am_other","target_users","co_works","TW notes","Sample status (v1, 2026-10-07)") else 16)
for r in range(2, ws.max_row + 1):
    url = str(ws.cell(r, 9).value or ""); m = re.search(r"/project/(\d+)", url)
    cid = ws.cell(r, 1).value
    tid = m.group(1) if m else ("8965" if cid == "I02" else "")
    st, rb = status(tid)
    row = {"Tracker ID": tid + (" (+8987)" if cid == "I02" else ""), "Park ID": u.loc[tid].parkid if tid in u.index else "",
           "Sample status (v1, 2026-10-07)": st, "52wk robustness": rb}
    if tid in pil.index:
        p = pil.loc[tid]; row["Pilot coding v0","Study area"] = "yes"
        for k in CODE: row[k] = "" if pd.isna(p.get(k)) else str(p.get(k)).replace("|", " (") + (")" if "|" in str(p.get(k)) else "")
        e = ev[ev.trackerid == tid]
        row["Key sources (full list: codebook/pilot_coding_v0.xlsx > evidence)"] = "\n".join(dict.fromkeys(e.source_url))
        row["Coder"] = "draft"
    for (k_cid, k_h), v in KEEP.items():
        if k_cid == cid: row[k_h] = v
    ref = ws.cell(r, 12)
    for j, name in enumerate(NEW):
        c = ws.cell(r, 13 + j, row.get(name, ""))
        c.font, c.alignment, c.border = copy(ref.font), copy(ref.alignment), copy(ref.border)
ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{ws.max_row}"
g = wb["Field Guide"]
while g.max_row > 7: g.delete_rows(g.max_row)
g.cell(2, 2).value = "V = video-screen candidate; D = data-demonstration case; I = ASLA/context inventory; C = tracker-based inventory candidate; S = sample-v1 project added for coding (2026-10-07)."
for f, h in [("Sample status (v1)", "confirmed = passes threshold with 2023–25 mobility data; pending = passes only if 2019–22 data arrive; out = fails (reason given). Rule: 26wk mobility before construction start and after admin completion, no other DPR project in same park within ±26wk, not infrastructure-only, park matched to Advan POI. Script: src/sample/build_sample_list.py"),
             ("52wk robustness", "yes = project also has 52wk before/after coverage (with 2019–22 data); used for robustness checks."),
             ("Coding fields (eligible … evidence_status)", "Defined in casestudy/codebook/codebook_v0.md. Amenity codes: ADD/UPG/REP/REM/CHG/NC/NM, confidence in brackets (H/M/L). NM = not mentioned, not 'no change'."),
             ("Coder / Verified by TW / TW notes", "Draft values remain provisional until TW fills 'Verified by TW' (date). Edit coding cells directly; put image dates and reasoning in TW notes.")]:
    g.append([f, h])
    for c in g[g.max_row]: c.alignment = copy(g.cell(7, 2).alignment); c.font = copy(g.cell(7, 2).font)
wb.save(F)
print("rows", ws.max_row - 1, "cols", ws.max_column)
