"""Round 4 visual system. Palette from gis/styles/Screenshot 2026-09-14 at 10.10.01 AM.png."""
import matplotlib as mpl
from matplotlib.patches import Rectangle

BG, LAND, EDGE = "#F3F4EF", "#EDEEE8", "#C3C6C0"
INK, INK_2, MUTED = "#17181A", "#4E5150", "#8C8F8A"

GOV = {"NYC Parks": "#3E7F70", "Other public parkland": "#6C9BA0",
       "Privately owned public access": "#DA9068",
       "Community-managed green space": "#F3D8BC",
       "Street-based public space": "#AA8B7B"}
GOV_ORDER = list(GOV)

PHASE = {"Design": "#F1BC86", "Procurement": "#D87948", "Construction": "#914521",
         "Proposed/unknown": "#BFC3BD"}
PHASE_ORDER = ["Design", "Procurement", "Construction", "Proposed/unknown"]
COMPLETED = "#82A99F"

# base map, kept far below the thematic layers
POP_RAMP = ["#EDF1EC", "#DCE6E1", "#C6D8D1", "#AAC4BC", "#8FAEA6"]
POP_ZERO, BLDG = "#EFEFEA", "#9A9E97"
ST_MINOR, ST_PRINCIPAL = "#EAECE6", "#C6CAC2"
SUBWAY, STATION = "#7E9A9C", "#6C878F"

BORO_STACK = {"Bronx": "#345652", "Brooklyn": "#7CA3A8", "Manhattan": "#C9EADF",
              "Queens": "#CC8C61", "Staten Island": "#75442C",
              "Unknown / unmatched": "#A7A8A3"}
BORO_ORDER = list(BORO_STACK)

SNAPSHOT = "2026-09-14"
SRC_GOV = ("Sources: NYC Parks Properties (enfh-gkve); DCP zoning POPS (qeta-4kqg) joined to "
           "DCP MapPLUTO tax lots by BBL; NYC Parks restrictive-declaration sites (igsj-fxac); "
           "DCP WPAA (jakx-zd39); NYC DOT pedestrian plazas (fnkv-pyhj); GreenThumb (p78i-pat6); "
           "NYC Facilities Database (ji82-xba5).")
SRC_REN = ("Sources: NYC Parks Capital Project Tracker (4hcv-tc5r); NYC Parks PIP all sites "
           "(buk3-3qpr); DCP CPDB project polygons (9jkp-n57r); NYC Parks Properties (enfh-gkve).")
SRC_BASE = ("Base: ACS 2023 5-year B01003 with TIGER 2023 block groups; NYC CSCL (inkn-q76z); "
            "NYC building footprints (5zhs-2jue); MTA subway lines (vtcn-vhd8) and stations "
            "(39hk-dx4f); NYC borough boundaries (gthc-hcne).")
NOT_FOOTPRINT = ("Mapped polygons represent matched park properties, PIP subsites, or documented "
                 "project polygons; they are not verified construction footprints.")

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.facecolor": BG, "savefig.facecolor": BG, "axes.facecolor": BG,
    "text.color": INK, "axes.edgecolor": MUTED,
    "pdf.fonttype": 42, "ps.fonttype": 42, "hatch.linewidth": 0.45,
})

TITLE, SUBTITLE, PANEL, LEGEND, BORO_LBL, NOTE = 21, 10.0, 11.5, 8.8, 9.5, 7.8


def blank(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_aspect("equal"); ax.set_facecolor(BG)


def north_arrow(ax, x=.955, y=.905, size=.045):
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
        ax.text(bx + ft * m, by + h * 2.3, lab, fontsize=6.8, ha="center",
                va="bottom", color=INK_2, zorder=40)


def save(fig, stem, outdir="maps/round4"):
    import os, matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    out = []
    for ext in ("png", "pdf"):
        p = f"{outdir}/{stem}.{ext}"
        fig.savefig(p, dpi=300 if ext == "png" else None, facecolor=BG)
        out.append(p); print(f"  wrote {p}")
    plt.close(fig)
    return out
