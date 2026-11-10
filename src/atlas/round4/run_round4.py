"""Round 4 master runner.  python3 src/atlas/round4/run_round4.py

Stops at the first failure. Will not carry on and emit a misleading map when a
required polygon layer is missing.
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [("1  geometry audit",              "r4_01_geometry_audit.py"),
         ("2  parcelise point governance",  "r4_02_parcelize_governance.py"),
         ("3  derived polygon layers",      "r4_03_build_site_status.py"),
         ("4  Figure 0 context",            "r4_05_fig0_context.py"),
         ("5  Figure 1 governance",         "r4_06_fig1_governance.py"),
         ("6  Figure 2 renovation sites",   "r4_07_fig2_renovation_sites.py"),
         ("7  Figure 3 summary panels",     "r4_08_fig3_summary.py"),
         ("8  round 4 GeoPackage",          "r4_10_gpkg.py"),
         ("9  QA",                          "r4_09_qa.py")]
REQUIRED = ["data/interim/atlas_round4/governance_display_polygons.gpkg",
            "data/interim/atlas_round4/renovation_site_status.gpkg",
            "data/interim/atlas_round4/pops_parcels.gpkg",
            "outputs/atlas/gis/nyc_green_space_atlas_round4.gpkg"]
FIGS = ["fig0_nyc_context_population_transport", "fig1_open_space_governance_polygons",
        "fig2_renovation_status_site_polygons", "fig3_renovation_summary_panels"]

if os.path.basename(os.getcwd()) != "park_renovation_thesis":
    sys.exit("run from the project root: cd <repository root>")
for label, script in STEPS:
    print(f"\n=== {label} ===", flush=True)
    if subprocess.run([sys.executable, os.path.join(HERE, script)]).returncode != 0:
        sys.exit(f"FAILED at '{label}' ({script}). No further output produced; "
                 "polygon matching did not silently fall back to point symbols.")
missing = [p for p in REQUIRED if not os.path.exists(p)]
if missing:
    sys.exit(f"FAILED: required polygon layers absent -> {missing}")

print("\n=== manifest ===")
from PIL import Image
for f in FIGS:
    png, pdf = f"maps/round4/{f}.png", f"maps/round4/{f}.pdf"
    if os.path.exists(png) and os.path.exists(pdf):
        w, h = Image.open(png).size
        print(f"  [PASS  ] {png}  {w}x{h}px  {os.path.getsize(png)/1e6:.1f} MB"
              f"   |  {pdf}  {os.path.getsize(pdf)/1e6:.1f} MB")
    else:
        print(f"  [REVIEW] {f}: PNG or PDF missing")
for p in REQUIRED + ["outputs/atlas/qa_round4.csv",
                     "outputs/atlas/source_provenance_round4.csv",
                     "data/interim/atlas_round4/geometry_audit.csv",
                     "maps/round4/README_round4.md"]:
    print(f"  [{'PASS  ' if os.path.exists(p) else 'REVIEW'}] {p}")
import pandas as pd
qa = pd.read_csv("outputs/atlas/qa_round4.csv")
n = qa.status.value_counts()
print(f"\nQA: {int(n.get('Passed',0))} passed, {int(n.get('Warning',0))} warning, "
      f"{int(n.get('Manual review',0))} manual review, {int(n.get('Blocked',0))} blocked")
print("OVERALL: " + ("PASS" if int(n.get("Blocked", 0)) == 0 else "BLOCKED"))
