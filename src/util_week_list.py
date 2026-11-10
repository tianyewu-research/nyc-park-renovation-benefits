"""Emit the exact Monday-start week list for each acquisition block.

Advan weeks start Monday; the existing extract runs 2023-01-02 .. 2025-12-29.
Usage:  python3 src/util_week_list.py [--write]
"""

import sys
import pandas as pd

BLOCKS = {
    # must buy: pushes the main panel back, design A 76 -> 223 projects
    "must_era2_2021h2_2022": ("2021-07-05", "2022-12-26"),
    # recommended: era 1 secondary replication, design B only
    "rec_era1_2019":         ("2019-01-07", "2020-02-24"),
    # must re-pull for vintage consistency
    "must_repull_2325":      ("2023-01-02", "2025-12-29"),
    # skip: COVID behavioural shock + pre-ATT panel
    "skip_covid_gap":        ("2020-03-02", "2021-06-28"),
}

write = "--write" in sys.argv

for name, (lo, hi) in BLOCKS.items():
    weeks = pd.date_range(lo, hi, freq="W-MON")
    print(f"{name:<16} {lo} .. {hi}   {len(weeks):>4} weeks   "
          f"~{len(weeks) * 3.7 / 1024:.2f} GB gz")
    if write:
        path = f"data/raw/advan/weeks_{name}.txt"
        with open(path, "w") as f:
            f.write("\n".join(w.strftime("%Y-%m-%d") for w in weeks) + "\n")
        print(f"                 -> {path}")

print("\ntotal to acquire (must + recommended + re-pull):")
n = sum(len(pd.date_range(*BLOCKS[k], freq="W-MON"))
        for k in ["must_era2_2021h2_2022", "rec_era1_2019", "must_repull_2325"])
print(f"  {n} weeks  ~{n * 3.7 / 1024:.2f} GB gz")
