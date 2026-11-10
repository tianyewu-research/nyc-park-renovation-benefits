"""Round 2 cartographic style. Round 1 scripts are untouched and still run.

Palette read from gis/styles/Screenshot 2026-09-14 at 10.10.01 AM.png:
teal -> sage -> pale neutrals -> warm cream -> rust.

  #3e7f70 #6c9ba0 #cbdad2 #d9dbd6 #e7eae9 #f3f4ef #f3d8ba #be9077 #da9068 #c47951

Encoding logic
--------------
Teal/green family   public parks, public agencies, completed work, base
Warm rust family    private-public arrangements, current work, key-case emphasis
Pale neutrals       land, background, unselected context

Governance SUBTYPE is carried by hatch / outline / line style, never by colour
alone, so the number of flat fill colours on any one map stays small.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# --- source palette ---------------------------------------------------------
TEAL_D   = "#3e7f70"
TEAL_M   = "#6c9ba0"
TEAL_L   = "#cbdad2"
NEUT_M   = "#d9dbd6"
NEUT_L   = "#e7eae9"
NEUT_XL  = "#f3f4ef"
CREAM    = "#f3d8ba"
RUST_MUT = "#be9077"
RUST_M   = "#da9068"
RUST_D   = "#c47951"

# --- roles ------------------------------------------------------------------
LAND        = NEUT_XL
LAND_EDGE   = "#ffffff"
SHORE       = "#c9ccc6"
INK         = "#1b1b1a"
INK_2       = "#4a4a47"
MUTED       = "#8b8d88"

# --- governance: THREE fill families only -----------------------------------
# The source palette is analogous, so five flat fills do not separate: the
# private-public / street-plaza pair scored CVD dE 6.8 (floor 8). Fill therefore
# carries the FAMILY and hatch/outline carries the SUBTYPE, as the brief
# requires. Three families checked all-pairs: normal dE 18.8, CVD dE 13.1 -- PASS.
GOV_PUBLIC      = TEAL_D    # any public owner: Parks, other agency, state/federal, authority
GOV_PRIVATE_PUB = RUST_M    # POPS, restrictive declaration, private public-access, DOT/BID
GOV_COMMUNITY   = CREAM     # community garden
GOV_UNKNOWN     = NEUT_M

# subtype = hatch, never colour alone
GOV_HATCH = {
    "NYC Parks property":                        "",
    "Other NYC agency public open space":        "..",
    "State or federal park":                     "//",
    "Public authority or trust":                 "\\\\",
    "Zoning POPS":                               "",
    "Restrictive-declaration public space":      "//",
    "Privately owned public-access park, non-POPS": "..",
    "DOT pedestrian plaza / BID-managed space":  "xx",
    "Community garden":                          "",
}
GOV_FAMILY = {
    "NYC Parks property":                        GOV_PUBLIC,
    "Other NYC agency public open space":        GOV_PUBLIC,
    "State or federal park":                     GOV_PUBLIC,
    "Public authority or trust":                 GOV_PUBLIC,
    "Zoning POPS":                               GOV_PRIVATE_PUB,
    "Restrictive-declaration public space":      GOV_PRIVATE_PUB,
    "Privately owned public-access park, non-POPS": GOV_PRIVATE_PUB,
    "DOT pedestrian plaza / BID-managed space":  GOV_PRIVATE_PUB,
    "Community garden":                          GOV_COMMUNITY,
}

# --- renovation status: pale cool base + ordered rust ramp -------------------
# Ordered, so darker = further through the pipeline. Adjacent-pair check:
# normal dE 17.3, CVD dE 14.0 -- PASS.
ST_COMPLETED    = NEUT_L      # #e7eae9, straight from the source palette
ST_DESIGN       = "#e9a061"
ST_PROCUREMENT  = "#c0602f"
ST_CONSTRUCTION = "#7a3013"
ST_PROPOSED     = CREAM
ST_POINT_ONLY   = "#7d7f7a"

KEY_CASE       = RUST_D

SNAPSHOT = "2026-09-14"
SOURCE_R2 = ("Sources: NYC Parks Capital Project Tracker (4hcv-tc5r), Parks Properties "
             "(enfh-gkve), PIP All Sites (buk3-3qpr); DCP CPDB polygons (9jkp-n57r), "
             "MapPLUTO (DCP feature service), NTA 2020 (9nt8-h7nd); DCAS COLP (c2g8-ercv); "
             "DCP Zoning POPS (qeta-4kqg), Restrictive Declaration Sites (igsj-fxac), "
             "WPAA (jakx-zd39); DOT Pedestrian Plazas (fnkv-pyhj); GreenThumb (p78i-pat6).")

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": MUTED, "text.color": INK,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "pdf.fonttype": 42, "ps.fonttype": 42, "hatch.linewidth": 0.6,
})


def blank(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_aspect("equal")


def north_arrow(ax, x=.955, y=.90, size=.05):
    ax.annotate("N", xy=(x, y), xytext=(x, y - size),
                xycoords="axes fraction", textcoords="axes fraction",
                ha="center", va="center", fontsize=9, color=INK_2,
                arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.2))


def scale_bar(ax, length_mi=2, x=.055, y=.04):
    """EPSG:2263 is in US survey feet."""
    ft = length_mi * 5280
    x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim()
    bx = x0 + x * (x1 - x0); by = y0 + y * (y1 - y0)
    h = .006 * (y1 - y0)
    ax.add_patch(Rectangle((bx, by), ft, h, facecolor=INK_2, ec="none", zorder=9))
    ax.add_patch(Rectangle((bx + ft, by), ft, h, facecolor="white",
                           ec=INK_2, lw=.6, zorder=9))
    for m, lab in ((0, "0"), (1, f"{length_mi}"), (2, f"{length_mi*2} mi")):
        ax.text(bx + ft * m, by + h * 2.2, lab, fontsize=7,
                ha="center", va="bottom", color=INK_2, zorder=9)


def footer(fig, limitation, source=SOURCE_R2, y0=.052):
    fig.text(.03, y0, "Limitation: " + limitation, fontsize=8.0,
             color=INK_2, va="top", style="italic", wrap=True)
    fig.text(.03, .018, f"{source}  Snapshot {SNAPSHOT}. "
             "Analysis CRS EPSG:2263 (NAD83 / New York Long Island, US ft). "
             "Basemap built from borough, shoreline and open-space geometry; "
             "no online basemap tiles.", fontsize=6.6, color=MUTED, va="top", wrap=True)


def title_block(fig, title, subtitle, x=.03, y=.972, ts=21, ss=11.5):
    fig.text(x, y, title, fontsize=ts, weight="bold", color=INK, va="top")
    fig.text(x, y - .030, subtitle, fontsize=ss, color=INK_2, va="top")


def save(fig, stem, outdir="maps/round2"):
    import os
    os.makedirs(outdir, exist_ok=True)
    for ext in ("png", "pdf"):
        p = f"{outdir}/{stem}.{ext}"
        fig.savefig(p, dpi=300 if ext == "png" else None,
                    bbox_inches="tight", facecolor="white")
        print(f"  wrote {p}")
    plt.close(fig)
