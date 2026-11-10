"""Round 3 master runner. Run from the project root:  python3 src/atlas/round3/run_round3.py

Fails loudly on a missing required layer or a failed population join. It will not
silently produce an empty map.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("1  audit + minimal acquisition",      "r3_01_acquire.py"),
    ("2  base layers (boro/pop/streets/subway)", "r3_02_base_layers.py"),
    ("3  building cartographic derivative", "r3_03_buildings.py"),
    ("4  governance + phase display fields", "r3_04_theme_layers.py"),
    ("5  Figure 0 contextual base",         "r3_05_fig0_base.py"),
    ("6  Figure 2 construction-starts chart","r3_06_chart_starts.py"),
    ("7  Figure 1 citywide + 5 borough details", "r3_07_fig1_greenspace.py"),
    ("8  round 3 GeoPackage",               "r3_08_gpkg.py"),
    ("9  QA",                               "r3_09_qa.py"),
]
REQUIRED = [
    "data/interim/atlas_round3/population_bg_2023.gpkg",
    "data/interim/atlas_round3/buildings_cartographic.gpkg",
    "data/interim/atlas_round3/streets_all.gpkg",
    "data/interim/atlas_round3/subway_routes.gpkg",
    "data/interim/atlas_round3/green_space_governance.gpkg",
    "outputs/atlas/gis/nyc_green_space_atlas_round3.gpkg",
]
FIGURES = ["map0_nyc_context_base", "map1_green_space_ownership_and_renovation_status",
           "map1a_bronx_green_space_detail", "map1b_brooklyn_green_space_detail",
           "map1c_manhattan_green_space_detail", "map1d_queens_green_space_detail",
           "map1e_staten_island_green_space_detail",
           "chart_recorded_construction_starts_by_year_and_borough"]

if os.path.basename(os.getcwd()) != "park_renovation_thesis":
    sys.exit("run from the project root: cd <repository root>")

for label, script in STEPS:
    print(f"\n=== {label} ===", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)])
    if r.returncode != 0:
        sys.exit(f"FAILED at step '{label}' ({script}); nothing further was produced.")

missing = [p for p in REQUIRED if not os.path.exists(p)]
if missing:
    sys.exit(f"FAILED: required layers absent -> {missing}")

print("\n=== manifest ===")
ok = True
for f in FIGURES:
    png, pdf = f"maps/round3/{f}.png", f"maps/round3/{f}.pdf"
    good = os.path.exists(png) and os.path.exists(pdf) and os.path.getsize(png) > 50_000
    ok &= good
    print(f"  [{'PASS  ' if good else 'REVIEW'}] maps/round3/{f}.png / .pdf")
for p in REQUIRED + ["outputs/atlas/qa_round3.csv",
                     "outputs/atlas/source_provenance_round3.csv",
                     "data/interim/atlas_round3/base_layer_audit.csv"]:
    print(f"  [{'PASS  ' if os.path.exists(p) else 'REVIEW'}] {p}")

import pandas as pd
qa = pd.read_csv("outputs/atlas/qa_round3.csv")
blocked = int((qa.status == "Blocked").sum()); review = int((qa.status == "Manual review").sum())
print(f"\nQA: {int((qa.status=='Passed').sum())} passed, {review} manual review, {blocked} blocked")
print("OVERALL: " + ("PASS" if ok and blocked == 0 else "REVIEW"))
