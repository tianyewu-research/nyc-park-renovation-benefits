"""Within-park comparisons for Astoria and Cunningham at POI level.
Each POI series is corrected for the Jan 2023 and Nov 2024 data breaks using the median jump of POIs of the
same size class (quintile of median weekly visits) in untouched Queens parks. Outcome = log(POI visits) minus
log(sum of the park's other stay POIs); compared 52 weeks after completion vs 52 weeks before start (same seasons)."""
import pandas as pd, numpy as np
W = pd.Timedelta(weeks=1); BREAKS = [pd.Timestamp('2023-01-02'), pd.Timestamp('2024-11-18')]
poi = pd.read_csv('data/queens_poi.csv', dtype={'ID_STORE': str}).set_index('ID_STORE')
d = pd.read_parquet('data/queens_poi_week_full.parquet', columns=['ID_STORE', 'VISIT_COUNTS', 'week'])
x = d.pivot(index='week', columns='ID_STORE', values='VISIT_COUNTS')
L = np.log(x.clip(lower=1))
ctrl = set(pd.read_csv('out/control_parks.csv').parkid)
q = pd.qcut(poi.med_visits.reindex(L.columns), 5, labels=False)
untouched = [c for c in L.columns if poi.matched_pid.get(c) in ctrl]
steps = {}
for B in BREAKS:
    rel = L.sub(L[untouched].median(axis=1), axis=0)
    st = rel[(L.index >= B) & (L.index < B + 8 * W)].mean() - rel[(L.index >= B - 8 * W) & (L.index < B)].mean()
    by_q = st[untouched].groupby(q[untouched]).median()
    steps[str(B.date())] = by_q
    L = L - pd.DataFrame(np.outer(L.index >= B, q.map(by_q).fillna(0).values), index=L.index, columns=L.columns)
pd.DataFrame(steps).to_csv('out/size_class_break_steps.csv')
L.to_parquet('data/poi_week_logvisits_corrected.parquet')
cases = [
    ('Astoria', 'Charybdis Playground + spray shower', '7320467', ['7320468', '6480004'], '2019-09-01', '2021-07-01'),
    ('Astoria', 'Charybdis Playground (2nd nearby POI)', '7320469', ['7320468', '6480004'], '2019-09-01', '2021-07-01'),
    ('Astoria', 'Great Lawn pathways', '6480004', ['7320468', '7320467'], '2024-09-01', '2025-10-01'),
    ('Cunningham', 'Redwood Upper Playground', '6481319', ['7320409', '6481323', '7320408'], '2022-10-01', '2023-10-01'),
    ('Cunningham', 'Neighbor POI 65 m from Redwood Upper', '6481324', ['7320409', '6481323', '7320408'], '2022-10-01', '2023-10-01'),
    ('Cunningham', '210th Street Playground', '6480970', ['7320409', '6481323', '7320408'], '2023-09-01', '2024-09-01')]
out = []
for park, name, tr, cmp, cs, ce in cases:
    cs, ce = pd.Timestamp(cs), pd.Timestamp(ce)
    r = L[tr] - np.log(np.exp(L[cmp]).sum(axis=1))
    o = {'park': park, 'project': name, 'poi': tr}
    for n in (26, 52):
        pre = r[(r.index >= cs - n * W) & (r.index < cs)]; post = r[(r.index >= ce) & (r.index < ce + n * W)]
        o[f'd{n}'] = post.mean() - pre.mean(); o[f'n_post{n}'] = post.notna().sum()
    # placebo: every other stay POI in untouched parks, same dates, vs its park's other stay POIs
    o['during'] = r[(r.index >= cs) & (r.index < ce)].mean() - r[(r.index >= cs - 52 * W) & (r.index < cs)].mean()
    out.append(o)
o = pd.DataFrame(out); o['pct52'] = np.expm1(o.d52); o['pct_during'] = np.expm1(o.during)
# placebo for within-park POI shares: untouched parks with >=2 stay POIs
P = poi[poi.stay & poi.matched_pid.isin(ctrl)]
multi = P.groupby('matched_pid').filter(lambda g: len(g) >= 2)
pl = []
for _, c in o.iterrows():
    cs, ce = [pd.Timestamp(v) for v in [cases[_][4], cases[_][5]]]
    for pid, g in multi.groupby('matched_pid'):
        for s in g.index:
            others = [z for z in g.index if z != s and z in L]
            if s not in L or not others: continue
            r = L[s] - np.log(np.exp(L[others]).sum(axis=1))
            pre = r[(r.index >= cs - 52 * W) & (r.index < cs)]; post = r[(r.index >= ce) & (r.index < ce + 52 * W)]
            pl.append({'case': c.project, 'd52': post.mean() - pre.mean()})
pl = pd.DataFrame(pl)
o['plc_p10'] = o.project.map(pl.groupby('case').d52.quantile(.1)); o['plc_p90'] = o.project.map(pl.groupby('case').d52.quantile(.9))
o['plc_n'] = o.project.map(pl.groupby('case').size())
o.to_csv('out/within_park_results.csv', index=False)
print(pd.DataFrame(steps).round(3)); print(o.round(3).to_string())
