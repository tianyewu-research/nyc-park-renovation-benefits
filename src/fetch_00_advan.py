"""Download the Advan weekly blocks from Dewey Data.

Setup once:

    pip install "deweydatapy@git+https://github.com/Dewey-Data/deweydatapy"
    export DEWEY_API_KEY=...        # Dewey -> Connections -> Add Connection -> API Key
    export DEWEY_PRODUCT_PATH=...   # the product's Get/Subscribe -> Connect to API

Then:

    python3 src/fetch_00_advan.py --check          # meta only, downloads nothing
    python3 src/fetch_00_advan.py --block must_era2_2021h2_2022
    python3 src/fetch_00_advan.py --block must_repull_2325
    python3 src/fetch_00_advan.py --block rec_era1_2019

Files land in data/raw/advan/. Dewey names them with a leading YYYY-MM-DD, which
is what lib_advan.py parses; --check verifies that before you download 295 files.

Re-running is safe: skip_exists=True.
"""

import argparse
import os
import sys

DEST = "data/raw/advan"
VINTAGE_LOG = "data/raw/VINTAGE.md"

BLOCKS = {
    "must_era2_2021h2_2022": ("2021-07-05", "2022-12-26", 78,
                              "main panel push-back; design A 76 -> 223 projects"),
    "must_repull_2325":      ("2023-01-02", "2025-12-29", 157,
                              "re-pull for vintage consistency with the new blocks"),
    "rec_era1_2019":         ("2019-01-07", "2020-02-24", 60,
                              "era 1 secondary replication, design B only"),
    "skip_covid_gap":        ("2020-03-02", "2021-06-28", 70,
                              "NOT needed: COVID behavioural shock + pre-ATT panel"),
}


def creds():
    key = os.environ.get("DEWEY_API_KEY", "").strip()
    path = os.environ.get("DEWEY_PRODUCT_PATH", "").strip()
    if not key or not path:
        raise SystemExit(
            "DEWEY_API_KEY and/or DEWEY_PRODUCT_PATH are not set.\n\n"
            "  API key:      Dewey -> Connections -> Add Connection -> API Key\n"
            "                (shown ONCE; copy it immediately)\n"
            "  Product path: open Advan Weekly Patterns -> Get/Subscribe\n"
            "                -> Connect to API -> copy the endpoint\n\n"
            "  export DEWEY_API_KEY=...\n"
            "  export DEWEY_PRODUCT_PATH=...\n")
    return key, path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", choices=list(BLOCKS))
    ap.add_argument("--check", action="store_true",
                    help="print dataset meta and the first filename, download nothing")
    args = ap.parse_args()

    try:
        import deweydatapy as ddp
    except ImportError:
        raise SystemExit(
            'deweydatapy is not installed.\n\n'
            '  pip install "deweydatapy@git+https://github.com/Dewey-Data/deweydatapy"\n')

    key, path = creds()

    if args.check:
        print("=== dataset meta ===")
        ddp.get_meta(key, path, print_meta=True)
        print("\n=== first week of the must-buy block, filename check ===")
        lo, hi, _, _ = BLOCKS["must_era2_2021h2_2022"]
        df = ddp.get_file_list(key, path, start_date=lo, end_date=lo,
                               print_info=True)
        if df is not None and len(df):
            print(df.head().to_string())
            print("\nCONFIRM: filenames must begin with YYYY-MM-DD (the week start).")
            print("lib_advan.py finds the week by regex on the filename; if Dewey's")
            print("naming differs, rename on arrival or adjust lib_advan.WEEK_RE.")
        return

    if not args.block:
        print("Blocks (pass one with --block):\n")
        for name, (lo, hi, n, why) in BLOCKS.items():
            print(f"  {name:<24} {lo} .. {hi}  {n:>3} wk   {why}")
        print("\nRecommended order: must_era2_2021h2_2022, must_repull_2325, "
              "rec_era1_2019")
        return

    lo, hi, n, why = BLOCKS[args.block]
    if args.block == "skip_covid_gap":
        print("This block is deliberately excluded from the design. "
              "Downloading it is not useful; see notes/03_research_design.md §3.")
        if input("Type 'yes' to download anyway: ").strip() != "yes":
            return

    os.makedirs(DEST, exist_ok=True)
    print(f"block {args.block}: {lo} .. {hi}  ({n} weeks)\n  {why}\n")

    files = ddp.get_file_list(key, path, start_date=lo, end_date=hi,
                              print_info=True)
    if files is None or not len(files):
        raise SystemExit("Dewey returned no files for that range. Check the "
                         "product path and your subscription's date coverage.")
    print(f"\n{len(files)} files listed; expected about {n}.")
    if abs(len(files) - n) > 2:
        print("WARNING: count differs from expectation by more than 2 weeks. "
              "Verify before proceeding.")

    ddp.download_files(files, DEST, skip_exists=True)

    with open(VINTAGE_LOG, "a") as f:
        from datetime import datetime, timezone
        f.write(f"\n- {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} · "
                f"block `{args.block}` · {lo}..{hi} · {len(files)} files · "
                f"product path `{path[:40]}...`\n")
    print(f"\nlogged to {VINTAGE_LOG}")
    print("Next: python3 src/gate_06_download_qa.py --rebuild")


if __name__ == "__main__":
    main()
