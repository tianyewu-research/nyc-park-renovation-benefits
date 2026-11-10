"""Extract Queens park POI-week rows (incl. visitor home CBGs) from Advan weekly 2019-2026.
Usage: python3 extract_queens.py START END   (file index range over sorted file list)"""
import sys, glob, pathlib, pandas as pd, pyarrow.parquet as pq
R = pathlib.Path.home()/'mnt/park_renovation_thesis'
out = R/'tmp/wed_2026-11-04/extract'; out.mkdir(parents=True, exist_ok=True)
xw = pd.read_csv(R/'data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv', dtype=str)
q = set(xw[(xw.match_status == 'matched') & xw.matched_pid.str.startswith('Q', na=False)].ID_STORE)
fs = sorted(glob.glob(str(R/'data/raw/advan_weekly_nycparks_2019_2026/19-26nycparks/*.parquet')))
a, b = int(sys.argv[1]), int(sys.argv[2])
cols = ['ID_STORE','DATE_RANGE_START','VISIT_COUNTS','VISITOR_COUNTS','DISTANCE_FROM_HOME','MEDIAN_DWELL',
        'VISITOR_HOME_CBGS','VISITOR_HOME_AGGREGATION','VISITS_BY_EACH_HOUR','VISITS_BY_DAY']
parts = []
for f in fs[a:b]:
    t = pq.read_table(f, columns=cols).to_pandas()
    parts.append(t[t.ID_STORE.isin(q)])
d = pd.concat(parts)
d['week'] = pd.to_datetime(d.DATE_RANGE_START).dt.tz_localize(None).dt.normalize()
d.drop(columns='DATE_RANGE_START').to_parquet(out/f'part_{a:03d}_{b:03d}.parquet', index=False)
print(a, b, len(d), d.ID_STORE.nunique())
