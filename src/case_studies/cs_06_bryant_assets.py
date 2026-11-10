"""Bryant Park case assets."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C, cs_fig as F, cs_assets_lib as L
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

CID, B1, B2, B3 = "BP", "board_1_history_profile", "board_2_renovation", "board_3_use_outcomes"
SRC_MT = "History of Bryant Park: Modern Times (bryantpark.org), p.1–2"
SRC_OLIN = "Bryant Park – OLIN (theolinstudio.com), p.1–2"

# ---- B1 timeline -----------------------------------------------------------
TL = [
 (1934, "Park redesigned; reopens to acclaim", SRC_MT, "B"),
 (1970, "By the early 1970s the park is largely avoided by Midtown workers and tourists", SRC_MT, "D"),
 (1980, "Bryant Park Restoration Corporation founded by Dan Biederman, Time Inc., "
        "NYPL chair Andrew Heiskell and the Rockefeller Brothers Fund", SRC_MT, "D"),
 (1988, "Park closes for a four-year reconstruction", SRC_MT, "D"),
 (1992, "Park reopens; restrooms reopen after 35 years closed", SRC_MT, "D"),
 (2002, "Le Carrousel added", SRC_MT, "D"),
 (2003, "Reading Room revived", SRC_MT, "D"),
]
tl = pd.DataFrame(TL, columns=["year", "event", "source", "evidence_grade"])
fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
ax.hlines(0, 1928, 2010, color=F.MUTED, lw=1.0)
for i, r in tl.iterrows():
    up = i % 2 == 0
    y = .55 if up else -.55
    ax.vlines(r.year, 0, y, color=F.RUST if r.year in (1988, 1992) else F.TEAL_M, lw=1.2)
    ax.plot(r.year, 0, "o", ms=6, color=F.RUST if r.year in (1988, 1992) else F.TEAL)
    ax.text(r.year, y + (.10 if up else -.10), f"{r.year}\n" +
            "\n".join(__import__("textwrap").wrap(r.event, 34)),
            ha="center", va="bottom" if up else "top", fontsize=7.2, color=F.INK)
ax.axvspan(1988, 1992, color=F.RUST, alpha=.10)
ax.set_xlim(1928, 2010); ax.set_ylim(-2.0, 2.0); ax.axis("off")
ax.set_title("Bryant Park: decline, management intervention, reconstruction",
             fontsize=11.5, color=F.INK, loc="left", weight="bold")
F.source_line(fig, f"Dates verified from {SRC_MT}. Shaded band = 1988–1992 closure.")
fig.tight_layout(rect=(0, .07, 1, 1))
F.export(fig, os.path.join(C.board_dir(CID, B1), "figures"), "BP_F00_timeline",
         "Bryant Park: decline, management intervention, reconstruction",
         "Verified dates from the park operator's published history.",
         "Manual transcription from a single primary source, page-referenced.",
         "year", SRC_MT, tl, case_id=CID, board=B1)

# ---- B2 intervention matrix + diagram -------------------------------------
IM = [
 ("Raised grade, perimeter fence and tall hedges", "Increase visibility into the park from street level; remove isolating hedges", "Passive surveillance from the sidewalk", SRC_MT, "D"),
 ("Restrooms closed for 35 years", "Reopen park restrooms", "Basic amenity restored", SRC_MT, "D"),
 ("No food service", "Build two restaurant pavilions and four concession kiosks", "Programmed active edges", SRC_MT, "D"),
 ("Fixed seating", "Introduce 2,000 movable bistro chairs", "User-arranged occupation", SRC_MT, "D"),
 ("City-only maintenance under a cash-strapped Parks Department", "Public-private management by BPRC from 1980", "Dedicated cleaning, security and programming", SRC_MT, "D"),
]
im = pd.DataFrame(IM, columns=["existing_condition", "renovation_action",
                               "intended_function", "source", "evidence_grade"])
im.to_csv(os.path.join(C.board_dir(CID, B2), "data", "BP_intervention_matrix.csv"), index=False)

fig, ax = plt.subplots(figsize=C.ASPECTS["4:3"]); ax.axis("off")
ax.set_xlim(0, 10); ax.set_ylim(0, 8)
ax.add_patch(FancyBboxPatch((1.2, 2.0), 7.6, 4.2, boxstyle="round,pad=.12",
                            fc="#E6EFE9", ec=F.TEAL, lw=1.2))
ax.text(5.0, 6.45, "Bryant Park — documented physical changes, 1988–1992",
        ha="center", fontsize=10.5, weight="bold", color=F.INK)
items = [(2.0, 5.4, "Sight lines opened\nfrom street level"),
         (5.0, 5.4, "Isolating hedges\nremoved"),
         (8.0, 5.4, "Restrooms reopened\n(closed 35 years)"),
         (2.0, 3.2, "Two restaurant\npavilions"),
         (5.0, 3.2, "Four concession\nkiosks"),
         (8.0, 3.2, "2,000 movable\nbistro chairs")]
for x, y, t in items:
    ax.add_patch(FancyBboxPatch((x - 1.25, y - .55), 2.5, 1.1, boxstyle="round,pad=.08",
                                fc=F.BG, ec=F.RUST, lw=1.0))
    ax.text(x, y, t, ha="center", va="center", fontsize=8.0, color=F.INK)
ax.text(5.0, 1.35, "ANALYTICAL DIAGRAM — schematic relationships only.\n"
        "No measured design plan is implied; no plan drawing was available.",
        ha="center", fontsize=7.6, color=F.INK_2, style="italic")
F.source_line(fig, f"Changes listed are those explicitly described in {SRC_MT}.")
F.export(fig, os.path.join(C.board_dir(CID, B2), "figures"), "BP_F10_intervention_diagram",
         "Bryant Park: documented physical changes, 1988–1992",
         "Analytical diagram of the physical changes named in the operator's published "
         "history. Not a measured design plan.",
         "Schematic; each element traceable to a named source sentence.",
         "documented intervention", SRC_MT, im, case_id=CID, board=B2)

fig, ax = plt.subplots(figsize=C.ASPECTS["4:3"]); ax.axis("off")
ax.set_xlim(0, 10); ax.set_ylim(0, 8)
rows = [("Land ownership", "City of New York (public park)", "E — not verified in local sources"),
        ("Park management", "Bryant Park Corporation / BPRC (founded 1980)", "D"),
        ("Design of record", "OLIN — Laurie Olin partner-in-charge, Dennis McGlade partner", "D"),
        ("Concessions & programming", "Operated under the park management body", "E — not verified in local sources"),
        ("Maintenance & security", "BPRC cleaning, security and programming from 1980", "D")]
for i, (k, v, g) in enumerate(rows):
    y = 6.6 - i * 1.15
    ax.add_patch(FancyBboxPatch((.5, y - .42), 3.1, .84, boxstyle="round,pad=.07",
                                fc="#E6EFE9", ec=F.TEAL, lw=.9))
    ax.text(2.05, y, k, ha="center", va="center", fontsize=8.4, weight="bold", color=F.INK)
    ax.add_patch(FancyBboxPatch((3.9, y - .42), 5.6, .84, boxstyle="round,pad=.07",
                                fc=F.BG, ec=F.MUTED, lw=.8))
    ax.text(4.1, y + .12, v, ha="left", va="center", fontsize=7.8, color=F.INK)
    ax.text(4.1, y - .20, f"evidence {g}", ha="left", va="center", fontsize=6.6,
            color=F.INK_2, style="italic")
ax.text(5.0, 7.5, "Bryant Park: separating ownership, management and design",
        ha="center", fontsize=10.5, weight="bold", color=F.INK)
F.source_line(fig, f"{SRC_MT}; {SRC_OLIN}. Rows marked evidence E are NOT verified in the "
              "local source set and must not be stated as fact on a board.")
pd.DataFrame(rows, columns=["layer", "documented_actor", "evidence_grade"]).to_csv(
    os.path.join(C.board_dir(CID, B2), "data", "BP_governance_layers.csv"), index=False)
gov_tbl = pd.DataFrame(rows, columns=["layer", "documented_actor", "evidence_grade"])
F.export(fig, os.path.join(C.board_dir(CID, B2), "figures"), "BP_F11_governance_diagram",
         "Bryant Park: separating ownership, management and design",
         "Governance layers shown separately so the redesign and the management model are "
         "not read as one intervention. Unverified rows are marked.",
         "Each row graded A–E; rows graded E are not supported by the local source set.",
         "governance layer", f"{SRC_MT}; {SRC_OLIN}", gov_tbl, case_id=CID, board=B2)

# ---- B3 --------------------------------------------------------------------
L.advan_index(CID, B3); L.advan_season(CID, B3)
L.pip_timelines(CID, B3); L.origin_and_composition(CID, B3)
n = F.flush_manifest(); print(f"\nBP assets done; manifest {n}")
