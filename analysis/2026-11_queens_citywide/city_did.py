"""Citywide preliminary analysis, one data era (Jan 2023 - Sep 2026).
Projects: NYC Parks Tracker, all boroughs, before/after windows inside 2023-01-02..2026-09-28, no other Tracker
project in the same park within the windows, park has >=1 stay POI (median dwell >= 5 min).
Visits: log weekly visits of the park's stay POIs minus log of the 10 nearest untouched parks; Nov 2024 break removed
per park. Origins: share of listed home block groups within 1 km of the park edge, and visitor-weighted tract income.
Placebo: same calculation on untouched parks at each project's dates."""
import pandas as pd, numpy as np, geopandas as gpd, re, sys
WK = pd.Timedelta(weeks=1); ERA0, END = pd.Timestamp('2023-01-02'), pd.Timestamp('2026-09-28'); B = pd.Timestamp('2024-11-18')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 26
d = pd.read_parquet('data/city_poi_week.parquet')
era = d[d.week >= ERA0]
dw = era.groupby('ID_STORE').dwell.median()
stay = set(dw[dw >= 5].index)
d = d[d.ID_STORE.isin(stay) & (d.week >= ERA0)]
pw = d.groupby(['park', 'week']).visits.sum().unstack(0)
weeks = pw.index
pw = pw[pw.columns[pw.notna().sum() >= len(weeks) - 4]]
L = np.log(pw.clip(lower=1))
rel = L.sub(L.mean(axis=1), axis=0)
step = rel[(weeks >= B) & (weeks < B + 6 * WK)].mean() - rel[(weeks >= B - 6 * WK) & (weeks < B)].mean()
L = L - pd.DataFrame(np.outer(weeks >= B, step), index=weeks, columns=L.columns)
O = {k: d.groupby(['park', 'week'])[k].sum().unstack(0).reindex(columns=pw.columns) for k in ['listed', 'l1k', 'inc_x', 'inc_n']}

t = pd.read_csv('src_data/data/raw/capital_projects/capital_project_tracker.csv', dtype=str)
t['cs'] = pd.to_datetime(t.constructionstart); t['ce'] = pd.to_datetime(t.constructionactualcompletion.fillna(t.constructionadjustedcompletion))
act = t[((t.cs <= END) & (t.ce.fillna(pd.Timestamp('2030')) >= '2022-01-01')) | t.currentphase.str.contains('construction', case=False, na=False)]
touched = set(act.parkid.dropna())
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263)
parks = parks.dissolve('gispropnum', aggfunc={'signname': 'first', 'acres': 'first', 'borough': 'first'})
cen = parks.geometry.representative_point()
ctrl = [p for p in pw.columns if p not in touched and p in cen.index]
INFRA = r"Roof|Filtration|Filter|Electrical|Plumbing|Boiler|HVAC|Condenser|Citywide|General Site Work|Seawall|Retaining Wall|Water Service|Generator|Elevator|Office|Garage|Expansion Joint|Structural|Sewer|Tower|Bridge|Telecommunication|Fire Alarm|Sediment|Bulkhead|Shoreline|Storehouse|Headquarters|Administration|Facility Electrification"
u = t.drop_duplicates('trackerid').dropna(subset=['cs', 'ce']).copy()
u = u[~u.title.str.contains(INFRA, case=False) & u.parkid.isin(pw.columns)]
tt = t.dropna(subset=['cs'])
def clean(r):
    o = tt[(tt.parkid == r.parkid) & (tt.trackerid != r.trackerid)]
    return not ((o.cs <= r.ce + N * WK) & (o.ce.fillna(pd.Timestamp('2030')) >= r.cs - N * WK)).any()
u = u[(u.cs - N * WK >= ERA0) & (u.ce + N * WK <= END + WK)]
u = u[u.apply(clean, axis=1)]
def kind(s):
    s = s.lower()
    for k, pat in [('Playground', r'playground|play area|spray|tot lot'), ('Sports field', r'field|turf|ballfield|track|soccer|baseball|football'),
                   ('Court', r'court|basketball|handball|tennis|pickleball'), ('Comfort station', r'comfort station|restroom|bathroom'),
                   ('Pool / rec center', r'pool|recreation center|rec center'), ('Dog run / skate', r'dog run|skate'),
                   ('Paths, plaza, entrance', r'path|plaza|entrance|stair|sidewalk|greenway|esplanade|promenade|ramp|fenc|lighting|seating|boardwalk'),
                   ('Planting / green infra', r'green|planting|forest|garden|tree|wetland|reforest|meadow')]:
        if re.search(pat, s): return k
    return 'Other / whole park'
u['kind'] = u.title.map(kind)
u['fund'] = pd.to_numeric(u.totalfunding.str.replace(r'[\$,]', '', regex=True), errors='coerce')
def gap(pid, pool):
    dist = cen[pool].distance(cen[pid]).sort_values(); c = [p for p in dist.index if p != pid][:10]
    return L[pid] - np.log(np.exp(L[c]).sum(axis=1)), c
def win(cs, ce):
    return (weeks >= cs - N * WK) & (weeks < cs), (weeks >= ce) & (weeks < ce + N * WK)
def share(cols, m, num, den): return O[num].loc[m, cols].sum().sum() / O[den].loc[m, cols].sum().sum()
def origin(cols, cs, ce):
    a, b = win(cs, ce)
    return {'loc': share(cols, b, 'l1k', 'listed') - share(cols, a, 'l1k', 'listed'), 'inc': share(cols, b, 'inc_x', 'inc_n') - share(cols, a, 'inc_x', 'inc_n')}
rows, plc = [], []
rng = np.random.default_rng(3)
for _, r in u.iterrows():
    g, c = gap(r.parkid, ctrl); a, b = win(r.cs, r.ce)
    ot, oc = origin([r.parkid], r.cs, r.ce), origin(c, r.cs, r.ce)
    rows.append({'trackerid': r.trackerid, 'title': r.title, 'park': r.parkid, 'borough': r.borough, 'kind': r.kind, 'fund': r.fund, 'cs': r.cs, 'ce': r.ce,
                 'acres': parks.acres.get(r.parkid), 'd': g[b].mean() - g[a].mean(), 'd_loc': ot['loc'] - oc['loc'], 'd_inc': ot['inc'] - oc['inc'],
                 'pre_level': g[a].mean(), 'straddles_nov24': (r.cs - N * WK < B) and (r.ce + N * WK > B),
                 'lat': r.latitude, 'lon': r.longitude})
    for p in rng.choice(ctrl, 15, replace=False):
        gp, cp = gap(p, ctrl); op, opc = origin([p], r.cs, r.ce), origin(cp, r.cs, r.ce)
        plc.append({'trackerid': r.trackerid, 'd': gp[b].mean() - gp[a].mean(), 'd_loc': op['loc'] - opc['loc'], 'd_inc': op['inc'] - opc['inc']})
R = pd.DataFrame(rows); P = pd.DataFrame(plc)
lo, hi = P.d.quantile([.1, .9]); llo, lhi = P.d_loc.quantile([.1, .9])
R['outcome'] = np.where(R.d > hi, 'clear gain', np.where(R.d < lo, 'clear loss', 'within normal range'))
R['origin'] = np.where(R.d_loc > lhi, 'more local', np.where(R.d_loc < llo, 'less local', 'within normal range'))
R.to_csv(f'out/city_did_{N}w.csv', index=False); P.to_csv(f'out/city_placebo_{N}w.csv', index=False)
print(f'window {N}w | projects {len(R)} | control parks {len(ctrl)} | stay POIs {len(stay)}')
print(R.borough.value_counts().to_dict())
print('visits: treated mean %.3f sd %.3f | placebo sd %.3f p10/p90 %.3f/%.3f' % (R.d.mean(), R.d.std(), P.d.std(), lo, hi))
print('local share: treated mean %.4f sd %.4f | placebo sd %.4f p10/p90 %.4f/%.4f' % (R.d_loc.mean(), R.d_loc.std(), P.d_loc.std(), llo, lhi))
print('income: treated mean %.0f sd %.0f | placebo sd %.0f' % (R.d_inc.mean(), R.d_inc.std(), P.d_inc.std()))
print(R.outcome.value_counts().to_dict(), R.origin.value_counts().to_dict())
g = R.groupby('kind').agg(n=('d', 'size'), vis=('d', 'mean'), vis_se=('d', lambda x: x.std() / np.sqrt(len(x))), loc=('d_loc', 'mean'), loc_se=('d_loc', lambda x: x.std() / np.sqrt(len(x))))
print(g.round(3).sort_values('n', ascending=False))
