"""Step 2 — render selected PDF pages at 300 dpi with Poppler. Sources never modified."""
import os, subprocess, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
import pandas as pd
from PIL import Image

# (case, board, source file, page, stem, caption, creator, rights)
SEL = [
 ("BP","board_1_history_profile","Bryant Park History.pdf",1,"BP_hist_p1",
  "Bryant Park history narrative, page 1","Bryant Park Corporation","reference only"),
 ("BP","board_2_renovation","BryantPark_1996_2016_2023-05.12.2024.pdf",1,"BP_ward_p1",
  "Alan Ward, Bryant Park 1996/2016 photographic study, cover","Alan Ward","reference only"),
 ("BP","board_2_renovation","BryantPark_1996_2016_2023-05.12.2024.pdf",5,"BP_ward_p5",
  "Alan Ward, paired 1996/2016 views","Alan Ward","reference only"),
 ("BP","board_2_renovation","BryantPark_1996_2016_2023-05.12.2024.pdf",9,"BP_ward_p9",
  "Alan Ward, paired 1996/2016 views","Alan Ward","reference only"),
 ("BP","board_3_use_outcomes","Bryant Park – OLIN.pdf",1,"BP_olin_p1",
  "OLIN project page: designer of record and award record","OLIN","reference only"),

 ("WSP","board_1_history_profile","wsp_final_report_pps.pdf",1,"WSP_pps_p1",
  "PPS Washington Square Park report, cover","Project for Public Spaces","reference only"),
 ("WSP","board_1_history_profile","wsp_final_report_pps.pdf",9,"WSP_pps_p9",
  "PPS pre-renovation use analysis page","Project for Public Spaces","reference only"),
 ("WSP","board_1_history_profile","wsp_final_report_pps.pdf",17,"WSP_pps_p17",
  "PPS observation/count material","Project for Public Spaces","reference only"),
 ("WSP","board_2_renovation","wsp.pdf",1,"WSP_phase1_schematic",
  "Phase 1 reconstruction schematic: northwest quadrant, Fountain Plaza, Thompson Street entrance",
  "NYC Parks, DPR Capital Projects","reference only"),
 ("WSP","board_2_renovation","news-ribbon-washington-square-park-comfort.pdf",1,"WSP_comfort_p1",
  "Comfort station completion notice","NYC Parks","reference only"),

 ("MCP","board_1_history_profile","2244.pdf",1,"MCP_lpc_p1",
  "LPC designation report LP-2244, McCarren Play Center, cover","NYC Landmarks Preservation Commission","public record"),
 ("MCP","board_1_history_profile","2244.pdf",12,"MCP_lpc_p12",
  "LPC designation report, historic description","NYC Landmarks Preservation Commission","public record"),
 ("MCP","board_1_history_profile","2012-06-28-NYTimes_McCarren.pdf",1,"MCP_nyt_p1",
  "New York Times, 28 June 2012, reopening report","The New York Times / Lisa W. Foderaro","reference only"),
] + [("MCP","board_2_renovation","B058_09-0717-Landmarks Boards shown to bidders FINAL.pdf",i,
      f"MCP_rm_board_{i}", f"2008 Rogers Marvel design board {i} of 5, shown to bidders",
      "Rogers Marvel Architects / NYC Parks","reference only") for i in range(1, 6)] + [
 ("MCP","board_2_renovation","McCarren_Results.pdf",2,"MCP_results_p2",
  "McCarren community survey results","NYC Parks (survey report)","reference only"),
]

rows = []
src_man = pd.read_csv(os.path.join(C.OUT, "source_manifest.csv"))
for cid, board, fname, page, stem, cap, creator, rights in SEL:
    src = os.path.join(C.CASES[cid]["src"], fname)
    if not os.path.exists(src):
        rows.append(dict(case_id=cid, board_id=board, stem=stem, source_pdf=src,
                         page=page, status="source_missing")); continue
    outdir = os.path.join(C.board_dir(cid, board), "images"); os.makedirs(outdir, exist_ok=True)
    prefix = os.path.join(outdir, stem)
    r = subprocess.run(["pdftoppm", "-r", "300", "-f", str(page), "-l", str(page),
                        "-png", "-singlefile", src, prefix], capture_output=True)
    png = prefix + ".png"
    if r.returncode != 0 or not os.path.exists(png):
        rows.append(dict(case_id=cid, board_id=board, stem=stem, source_pdf=src,
                         page=page, status=f"render_failed:{r.returncode}")); continue
    with Image.open(png) as im: w, h = im.size
    rows.append(dict(case_id=cid, board_id=board, stem=stem, output_png=png,
        source_pdf=src, source_file=fname, page=page, crop="full page",
        width_px=w, height_px=h, dpi=300, caption=cap, creator=creator,
        rights_status=rights, status="ok",
        source_sha256_16=src_man.loc[src_man.file_name == fname, "sha256_16"].iloc[0]
            if (src_man.file_name == fname).any() else ""))
    print(f"  {stem}: p{page} {w}x{h}")

im = pd.DataFrame(rows)
im.to_csv(os.path.join(C.OUT, "image_manifest.csv"), index=False)
print(f"\nimage_manifest.csv: {len(im)} entries | ok {int((im.status=='ok').sum())}")
print(im.groupby(['case_id','board_id']).size().to_string())
