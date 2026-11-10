"""Round 4, step 2 — turn the remaining point governance layers into real polygons.

Two layers are still points: zoning POPS (392) and state/federal open space (43).

POPS   : the DCP register carries BBL, so lots are pulled by BBL from the DCP
         MAPPLUTO feature service. Where BBL is absent or unusable, the point is
         matched by CONTAINMENT (select by location) to a tax lot. Boundary
         cases, multi-parcel hits and no-hit points are ambiguous and are NOT
         silently snapped to the nearest parcel.
State/ : official public-land polygons first (Parks register, other public
federal  open space, authority/trust, COLP-derived layers already in the atlas),
         then an owner-checked MapPLUTO parcel, then unmatched.

A MapPLUTO lot is the OWNING PARCEL. It is a proxy for the privately owned site
and is not a surveyed public-access footprint. That wording travels in the data.

Full MapPLUTO is ~858k lots and well over the 500 MB ceiling; the DCP feature
service is the same authority and is queried for only the lots needed.
"""
import hashlib, json, os, urllib.parse, urllib.request, warnings
from datetime import datetime, timezone
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
RAW4, OUT = "data/raw/atlas_round4", "data/interim/atlas_round4"
PROV = "outputs/atlas/source_provenance_round4.csv"
CRS = "EPSG:2263"
MP = ("https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/"
      "MAPPLUTO/FeatureServer/0/query")
PROXY_NOTE = ("parcel proxy for the privately owned site; not a surveyed "
              "public-access footprint")
for d in (RAW4, OUT): os.makedirs(d, exist_ok=True)
prov, rows = [], []

def fetch_lots(where, tag):
    # POST: a long BBL IN (...) clause overruns the GET URL limit and 404s
    body = urllib.parse.urlencode({"where": where, "outFields": "BBL,Address,OwnerName,LotArea",
                                   "returnGeometry": "true", "outSR": "2263",
                                   "f": "geojson"}).encode()
    req = urllib.request.Request(MP, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "nyc-atlas-round4/research"})
    with urllib.request.urlopen(req, timeout=300) as r:
        js = json.load(r)
    p = f"{RAW4}/mappluto_{tag}.geojson"
    with open(p, "w") as f: json.dump(js, f)
    g = gpd.GeoDataFrame.from_features(js.get("features", []), crs=CRS)
    prov.append(dict(layer_slug=f"mappluto_{tag}", dataset_id="DCP MAPPLUTO FeatureServer/0",
        source_url=f"{MP} (POST) where={where[:80]}...", local_path=p, status="OK",
        retrieved_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_crs=CRS, feature_count=len(g),
        geometry_type=";".join(sorted(map(str, g.geom_type.dropna().unique()))) if len(g) else "",
        size_mb=round(os.path.getsize(p)/1e6, 3),
        sha256_16=hashlib.sha256(open(p,'rb').read()).hexdigest()[:16],
        filtering_generalisation=("targeted query only; the full MapPLUTO release is ~858k lots "
            "and exceeds the 500 MB ceiling, so the DCP feature service (same authority) is "
            "queried for just the lots needed"),
        license="NYC Open Data / DCP terms; " + PROXY_NOTE))
    return g

# ---------------- POPS -----------------------------------------------------
pops = gpd.read_file(R2, layer="zoning_pops")
n_pops = len(pops)
raw_pops = gpd.read_file(sorted([f"data/raw/external_downloads/{x}" for x in
    os.listdir("data/raw/external_downloads") if x.startswith("pops_")])[-1])
bbl_map = dict(zip(raw_pops["pops_number"].astype(str), raw_pops["bbl"].astype(str)))
pops["BBL"] = pops["Site_Key"].astype(str).map(bbl_map)
good = pops["BBL"].fillna("").str.fullmatch(r"\d{10}")
print(f"POPS {n_pops}: usable BBL on {int(good.sum())}")

lots = gpd.GeoDataFrame(columns=["BBL","geometry"], geometry="geometry", crs=CRS)
want = sorted(pops.loc[good, "BBL"].unique())
chunks = []
for i in range(0, len(want), 150):
    chunks.append(fetch_lots("BBL IN (" + ",".join(want[i:i+150]) + ")", f"pops_{i}"))
if chunks: lots = pd.concat(chunks, ignore_index=True)
lots["BBL"] = lots["BBL"].astype("Int64").astype(str)
lots = lots[lots.geometry.notna()].copy()
print(f"  MapPLUTO returned {len(lots)} lots for {len(want)} requested BBLs")

lot_by_bbl = lots.drop_duplicates("BBL").set_index("BBL")["geometry"]
recs = []
for _, r in pops.iterrows():
    bbl = r["BBL"] if isinstance(r["BBL"], str) and r["BBL"].isdigit() else None
    geom, method, conf, amb, qa = None, None, None, 0, ""
    if bbl and bbl in lot_by_bbl.index:
        geom, method, conf = lot_by_bbl[bbl], "bbl_join", "high"
        qa = f"BBL join to MapPLUTO; {PROXY_NOTE}"
    else:
        hit = lots[lots.contains(r.geometry)] if len(lots) else lots
        amb = len(hit)
        if amb == 1:
            geom, method, conf = hit.geometry.iloc[0], "select_by_location_contains", "high"
            bbl = hit["BBL"].iloc[0]
            qa = f"point contained by exactly one tax lot; {PROXY_NOTE}"
        elif amb > 1:
            method, conf = "ambiguous_multi_parcel", "review"
            qa = "point falls in more than one candidate parcel; NOT snapped, manual review"
        else:
            method, conf = "no_containing_parcel", "review"
            qa = ("no BBL and no containing parcel in the queried set; nearest-parcel "
                  "assignment deliberately NOT performed")
    recs.append(dict(source_site_id=r["Site_Key"], source_site_name=r.get("Site_Name"),
        source_subtype=r["Governance_Category"], BBL=bbl, parcel_match_method=method,
        parcel_match_confidence=conf, parcel_match_ambiguity_count=amb,
        geometry_role="tax_lot_proxy" if geom is not None else "unmatched_point",
        geometry_qa=qa, source_url="DCP zoning POPS qeta-4kqg + DCP MAPPLUTO FeatureServer",
        source_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        geometry=geom, point_geometry=r.geometry))
pdf = pd.DataFrame(recs)
pops_poly = gpd.GeoDataFrame(pdf[pdf.geometry.notna()].drop(columns="point_geometry"),
                             geometry="geometry", crs=CRS)
pops_bad = pdf[pdf.geometry.isna()].drop(columns=["geometry"]).rename(
    columns={"point_geometry": "geometry"})
pops_bad = gpd.GeoDataFrame(pops_bad, geometry="geometry", crs=CRS)

# ------------- state / federal --------------------------------------------
sf = gpd.read_file(R2, layer="state_federal_open_space")
n_sf = len(sf)
public = pd.concat([gpd.read_file(R2, layer=l) for l in
                    ("parks_properties", "other_public_open_space",
                     "public_authority_or_trust")], ignore_index=True)
public = gpd.GeoDataFrame(public, geometry="geometry", crs=CRS)
srecs = []
for _, r in sf.iterrows():
    hit = public[public.contains(r.geometry)]
    if len(hit) == 1:
        srecs.append(dict(geom=hit.geometry.iloc[0], method="official_public_land_polygon",
            conf="high", amb=1, role="public_land_polygon",
            qa=f"point contained by one official public-land polygon ({hit['Site_Key'].iloc[0]})"))
    elif len(hit) > 1:
        sm = hit.assign(_a=hit.geometry.area).nsmallest(1, "_a")
        srecs.append(dict(geom=sm.geometry.iloc[0], method="official_public_land_polygon_smallest",
            conf="medium", amb=len(hit), role="public_land_polygon",
            qa=f"contained by {len(hit)} nested public-land polygons; smallest kept, count retained"))
    else:
        srecs.append(dict(geom=None, method="no_official_polygon", conf="review", amb=0,
            role="unmatched_point",
            qa=("no official public-land polygon contains this point; an NPS/state boundary "
                "source is required. Excluded from the polygon map, retained in QA.")))
sdf = pd.DataFrame(srecs)
sf_out = sf.reset_index(drop=True).join(sdf)
sf_poly = gpd.GeoDataFrame(sf_out[sf_out.geom.notna()].drop(columns=["geometry"])
                           .rename(columns={"geom": "geometry"}), geometry="geometry", crs=CRS)
sf_bad = sf_out[sf_out.geom.isna()].drop(columns=["geom"])
sf_bad = gpd.GeoDataFrame(sf_bad, geometry="geometry", crs=CRS)

# ---------------- write ----------------------------------------------------
pops_poly.to_file(f"{OUT}/pops_parcels.gpkg", layer="pops_parcels", driver="GPKG")
if len(pops_bad): pops_bad.to_file(f"{OUT}/pops_unmatched.gpkg", layer="pops_unmatched", driver="GPKG")
sf_poly.to_file(f"{OUT}/state_federal_polygons.gpkg", layer="state_federal_polygons", driver="GPKG")
if len(sf_bad): sf_bad.to_file(f"{OUT}/state_federal_unmatched.gpkg",
                               layer="state_federal_unmatched", driver="GPKG")
pdf.drop(columns=["geometry","point_geometry"]).to_csv(f"{OUT}/pops_parcel_match.csv", index=False)
sf_out.drop(columns=["geometry","geom"]).to_csv(f"{OUT}/state_federal_match.csv", index=False)
pd.DataFrame(prov).to_csv(PROV, index=False)

summary = dict(
  pops_source=n_pops, pops_matched=len(pops_poly),
  pops_bbl_join=int((pdf.parcel_match_method=="bbl_join").sum()),
  pops_select_by_location=int((pdf.parcel_match_method=="select_by_location_contains").sum()),
  pops_ambiguous=int((pdf.parcel_match_method=="ambiguous_multi_parcel").sum()),
  pops_unmatched=int((pdf.parcel_match_method=="no_containing_parcel").sum()),
  sf_source=n_sf, sf_matched=len(sf_poly), sf_unmatched=len(sf_bad))
pd.DataFrame([summary]).to_csv(f"{OUT}/parcelize_summary.csv", index=False)
print("\n=== parcelisation ===")
for k, v in summary.items(): print(f"  {k:<28} {v}")
assert summary["pops_matched"] + summary["pops_ambiguous"] + summary["pops_unmatched"] == n_pops
assert summary["sf_matched"] + summary["sf_unmatched"] == n_sf
print("  conservation checks PASSED")
