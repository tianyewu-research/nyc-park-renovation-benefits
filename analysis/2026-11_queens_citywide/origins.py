"""Weekly visitor-origin metrics per park (stay POIs; all POIs if a park has none) and per selected POI.
Metrics: local share (home CBG centroid within 1 km / 500 m of the park edge), Queens share, visitor-weighted
median household income of home tracts (ACS 2019-23), number of home CBGs. Advan suppresses CBGs with <2 visitors."""
import pandas as pd, numpy as np, geopandas as gpd, json
poi = pd.read_csv('data/queens_poi.csv', dtype={'ID_STORE': str})
res = pd.read_csv('out/queens_did_first_pass.csv', dtype={'park': str})
ctrl = pd.read_csv('out/control_parks.csv').parkid.tolist()
need = set(res.park.dropna()) | set(ctrl) | {'Q004', 'Q021'}
has_stay = poi.groupby('matched_pid').stay.any()
P = poi[poi.matched_pid.isin(need) & (poi.stay | ~poi.matched_pid.map(has_stay))]
d = pd.read_parquet('data/queens_poi_week_full.parquet', columns=['ID_STORE', 'week', 'VISITOR_HOME_CBGS'])
d = d[d.ID_STORE.isin(P.ID_STORE) & d.VISITOR_HOME_CBGS.notna()]
recs = []
for sid, wk, js in zip(d.ID_STORE.values, d.week.values, d.VISITOR_HOME_CBGS.values):
    for k, v in json.loads(js).items(): recs.append((sid, wk, k, v))
L = pd.DataFrame(recs, columns=['ID_STORE', 'week', 'cbg', 'n'])
L = L[L.cbg.str[:5].isin(['36005', '36047', '36061', '36081', '36085'])]
L.to_parquet('data/poi_week_homecbg_long.parquet', index=False)
print('long rows', len(L))
bg = gpd.read_file('src_data/data/raw/census_geo_2020/tl_2023_36_bg/tl_2023_36_bg.shp').to_crs(2263)
bg = bg[bg.COUNTYFP.isin(['005', '047', '061', '081', '085'])]
bgc = bg.set_index('GEOID').geometry.representative_point()
inc = pd.read_csv('src_data/data/raw/acs_panel/from_walkability/b19013_2023_tract/ACSDT5Y2023.B19013-Data.csv', skiprows=[1])
inc['tract'] = inc.GEO_ID.str[-11:]; inc['mhi'] = pd.to_numeric(inc.B19013_001E, errors='coerce')
parks = gpd.read_file('src_data/data/raw/park_boundaries/parks_properties_20260623/geo_export_1a108b51-4bb1-4d99-b4b9-8ec54acb553d.shp').to_crs(2263).dissolve('gispropnum')
L = L.merge(P[['ID_STORE', 'matched_pid']], on='ID_STORE')
dl = []
for p in L.matched_pid.unique():
    cb = L.loc[L.matched_pid == p, 'cbg'].unique(); cb = cb[np.isin(cb, bgc.index)]
    dl.append(pd.DataFrame({'matched_pid': p, 'cbg': cb, 'dist_m': bgc[cb].distance(parks.geometry[p]).values * 0.3048}))
L = L.merge(pd.concat(dl), on=['matched_pid', 'cbg'])
L['mhi'] = L.cbg.str[:11].map(inc.set_index('tract').mhi)
L['l1k'] = L.n * (L.dist_m <= 1000); L['l500'] = L.n * (L.dist_m <= 500); L['qn'] = L.n * (L.cbg.str[2:5] == '081')
L['inc_n'] = L.n * L.mhi.notna(); L['inc_x'] = (L.n * L.mhi).fillna(0)
def agg(keys):
    a = L.groupby(keys).agg(listed=('n', 'sum'), l1k=('l1k', 'sum'), l500=('l500', 'sum'), qn=('qn', 'sum'), inc_n=('inc_n', 'sum'), inc_x=('inc_x', 'sum'), n_cbg=('cbg', 'nunique')).reset_index()
    a['local1km'] = a.l1k / a.listed; a['local500'] = a.l500 / a.listed; a['queens'] = a.qn / a.listed; a['inc_w'] = a.inc_x / a.inc_n
    return a
agg(['matched_pid', 'week']).to_parquet('data/park_week_origins.parquet', index=False)
agg(['ID_STORE', 'week']).to_parquet('data/poi_week_origins.parquet', index=False)
print(agg(['matched_pid', 'week'])[['listed', 'local1km', 'local500', 'queens', 'inc_w', 'n_cbg']].describe().round(3))
