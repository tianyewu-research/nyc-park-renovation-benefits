import pandas as pd, numpy as np, matplotlib.pyplot as plt
from style import *
poi = pd.read_csv('data/queens_poi.csv', dtype={'ID_STORE': str})
bins = [-1, 1, 2, 4, 9, 19, 1e9]; labs = ['1 min', '2 min', '3–4', '5–9', '10–19', '20+ min']
poi['b'] = pd.cut(poi.dwell, bins, labels=labs)
a = poi.groupby('b', observed=False).agg(n=('ID_STORE', 'size'), v=('med_visits', 'sum'))
a['vs'] = a.v / a.v.sum(); a['ns'] = a.n / a.n.sum()
exec(open('queens_did.py').read().split("t = pd.read_csv")[0])
rel = L_raw.sub(L_raw.mean(axis=1), axis=0); k = 6
jump = pd.Series({w: (rel.iloc[i:i + k].mean() - rel.iloc[i - k:i].mean()).abs().median() for i, w in enumerate(rel.index) if k <= i < len(rel) - k})
fig, axs = plt.subplots(1, 3, figsize=(16, 4.4), gridspec_kw={'width_ratios': [1, 1.3, 1.1]})
ax = axs[0]
cols = [LOSS, LOSS, '#d9a0a0', '#9fb48a', '#6f8f5a', '#4d6b3c']
ax.bar(range(6), a.vs, color=cols, width=.7)
for i, (vs, n) in enumerate(zip(a.vs, a.n)): ax.text(i, vs + .01, f'{vs:.0%}\n{n} POIs', ha='center', fontsize=8, color=INK)
ax.set_xticks(range(6)); ax.set_xticklabels(labs); ax.set_xlabel('Median time a device stays at the POI')
ax.set_yticks([]); ax.spines['left'].set_visible(False); ax.set_ylim(0, a.vs.max() * 1.3)
ax.set_title(f'{a.vs.iloc[:2].sum():.0%} of Queens park "visits" stay 2 minutes or less')
ax.text(0, -.25, 'Share of median weekly visits, 927 Queens park POIs, 2019–2026', transform=ax.transAxes, fontsize=7.5, color=MUTED)
ax = axs[1]
ax.plot(jump.index, jump.values, color='#555555', lw=1)
ax.axhline(jump.median(), color=LIGHT, lw=.8, ls=':')
for d, t in [('2020-03-23', 'COVID-19\nlockdown'), ('2023-01-02', 'Data break\nJan 2023'), ('2024-11-18', 'Data break\nNov 2024')]:
    y = jump[pd.Timestamp(d) - pd.Timedelta(weeks=1):pd.Timestamp(d) + pd.Timedelta(weeks=1)].max()
    ax.annotate(t, (pd.Timestamp(d), y), xytext=(8, 2), textcoords='offset points', fontsize=8, color=LOSS if 'break' in t else INK)
ax.set_ylim(0.06, 0.46); ax.set_ylabel('Typical park-specific level jump\n(median |log change|, 6 weeks either side)')
ax.set_title('Two dates where parks jump for data, not park, reasons')
ax = axs[2]
m = pd.read_csv('out/origin_listing_over_time.csv', parse_dates=['week']).set_index('week').rolling(4, center=True).mean()
ax.plot(m.index, m.local * 100, color=INK, lw=1.2); ax.set_ylim(0, 100)
ax.set_ylabel('Visitors living within 1 km of the park (median %)')
pre = m.loc['2021-01':'2022-12', 'n_cbg'].mean(); post = m.loc['2023-07':'2024-12', 'n_cbg'].mean()
ax.text(0.98, 0.06, f'Home block groups listed per park-week:\n~{pre:.0f} before → ~{post:.0f} after', transform=ax.transAxes, fontsize=8, color=INK, ha='right')
ax.axvline(pd.Timestamp('2023-01-02'), color=LOSS, ls='--', lw=.8)
ax.set_title('Visitor origins shift overnight in Jan 2023')
fig.tight_layout(); fig.savefig('fig/fig02_data_checks.png'); plt.close(); print(a)
