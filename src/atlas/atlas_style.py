"""Shared cartographic style for the atlas maps.

Colour policy
-------------
Categorical hues come from the reference palette in fixed slot order and are
capped at THREE per all-pairs view (a categorical point map is an all-pairs
form, like a scatter or choropleth). Anything needing more categories is
FACETED, so each panel carries one accent against grey context. Verified with
an OKLab + CVD-simulation check: blue/orange/aqua score worst-pair CVD dE 9.5
and normal-vision dE 24.0, both clear of the 8 / 15 floors.

Green is reserved for the green-space base and is never used as a categorical
series colour.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

# categorical slots (light mode), fixed order
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
# green-space base ramp (one hue, light -> dark)
PARK_PALE, PARK_MID, PARK_DEEP = "#dcebd4", "#aed49f", "#6faa5b"
# ink
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
LAND, WATERISH, EDGE = "#efeeea", "#eceff1", "#ffffff"

SNAPSHOT = "2026-09-08"
SOURCE = ("Sources: NYC Parks Capital Project Tracker (4hcv-tc5r); Parks Properties "
          "(enfh-gkve); GreenThumb (p78i-pat6); POPS (qeta-4kqg); "
          "Active & Passive Recreation (kcqe-vnci); Borough Boundaries (gthc-hcne).")

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": MUTED, "text.color": INK,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "pdf.fonttype": 42, "ps.fonttype": 42,
})


def blank(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_aspect("equal")


def north_arrow(ax, x=0.955, y=0.90, size=0.055):
    """Simple orientation cue in axes fraction."""
    ax.annotate("N", xy=(x, y), xytext=(x, y - size),
                xycoords="axes fraction", textcoords="axes fraction",
                ha="center", va="center", fontsize=8, color=INK_2,
                arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.1))


def scale_bar(ax, length_mi=2, x=0.055, y=0.055):
    """Scale bar for EPSG:2263 (US survey feet)."""
    ft = length_mi * 5280
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    w = (x1 - x0)
    bx = x0 + x * w
    by = y0 + y * (y1 - y0)
    h = 0.006 * (y1 - y0)
    ax.add_patch(Rectangle((bx, by), ft, h, facecolor=INK_2, edgecolor="none", zorder=9))
    ax.add_patch(Rectangle((bx + ft, by), ft, h, facecolor="white",
                           edgecolor=INK_2, lw=0.6, zorder=9))
    for mult, lab in ((0, "0"), (1, f"{length_mi}"), (2, f"{length_mi*2} mi")):
        ax.text(bx + ft * mult, by + h * 2.2, lab, fontsize=6.5,
                ha="center", va="bottom", color=INK_2, zorder=9)


def frame(fig, title, subtitle, limitation, source=SOURCE):
    fig.text(0.045, 0.965, title, fontsize=17, weight="bold",
             color=INK, va="top")
    fig.text(0.045, 0.928, subtitle, fontsize=9.5, color=INK_2, va="top")
    fig.text(0.045, 0.038, f"Limitation: {limitation}", fontsize=7.4,
             color=INK_2, va="top", style="italic")
    fig.text(0.045, 0.018, f"{source}  Snapshot {SNAPSHOT}. "
             f"Projection EPSG:2263 (NAD83 / New York Long Island, US ft).",
             fontsize=6.4, color=MUTED, va="top")


def save(fig, stem):
    import os
    os.makedirs("maps", exist_ok=True)
    png, pdf = f"maps/{stem}.png", f"maps/{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  wrote {png}")
    print(f"  wrote {pdf}")
    return png, pdf
