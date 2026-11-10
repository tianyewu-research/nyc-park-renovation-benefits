"""Citywide 2019-2026, visits only (origins are not comparable across the Jan 2023 change).
Same rules as the Queens analysis: stay POIs (median dwell >= 5 min, measured 2022-07..2026-09), park-level weekly
visits, park-specific steps removed at 2023-01-02 and 2024-11-18, 10 nearest untouched parks as control, 52-week
same-season windows (26-week as a robustness check), placebo on untouched parks."""
import pandas as pd, numpy as np, geopandas as gpd, re
WK = pd.Timedelta(weeks=1); BREAKS = [pd.Timestamp('2023-01-02'), pd.Timestamp('2024-11-18')]
S, END = pd.Timestamp('2019-01-07'), pd.Timestamp('2026-09-28')
c = pd.read_parquet('src_data/data/interim/advan_v3/core_long.parquet', columns=['ID_STORE', 'VISIT_COUNTS', 'week'])
c['VISIT_COUNTS'] = pd.to_numeric(c.VISIT_COUNTS.astype(str), errors='coerce')
xw = pd.read_csv('src_data/data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv', dtype=str)
xw = xw[xw.match_status == 'matched']
dw = pd.read_parquet('data/city_poi_week.parquet', columns=['ID_STORE', 'dwell']).groupby('ID_STORE').dwell.median()
stay = set(dw[dw >= 5].index)
c = c[c.ID_STORE.isin(stay)].merge(xw[['ID_STORE', 'matched_pid']], on='ID_STORE')
pw = c.groupby(['matched_pid', 'week']).VISIT_COUNTS.sum().unstack(0)
weeks = pw.index
pw = pw[pw.columns[pw.notna().sum() >= len(weeks) - 4]]
L = np.log(pw.clip(lower=1))
for B in BREAKS:
    rel = L.sub(L.mean(axis=1), axis=0)
    st = rel[(weeks >= B) & (weeks < B + 6 * WK)].mean() - rel[(weeks >= B - 6 * WK) & (weeks < B)].mean()
    L = L - pd.DataFrame(np.outer(weeks >= B, st), index=weeks, columns=L.columns)
L.to_parquet('data/city_park_week_logvisits_corrected.parquet')
t = pd.read_csv('src_data/data/raw/capital_projects/capital_project_tracker.csv', dtype=str)
t['cs'] = pd.to_datetime(t.constructionstart); t['ce'] = pd.to_datetime(t.constructionactualcompletion.fillna(t.constructionadjustedcompletion))
act = t[((t.cs <= END) & (t.ce.fillna(pd.Timestamp('2030')) >= '2018-01-01')) | t.currentphase.str.contains('construction', case=False, na=False)]
touched = set(act.parkid.dropna())
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263)
parks = parks.dissolve('gispropnum', aggfunc={'signname': 'first', 'acres': 'first', 'borough': 'first'})
cen = parks.geometry.representative_point()
ctrl = [p for p in pw.columns if p not in touched and p in cen.index]
INFRA = r"Roof|Filtration|Filter|Electrical|Plumbing|Boiler|HVAC|Condenser|Citywide|General Site Work|Seawall|Retaining Wall|Water Service|Generator|Elevator|Office|Garage|Expansion Joint|Structural|Sewer|Tower|Bridge|Telecommunication|Fire Alarm|Sediment|Bulkhead|Shoreline|Storehouse|Headquarters|Administration|Facility Electrification"
u = t.drop_duplicates('trackerid').dropna(subset=['cs', 'ce']).copy()
u = u[~u.title.str.contains(INFRA, case=False) & u.parkid.isin(pw.columns)]
tt = t.dropna(subset=['cs'])
def kind(s):
    s = s.lower()
    for k, pat in [('Playground', r'playground|play area|spray|tot lot'), ('Sports field', r'field|turf|ballfield|track|soccer|baseball|football'),
                   ('Court', r'court|basketball|handball|tennis|pickleball'), ('Comfort station', r'comfort station|restroom|bathroom'),
                   ('Pool / rec center', r'pool|recreation center|rec center'), ('Dog run / skate', r'dog run|skate'),
                   ('Paths, plaza, entrance', r'path|plaza|entrance|stair|sidewalk|greenway|esplanade|promenade|ramp|fenc|lighting|seating|boardwalk'),
                   ('Planting / green infra', r'green|planting|forest|garden|tree|wetland|reforest|meadow')]:
        if re.search(pat, s): return k
    return 'Other / whole park'
def gap(pid):
    dist = cen[ctrl].distance(cen[pid]).sort_values(); cc = [p for p in dist.index if p != pid][:10]
    return L[pid] - L[cc].mean(axis=1)
G = {}
def delta(g, cs, ce, n):
    a = (weeks >= cs - n * WK) & (weeks < cs); b = (weeks >= ce) & (weeks < ce + n * WK)
    if a.sum() < n - 2 or b.sum() < n - 2: return np.nan, np.nan
    return g[b].mean() - g[a].mean(), g[a].mean() - g[(weeks < cs - n * WK) | (weeks >= ce + n * WK)].mean()
rows = []
for n in (26, 52):
    def clean(r):
        o = tt[(tt.parkid == r.parkid) & (tt.trackerid != r.trackerid)]
        return not ((o.cs <= r.ce + n * WK) & (o.ce.fillna(pd.Timestamp('2030')) >= r.cs - n * WK)).any()
    v = u[(u.cs - n * WK >= S) & (u.ce + n * WK <= END + WK)]
    v = v[v.apply(clean, axis=1)]
    for _, r in v.iterrows():
        if r.parkid not in G: G[r.parkid] = gap(r.parkid)
        dd, pre_dev = delta(G[r.parkid], r.cs, r.ce, n)
        rows.append({'window': n, 'trackerid': r.trackerid, 'title': r.title, 'park': r.parkid, 'borough': r.borough, 'kind': kind(r.title),
                     'fund': pd.to_numeric(str(r.totalfunding).replace('$', '').replace(',', ''), errors='coerce'), 'cs': r.cs, 'ce': r.ce,
                     'acres': parks.acres.get(r.parkid), 'd': dd, 'pre_dev': pre_dev,
                     'covid': (r.cs - n * WK < pd.Timestamp('2021-07-01')) and (r.ce + n * WK > pd.Timestamp('2020-03-01')),
                     'near_break': any(abs((x - B).days) < 56 for x in (r.cs, r.ce) for B in BREAKS), 'lat': r.latitude, 'lon': r.longitude})
R = pd.DataFrame(rows).dropna(subset=['d'])
rng = np.random.default_rng(5); plc = []
for _, r in R[R.window == 52].iterrows():
    for p in rng.choice(ctrl, 15, replace=False):
        if p not in G: G[p] = gap(p)
        plc.append({'trackerid': r.trackerid, 'd': delta(G[p], r.cs, r.ce, 52)[0]})
P = pd.DataFrame(plc).dropna()
lo, hi = P.d.quantile([.1, .9])
R['outcome'] = np.where(R.d > hi, 'clear gain', np.where(R.d < lo, 'clear loss', 'within normal range'))
R['plc_p10'], R['plc_p90'] = lo, hi
R.to_csv('out/city_full_did.csv', index=False); P.to_csv('out/city_full_placebo.csv', index=False)
for n in (26, 52):
    x = R[R.window == n]
    print(f'{n}w: projects {len(x)} | mean {x.d.mean():.3f} (se {x.d.std() / np.sqrt(len(x)):.3f}) sd {x.d.std():.3f}', x.borough.value_counts().to_dict())
x = R[R.window == 52]
print('placebo sd %.3f p10/p90 %.3f/%.3f | controls %d | stay POIs %d' % (P.d.std(), lo, hi, len(ctrl), len(stay)))
print(x.outcome.value_counts().to_dict())
print(x.groupby('kind').agg(n=('d', 'size'), mean=('d', 'mean'), se=('d', lambda z: z.std() / np.sqrt(len(z)))).round(3).sort_values('n', ascending=False))
print('corr with pre-period deviation:', round(x[['d', 'pre_dev']].corr().iloc[0, 1], 2))
print('corr with log fund:', round(np.corrcoef(x.d[x.fund > 0], np.log(x.fund[x.fund > 0]))[0, 1], 2), '| log acres:', round(np.corrcoef(x.d, np.log(x.acres.astype(float)))[0, 1], 2))
print('covid vs not:', x.groupby('covid').d.agg(['mean', 'size']).round(3).to_dict())
