"""Round 3 palette. Sampled from gis/styles/Screenshot 2026-09-14 at 10.10.01 AM.png."""
import matplotlib as mpl
from matplotlib.patches import Rectangle

TEAL_D, TEAL_M, TEAL_PG = "#3E7F70", "#6C9BA0", "#CBDAD2"
GREY_W, GREY_C, OFFWHITE = "#D9DBD6", "#E7EAE9", "#F3F4EF"
PEACH, ORANGE, RUST = "#F3D8BC", "#DA9068", "#C47951"

BG          = OFFWHITE          # background is off-white, never pure white
LAND        = "#EDEEE8"
SHORE       = "#C3C6C0"
INK         = "#17181A"         # near-black, titles and essential labels only
INK_2       = "#4E5150"
MUTED       = "#8C8F8A"

# base map, deliberately quiet
BLDG        = "#9A9E97"   # used at low alpha as grain, never as a blanket
ST_MINOR    = "#EAECE6"   # near-background: minor streets must nearly vanish citywide
ST_PRINCIPAL= "#C6CAC2"
SUBWAY      = "#7E9A9C"
STATION     = "#6C878F"

# population: low-contrast pale-teal monochrome ramp
POP_RAMP    = ["#EDF1EC", "#D6E2DC", "#B7CCC4", "#93B2AA", "#6B9088"]
POP_ZERO    = "#EFEFEA"

# governance families (fill = family, hatch = subtype)
FAM_PUBLIC, FAM_PRIVPUB, FAM_COMMUNITY = TEAL_D, ORANGE, PEACH
# renovation phase: one ordered warm sequence, separate from ownership
PHASE = {"Completed": "#F0C9A8", "Design / design-procurement": "#E39A62",
         "Procurement": "#C97440", "Construction": "#8F4520",
         "Proposed / other / unknown": "#BFC3BD"}
PHASE_ORDER = ["Completed", "Proposed / other / unknown",
               "Design / design-procurement", "Procurement", "Construction"]

# five-borough stack: reference hues, lightness-spread so adjacent stacks separate
# checked on the stacked (adjacent) pairlist: normal dE 22.3, CVD dE 15.6
BORO_COL = {"Bronx": "#345652", "Brooklyn": "#7CA3A8", "Manhattan": "#C9EADF",
            "Queens": "#CC8C61", "Staten Island": "#75442C",
            "Unknown / unmatched": "#A7A8A3"}
BORO_ORDER = ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island",
              "Unknown / unmatched"]

SNAPSHOT = "2026-09-14"
SRC_BASE = ("Sources: ACS 2023 5-year B01003 + TIGER 2023 block groups (2020 vintage); "
            "NYC CSCL street centerline (inkn-q76z); NYC building footprints (5zhs-2jue); "
            "MTA subway service lines (vtcn-vhd8) and stations (39hk-dx4f); "
            "NYC borough boundaries (gthc-hcne).")
SRC_THEME = ("Sources: NYC Parks Capital Project Tracker (4hcv-tc5r) and Parks Properties "
             "(enfh-gkve); DCP zoning POPS (qeta-4kqg), WPAA (jakx-zd39); NYC Parks "
             "restrictive-declaration sites (igsj-fxac); DOT pedestrian plazas (fnkv-pyhj); "
             "GreenThumb (p78i-pat6); DCAS COLP (c2g8-ercv); DCP CPDB (9jkp-n57r); "
             "NYC Parks PIP all sites (buk3-3qpr).")

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.facecolor": BG, "savefig.facecolor": BG, "axes.facecolor": BG,
    "text.color": INK, "axes.edgecolor": MUTED,
    "pdf.fonttype": 42, "ps.fonttype": 42, "hatch.linewidth": 0.5,
})


def blank(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_aspect("equal"); ax.set_facecolor(BG)


def north_arrow(ax, x=.958, y=.905, size=.045):
    ax.annotate("N", xy=(x, y), xytext=(x, y - size), xycoords="axes fraction",
                textcoords="axes fraction", ha="center", va="center",
                fontsize=8.5, color=INK_2,
                arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.1))


def scale_bar(ax, length_mi=2, x=.05, y=.035):
    ft = length_mi * 5280
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    bx, by = x0 + x * (x1 - x0), y0 + y * (y1 - y0)
    h = .0055 * (y1 - y0)
    ax.add_patch(Rectangle((bx, by), ft, h, facecolor=INK_2, ec="none", zorder=40))
    ax.add_patch(Rectangle((bx + ft, by), ft, h, facecolor=BG, ec=INK_2, lw=.6, zorder=40))
    for m, lab in ((0, "0"), (1, str(length_mi)), (2, f"{length_mi*2} mi")):
        ax.text(bx + ft * m, by + h * 2.3, lab, fontsize=6.6, ha="center",
                va="bottom", color=INK_2, zorder=40)


def save(fig, stem, outdir="maps/round3"):
    import os, matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    out = []
    for ext in ("png", "pdf"):
        p = f"{outdir}/{stem}.{ext}"
        fig.savefig(p, dpi=300 if ext == "png" else None, bbox_inches="tight",
                    facecolor=BG)
        out.append(p); print(f"  wrote {p}")
    plt.close(fig)
    return out
