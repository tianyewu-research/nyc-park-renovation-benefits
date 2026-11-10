"""Download every ACS 5-year table this thesis needs, for every vintage.

The Census API now REQUIRES a key: a keyless request 302s to
api.census.gov/data/missing_key.html and returns nothing. Get a free key at
https://api.census.gov/data/key_signup.html (arrives by email in minutes), then:

    export CENSUS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    python3 src/fetch_01_acs.py

Writes data/raw/acs_panel/acs5_<year>/<TABLE>_<geo>.csv

Vintage note: ACS 2019 5-year is published on 2010-vintage tracts/block groups;
2023 and later use 2020 vintage. They are NOT directly comparable by GEOID --
use data/raw/census_geo_2010/bg_crosswalk_2010_2020_nyc.csv (fetch_02_geo.py).

B19013 is also pulled at TRACT level because its block-group margins of error are
very large; the LPUR paper assigns the tract median to constituent block groups
and this thesis follows the same rule.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

OUT = "data/raw/acs_panel"
STATE = "36"
COUNTIES = ["005", "047", "061", "081", "085"]   # Bronx Kings NewYork Queens Richmond

# table -> why it is here
TABLES = {
    "B01003": "total population",
    "B03002": "hispanic origin by race (LPUR paper uses this, NOT B02001)",
    "B19013": "median household income",
    "B25003": "tenure (owner/renter)",
    "B25064": "median gross rent",
    "B25077": "median home value",
}

# 2019 -> era 1 origin SES (2010 geography)
# 2023 -> main analysis (already in ../paper_walkability, re-pulled here for a
#         self-contained panel)
# 2024 -> later comparison point for the green-gentrification check
VINTAGES = [2019, 2023, 2024]

GEOS = {
    "bg": ("block%20group:*", f"state:{STATE}%20county:{{county}}"),
    "tract": ("tract:*", f"state:{STATE}%20county:{{county}}"),
}
# only B19013 needs the tract-level pull
TRACT_ONLY = {"B19013"}


def request(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                if r.geturl().endswith("missing_key.html"):
                    raise SystemExit(
                        "Census API rejected the key.\n"
                        "  Set a valid key:  export CENSUS_API_KEY=...\n"
                        "  Sign up (free):   https://api.census.gov/data/key_signup.html")
                return json.loads(r.read().decode())
        except SystemExit:
            raise
        except Exception as e:  # transient 500s are common on this API
            if i == tries - 1:
                print(f"      FAILED after {tries} tries: {e}")
                return None
            time.sleep(2 * (i + 1))
    return None


def pull(year, table, geo, key):
    for_clause, in_tmpl = GEOS[geo]
    rows, header = [], None
    for county in COUNTIES:
        url = (f"https://api.census.gov/data/{year}/acs/acs5"
               f"?get=group({table})"
               f"&for={for_clause}"
               f"&in={in_tmpl.format(county=county)}"
               f"&key={key}")
        data = request(url)
        if not data or len(data) < 2:
            print(f"      county {county}: no data")
            continue
        if header is None:
            header = data[0]
            rows.append(header)
        elif data[0] != header:
            print(f"      county {county}: header mismatch, skipped")
            continue
        rows.extend(data[1:])
    return rows


def main():
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "CENSUS_API_KEY is not set.\n\n"
            "  1. Request a free key: https://api.census.gov/data/key_signup.html\n"
            "     (name + email + organization; the key arrives by email, usually "
            "within a few minutes)\n"
            "  2. export CENSUS_API_KEY=<the 40-character key>\n"
            "  3. python3 src/fetch_01_acs.py\n")

    import csv
    total_files = 0
    for year in VINTAGES:
        ydir = os.path.join(OUT, f"acs5_{year}")
        os.makedirs(ydir, exist_ok=True)
        print(f"\n=== ACS 5-year {year} "
              f"({'2010' if year <= 2019 else '2020'} geography) ===")
        for table, why in TABLES.items():
            geos = ["bg"] + (["tract"] if table in TRACT_ONLY else [])
            for geo in geos:
                dest = os.path.join(ydir, f"{table}_{geo}.csv")
                if os.path.exists(dest) and os.path.getsize(dest) > 200:
                    print(f"  {table:<8} {geo:<6} exists, skipping")
                    total_files += 1
                    continue
                print(f"  {table:<8} {geo:<6} {why}", flush=True)
                rows = pull(year, table, geo, key)
                if not rows or len(rows) < 2:
                    print("      -> nothing returned "
                          f"(is {table} published at {geo} level in {year}?)")
                    continue
                with open(dest, "w", newline="") as f:
                    csv.writer(f).writerows(rows)
                print(f"      -> {dest}  ({len(rows) - 1:,} rows)")
                total_files += 1

    print(f"\n{total_files} files in {OUT}")
    print("\nNOTE: 2019 uses 2010-vintage GEOIDs and 2023/2024 use 2020-vintage.")
    print("Join them only through data/raw/census_geo_2010/"
          "bg_crosswalk_2010_2020_nyc.csv")


if __name__ == "__main__":
    main()
