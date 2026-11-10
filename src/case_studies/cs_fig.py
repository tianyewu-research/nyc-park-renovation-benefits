"""Shared figure export: PDF + SVG + 300 dpi PNG + plotted-data CSV + caption .md."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
sys.path.insert(0, os.path.join(C.ROOT, "src/atlas/round4"))
import r4_04_style as R4
import matplotlib.pyplot as plt
import pandas as pd

BG, INK, INK_2, MUTED, EDGE, LAND = R4.BG, R4.INK, R4.INK_2, R4.MUTED, R4.EDGE, R4.LAND
TEAL, TEAL_M = R4.GOV["NYC Parks"], R4.GOV["Other public parkland"]
ORANGE, RUST = R4.GOV["Privately owned public access"], R4.PHASE["Construction"]
PHASE, COMPLETED = R4.PHASE, R4.COMPLETED
BLDG, ST, SUB, STA = R4.BLDG, R4.ST_PRINCIPAL, R4.SUBWAY, R4.STATION
blank, north_arrow, scale_bar = R4.blank, R4.north_arrow, R4.scale_bar

MANIFEST = []

def export(fig, out_dir, stem, title, caption, method, unit, source,
           data: pd.DataFrame = None, case_id="", board="", kind="figure"):
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for ext in ("pdf", "png", "svg"):
        p = os.path.join(out_dir, f"{stem}.{ext}")
        try:
            fig.savefig(p, dpi=300 if ext == "png" else None, facecolor=BG,
                        bbox_inches="tight")
            paths[ext] = p
        except Exception as e:
            print(f"    {ext} failed: {type(e).__name__}")
    plt.close(fig)
    dcsv = ""
    if data is not None:
        ddir = out_dir.replace("/figures", "/data").replace("/maps", "/data")
        os.makedirs(ddir, exist_ok=True)
        dcsv = os.path.join(ddir, f"{stem}__plotted_data.csv")
        data.to_csv(dcsv, index=False)
    md = os.path.join(out_dir, f"{stem}.md")
    with open(md, "w") as f:
        f.write(f"# {title}\n\n**Caption.** {caption}\n\n**Method.** {method}\n\n"
                f"**Unit.** {unit}\n\n**Source.** {source}\n\n"
                f"**Files.** " + ", ".join(f"`{os.path.basename(v)}`" for v in paths.values())
                + (f", `{os.path.basename(dcsv)}`" if dcsv else "") + "\n")
    MANIFEST.append(dict(case_id=case_id, board_id=board, kind=kind, stem=stem,
        title=title, pdf=paths.get("pdf", ""), png=paths.get("png", ""),
        svg=paths.get("svg", ""), plotted_data_csv=dcsv, caption_md=md,
        unit=unit, source=source))
    print(f"    {stem}: " + "+".join(paths) + (" +csv" if dcsv else ""))
    return paths

def source_line(fig, text, y=.012, x=.02, size=7.0):
    fig.text(x, y, text, fontsize=size, color=MUTED, va="bottom", wrap=True)

def flush_manifest():
    p = os.path.join(C.OUT, "content_manifest.csv")
    df = pd.DataFrame(MANIFEST)
    if os.path.exists(p):
        old = pd.read_csv(p)
        df = pd.concat([old[~old.stem.isin(df.stem)], df], ignore_index=True)
    df.to_csv(p, index=False)
    return len(df)
