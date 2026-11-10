"""Step 1 — inventory and text-extract every local source. Sources are read-only."""
import hashlib, os, subprocess, sys, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
import pandas as pd
from PIL import Image

TXT = os.path.join(C.INTERIM, "pdf_text")
os.makedirs(TXT, exist_ok=True)
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

def sha(p, lim=64 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        n = 0
        while n < lim:
            b = f.read(1 << 20)
            if not b: break
            h.update(b); n += len(b)
    return h.hexdigest()[:16]

rows, gaps = [], []
for cid, cfg in C.CASES.items():
    folder = cfg["src"]
    if not os.path.isdir(folder):
        gaps.append(dict(case_id=cid, gap_type="source_folder_missing", detail=folder))
        continue
    for fn in sorted(os.listdir(folder)):
        fp = os.path.join(folder, fn)
        if os.path.isdir(fp) or fn.startswith("."):
            continue
        ext = os.path.splitext(fn)[1].lower()
        rec = dict(case_id=cid, file_name=fn, source_path=fp, file_type=ext.lstrip("."),
                   size_mb=round(os.path.getsize(fp)/1e6, 3), sha256_16=sha(fp),
                   modified=datetime.fromtimestamp(os.path.getmtime(fp), timezone.utc)
                            .strftime("%Y-%m-%d"),
                   page_count=pd.NA, pdf_title="", pdf_author="",
                   img_width=pd.NA, img_height=pd.NA,
                   evidence_status="usable", exclusion_reason="")
        if fn in C.EXCLUDE_AS_EVIDENCE:
            rec["evidence_status"] = "excluded"; rec["exclusion_reason"] = C.EXCLUDE_REASON
        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(fp) as pdf:
                    rec["page_count"] = len(pdf.pages)
                    md = pdf.metadata or {}
                    rec["pdf_title"] = str(md.get("Title", ""))[:120]
                    rec["pdf_author"] = str(md.get("Author", ""))[:120]
                    if rec["evidence_status"] == "usable":
                        stem = f"{cid}__" + os.path.splitext(fn)[0].replace(" ", "_")[:60]
                        with open(os.path.join(TXT, stem + ".txt"), "w") as out:
                            for i, page in enumerate(pdf.pages, 1):
                                out.write(f"\n===== PAGE {i} =====\n")
                                out.write((page.extract_text() or "").strip() + "\n")
            except Exception as e:
                rec["evidence_status"] = "unreadable"
                rec["exclusion_reason"] = f"{type(e).__name__}: {e}"
        elif ext in IMG_EXT:
            try:
                with Image.open(fp) as im:
                    rec["img_width"], rec["img_height"] = im.size
            except Exception as e:
                rec["evidence_status"] = "unreadable"
                rec["exclusion_reason"] = f"{type(e).__name__}"
        rows.append(rec)

# the two official McCarren attendance CSVs
for key, lbl in (("mcp_att_old", "jvwx-xnsr.csv"), ("mcp_att_new", "82jf-bykm.csv")):
    fp = C.p(key)
    if os.path.exists(fp):
        d = pd.read_csv(fp, low_memory=False)
        rows.append(dict(case_id="MCP", file_name=lbl, source_path=fp, file_type="csv",
            size_mb=round(os.path.getsize(fp)/1e6, 3), sha256_16=sha(fp),
            modified=datetime.fromtimestamp(os.path.getmtime(fp), timezone.utc).strftime("%Y-%m-%d"),
            page_count=pd.NA, pdf_title=f"{len(d)} rows x {d.shape[1]} cols",
            pdf_author="; ".join(map(str, d.columns[:10])), img_width=pd.NA, img_height=pd.NA,
            evidence_status="usable", exclusion_reason=""))
    else:
        gaps.append(dict(case_id="MCP", gap_type="attendance_csv_missing", detail=fp))

man = pd.DataFrame(rows)
man.to_csv(os.path.join(C.OUT, "source_manifest.csv"), index=False)
pd.DataFrame(gaps or [dict(case_id="", gap_type="", detail="")]).to_csv(
    os.path.join(C.OUT, "data_gaps.csv"), index=False)
print(f"source_manifest.csv: {len(man)} files")
for cid in C.CASES:
    s = man[man.case_id == cid]
    print(f"  {cid}: {len(s)} files | pdf {int((s.file_type=='pdf').sum())} "
          f"| img {int(s.file_type.isin(['jpg','jpeg','png','webp']).sum())} "
          f"| excluded {int((s.evidence_status=='excluded').sum())} "
          f"| unreadable {int((s.evidence_status=='unreadable').sum())}")
print(f"  pages extracted -> {TXT}")
