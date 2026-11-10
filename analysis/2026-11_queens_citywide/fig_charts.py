import pandas as pd, numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from style import *
res = pd.read_csv('out/queens_did_with_origins.csv'); res['code'] = res.nature.map(nat_code)
plc = pd.read_csv('out/placebo_deltas.csv')
lo, hi = plc.cor52.quantile([.1, .9])

# --- Fig 3: ranked change, 59 projects, with placebo band ---
r = res.dropna(subset=['d52_cor']).sort_values('d52_cor').reset_index(drop=True)
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.axhspan(np.expm1(lo), np.expm1(hi), color='#eeeeee', zorder=0)
ax.axhline(0, color='#999999', lw=.6)
for i, x in r.iterrows():
    v = np.expm1(x.d52_cor)
    ax.plot([i, i], [0, v], color=TYPE_COL[x.code], lw=1.6, alpha=.8)
    ax.scatter(i, v, s=34, facecolor=TYPE_COL[x.code] if x.robust else 'white', edgecolor=TYPE_COL[x.code] if not x.robust else 'white', lw=1.2 if not x.robust else .6, zorder=3)
ax.text(len(r) - .5, np.expm1(hi) + .03, 'Range of changes in untouched parks at the same dates (10th–90th percentile)', ha='right', va='bottom', fontsize=8, color=MUTED)
for i, x in r.iterrows():
    if x.outcome in ('clear gain', 'clear loss'):
        nm = x['Project / site'].replace(' Reconstruction', '').replace(' Construction', '').replace(' (Hurricane Sandy)', '').replace(' and Adult Fitness Equipment', '').replace(' Synthetic Turf', '')
        v = np.expm1(x.d52_cor)
        nm = nm + ('' if x.robust else ' *')
        ax.annotate(nm, (i, v), xytext=(0, 8 if v > 0 else -8), textcoords='offset points', rotation=90, ha='center', va='bottom' if v > 0 else 'top', fontsize=7.5, color=INK)
ax.set_xticks([]); ax.set_xlim(-1, len(r))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:+.0%}'))
ax.set_ylabel('Change in weekly visits vs. nearby untouched parks')
ax.set_ylim(-1.15, 3.1)
h = [Line2D([], [], marker='o', ls='', color=TYPE_COL[k], markersize=7, label=TYPE_LAB[k]) for k in ['A', 'B', 'C1', 'C2', 'D', '?']]
h += [Line2D([], [], marker='o', ls='', markerfacecolor='white', markeredgecolor='#666666', markersize=7, label='Sign flips without the data-break correction')]
ax.legend(handles=h, loc='upper left', ncol=2, fontsize=8)
ax.set_title(f'Most renovations fall inside the range of ordinary year-to-year change ({(r.outcome == "within normal range").sum()} of {len(r)})')
fig.text(0.01, -0.13, '52 weeks after completion vs 52 weeks before construction start. Visits = Advan weekly visits at the park\'s "stay" POIs (median dwell ≥ 5 min), '
         'corrected for park-specific level shifts at the Jan 2023 and Nov 2024 data breaks.\nPlacebo = the same calculation on 20 randomly drawn untouched Queens parks per project. 5 projects lack a full 52-week window.', fontsize=7.5, color=MUTED, va='top')
fig.savefig('fig/fig03_who_changed.png'); plt.close()

# --- Fig 5: by type of change, visits only ---
fig, ax = plt.subplots(figsize=(9, 4.2))
order = ['A', 'B', 'C1', 'C2', 'D']
for j, k in enumerate(order):
    x = res.loc[res.code == k, 'd52_cor'].dropna()
    m, se = x.mean(), x.std() / np.sqrt(len(x))
    ax.scatter(x, np.full(len(x), j) + np.random.default_rng(j).uniform(-.18, .18, len(x)), s=14, color=TYPE_COL[k], alpha=.4, lw=0)
    ax.plot([m - 1.96 * se, m + 1.96 * se], [j, j], color=TYPE_COL[k], lw=2.6)
    ax.scatter(m, j, s=70, color=TYPE_COL[k], edgecolor='white', zorder=3)
    ax.text(1.01, j, f'{np.expm1(m):+.0%}   [{np.expm1(m - 1.96 * se):+.0%}, {np.expm1(m + 1.96 * se):+.0%}]   n={len(x)}', transform=ax.get_yaxis_transform(), fontsize=8.5, va='center', color=INK)
ax.axvspan(lo, hi, color='#f0f0f0', zorder=0)
ax.axvline(0, color='#999999', lw=.6)
ax.set_yticks(range(5)); ax.set_yticklabels([TYPE_LAB[k] for k in order]); ax.invert_yaxis()
ax.set_xlim(-1.3, 1.3); ax.set_xticks(np.log1p([-.6, -.3, 0, .5, 1, 2])); ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{np.expm1(v):+.0%}'))
ax.set_xlabel('Change in weekly visits vs. nearby untouched parks (52 weeks after vs before)')
ax.set_title('By type of change: every group average sits inside the placebo range')
fig.text(0.01, -0.06, 'Dots = projects; bar = group mean with 95% interval; grey band = 10th–90th percentile of placebo changes in untouched parks.', fontsize=7.5, color=MUTED, va='top')
fig.savefig('fig/fig05_by_type.png'); plt.close()
print('ok', lo, hi)
