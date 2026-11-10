"""Round 2, stage 5 — GeoPackage, 4326 share copies, Shapefile set, QML styles."""
import os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

OUT = "data/interim/atlas_round2"
GIS = "outputs/atlas/gis"
GPKG = f"{GIS}/nyc_green_space_renovation_atlas_round2.gpkg"
SHARE, SHP, QML = f"{GIS}/share_4326", f"{GIS}/shapefile_2263", f"{GIS}/styles"
for d in (SHARE, SHP, QML): os.makedirs(d, exist_ok=True)

GOV = ["boroughs","nta2020","parks_properties","other_public_open_space",
       "public_authority_or_trust","state_federal_open_space","community_gardens",
       "zoning_pops","restrictive_declaration_sites","dot_pedestrian_plazas",
       "waterfront_public_access_areas"]
layers = {k: gpd.read_file(f"{OUT}/gov_{k}.gpkg", layer=k) for k in GOV}
layers["renovation_site_polygons"] = gpd.read_file(f"{OUT}/renovation_site_polygons.gpkg",
                                                   layer="renovation_site_polygons")
layers["unmatched_project_points"] = gpd.read_file(f"{OUT}/unmatched_project_points.gpkg",
                                                   layer="unmatched_project_points")
layers["renovation_project_locations"] = gpd.read_file(
    "outputs/atlas/gis/nyc_green_space_renovation_atlas.gpkg",
    layer="renovation_project_locations")

wb = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
pi = pd.read_excel(wb, sheet_name="Project Inventory")
kc = pi[pi["Key_Case_Flag"].astype(str).ne("") & pi["Key_Case_Flag"].notna()]
rpl = layers["renovation_project_locations"]
layers["key_case_projects"] = rpl[rpl["Map_ID"].isin(kc["Map_ID"])].merge(
    kc[["Map_ID","Map_Label_No","Ownership_Model","Key_Case_Flag","Profile_Rationale",
        "Funding_Exact_USD","Administrative_Completion_Date"]], on="Map_ID", how="left")

xwalk = pd.read_csv(f"{OUT}/project_site_crosswalk.csv", dtype={"BBL": str})

if os.path.exists(GPKG): os.remove(GPKG)
rows = []
for nm, g in layers.items():
    g = g.copy()
    for c in g.columns:
        if c != "geometry" and g[c].dtype == "object":
            g[c] = g[c].astype(str).replace({"nan": None, "NaT": None, "<NA>": None})
    g.to_file(GPKG, layer=nm, driver="GPKG")
    g.to_crs(4326).to_file(f"{SHARE}/{nm}.geojson", driver="GeoJSON")
    rows.append((nm, len(g), str(g.crs), ",".join(sorted(map(str, g.geom_type.dropna().unique())))))
xwalk.to_file if False else None
import sqlite3
xwalk.to_sql("project_site_crosswalk", sqlite3.connect(GPKG), if_exists="replace", index=False)
rows.append(("project_site_crosswalk (table)", len(xwalk), "n/a", "non-spatial"))

# Shapefile set + truncation crosswalk
fx = []
for nm, g in layers.items():
    gg = g.copy()
    ren = {}
    for c in [c for c in gg.columns if c != "geometry"]:
        t = c[:10]
        i = 1
        while t in ren.values():
            t = f"{c[:8]}{i}"; i += 1
        ren[c] = t
        fx.append({"layer": nm, "original_field": c, "shapefile_field": t,
                   "truncated": c != t})
    gg.rename(columns=ren).to_file(f"{SHP}/{nm}.shp")
pd.DataFrame(fx).to_csv(f"{SHP}/field_name_crosswalk.csv", index=False)

# QML styles (hand-written; no QGIS on this machine)
def qml(fill, stroke, style="solid", width="0.26"):
    return f"""<!DOCTYPE qgis><qgis version="3.28" styleCategories="Symbology">
 <renderer-v2 type="singleSymbol"><symbols><symbol type="fill" name="0">
 <layer class="SimpleFill"><Option type="Map">
 <Option name="color" type="QString" value="{fill}"/>
 <Option name="outline_color" type="QString" value="{stroke}"/>
 <Option name="outline_width" type="QString" value="{width}"/>
 <Option name="style" type="QString" value="{style}"/>
 </Option></layer></symbol></symbols></renderer-v2></qgis>"""
STY = {"parks_properties": ("62,127,112,255","255,255,255,255"),
       "other_public_open_space": ("108,155,160,255","255,255,255,255"),
       "public_authority_or_trust": ("108,155,160,255","27,27,26,255"),
       "state_federal_open_space": ("62,127,112,255","27,27,26,255"),
       "zoning_pops": ("218,144,104,255","255,255,255,255"),
       "restrictive_declaration_sites": ("218,144,104,255","27,27,26,255"),
       "waterfront_public_access_areas": ("218,144,104,255","122,48,19,255"),
       "dot_pedestrian_plazas": ("196,121,81,255","255,255,255,255"),
       "community_gardens": ("243,216,186,255","122,48,19,255"),
       "renovation_site_polygons": ("192,96,47,255","255,255,255,255"),
       "boroughs": ("243,244,239,255","255,255,255,255"),
       "nta2020": ("243,244,239,0","201,204,198,255")}
for nm, (f_, s_) in STY.items():
    open(f"{QML}/{nm}.qml", "w").write(qml(f_, s_))

print("=== round 2 GeoPackage ===")
for nm, n, crs, gt in rows: print(f"  {nm:<34} {n:>6}  {crs:<10} {gt}")
print(f"\nGPKG   {GPKG}")
print(f"4326   {SHARE}/  ({len(layers)} GeoJSON)")
print(f"SHP    {SHP}/  + field_name_crosswalk.csv "
      f"({int(pd.DataFrame(fx)['truncated'].sum())} fields truncated)")
print(f"QML    {QML}/  ({len(STY)} styles)")
print("\nNo .qgz written: QGIS is not installed on this machine and a project file "
      "will not be fabricated. ArcGIS Pro reads the GPKG directly; no ArcPy, so no .lyrx.")
