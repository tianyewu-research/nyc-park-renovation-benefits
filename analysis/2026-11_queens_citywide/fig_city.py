import pandas as pd, numpy as np, geopandas as gpd, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import *
R = pd.read_csv('out/city_full_did.csv'); x = R[R.window == 52].copy(); P = pd.read_csv('out/city_full_placebo.csv')
lo, hi = P.d.quantile([.1, .9])
boro = gpd.read_file('src_data/data/raw/geography/Borough_Boundaries_20260623.geojson').to_crs(2263)
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263)
g = gpd.GeoDataFrame(x, geometry=gpd.points_from_xy(x.lon.astype(float), x.lat.astype(float)), crs=4326).to_crs(2263)
fig, ax = plt.subplots(figsize=(10, 9.5))
boro.plot(ax=ax, color=LAND, edgecolor='#999999', lw=.5); parks.plot(ax=ax, color=PARK, edgecolor='none')
col = g.outcome.map({'clear gain': GAIN, 'clear loss': LOSS, 'within normal range': NEUTRAL})
ax.scatter(g.geometry.x, g.geometry.y, s=18 + 60 * np.abs(g.d), color=col, edgecolor='white', lw=.6, zorder=5, alpha=.9)
ax.set_axis_off(); ax.set_facecolor(WATER)
h = [Line2D([], [], marker='o', ls='', color=c, markersize=8, label=f'{l} ({(x.outcome == k).sum()})') for c, l, k in
     [(GAIN, 'Clear gain', 'clear gain'), (NEUTRAL, 'Within the placebo range', 'within normal range'), (LOSS, 'Clear loss', 'clear loss')]]
ax.legend(handles=h, loc='upper left', fontsize=9)
ax.set_title(f'{len(x)} NYC Parks projects, 2019–2026: change in visits a year after vs a year before', fontsize=11.5)
ax.text(0.99, 0.02, 'Relative to the 10 nearest untouched parks; stay POIs only; Jan 2023 and Nov 2024 breaks removed', transform=ax.transAxes, ha='right', fontsize=8, color=MUTED)
fig.savefig('fig/fig07_city_map.png'); plt.close()

# by kind of project (title keywords), mean and 95% CI, placebo band
fig, ax = plt.subplots(figsize=(9.5, 4.6))
k = x.groupby('kind').d.agg(['mean', 'count', 'std']).sort_values('count', ascending=False)
k = k[k['count'] >= 3]
for j, (name, r) in enumerate(k.iterrows()):
    se = r['std'] / np.sqrt(r['count']); xs = x[x.kind == name].d
    ax.scatter(xs, np.full(len(xs), j) + np.random.default_rng(j).uniform(-.18, .18, len(xs)), s=10, color='#8c8c8c', alpha=.35, lw=0)
    c = INK if abs(r['mean']) < 1.96 * se else ('#2e7d32' if r['mean'] > 0 else LOSS)
    ax.plot([r['mean'] - 1.96 * se, r['mean'] + 1.96 * se], [j, j], color=c, lw=2.4); ax.scatter(r['mean'], j, s=60, color=c, edgecolor='white', zorder=3)
    ax.text(1.01, j, f"{np.expm1(r['mean']):+.0%}   n={int(r['count'])}", transform=ax.get_yaxis_transform(), fontsize=8.5, va='center')
ax.axvspan(lo, hi, color='#f0f0f0', zorder=0); ax.axvline(0, color='#999999', lw=.6)
ax.set_yticks(range(len(k))); ax.set_yticklabels(k.index); ax.invert_yaxis()
ax.set_xlim(-1.4, 1.4); ax.set_xticks(np.log1p([-.6, -.3, 0, .5, 1, 2])); ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{np.expm1(v):+.0%}'))
ax.set_xlabel('Change in weekly visits vs nearby untouched parks (52 weeks after vs before)')
ax.set_title('Citywide by project type: 95 playgrounds average zero; only courts (4) sit clearly above')
fig.text(0.01, -0.06, 'Bar = mean with 95% interval (green = above zero). Grey band = 10th–90th percentile of placebo changes. Types with fewer than 3 projects not shown.', fontsize=7.5, color=MUTED, va='top')
fig.savefig('fig/fig08_city_by_kind.png'); plt.close()
print(k.round(3))
