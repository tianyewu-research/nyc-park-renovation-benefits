"""Round 2, stage 3 — auditable project-location -> site-polygon crosswalk.

Every candidate match is computed and recorded. Two separate outputs per row:

  Matched_Site_ID  site IDENTITY, resolved in the brief's order A -> G
  Geometry_Role    the most PRECISE geometry actually available, because the
                   Geometry_Role vocabulary is itself ordered by precision and a
                   whole Parks property must never stand in for a construction
                   footprint

Confidence is never inflated: a tax lot under a POPS is tax_lot_proxy, not a
POPS footprint; a CPDB polygon carries DCP's own caveat that some geometries
come from manual or fuzzy matching.
"""
import glob, json, os, re, urllib.parse, urllib.request, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2, OUT = "data/raw/atlas_round2", "data/interim/atlas_round2"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory.xlsx"
CRS = "EPSG:2263"
MAPPLUTO = ("https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/"
            "MAPPLUTO/FeatureServer/0/query")

def prep(g):
    g = g[~(g.geometry.is_empty | g.geometry.isna())].copy()
    bad = ~g.geometry.is_valid
    if bad.any():
        g.loc[bad, "geometry"] = g.loc[bad, "geometry"].buffer(0)
    return g.to_crs(CRS)

pi = pd.read_excel(WB, sheet_name="Project Inventory")
pts = gpd.read_file("outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg",
                    layer="renovation_project_locations")
print(f"project-location rows in inventory : {len(pi)}")
print(f"with a mappable point              : {len(pts)}")

parks = prep(gpd.read_file(sorted(glob.glob(
    "data/raw/park_boundaries/parks_properties_20260623/*.shp"))[-1]))
cpdb  = prep(gpd.read_file(f"{R2}/cpdb_project_polygons.geojson"))
pipp  = prep(gpd.read_file(f"{R2}/pip_all_sites_mapped.geojson"))
popsg = prep(gpd.read_file(sorted(glob.glob("data/raw/external_downloads/pops_*.geojson"))[-1]))
wpaa  = prep(gpd.read_file(f"{R2}/waterfront_public_access_areas.geojson"))
plaza = prep(gpd.read_file(f"{R2}/dot_pedestrian_plazas.geojson"))
rdecl = prep(gpd.read_file(f"{R2}/restrictive_declaration_sites.geojson"))

# ---- A  Park_ID -> Parks Properties ---------------------------------------
park_by_id = parks.set_index(parks["gispropnum"].astype(str))
A = pts["Park_ID"].astype(str).map(lambda k: k if k in park_by_id.index else None)

# ---- B  FMS_ID -> CPDB project polygon ------------------------------------
def fms_proj(s):
    s = str(s).strip().upper()
    m = re.match(r"^(\d{3})\s+(.+)$", s)
    return (m.group(2) if m else s).replace(" ", "")
cpdb["cp_pj"] = cpdb["projectid"].astype(str).str.upper().str.replace(" ", "", regex=False)
cpdb_by_pj = cpdb.drop_duplicates("cp_pj").set_index("cp_pj")
pts["_fms"] = pts["FMS_ID"].apply(fms_proj)
B = pts["_fms"].map(lambda k: k if k in cpdb_by_pj.index else None)

# ---- C  point within PIP sub-property polygon -----------------------------
# PIP sites nest: a park polygon contains its sub-site polygons, so a point
# lands inside several. Keep the SMALLEST containing polygon -- the most precise
# sub-site -- and record how many candidates there were.
pipp = pipp.reset_index(drop=True)
pipp["_area"] = pipp.geometry.area
jc = gpd.sjoin(pts[["geometry"]], pipp[["prop_id", "site_name", "_area", "geometry"]],
               how="left", predicate="within")
amb_c = jc.groupby(level=0).size()
jc = (jc.reset_index().sort_values(["index", "_area"])
        .drop_duplicates("index", keep="first").set_index("index"))
C = jc["prop_id"]
C_site = jc["site_name"]

# ---- D  official private/public-space geometries ---------------------------
D_LAYERS = [("zoning_pops", popsg, "pops_number"),
            ("wpaa", wpaa, "wpaa_id"),
            ("dot_plaza", plaza, "plazaname"),
            ("restrictive_declaration", rdecl, "gispropnum")]
D_src, D_id = pd.Series(index=pts.index, dtype=object), pd.Series(index=pts.index, dtype=object)
for nm, lyr, key in D_LAYERS:
    if key not in lyr.columns:
        continue
    j = gpd.sjoin(pts[["geometry"]], lyr[[key, "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    hit = j[key].notna() & D_src.isna()
    D_src.loc[hit] = nm
    D_id.loc[hit] = j.loc[hit, key].astype(str)

# ---- E  BBL -> MapPLUTO tax lot (targeted, never a bulk download) ----------
need_bbl = pts.index[D_src.eq("zoning_pops") | D_src.eq("restrictive_declaration")]
bbl_map = {}
if len(need_bbl):
    pops_bbl = popsg.set_index(popsg["pops_number"].astype(str))["bbl"].astype(str).to_dict() \
        if "bbl" in popsg.columns else {}
    wanted = sorted({bbl_map.setdefault(i, pops_bbl.get(str(D_id.get(i)), None))
                     for i in need_bbl} - {None})
    wanted = [w for w in wanted if w and w.isdigit()]
    print(f"MapPLUTO: requesting {len(wanted)} tax lots by BBL (no bulk download)")
    lots = []
    for i in range(0, len(wanted), 200):
        chunk = ",".join(wanted[i:i + 200])
        q = urllib.parse.urlencode({"where": f"BBL IN ({chunk})", "outFields": "BBL",
                                    "returnGeometry": "true", "outSR": "2263",
                                    "f": "geojson"})
        try:
            with urllib.request.urlopen(f"{MAPPLUTO}?{q}", timeout=180) as r:
                lots.append(gpd.GeoDataFrame.from_features(json.load(r)["features"], crs=CRS))
        except Exception as e:
            print(f"   BBL chunk {i}: {type(e).__name__}")
    plutos = pd.concat(lots, ignore_index=True) if lots else gpd.GeoDataFrame(
        columns=["BBL", "geometry"], geometry="geometry", crs=CRS)
    print(f"   received {len(plutos)} tax-lot polygons")
else:
    plutos = gpd.GeoDataFrame(columns=["BBL", "geometry"], geometry="geometry", crs=CRS)

# ---- assemble --------------------------------------------------------------
recs = []
for i, row in pts.iterrows():
    a, b, c = A.get(i), B.get(i), C.get(i)
    dsrc, did = D_src.get(i), D_id.get(i)
    if not isinstance(dsrc, str):
        dsrc, did = None, None          # sjoin fills misses with NaN, not None
    if not isinstance(a, str) or a in ("None", "nan"):
        a = None
    if not isinstance(b, str) or b in ("None", "nan"):
        b = None
    c = c if isinstance(c, str) and c not in ("None", "nan") else None
    bbl = bbl_map.get(i)
    if not isinstance(bbl, str):
        bbl = None
    # site identity: brief's order A -> G
    if a:            sid, sid_rule = f"PARK:{a}", "A park_id -> parks_properties"
    elif b:          sid, sid_rule = f"CPDB:{b}", "B fms_id -> cpdb projectid"
    elif c:          sid, sid_rule = f"PIP:{c}", "C point within pip sub-property"
    elif dsrc:       sid, sid_rule = f"{dsrc.upper()}:{did}", f"D point within {dsrc}"
    elif bbl:        sid, sid_rule = f"BBL:{bbl}", "E bbl -> mappluto tax lot"
    else:            sid, sid_rule = None, "G no site resolved"
    # geometry: most precise available
    if b:
        role, src, meth, conf = ("cpdb_project_polygon", "DCP CPDB 9jkp-n57r",
            "join on FMS projectid", "medium")
        qa = ("DCP states some CPDB geometries are produced by manual or fuzzy "
              "matching; treat as project extent, not surveyed footprint")
    elif c:
        role, src, meth, conf = ("pip_subsite_polygon", "NYC Parks PIP buk3-3qpr",
            "point-in-polygon", "medium")
        qa = "Sub-property extent, finer than the park but not the construction area"
    elif dsrc:
        role, src, meth, conf = ("park_property_polygon" if dsrc == "restrictive_declaration"
            else "park_property_polygon", f"official {dsrc} layer", "point-in-polygon", "medium")
        role = "park_property_polygon"
        qa = f"Official {dsrc} geometry; whole designated space, not the works area"
    elif a:
        role, src, meth, conf = ("park_property_polygon", "NYC Parks Properties enfh-gkve",
            "park_id join", "low")
        qa = ("WHOLE Parks property. Must NOT be read as a construction footprint; "
              "most capital work occupies part of a property")
    elif bbl:
        role, src, meth, conf = ("tax_lot_proxy", "DCP MapPLUTO feature service",
            "bbl join", "low")
        qa = "Tax lot under the space, NOT the public-space footprint"
    else:
        role, src, meth, conf = ("point_only", "Capital Project Tracker",
            "administrative point", "low")
        qa = "No site polygon could be resolved; point retained, nothing fabricated"
    recs.append(dict(
        Map_ID=row.get("Map_ID"), Project_Location_ID=row.get("Project_Location_ID"),
        Tracker_ID=row.get("Tracker_ID"), FMS_ID=row.get("FMS_ID"),
        Park_ID=row.get("Park_ID"), Matched_Site_ID=sid, Site_ID_Rule=sid_rule,
        Geometry_Role=role, Geometry_Source=src, Geometry_Method=meth,
        Geometry_Confidence=conf, Geometry_QA=qa, BBL=bbl,
        Match_Distance_Ft=0.0 if role != "point_only" else pd.NA,
        Match_Ambiguity_Count=int(amb_c.get(i, 1)),
        Cand_A_park=a, Cand_B_cpdb=b, Cand_C_pip=c, Cand_D_layer=dsrc))

xw = pd.DataFrame(recs)
xw.to_csv(f"{OUT}/project_site_crosswalk.csv", index=False)
need = xw[(xw.Geometry_Role.isin(["point_only", "tax_lot_proxy"])) |
          (xw.Match_Ambiguity_Count > 1) | (xw.Matched_Site_ID.isna())]
need.to_csv(f"{OUT}/geometry_match_manual_review.csv", index=False)

print("\n=== Geometry_Role ===")
print(xw["Geometry_Role"].value_counts().to_string())
print("\n=== Site identity rule ===")
print(xw["Site_ID_Rule"].value_counts().to_string())
print(f"\nambiguous (point in >1 PIP polygon): {int((xw.Match_Ambiguity_Count>1).sum())}")
print(f"manual review rows: {len(need)} -> {OUT}/geometry_match_manual_review.csv")
print(f"crosswalk rows: {len(xw)} (expected {len(pts)})")
