import pandas as pd, numpy as np, geopandas as gpd, matplotlib.pyplot as plt, matplotlib.dates as mdates
from matplotlib.patches import FancyArrow
from style import *
poi = pd.read_csv('data/queens_poi.csv', dtype={'ID_STORE': str})
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263)
plan = gpd.read_parquet('data/planimetric_open_space.parquet').to_crs(2263)
t = pd.read_csv('src_data/data/raw/capital_projects/capital_project_tracker.csv', dtype=str).drop_duplicates('trackerid')
L = pd.read_parquet('data/poi_week_logvisits_corrected.parquet')
BREAKS = [pd.Timestamp('2023-01-02'), pd.Timestamp('2024-11-18')]
FEAT = '#cbd8bb'; HARD = '#d9d4c7'

PARKS = {
 'Q004': dict(name='Astoria Park', acres=60, rot=False,
   poi_names={'7320468': 'Pool', '7320467': 'Charybdis / center', '7320469': 'Center (small)', '6480004': 'North lawn',
              '6480008': 'Track & bridge approach'},
   poi_col={'7320468': '#3d6fa8', '7320467': '#d1495b', '7320469': '#e8a33d', '6480004': '#2e7d32'},
   off={'7320468': (-14, -4), '7320469': (-10, 6), '7320467': (12, -10)},
   projects=[  # (no, trackerid, short label, cs, ce, $M, location override 'track' or None)
     (1, '8892', 'Track and field', '2018-11', '2019-10', 12.9, 'track'),
     (2, '8965', 'Charybdis Playground + spray shower', '2019-09', '2021-07', 11.6, None),
     (3, '8987', 'Charybdis Playground restroom', '2020-02', '2021-11', 1.3, None),
     (4, '1254111', 'Field house restrooms', '2021-03', '2021-12', 1.0, None),
     (5, '9322', 'Pool filtration system', '2022-10', '2024-06', 18.9, None),
     (6, '9592', 'Great Lawn pathways', '2024-09', '2025-10', 4.2, None)]),
 'Q021': dict(name='Cunningham Park', acres=358, rot=False,
   poi_names={'7320409': 'Central fields', '6481323': 'SW ballfields', '7320408': 'East', '6481319': 'Redwood Upper Playground',
              '6481324': 'Neighbor, 65 m', '6480970': '210th St Playground', '7379123': 'Expressway edge'},
   off={'6481324': (-10, 4), '6481319': (10, -10)},
   poi_col={'7320409': '#3d6fa8', '6481323': '#6a4c93', '7320408': '#8c8c8c', '6481319': '#d1495b', '6481324': '#e8a33d', '6480970': '#2e7d32'},
   projects=[
     (1, '7254', 'Lower Redwood tot lot*', '2018-07', '2020-04', 1.8, None),
     (2, '9202', 'Vanderbilt Motor Parkway path, phase 2', '2022-07', '2023-04', 3.7, None),
     (3, '9195', 'Redwood Upper Playground', '2022-10', '2023-10', 3.6, None),
     (4, '9546', '210th Street Playground', '2023-09', '2024-09', 3.8, None),
     (5, '10303', 'Lower Redwood spray shower', '2023-10', '2023-12', 0.5, None),
     (6, '8649', 'Maintenance garage (not public)', '2024-11', '2026-12', 41.9, None)])}

def scalebar(ax, x0, y0, m=200):
    ft = m / 0.3048
    ax.plot([x0, x0 + ft], [y0, y0], color=INK, lw=2, solid_capstyle='butt')
    ax.text(x0 + ft / 2, y0 + 60, f'{m} m', ha='center', va='bottom', fontsize=8, color=INK)
def north(ax, x, y, s=250):
    ax.annotate('', xy=(x, y + s), xytext=(x, y), arrowprops=dict(arrowstyle='-|>', color=INK, lw=1.2))
    ax.text(x, y + s + 40, 'N', ha='center', va='bottom', fontsize=9, fontweight='bold')

for pid, P in PARKS.items():
    pk = parks[parks.gispropnum == pid]; geom = pk.union_all()
    feats = plan[plan.intersects(geom.buffer(30)) & (plan.sub_code != '498000')]
    lawn = plan[plan.intersects(geom.buffer(30)) & (plan.sub_code == '498000')]
    pp = poi[poi.matched_pid == pid]
    g = gpd.GeoDataFrame(pp, geometry=gpd.points_from_xy(pp.longitude, pp.latitude), crs=4326).to_crs(2263)
    tt = t.set_index('trackerid')
    fig, ax = plt.subplots(figsize=(8, 8.5))
    pk.plot(ax=ax, color=PARK, edgecolor=PARK_EDGE, lw=1)
    feats.plot(ax=ax, color=HARD, edgecolor='white', lw=.4)
    # POIs
    st = g[g.stay]; ps = g[~g.stay]
    ax.scatter(ps.geometry.x, ps.geometry.y, s=8 + 300 * np.sqrt(ps.med_visits / g.med_visits.max()), facecolor='none', edgecolor='#999999', lw=.8, zorder=4)
    for _, r in st.iterrows():
        c = P['poi_col'].get(r.ID_STORE, '#8c8c8c')
        ax.scatter(r.geometry.x, r.geometry.y, s=20 + 900 * np.sqrt(r.med_visits / g.med_visits.max()), color=c, alpha=.55, edgecolor='white', lw=.8, zorder=5)
        if r.ID_STORE in P['poi_names']:
            off = P.get('off', {}).get(r.ID_STORE, (9, -3))
            ax.annotate(P['poi_names'][r.ID_STORE], (r.geometry.x, r.geometry.y), xytext=off, textcoords='offset points', fontsize=8, color=c, fontweight='bold', zorder=8, ha='right' if off[0] < 0 else 'left',
                        bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=.75))
    for _, r in ps.iterrows():
        if r.ID_STORE in P['poi_names']:
            ax.annotate(P['poi_names'][r.ID_STORE] + ' (pass-through)', (r.geometry.x, r.geometry.y), xytext=(9, -3), textcoords='offset points', fontsize=7.5, color=MUTED, zorder=8)
    # projects
    for no, tid, lab, cs, ce, usd, loc in P['projects']:
        if loc == 'track':
            ff = feats[feats.sub_code == '496000']; pt = ff.union_all().centroid
        else:
            pt = gpd.GeoSeries(gpd.points_from_xy([float(tt.loc[tid, 'longitude'])], [float(tt.loc[tid, 'latitude'])]), crs=4326).to_crs(2263).iloc[0]
        if pid == 'Q021' and no == 1: pt = type(pt)(pt.x - 90, pt.y + 60)
        ax.scatter(pt.x, pt.y, s=150, color=INK, zorder=9, edgecolor='white', lw=1)
        ax.text(pt.x, pt.y, str(no), color='white', ha='center', va='center', fontsize=7.5, fontweight='bold', zorder=10)
    xmin, ymin, xmax, ymax = geom.bounds; pad = 250
    ax.set_xlim(xmin - pad, xmax + pad); ax.set_ylim(ymin - pad, ymax + pad); ax.set_aspect('equal'); ax.set_axis_off()
    scalebar(ax, xmin - pad + 80, ymin - pad + 120); north(ax, xmax + pad - 150, ymin - pad + 100)
    ax.set_title(f"{P['name']}  ·  {P['acres']} acres  ·  {len(g)} Advan POIs ({g.stay.sum()} stay, {(~g.stay).sum()} pass-through)", fontsize=11)
    fn = {'Q004': 'Numbers = projects (see timeline). Project 1 placed on the mapped running track; its Tracker point sits at the pool.\nFilled circles = stay POIs (median dwell ≥ 5 min), sized by weekly visits; open circles = pass-through POIs. Base: NYC Parks property and planimetric open-space layers.',
          'Q021': 'Numbers = projects (see timeline). *Tracker gives projects 1 and 4 the same coordinates; 1 is shifted slightly to stay visible.\nFilled circles = stay POIs (median dwell ≥ 5 min), sized by weekly visits; open circles = pass-through POIs. Base: NYC Parks property and planimetric open-space layers.'}[pid]
    fig.text(0.02, 0.03, fn, fontsize=7.3, color=MUTED, va='top')
    fig.savefig(f'fig/fig_{pid}_plan.png'); plt.close()

    # timeline: share of stay-POI visits by POI + Gantt
    ids = [i for i in P['poi_col'] if i in L.columns]
    V = np.exp(L[ids]); sh = V.div(V.sum(axis=1), axis=0).rolling(8, center=True, min_periods=5).mean()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 6.2), sharex=True, gridspec_kw={'height_ratios': [2.3, 1]})
    ys = {}
    for i in ids:
        a1.plot(sh.index, sh[i] * 100, color=P['poi_col'][i], lw=1.8 if i in ('6480004', '6481319', '6481324', '6480970', '7320467') else 1.1)
        ys[i] = np.log10(sh[i].dropna().iloc[-1] * 100)
    order = sorted(ys, key=ys.get); prev = -9
    for i in order:
        y = max(ys[i], prev + 0.09); prev = y
        a1.text(sh.index[-1] + pd.Timedelta(weeks=3), 10 ** y, P['poi_names'][i], color=P['poi_col'][i], fontsize=8, va='center', fontweight='bold')
    a1.set_ylabel('Share of the park\'s stay visits (%)'); a1.set_yscale('log')
    a1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:g}'))
    for B in BREAKS:
        for a in (a1, a2): a.axvline(B, color=LOSS, ls=(0, (3, 3)), lw=.8)
        a1.text(B, a1.get_ylim()[1], ' data break', color=LOSS, fontsize=7.5, va='top')
    a1.axvspan(pd.Timestamp('2020-03-15'), pd.Timestamp('2021-06-30'), color='#f3f3f3', zorder=0)
    a1.text(pd.Timestamp('2020-03-20'), a1.get_ylim()[0] * 1.05, 'COVID-19 period', fontsize=7.5, color=MUTED, va='bottom')
    for j, (no, tid, lab, cs, ce, usd, loc) in enumerate(P['projects']):
        s, e = pd.Timestamp(cs), pd.Timestamp(ce)
        a2.barh(j, (e - s).days, left=s, height=.6, color=INK if usd >= 1 else '#999999')
        a2.text(e + pd.Timedelta(days=20), j, f'{no}  {lab}  (${usd:g}M)', va='center', fontsize=7.8, color=INK)
    a2.set_yticks([]); a2.invert_yaxis(); a2.spines['left'].set_visible(False)
    a2.set_xlim(pd.Timestamp('2018-06-01'), pd.Timestamp('2027-09-01'))
    a1.set_title(f"{P['name']}: where visitors go inside the park, and when projects were under construction", fontsize=11.5)
    fig.text(0.01, -0.01, 'Lines = 8-week moving share among the park\'s stay POIs; each POI corrected for size-dependent jumps at the two data breaks. Bars = Tracker construction start to completion.',
             fontsize=7.5, color=MUTED, va='top')
    fig.tight_layout(); fig.savefig(f'fig/fig_{pid}_timeline.png'); plt.close()
print('ok')
