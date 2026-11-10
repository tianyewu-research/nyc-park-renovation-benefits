"""Round 3, step 2 — boroughs, population density, streets, subway.

Population: ACS 2023 5-year B01003 total population joined to 2020-vintage
TIGER block groups on GEOID. Density uses ALAND (land area), not total polygon
area, so waterfront block groups are not diluted by their water.

Streets: principal roads are selected with DOCUMENTED CSCL fields only.
RW_TYPE domain is published in the City's geo-metadata (1 Street, 2 Highway,
3 Bridge, 4 Tunnel, 9 Ramp ...). CARTO_DISPLAY_LEVEL is NOT documented there and
is therefore not used as a filter.
"""
import glob, json, os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd

RAW, INT = "data/raw/atlas_round3", "data/interim/atlas_round3"
R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
CRS = "EPSG:2263"
MARGIN_FT = 1500
os.makedirs(INT, exist_ok=True)
qa = []
def log(area, test, detail): qa.append(dict(area=area, test=test, detail=detail))

def prep(g, name):
    n0 = len(g)
    empt = int((g.geometry.is_empty | g.geometry.isna()).sum())
    g = g[~(g.geometry.is_empty | g.geometry.isna())].copy()
    bad = ~g.geometry.is_valid
    rep = int(bad.sum())
    if rep: g.loc[bad, "geometry"] = g.loc[bad, "geometry"].buffer(0)
    still = int((~g.geometry.is_valid).sum())
    g = g.to_crs(CRS)
    log("geometry", f"{name}_repair",
        f"in={n0} empty_dropped={empt} invalid_repaired={rep} still_invalid={still} out={len(g)}")
    return g

# ---- boroughs + clip frame -------------------------------------------------
boro = gpd.read_file(R2, layer="boroughs")
assert str(boro.crs) == CRS
frame = boro.union_all().buffer(MARGIN_FT)
frame_gs = gpd.GeoSeries([frame], crs=CRS)
boro.to_file(f"{INT}/boroughs.gpkg", layer="boroughs", driver="GPKG")
log("frame", "clip_frame", f"five-borough union buffered {MARGIN_FT} ft for a consistent margin")

# ---- population density ----------------------------------------------------
acs_f = glob.glob("data/raw/acs_panel/from_walkability/b01003_2023_bg/*Data.csv")[0]
acs = pd.read_csv(acs_f, low_memory=False).iloc[1:].copy()
acs["GEOID"] = acs["GEO_ID"].astype(str).str.split("US").str[-1]
acs["pop_total"] = pd.to_numeric(acs["B01003_001E"], errors="coerce")
bg = gpd.read_file("data/raw/census_geo_2020/tl_2023_36_bg/tl_2023_36_bg.shp")
bg = bg[bg["COUNTYFP"].isin(["005","047","061","081","085"])].copy()
before = len(bg)
pg = bg.merge(acs[["GEOID","pop_total"]], on="GEOID", how="left")
matched = int(pg["pop_total"].notna().sum())
unmatched = sorted(pg.loc[pg["pop_total"].isna(), "GEOID"].tolist())
if matched / before < 0.99:
    raise SystemExit(f"population join failed: only {matched}/{before} block groups matched")
log("population", "acs_bg_join",
    f"{matched}/{before} block groups joined ({matched/before:.2%}); unmatched GEOIDs: "
    f"{unmatched[:10] if unmatched else 'none'}")

pg["land_sqmi"] = pg["ALAND"] / 2_589_988.110336     # sq metres -> sq miles
pg["population_density_sqmi"] = np.where(pg["land_sqmi"] > 0,
                                         pg["pop_total"] / pg["land_sqmi"], np.nan)
pg["pop_state"] = np.select(
    [pg["pop_total"].isna(), pg["pop_total"] == 0, pg["land_sqmi"] <= 0],
    ["missing", "zero_population", "no_land_area"], default="valid")
pg = prep(pg, "population_bg")
d = pg.loc[pg["pop_state"] == "valid", "population_density_sqmi"]
lo, hi = float(d.quantile(.02)), float(d.quantile(.98))
pg["density_display"] = pg["population_density_sqmi"].clip(lo, hi)
pg[["GEOID","pop_total","ALAND","land_sqmi","population_density_sqmi",
    "density_display","pop_state","geometry"]].to_file(
    f"{INT}/population_bg_2023.gpkg", layer="population_bg_2023", driver="GPKG")
log("population", "density_calc",
    f"population_density_sqmi = B01003_001E / (ALAND land area in sq mi). "
    f"valid={int((pg.pop_state=='valid').sum())} zero={int((pg.pop_state=='zero_population').sum())} "
    f"missing={int((pg.pop_state=='missing').sum())} no_land={int((pg.pop_state=='no_land_area').sum())}")
log("population", "density_range",
    f"raw min={d.min():,.0f} max={d.max():,.0f} median={d.median():,.0f}; "
    f"display clipped to 2nd-98th pct [{lo:,.0f}, {hi:,.0f}]; raw values retained")

# ---- streets ---------------------------------------------------------------
st = gpd.read_file(f"{RAW}/streets_centerline.geojson")
n_raw = len(st)
st["status"] = st["status"].astype(str)
st = st[st["status"] == "2"].copy()                      # 2 = Constructed
st["rw_type"] = pd.to_numeric(st["rw_type"], errors="coerce")
st = prep(st, "streets")
st = st[st.intersects(frame)].copy()
PRINCIPAL = {2, 3, 4, 9}                                  # Highway, Bridge, Tunnel, Ramp
st["is_principal"] = st["rw_type"].isin(PRINCIPAL)
st[["physicalid","rw_type","is_principal","geometry"]].to_file(
    f"{INT}/streets_all.gpkg", layer="streets_all", driver="GPKG")
st[st.is_principal][["physicalid","rw_type","geometry"]].to_file(
    f"{INT}/streets_principal.gpkg", layer="streets_principal", driver="GPKG")
log("streets", "street_filter",
    f"raw={n_raw:,} -> STATUS=2 (Constructed) and inside frame -> {len(st):,}; "
    f"principal = RW_TYPE in {{2 Highway, 3 Bridge, 4 Tunnel, 9 Ramp}} = {int(st.is_principal.sum()):,}. "
    "CARTO_DISPLAY_LEVEL exists but is undocumented in the City's geo-metadata and was NOT used.")

# ---- subway ----------------------------------------------------------------
rt = prep(gpd.read_file(f"{RAW}/subway_routes.geojson"), "subway_routes")
rt = rt[rt.intersects(frame)].copy()
rt[[c for c in rt.columns if c == "geometry" or not c.startswith(":")][:8]].to_file(
    f"{INT}/subway_routes.gpkg", layer="subway_routes", driver="GPKG")
sn = gpd.read_file(f"{RAW}/subway_stations.geojson")
sn = prep(sn, "subway_stations")
sn = sn[sn.within(frame)].copy()
sn[["stop_name","borough","daytime_routes","geometry"]].to_file(
    f"{INT}/subway_stations.gpkg", layer="subway_stations", driver="GPKG")
log("transit", "subway",
    f"routes={len(rt)} (MTA vtcn-vhd8), stations={len(sn)} (MTA 39hk-dx4f); "
    "MTA service colours deliberately not used")

pd.DataFrame(qa).to_csv(f"{INT}/base_layer_audit.csv", index=False)
print("=== round 3 base layers ===")
for r in qa: print(f"  [{r['area']:<11}] {r['test']:<22} {r['detail']}")
print(f"\nwrote {INT}/base_layer_audit.csv")
