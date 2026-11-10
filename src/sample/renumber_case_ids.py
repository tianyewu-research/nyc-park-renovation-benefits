"""Renumber Case IDs (2026-10-16): <borough letter><3-digit seq>, seq by construction start date within borough.
Borough letters follow NYC Parks property IDs: Q Queens, B Brooklyn, M Manhattan, X Bronx, R Staten Island.
Rules: IDs already in new format are KEPT (stable IDs; never renumber after assignment).
New rows get the next free number in their borough. Rows without a Tracker start date go after dated rows.
Old IDs (V/D/I/C/S) are kept in column 'Old Case ID'. Rows are re-sorted by Case ID."""
import openpyxl, pandas as pd, pathlib, re
from copy import copy
R = pathlib.Path(__file__).resolve().parents[2]
F = R/"casestudy/Case_Inventory.xlsx"
t = pd.read_csv(R/"data/raw/capital_projects/capital_project_tracker.csv", dtype=str).drop_duplicates("trackerid").set_index("trackerid")
wb = openpyxl.load_workbook(F); ws = wb["Case Inventory"]
h = {c.value: i+1 for i, c in enumerate(ws[1])}
if "Old Case ID" not in h:
    col = ws.max_column + 1; ws.cell(1, col, "Old Case ID")
    src = ws.cell(1, 12); c = ws.cell(1, col); c.font, c.fill, c.alignment, c.border = copy(src.font), copy(src.fill), copy(src.alignment), copy(src.border)
    ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 12
    for r in range(2, ws.max_row + 1): ws.cell(r, col, ws.cell(r, 1).value)
    h["Old Case ID"] = col
BOR = {"Queens": "Q", "Brooklyn": "B", "Manhattan": "M", "Bronx": "X", "Staten Island": "R"}
NEWFMT = re.compile(r"^[QBMXR]\d{3}$")
rows = []
for r in range(2, ws.max_row + 1):
    b = str(ws.cell(r, 3).value or "")
    pre = next((v for k, v in BOR.items() if b.startswith(k)), "Z")
    tid = re.match(r"\d+", str(ws.cell(r, h["Tracker ID"]).value or ""))
    cs = pd.to_datetime(t.loc[tid.group(0), "constructionstart"]) if tid and tid.group(0) in t.index else pd.NaT
    rows.append(dict(r=r, pre=pre, cs=cs, cid=str(ws.cell(r, 1).value or ""), old=str(ws.cell(r, h["Old Case ID"]).value or "")))
used = {}
for x in rows:
    if NEWFMT.match(x["cid"]): used.setdefault(x["pre"], set()).add(int(x["cid"][1:]))
todo = sorted([x for x in rows if not NEWFMT.match(x["cid"])], key=lambda x: (x["pre"], pd.isna(x["cs"]), x["cs"] if pd.notna(x["cs"]) else pd.Timestamp(0), x["old"]))
for x in todo:
    n = max(used.get(x["pre"], {0}) | {0}) + 1; used.setdefault(x["pre"], set()).add(n)
    x["cid"] = f"{x['pre']}{n:03d}"; ws.cell(x["r"], 1).value = x["cid"]
# physically sort rows by Case ID (Queens first)
order = {"Q": 0, "B": 1, "M": 2, "X": 3, "R": 4, "Z": 5}
snap = []
for x in rows:
    cells = [ws.cell(x["r"], j) for j in range(1, ws.max_column + 1)]
    snap.append((x["cid"], [(c.value, copy(c.font), copy(c.fill), copy(c.alignment), copy(c.border), c.number_format) for c in cells]))
snap.sort(key=lambda s: (order[s[0][0]] if s[0][0] in order else 9, s[0]))
for i, (_, cells) in enumerate(snap, start=2):
    for j, (v, f, fi, al, bo, nf) in enumerate(cells, start=1):
        c = ws.cell(i, j); c.value, c.font, c.fill, c.alignment, c.border, c.number_format = v, f, fi, al, bo, nf
g = wb["Field Guide"]
for row in g.iter_rows(min_row=2):
    if row[0].value == "Case ID":
        row[1].value = ("Borough letter + 3-digit number (Q Queens, B Brooklyn, M Manhattan, X Bronx, R Staten Island), numbered by Tracker construction start "
                        "within borough at first assignment (2026-10-16). IDs are stable: new projects get the next number, existing IDs are never renumbered. "
                        "Rows without a Tracker start date are numbered after dated rows. Previous V/D/I/C/S codes are in 'Old Case ID'.")
wb.save(F)
print(pd.DataFrame([(s[0], s[1][h['Old Case ID']-1][0], s[1][1][0]) for s in snap], columns=["Case ID","Old","Project"]).to_string(index=False))
