import pandas as pd, numpy as np, geopandas as gpd, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import *
boro = gpd.read_file('src_data/data/raw/geography/Borough_Boundaries_20260623.geojson').to_crs(2263)
Q = boro[boro.boroname.str.contains('Queens', case=False)] if 'boroname' in boro else boro[boro.iloc[:, 0].astype(str).str.contains('Queens')]
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263)
qp = parks[parks.borough == 'Q']
res = pd.read_csv('out/queens_did_with_origins.csv')
res['code'] = res.nature.map(nat_code); res['outcome'] = res.outcome.fillna('n/a')
g = gpd.GeoDataFrame(res, geometry=gpd.points_from_xy(res.Longitude, res.Latitude), crs=4326).to_crs(2263)
ctrl = pd.read_csv('out/control_parks.csv').parkid
xmin, ymin, xmax, ymax = Q.total_bounds

def base(ax):
    boro.plot(ax=ax, color='#f1f1ee', edgecolor='none')
    Q.plot(ax=ax, color=LAND, edgecolor='#999999', lw=.5)
    qp.plot(ax=ax, color=PARK, edgecolor='none')
    ax.set_xlim(xmin - 2000, xmax + 2000); ax.set_ylim(ymin - 2000, ymax + 2000); ax.set_axis_off(); ax.set_facecolor(WATER)
    ax.figure.patch.set_facecolor('white')

# --- Fig 1: inventory map ---
fig, ax = plt.subplots(figsize=(10, 8.6))
base(ax)
qp[qp.gispropnum.isin(ctrl)].plot(ax=ax, color='none', edgecolor='#6f8f5a', lw=.6)
sz = 18 + 260 * (g.fund / g.fund.max())
for k in ['A', 'B', 'C1', 'C2', 'D', '?']:
    m = g.code == k
    ax.scatter(g[m].geometry.x, g[m].geometry.y, s=sz[m], color=TYPE_COL[k], edgecolor='white', lw=.7, alpha=.95, zorder=5, label=TYPE_LAB[k])
for name, pid in [('Astoria Park', 'Q004'), ('Cunningham Park', 'Q021')]:
    pg = qp[qp.gispropnum == pid]
    pg.plot(ax=ax, color='none', edgecolor=INK, lw=1.2, zorder=6)
    c = pg.union_all().centroid
    ax.annotate(name, (c.x, c.y), xytext=(14, 10), textcoords='offset points', fontsize=9.5, fontweight='bold', color=INK,
                arrowprops=dict(arrowstyle='-', color=INK, lw=.6), zorder=7)
h = [Line2D([], [], marker='o', ls='', color=TYPE_COL[k], markersize=8, label=TYPE_LAB[k]) for k in ['A', 'B', 'C1', 'C2', 'D', '?']]
h += [Line2D([], [], marker='s', ls='', markerfacecolor='none', markeredgecolor='#6f8f5a', markersize=9, label='Comparison park (no Parks construction 2018–2026)')]
ax.legend(handles=h, loc='lower left', bbox_to_anchor=(0.0, 0.34), fontsize=8.5, title='Type of change', title_fontsize=9, alignment='left')
for f, lab in [(1e6, '$1M'), (5e6, '$5M')]:
    ax.scatter([], [], s=18 + 260 * f / g.fund.max(), color='#cccccc', label=lab)
ax.text(0.99, 0.02, f'64 renovation projects · {len(ctrl)} comparison parks\nDot size = Tracker funding (\\$0.14M–\\$9.3M)', transform=ax.transAxes, ha='right', fontsize=8, color=MUTED)
fig.savefig('fig/fig01_queens_inventory_map.png'); plt.close()

# --- Fig 4: gains / losses map ---
fig, ax = plt.subplots(figsize=(10, 8.6)); base(ax)
col = res.outcome.map({'clear gain': GAIN, 'clear loss': LOSS, 'within normal range': NEUTRAL, 'n/a': '#e0e0e0'})
ax.scatter(g.geometry.x, g.geometry.y, s=26 + 70 * np.abs(res.d52_cor.fillna(0)), color=col, edgecolor='white', lw=.7, zorder=5)
lab = res[res.outcome.isin(['clear gain', 'clear loss'])]
for _, r in g.loc[lab.index].iterrows():
    nm = r['Project / site'].replace(' Reconstruction', '').replace(' Construction', '').replace(' (Hurricane Sandy)', '').replace(' and Adult Fitness Equipment', '')[:34]
    off = {'Q053': (-10, -14), 'Q066': (8, 6), 'Q013': (8, 0), 'Q045': (-60, 10), 'Q037': (6, 6)}.get(r.case, (6, 4))
    ax.annotate(f"{nm} ({r.pct:+.0%}){'' if r.robust else ' *'}", (r.geometry.x, r.geometry.y), xytext=off, textcoords='offset points', fontsize=7.2, ha='right' if off[0] < 0 else 'left',
                color=GAIN if r.outcome == 'clear gain' else LOSS, zorder=7)
h = [Line2D([], [], marker='o', ls='', color=c, markersize=8, label=l) for c, l in
     [(GAIN, 'Clear gain (above 90% of placebo changes)'), (NEUTRAL, 'Within the range of untouched parks'), (LOSS, 'Clear loss (below 10% of placebo changes)'), ('#e0e0e0', 'Not computable (no 52-week window)')]]
ax.legend(handles=h, loc='lower left', bbox_to_anchor=(0.0, 0.34), fontsize=8.5)
ax.text(0.99, 0.02, 'Change in visits, 52 weeks after vs before, relative to 10 nearest untouched parks\n* direction reverses without the data-break correction', transform=ax.transAxes, ha='right', fontsize=8, color=MUTED)
fig.savefig('fig/fig04_gain_loss_map.png'); plt.close()
print('ok')
