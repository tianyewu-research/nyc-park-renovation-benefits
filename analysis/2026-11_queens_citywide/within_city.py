"""Replacement within-park cases where the full before/after span sits in one data era (no break inside).
Outcome: log visits of the POI nearest the project minus mean log visits of the park's other stay POIs,
26 weeks after completion vs 26 weeks before start. Placebo: every stay POI in untouched multi-POI parks, same dates.
Also: share of the POI's listed visitors living within 1 km of the park, after minus before (vs the park's other POIs)."""
import pandas as pd, numpy as np, geopandas as gpd
WK = pd.Timedelta(weeks=1)
d = pd.read_parquet('data/city_poi_week.parquet')
s = d.groupby(['ID_STORE', 'park']).agg(dwell=('dwell', 'median'), vis=('visits', 'median')).reset_index(); s = s[s.dwell >= 5]
V = d[d.ID_STORE.isin(s.ID_STORE)]
LV = np.log(V.pivot(index='week', columns='ID_STORE', values='visits').clip(lower=1))
L1 = V.pivot(index='week', columns='ID_STORE', values='l1k'); LS = V.pivot(index='week', columns='ID_STORE', values='listed')
weeks = LV.index
t = pd.read_csv('src_data/data/raw/capital_projects/capital_project_tracker.csv', dtype=str)
t['cs'] = pd.to_datetime(t.constructionstart); t['ce'] = pd.to_datetime(t.constructionactualcompletion.fillna(t.constructionadjustedcompletion))
touched = set(t[((t.cs <= '2026-09-28') & (t.ce.fillna(pd.Timestamp('2030')) >= '2022-01-01')) | t.currentphase.str.contains('construction', case=False, na=False)].parkid.dropna())
park_of = s.set_index('ID_STORE').park
cases = [('Kissena Corridor Park', 'Synthetic turf soccer field ($6.8M)', '7320427', 'Q300', '2025-11-01', '2025-12-01'),
         ('Baisley Pond Park', '157th St playground + paths ($1.25M)', '7320460', 'Q005', '2025-11-01', '2026-03-01'),
         ('Bloomingdale Park (SI)', 'Basketball court ($0.74M)', '7320526', 'R106', '2025-09-01', '2025-12-01'),
         ('St. Nicholas Park (Manh.)', 'Paths ($0.5M)', '6481501', 'M077', '2023-10-01', '2023-12-01')]
def rel(poi, park):
    others = [x for x in s[s.park == park].ID_STORE if x != poi]
    return LV[poi] - LV[others].mean(axis=1), others
def dd(r, cs, ce, n=26):
    a = (weeks >= cs - n * WK) & (weeks < cs); b = (weeks >= ce) & (weeks < ce + n * WK)
    return r[b].mean() - r[a].mean()
def loc(poi, cs, ce, n=26):
    a = (weeks >= cs - n * WK) & (weeks < cs); b = (weeks >= ce) & (weeks < ce + n * WK)
    return L1.loc[b, poi].sum() / LS.loc[b, poi].sum() - L1.loc[a, poi].sum() / LS.loc[a, poi].sum()
pool = s[~s.park.isin(touched)].groupby('park').filter(lambda z: len(z) >= 2)
out = []
for park, proj, poi, pid, cs, ce in cases:
    cs, ce = pd.Timestamp(cs), pd.Timestamp(ce)
    r, others = rel(poi, pid)
    pl = [dd(rel(x, p)[0], cs, ce) for x, p in zip(pool.ID_STORE, pool.park)]
    pl = pd.Series(pl).dropna()
    lo_t = loc(poi, cs, ce); lo_o = np.nanmean([loc(x, cs, ce) for x in others])
    pll = pd.Series([loc(x, cs, ce) for x in pool.ID_STORE]).dropna()
    out.append({'park': park, 'project': proj, 'poi': poi, 'n_other': len(others), 'd': dd(r, cs, ce), 'plc_p10': pl.quantile(.1), 'plc_p90': pl.quantile(.9),
                'local_change_pts': (lo_t - lo_o) * 100, 'local_plc_p10': pll.quantile(.1) * 100, 'local_plc_p90': pll.quantile(.9) * 100})
o = pd.DataFrame(out); o['pct'] = np.expm1(o.d)
for c in ['plc_p10', 'plc_p90']: o[c + '_pct'] = np.expm1(o[c])
o.to_csv('out/within_park_city_era3.csv', index=False)
pd.set_option('display.width', 250); print(o.round(3).to_string())
