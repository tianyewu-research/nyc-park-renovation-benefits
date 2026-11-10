"""Phase 1 (this round) — acquire only the layers the three maps need.

The GIS Layer Index inside the supplied workbook is the authoritative
acquisition register. Nothing here is reconstructed from memory: every URL and
dataset id is read out of that sheet.

Scope for this round is deliberately narrow. Layers marked NEEDED below are the
minimum for Maps 1-3; everything else in the register is left alone.

Writes provenance for every fetch to logs/provenance_downloads.csv.
"""

import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import pandas as pd

WB = "data/interim/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
DEST = "data/raw/external_downloads"
PROV = "logs/provenance_downloads.csv"

# layer names exactly as they appear in the register
NEEDED = [
    "GreenThumb Garden Info",
    "Privately Owned Public Spaces",
    "NYC Parks Active and Passive Recreation",
]

SLUG = {
    "GreenThumb Garden Info": "greenthumb_gardens",
    "Privately Owned Public Spaces": "pops",
    "NYC Parks Active and Passive Recreation": "active_passive_recreation",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    reg = pd.read_excel(WB, sheet_name="GIS Layer Index")
    os.makedirs(DEST, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    rows = []
    for name in NEEDED:
        r = reg[reg["Layer_Name"] == name]
        if r.empty:
            print(f"  !! '{name}' not in the register -- skipped, not invented")
            continue
        r = r.iloc[0]
        url = r["Direct_Download_URL"]
        slug = SLUG[name]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        dest = os.path.join(DEST, f"{slug}_{stamp}.geojson")

        print(f"\n{name}")
        print(f"  dataset_id : {r['Dataset_ID']}")
        print(f"  register    : Priority={r['Priority']}  Local_Status={r['Local_Status']}")

        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print("  already downloaded, skipping fetch")
        else:
            print(f"  GET {url[:88]}...")
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "nyc-green-space-atlas/research"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = resp.read()
                with open(dest, "wb") as f:
                    f.write(data)
            except Exception as e:
                print(f"  FAILED: {type(e).__name__}: {e}")
                rows.append({"layer_name": name, "dataset_id": r["Dataset_ID"],
                             "source_url": url, "local_path": "",
                             "accessed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "status": f"FAILED {type(e).__name__}", "sha256": "",
                             "n_records": pd.NA, "crs": "", "geometry_type": "",
                             "size_mb": pd.NA,
                             "official_page": r.get("Official_Page", ""),
                             "licence": "NYC Open Data Terms of Use",
                             "register_limitation": r.get("Important_Limitation", "")})
                continue

        # verify it parses and record what it actually contains
        try:
            import geopandas as gpd
            g = gpd.read_file(dest)
            n, crs = len(g), str(g.crs)
            gt = ",".join(sorted(map(str, g.geom_type.dropna().unique())))
            print(f"  OK  {n} features · CRS {crs} · {gt}")
        except Exception as e:
            n, crs, gt = pd.NA, "", ""
            print(f"  parsed FAILED: {type(e).__name__}: {e}")

        rows.append({
            "layer_name": name, "dataset_id": r["Dataset_ID"], "source_url": url,
            "local_path": dest,
            "accessed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "OK", "sha256": sha256(dest), "n_records": n, "crs": crs,
            "geometry_type": gt, "size_mb": round(os.path.getsize(dest) / 1e6, 2),
            "official_page": r.get("Official_Page", ""),
            "licence": "NYC Open Data Terms of Use",
            "register_limitation": r.get("Important_Limitation", ""),
        })

    prov = pd.DataFrame(rows)
    if os.path.exists(PROV):
        prov = pd.concat([pd.read_csv(PROV), prov], ignore_index=True)
    prov.to_csv(PROV, index=False)
    print(f"\nwrote {PROV}")


if __name__ == "__main__":
    main()
