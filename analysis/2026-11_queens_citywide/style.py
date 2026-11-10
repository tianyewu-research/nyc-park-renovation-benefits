import matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ['Inter', 'Helvetica Neue', 'Arial', 'DejaVu Sans']:
    if any(f in x.name for x in font_manager.fontManager.ttflist): FONT = f; break
mpl.rcParams.update({
    'font.family': FONT, 'font.size': 10, 'axes.titlesize': 12, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#555555', 'axes.linewidth': .6,
    'axes.labelcolor': '#333333', 'xtick.color': '#555555', 'ytick.color': '#555555', 'xtick.labelsize': 9, 'ytick.labelsize': 9,
    'axes.grid': False, 'figure.dpi': 100, 'savefig.dpi': 220, 'savefig.bbox': 'tight', 'savefig.facecolor': 'white',
    'legend.frameon': False, 'legend.fontsize': 9})
INK = '#222222'; MUTED = '#777777'; LIGHT = '#bbbbbb'
PARK = '#dfe8d3'; PARK_EDGE = '#9fb48a'; WATER = '#eef3f6'; LAND = '#f7f6f2'
TYPE_COL = {'A': '#9a9a9a', 'B': '#3d6fa8', 'C1': '#d1495b', 'C2': '#e8a33d', 'D': '#6a4c93', '?': '#d0d0d0'}
TYPE_LAB = {'A': 'A  Like-for-like replacement', 'B': 'B  Upgrade', 'C1': 'C1 New activity facility',
            'C2': 'C2 New amenities only', 'D': 'D  Replaced or removed a use', '?': 'Not yet classified'}
GAIN = '#2e7d32'; LOSS = '#b23a3a'; NEUTRAL = '#a9a9a9'
def nat_code(s):
    s = str(s)
    for k in ['C1', 'C2', 'A', 'B', 'D']:
        if s.startswith(k): return k
    return '?'
def note(fig, text, y=-0.02):
    fig.text(0.01, y, text, fontsize=7.5, color=MUTED, ha='left', va='top')
