"""Citywide NYC park POIs, weeks from 2022-07-04: visits, dwell, and visitor-origin aggregates per POI-week.
Origin aggregates use Advan VISITOR_HOME_CBGS restricted to the five NYC counties.
Usage: python3 extract_city.py START END  (index range over files with week >= 2022-07-04)"""
import sys, glob, json, pathlib, pandas as pd, pyarrow.parquet as pq
R = pathlib.Path.home() / 'mnt/park_renovation_thesis'
H = R / 'src/wed'
out = R / 'tmp/wed_2026-11-04/city'; out.mkdir(parents=True, exist_ok=True)
xw = pd.read_csv(R / 'data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv', dtype=str)
xw = xw[xw.match_status == 'matched']; pid = dict(zip(xw.ID_STORE, xw.matched_pid))
near = pd.read_csv(H / 'park_cbg_1km.csv', dtype={'cbg': str})
d1 = {(p, c): d for p, c, d in zip(near.gispropnum, near.cbg, near.dist_m)}
mhi = pd.read_csv(H / 'tract_mhi.csv', dtype={'tract': str}).set_index('tract').mhi.to_dict()
fs = [f for f in sorted(glob.glob(str(R / 'data/raw/advan_weekly_nycparks_2019_2026/19-26nycparks/*.parquet'))) if f.split('/')[-1][:10] >= '2022-07-04']
a, b = int(sys.argv[1]), int(sys.argv[2])
NYC = ('36005', '36047', '36061', '36081', '36085')
rows = []
for f in fs[a:b]:
    t = pq.read_table(f, columns=['ID_STORE', 'DATE_RANGE_START', 'VISIT_COUNTS', 'VISITOR_COUNTS', 'MEDIAN_DWELL', 'DISTANCE_FROM_HOME', 'VISITOR_HOME_CBGS']).to_pandas()
    t = t[t.ID_STORE.isin(pid)]
    wk = f.split('/')[-1][:10]
    for s, v, vr, dw, dh, js in zip(t.ID_STORE, t.VISIT_COUNTS, t.VISITOR_COUNTS, t.MEDIAN_DWELL, t.DISTANCE_FROM_HOME, t.VISITOR_HOME_CBGS):
        p = pid[s]; listed = l1 = l5 = incx = incn = n = 0
        if isinstance(js, str):
            for c, k in json.loads(js).items():
                if not c.startswith(NYC): continue
                listed += k; n += 1
                dd = d1.get((p, c))
                if dd is not None:
                    l1 += k
                    if dd <= 500: l5 += k
                m = mhi.get(c[:11])
                if m == m and m is not None: incx += k * m; incn += k
        rows.append((s, p, wk, float(v or 0), float(vr or 0), float(dw) if dw == dw and dw is not None else None, float(dh) if dh == dh and dh is not None else None, listed, l1, l5, incx, incn, n))
pd.DataFrame(rows, columns=['ID_STORE', 'park', 'week', 'visits', 'visitors', 'dwell', 'dist_home', 'listed', 'l1k', 'l500', 'inc_x', 'inc_n', 'n_cbg']).to_parquet(out / f'city_{a:03d}_{b:03d}.parquet', index=False)
print(a, b, len(rows), 'files', len(fs))
