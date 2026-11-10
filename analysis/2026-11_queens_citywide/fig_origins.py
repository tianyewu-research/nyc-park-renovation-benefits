import pandas as pd, numpy as np, geopandas as gpd, matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from style import *
W = pd.Timedelta(weeks=1)
res = pd.read_csv('out/queens_did_with_origins.csv', parse_dates=['cs', 'ce'])
poi = pd.read_csv('data/queens_poi.csv', dtype={'ID_STORE': str})
Lg = pd.read_parquet('data/poi_week_homecbg_long.parquet')
bg = gpd.read_file('src_data/data/raw/census_geo_2020/tl_2023_36_bg/tl_2023_36_bg.shp').to_crs(2263)
bg = bg[bg.COUNTYFP.isin(['005', '047', '061', '081', '085'])].set_index('GEOID')
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263).dissolve('gispropnum')
has_stay = poi.groupby('matched_pid').stay.any()
cases = ['Q014', 'Q016']
bins = [0, .5, 1, 2, 4, 8, 100]; cols = ['#f2efe6', '#e3d7b8', '#d1b67f', '#b98c4a', '#8c5a2b', '#5a3416']
cmap = ListedColormap(cols); norm = BoundaryNorm(bins, cmap.N)
fig, axs = plt.subplots(2, 2, figsize=(11, 10.5))
for row, case in zip(axs, cases):
    r = res[res.case == case].iloc[0]; pid = r.park
    ids = poi[(poi.matched_pid == pid) & (poi.stay | ~poi.matched_pid.map(has_stay))].ID_STORE
    sub = Lg[Lg.ID_STORE.isin(ids)]
    geom = parks.geometry[pid]; c = geom.centroid; R = 4.5 / 0.0003048
    for ax, (lab, a, b) in zip(row, [('Before', r.cs - 52 * W, r.cs), ('After', r.ce, r.ce + 52 * W)]):
        s = sub[(sub.week >= a) & (sub.week < b)].groupby('cbg').n.sum(); s = s / s.sum() * 100
        g = bg.join(s.rename('pct'), how='inner')
        bg.plot(ax=ax, color='#fbfaf7', edgecolor='#e6e6e6', lw=.2)
        pts = g.geometry.representative_point()
        ax.scatter(pts.x, pts.y, s=g.pct * 22, color='#8c5a2b', alpha=.55, edgecolor='white', lw=.3, zorder=3)
        gpd.GeoSeries([geom.buffer(1000 / 0.3048)], crs=2263).boundary.plot(ax=ax, color=INK, lw=.8, linestyle='--')
        gpd.GeoSeries([geom], crs=2263).plot(ax=ax, color='#2e7d32')
        d = parks.geometry  # distance for local share
        loc = s[s.index.isin(bg.index)]; dist = bg.loc[loc.index].geometry.representative_point().distance(geom) * 0.3048
        l1k = loc[dist.values <= 1000].sum()
        ax.set_xlim(c.x - R, c.x + R); ax.set_ylim(c.y - R, c.y + R); ax.set_axis_off()
        ax.set_title(f"{lab}  ({a:%b %Y}–{b - W:%b %Y})", fontsize=10, loc='left')
        ax.text(0.02, 0.03, f"{l1k:.0f}% of visitors live within 1 km\n{len(loc)} home block groups listed", transform=ax.transAxes, fontsize=8.5,
                bbox=dict(fc='white', ec='none', alpha=.85))
    nm = r['Project / site'].replace(' Reconstruction', '')
    row[0].text(-0.02, 0.5, f"{nm}\n{TYPE_LAB[nat_code(r.nature)].split('  ')[-1].strip()} · visits {np.expm1(r.d52_cor):+.0%}", transform=row[0].transAxes,
                rotation=90, ha='right', va='center', fontsize=10, fontweight='bold')
for v in [1, 4, 10]:
    axs[1][1].scatter([], [], s=v * 22, color='#8c5a2b', alpha=.55, label=f'{v}% of visitors')
axs[1][1].legend(loc='lower right', fontsize=8, title='Home block group', title_fontsize=8)
fig.suptitle('Two 2024–25 renovations that gained visitors: the share living within 1 km also rose', x=0.02, ha='left', fontsize=12.5, fontweight='bold', y=.95)
fig.text(0.02, 0.035, 'Dashed line = 1 km from the park edge. Advan home block groups; groups with fewer than 2 visitors in a week are suppressed. '
         'Both projects sit after the Jan 2023 origin-data change; both cross the Nov 2024 break.', fontsize=7.5, color=MUTED)
fig.savefig('fig/fig06_origins_two_gains.png'); plt.close(); print('ok')
