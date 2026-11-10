"""Update the master workbook for this atlas round.

Rules honoured:
  * the supplied workbook is the base; every sheet is preserved
  * ONE primary filterable Project Inventory table -- no competing inventories
  * Map_ID values already in the workbook are never renumbered
  * nothing is inferred: added columns record what the atlas DID, not new facts

Adds to Project Inventory:  Mapped_In_Atlas_Round1, Atlas_Map_Layer, Site_Type_Panel
Updates GIS Layer Index:    Local_Status / Local_Path for layers acquired this round
Adds sheet:                 Atlas_Round_Log (what this round produced)
"""
import glob
import shutil
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

SRC = "data/interim/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
OUT = "outputs/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
SNAP = "2026-09-08"

xl = pd.ExcelFile(SRC)
sheets = {s: xl.parse(s, header=None) if s == "Overview" else xl.parse(s)
          for s in xl.sheet_names}

# ---- Project Inventory --------------------------------------------------
pi = sheets["Project Inventory"]
lat = pd.to_numeric(pi["Latitude_Map"], errors="coerce")
lon = pd.to_numeric(pi["Longitude_Map"], errors="coerce")
mapped = lat.notna() & lon.notna()

pi["Mapped_In_Atlas_Round1"] = mapped.map({True: "Yes", False: "No - inventory only"})
pi["Atlas_Map_Layer"] = mapped.map(
    {True: "renovation_project_locations", False: ""})
pi["Site_Type_Panel"] = pi["Site_Type"]        # panel used on Map 3
pi["Atlas_Snapshot_Date"] = SNAP

# Public_Reopen_Date in the supplied workbook is a verbatim copy of the
# administrative completion date for every populated row. The project rule says
# administrative completion is NOT an automatic public reopening date, so the
# column is kept (supplied data is never deleted) but explicitly flagged rather
# than used as if it were independently sourced.
_pr = pd.to_datetime(pi["Public_Reopen_Date"], errors="coerce")
_cc = pd.to_datetime(pi["Construction_Actual_Completion"], errors="coerce")
_both = _pr.notna() & _cc.notna()
_ident = int((_pr[_both] == _cc[_both]).sum())
pi["Public_Reopen_Date_QA"] = ""
pi.loc[_both & (_pr == _cc), "Public_Reopen_Date_QA"] = (
    "Equals administrative Construction_Actual_Completion; NOT independently "
    "verified as a public reopening date. Do not treat as an access date.")
pi.loc[_pr.isna(), "Public_Reopen_Date_QA"] = "No reopening date recorded"
print(f"Public_Reopen_Date: {_ident}/{int(_both.sum())} rows identical to the "
      f"administrative completion date -> flagged, not used as an access date")
sheets["Project Inventory"] = pi
print(f"Project Inventory: {len(pi)} rows, {mapped.sum()} mapped, "
      f"{(~mapped).sum()} inventory-only")

# ---- GIS Layer Index ----------------------------------------------------
gi = sheets["GIS Layer Index"]
prov = pd.read_csv("logs/provenance_downloads.csv")
for _, r in prov[prov["status"] == "OK"].iterrows():
    m = gi["Layer_Name"] == r["layer_name"]
    gi.loc[m, "Local_Status"] = f"Downloaded {SNAP}"
    gi.loc[m, "Local_Path"] = r["local_path"]
# layers reused from local copies for this round
REUSED = {
    "Borough Boundaries": "data/raw/geography/Borough_Boundaries_20260623.geojson",
    "Parks Properties": "data/raw/park_boundaries/parks_properties_20260623/",
    "Capital Project Tracker": "data/raw/capital_projects/capital_project_tracker.csv",
}
for name, path in REUSED.items():
    m = gi["Layer_Name"] == name
    gi.loc[m, "Local_Status"] = f"Available locally; used in atlas round 1 ({SNAP})"
    gi.loc[m, "Local_Path"] = path
sheets["GIS Layer Index"] = gi
print(f"GIS Layer Index: {len(gi)} layers, "
      f"{int((gi['Local_Status'].astype(str).str.contains('atlas round 1|Downloaded')).sum())} touched this round")

# ---- round log ----------------------------------------------------------
log = pd.DataFrame([
    ("Scope", "Exploratory, reader-facing atlas round. No causal analysis, no thesis sample."),
    ("Snapshot date", SNAP),
    ("Project-location records", "2,758 (full Capital Project Tracker universe preserved)"),
    ("Mapped project locations", "2,474"),
    ("Inventory-only (no usable coordinate)", "284 — retained here with null map geometry"),
    ("Map 1", "maps/map1_green_space_and_renovation_landscape.png / .pdf"),
    ("Map 2a", "maps/map2_phase_status.png / .pdf  (current phase map)"),
    ("Map 2b", "maps/chart_construction_starts_by_year.png / .pdf  (annual starts by borough)"),
    ("Map 2 (archived)", "maps/archive/map2_phase_and_timing_pre_split_20260909.png / .pdf "
                         "— combined map+chart, superseded 2026-09-09"),
    ("Map 3", "maps/map3_site_model_mismatch.png / .pdf"),
    ("GIS package", "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg (EPSG:2263)"),
    ("Share export", "outputs/atlas/gis/renovation_project_locations_4326.geojson"),
    ("Layers acquired", "GreenThumb (p78i-pat6); POPS (qeta-4kqg); Active & Passive Recreation (kcqe-vnci)"),
    ("Layers reused locally", "Borough Boundaries; Parks Properties; Capital Project Tracker"),
    ("Illustrative labelled set", "Not created — no map in this round labels individual projects, "
                                  "so no numbered subset was needed. Map_ID values are unchanged."),
    ("Key caveat 1", "283 of the 284 unmapped records are also the records with no Park ID: "
                     "missing location and missing site identity are the same gap."),
    ("Key caveat 2", "Public_Reopen_Date is a verbatim copy of Construction_Actual_Completion "
                     "for all 1,775 populated rows. Flagged in Public_Reopen_Date_QA; the atlas "
                     "does not treat it as a public access date. Needs an independent source."),
    ("Not done this round", "Regression, event study, clustering, accessibility/network modelling, "
                            "catchment analysis, equity indices, mobile-data linkage, causal claims."),
], columns=["Item", "Value"])
sheets["Atlas_Round_Log"] = log

# ---- write --------------------------------------------------------------
with pd.ExcelWriter(OUT, engine="openpyxl") as w:
    for name, df in sheets.items():
        df.to_excel(w, sheet_name=name, index=False,
                    header=(name != "Overview"))
print(f"\nwrote {OUT}")
for name, df in sheets.items():
    print(f"  {name:<24} {len(df):>5} rows x {df.shape[1]:>3} cols")
