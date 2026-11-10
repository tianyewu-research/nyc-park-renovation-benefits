"""Master runner. python3 src/case_studies/run_case_studies.py"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [("1  audit sources",        "cs_01_audit_sources.py"),
         ("2  extract PDF assets",   "cs_02_extract_pdf_assets.py"),
         ("3  case tables",          "cs_03_build_case_tables.py"),
         ("4  spatial context",      "cs_04_build_spatial_context.py"),
         ("5  mobile profiles",      "cs_05_build_mobile_profiles.py"),
         ("6  Bryant Park assets",   "cs_06_bryant_assets.py"),
         ("7  Washington Sq assets", "cs_07_washington_assets.py"),
         ("8  McCarren assets",      "cs_08_mccarren_assets.py"),
         ("9  board copy + ledger",  "cs_09_write_board_copy.py"),
         ("10 QA",                   "cs_10_qa.py")]
if os.path.basename(os.getcwd()) != "park_renovation_thesis":
    sys.exit("run from the project root")
for label, s in STEPS:
    print(f"\n=== {label} ===", flush=True)
    if subprocess.run([sys.executable, os.path.join(HERE, s)]).returncode != 0:
        sys.exit(f"FAILED at '{label}' ({s})")
import pandas as pd
sys.path.insert(0, HERE); import cs_00_config as C
man = pd.read_csv(os.path.join(C.OUT, "content_manifest.csv"))
img = pd.read_csv(os.path.join(C.OUT, "image_manifest.csv"))
qa = pd.read_csv(os.path.join(C.OUT, "qa_report.csv"))
print("\n=== manifest ===")
for cid in C.CASES:
    for b in C.BOARDS:
        f = len(man[(man.case_id == cid) & (man.board_id == b)])
        i = len(img[(img.case_id == cid) & (img.board_id == b) & (img.status == "ok")])
        print(f"  {cid:<4} {b:<26} {f} figures  {i} extracted images")
print(f"\nshared assets: {len(man[man.case_id.isna() | (man.case_id=='')])}")
n = qa.status.value_counts()
print(f"QA: {int(n.get('Passed',0))} passed, {int(n.get('Warning',0))} warning, "
      f"{int(n.get('Blocked',0))} blocked")
print("OVERALL: " + ("PASS" if int(n.get("Blocked", 0)) == 0 else "BLOCKED"))
