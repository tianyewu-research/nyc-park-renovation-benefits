"""First-pass Queens-wide comparison: each of the 64 projects vs its 10 nearest untouched Queens parks.
Outcome = log weekly visits summed over the park's 'stay' POIs (median dwell >= 5 min; all POIs if a park has none).
Delta = [mean(log T - log C) in 26 weeks after completion] - [same in 26 weeks before construction start].
A park-specific level step at the 2023-01-02 data-vintage break is removed ('corrected' series).
Noise benchmark: the same calculation on untouched parks at the same dates (placebo)."""
import pandas as pd, numpy as np, geopandas as gpd
W = pd.Timedelta(weeks=1); BREAKS = [pd.Timestamp('2023-01-02'), pd.Timestamp('2024-11-18')]; BREAK = BREAKS[0]
poi = pd.read_csv('data/queens_poi.csv', dtype={'ID_STORE': str})
d = pd.read_parquet('data/queens_poi_week_full.parquet', columns=['ID_STORE', 'VISIT_COUNTS', 'week'])
d = d.merge(poi[['ID_STORE', 'matched_pid', 'stay']], on='ID_STORE')
has_stay = poi.groupby('matched_pid').stay.any()
d['use'] = d.stay | ~d.matched_pid.map(has_stay)
pw = d[d.use].groupby(['matched_pid', 'week']).VISIT_COUNTS.sum().unstack(0)
weeks = pw.index
pw = pw[pw.columns[pw.notna().sum() >= 400]]
L_raw = np.log(pw.clip(lower=1))
L_cor = L_raw.copy(); steps = {}
for B in BREAKS:
    rel = L_cor.sub(L_cor.mean(axis=1), axis=0)
    st = rel[(weeks >= B) & (weeks < B + 6 * W)].mean() - rel[(weeks >= B - 6 * W) & (weeks < B)].mean()
    L_cor = L_cor - pd.DataFrame(np.outer(weeks >= B, st), index=weeks, columns=pw.columns); steps[str(B.date())] = st
step = pd.DataFrame(steps)
step.to_csv('out/park_steps_breaks.csv')

t = pd.read_csv('src_data/data/raw/capital_projects/capital_project_tracker.csv', dtype=str)
t['cs'] = pd.to_datetime(t.constructionstart); t['ce'] = pd.to_datetime(t.constructionactualcompletion.fillna(t.constructionadjustedcompletion))
act = t[((t.cs <= '2026-09-28') & (t.ce.fillna(pd.Timestamp('2030')) >= '2018-01-01')) | t.currentphase.str.contains('construction', case=False, na=False)]
touched = set(act.parkid.dropna())
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263)
parks = parks.dissolve('gispropnum', aggfunc={'signname': 'first', 'acres': 'first'})
cen = parks.geometry.representative_point()
ctrl = [p for p in pw.columns if p not in touched and p in cen.index and has_stay.get(p, False)]
pd.Series(ctrl, name='parkid').to_csv('out/control_parks.csv', index=False)

def gap(L, pid, pool):
    dist = cen[pool].distance(cen[pid]).sort_values(); c = [p for p in dist.index if p != pid][:10]
    C = L[c].mean(axis=1)
    return L[pid] - C, c, dist.iloc[9] * 0.3048 / 1000
def delta(g, cs, ce, n=26):
    pre = g[(weeks >= cs - n * W) & (weeks < cs)]; post = g[(weeks >= ce) & (weeks < ce + n * W)]
    if len(pre) < n - 2 or len(post) < n - 2: return np.nan
    return post.mean() - pre.mean()

s = pd.read_csv('src_data/tmp/inventory_2026-10-21/queens64_derived.csv', dtype=str)
s['cs'] = pd.to_datetime(s.cs); s['ce'] = pd.to_datetime(s.ce); s['fund'] = s.fund.astype(float)
rows = []
for _, r in s.iterrows():
    pid = r['Park ID']
    o = {'case': r['Case ID'], 'park': pid}
    if pid not in pw.columns: o['note'] = 'no full park series'; rows.append(o); continue
    for lab, L in [('raw', L_raw), ('cor', L_cor)]:
        g, c, km = gap(L, pid, ctrl)
        o[f'd26_{lab}'] = delta(g, r.cs, r.ce, 26); o[f'd52_{lab}'] = delta(g, r.cs, r.ce, 52)
        dur = g[(weeks >= r.cs) & (weeks < r.ce)].mean() - g[(weeks >= r.cs - 26 * W) & (weeks < r.cs)].mean()
        o[f'during_{lab}'] = dur
    o['ctrl_parks'] = ','.join(c); o['ctrl_km'] = km
    o['straddles_break'] = any((r.cs - 52 * W < B) and (r.ce + 52 * W > B) for B in BREAKS)
    o['near_break'] = any((abs((r.cs - B).days) < 56) or (abs((r.ce - B).days) < 56) for B in BREAKS)
    o['stay_only'] = bool(has_stay.get(pid, False))
    rows.append(o)
res = pd.DataFrame(rows).merge(s[['Case ID', 'Project / site', 'Tracker ID', 'nature', 'pt', 'fund', 'scope', 'flags', 'cs', 'ce', 'covid', 'g_child', 'g_sport', 'g_night', 'g_passive', 'g_fitness', 'Latitude', 'Longitude', 'displaced_use']], left_on='case', right_on='Case ID')

rng = np.random.default_rng(7); plc = []
for _, r in res.iterrows():
    for p in rng.choice(ctrl, 20, replace=False):
        o = {'case': r.case, 'park': p}
        for lab, L in [('raw', L_raw), ('cor', L_cor)]:
            gg = gap(L, p, ctrl)[0]
            o[lab] = delta(gg, r.cs, r.ce, 26); o[lab + '52'] = delta(gg, r.cs, r.ce, 52)
        plc.append(o)
plc = pd.DataFrame(plc); plc.to_csv('out/placebo_deltas.csv', index=False)
for lab in ['raw', 'cor']:
    print(lab, 'placebo sd', round(plc[lab].std(), 3), 'treated sd', round(res[f'd26_{lab}'].std(), 3),
          'treated mean', round(res[f'd26_{lab}'].mean(), 3), 'corr 26v52', round(res[[f'd26_{lab}', f'd52_{lab}']].corr().iloc[0, 1], 2))
print('52wk: placebo sd', round(plc.cor52.std(), 3), 'treated sd', round(res.d52_cor.std(), 3), 'treated mean', round(res.d52_cor.mean(), 3), 'n', res.d52_cor.notna().sum())
lo, hi = plc.cor52.quantile([.1, .9]); lo5, hi5 = plc.cor52.quantile([.05, .95])
def cls(x):
    if pd.isna(x): return 'n/a'
    return 'clear gain' if x > hi else ('clear loss' if x < lo else 'within normal range')
res['outcome'] = res.d52_cor.map(cls)
res['robust'] = np.sign(res.d52_raw) == np.sign(res.d52_cor)
res['pct'] = np.exp(res.d52_cor) - 1
res['plc_p10'], res['plc_p90'], res['plc_p05'], res['plc_p95'] = lo, hi, lo5, hi5
res.to_csv('out/queens_did_first_pass.csv', index=False)
print('p10/p90', round(lo, 3), round(hi, 3)); print(res.outcome.value_counts())
print(res.groupby('nature').agg(n=('case', 'size'), med=('pct', 'median'), gain=('outcome', lambda x: (x == 'clear gain').sum()), loss=('outcome', lambda x: (x == 'clear loss').sum())))
print('during-construction dip (cor): median', round(res.during_cor.median(), 3), 'share below -10%:', round((res.during_cor < np.log(.9)).mean(), 2))
