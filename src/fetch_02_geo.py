"""Download census geography for the 2019 era: TIGER 2019 block groups and the
official 2010<->2020 block-group relationship file.

Needs no API key and no account. Runs in about a minute.

Why this exists: 2019 Advan data carries 2010-vintage CBG ids; 2021+ carries
2020-vintage. Origin-distance calculations therefore need both boundary sets
plus a crosswalk between them.

The relationship file gives GEOID_BLKGRP_20 <-> GEOID_BLKGRP_10 with
AREALAND_PART, so a 2010 CBG's visits can be allocated to 2020 CBGs by land-area
share. NHGIS is not needed.

Usage:  python3 src/fetch_02_geo.py
"""

import io
import os
import zipfile

import urllib.request

OUT = "data/raw/census_geo_2010"

TIGER_BG_2019 = "https://www2.census.gov/geo/tiger/TIGER2019/BG/tl_2019_36_bg.zip"
RELFILE = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/blkgrp/"
           "tab20_blkgrp20_blkgrp10_st36.txt")

NYC_COUNTIES = {"005": "Bronx", "047": "Kings", "061": "New York",
                "081": "Queens", "085": "Richmond"}


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  exists, skipping: {dest}")
        return dest
    print(f"  downloading {os.path.basename(url)} ...", flush=True)
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    print(f"    -> {dest}  ({len(data) / 1e6:.1f} MB)")
    return dest


def main():
    os.makedirs(OUT, exist_ok=True)

    print("1. TIGER 2019 block groups, New York State (2010 vintage)")
    zpath = fetch(TIGER_BG_2019, os.path.join(OUT, "tl_2019_36_bg.zip"))
    ddir = os.path.join(OUT, "tl_2019_36_bg")
    if not os.path.isdir(ddir):
        with zipfile.ZipFile(zpath) as z:
            z.extractall(ddir)
        print(f"    extracted -> {ddir}")
    print("    contents:", ", ".join(sorted(os.listdir(ddir))))

    print("\n2. Official 2010 <-> 2020 block-group relationship file")
    rpath = fetch(RELFILE, os.path.join(OUT, "tab20_blkgrp20_blkgrp10_st36.txt"))

    # quick sanity check restricted to the five boroughs
    import pandas as pd
    rel = pd.read_csv(rpath, sep="|", dtype=str)
    rel.columns = [c.strip().lstrip("﻿") for c in rel.columns]
    rel["cty20"] = rel["GEOID_BLKGRP_20"].str[2:5]
    nyc = rel[rel["GEOID_BLKGRP_20"].str.startswith("36")
              & rel["cty20"].isin(NYC_COUNTIES)]
    print(f"    statewide rows: {len(rel):,}   NYC rows: {len(nyc):,}")
    print(f"    distinct 2020 CBGs in NYC: {nyc['GEOID_BLKGRP_20'].nunique():,}")
    print(f"    distinct 2010 CBGs in NYC: {nyc['GEOID_BLKGRP_10'].nunique():,}")
    split = nyc.groupby("GEOID_BLKGRP_10")["GEOID_BLKGRP_20"].nunique()
    print(f"    2010 CBGs mapping to >1 2020 CBG: {int((split > 1).sum()):,} "
          f"({(split > 1).mean():.0%}) -- these need area-weighted allocation")

    nyc_out = os.path.join(OUT, "bg_crosswalk_2010_2020_nyc.csv")
    nyc.to_csv(nyc_out, index=False)
    print(f"    wrote NYC-only crosswalk -> {nyc_out}")

    print("\nDone. Both items for notes/07 D8 are now in place.")


if __name__ == "__main__":
    main()
