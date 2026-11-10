"""Change in visitor-origin mix (52 weeks after completion vs 52 weeks before start), relative to the same
10 nearest untouched parks used for visits; placebo = untouched parks at the same dates."""
import pandas as pd, numpy as np
W = pd.Timedelta(weeks=1)
o = pd.read_parquet('data/park_week_origins.parquet')
res = pd.read_csv('out/queens_did_first_pass.csv', parse_dates=['cs', 'ce'])
ctrl = pd.read_csv('out/control_parks.csv').parkid.tolist()
M = {m: o.pivot(index='week', columns='matched_pid', values=v) for m, v in [('l1k', 'l1k'), ('listed', 'listed'), ('inc_x', 'inc_x'), ('inc_n', 'inc_n'), ('qn', 'qn')]}
weeks = M['listed'].index
def window_share(cols, a, b, num, den):
    m = (weeks >= a) & (weeks < b)
    return M[num].loc[m, cols].sum().sum() / M[den].loc[m, cols].sum().sum()
def metrics(cols, cs, ce, n=52):
    pre = (cs - n * W, cs); post = (ce, ce + n * W)
    out = {}
    for name, num, den in [('local1km', 'l1k', 'listed'), ('income', 'inc_x', 'inc_n'), ('queens', 'qn', 'listed')]:
        out[name] = window_share(cols, *post, num, den) - window_share(cols, *pre, num, den)
    return out
rows, plc = [], []
rng = np.random.default_rng(11)
for _, r in res.dropna(subset=['d52_cor']).iterrows():
    c = r.ctrl_parks.split(',')
    if r.park not in M['listed'].columns: continue
    t = metrics([r.park], r.cs, r.ce); cc = metrics([x for x in c if x in M['listed'].columns], r.cs, r.ce)
    rows.append({'case': r.case, **{f'd_{k}': t[k] - cc[k] for k in t}, **{f'raw_{k}': t[k] for k in t}})
    for p in rng.choice([x for x in ctrl if x in M['listed'].columns], 20, replace=False):
        plc.append({'case': r.case, **metrics([p], r.cs, r.ce)})
R = pd.DataFrame(rows); PL = pd.DataFrame(plc)
for k in ['local1km', 'income', 'queens']:
    print(k, 'treated mean', round(R[f'd_{k}'].mean(), 4), 'sd', round(R[f'd_{k}'].std(), 4), '| placebo sd', round(PL[k].std(), 4), 'p10/p90', PL[k].quantile([.1, .9]).round(4).tolist())
R.to_csv('out/origins_did.csv', index=False); PL.to_csv('out/origins_placebo.csv', index=False)
res = res.merge(R, on='case', how='left'); res.to_csv('out/queens_did_with_origins.csv', index=False)
print(res.groupby('nature')[['d_local1km', 'd_income']].median().round(3))
print(res[['d52_cor', 'd_local1km', 'd_income']].corr().round(2))
