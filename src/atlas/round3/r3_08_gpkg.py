"""Round 3, step 8 — reusable GeoPackage of exactly the layers the figures use."""
import os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

INT = "data/interim/atlas_round3"
OUT = "outputs/atlas/gis/nyc_green_space_atlas_round3.gpkg"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
if os.path.exists(OUT): os.remove(OUT)

SRC = [("boroughs","boroughs"), ("population_bg_2023","population_bg_2023"),
       ("buildings_cartographic","buildings_cartographic"), ("streets_all","streets_all"),
       ("streets_principal","streets_principal"), ("subway_routes","subway_routes"),
       ("subway_stations","subway_stations"),
       ("green_space_governance","green_space_governance"),
       ("renovation_project_locations","renovation_project_locations")]
rows = []
for f, l in SRC:
    g = gpd.read_file(f"{INT}/{f}.gpkg", layer=l)
    assert str(g.crs) == "EPSG:2263", f"{l} not in EPSG:2263"
    for c in g.columns:
        if c != "geometry" and g[c].dtype == "object":
            g[c] = g[c].astype(str).replace({"nan": None, "None": None, "<NA>": None})
    g.to_file(OUT, layer=l, driver="GPKG")
    rows.append(dict(layer=l, features=len(g), crs=str(g.crs),
                     geom=",".join(sorted(map(str, g.geom_type.dropna().unique()))),
                     fields=len([c for c in g.columns if c != "geometry"])))
# site polygons are referenced in the caption but not drawn; include for reuse
sp = gpd.read_file("outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg",
                   layer="renovation_site_polygons")
for c in sp.columns:
    if c != "geometry" and sp[c].dtype == "object":
        sp[c] = sp[c].astype(str).replace({"nan": None, "None": None, "<NA>": None})
sp.to_file(OUT, layer="renovation_site_polygons", driver="GPKG")
rows.append(dict(layer="renovation_site_polygons", features=len(sp), crs=str(sp.crs),
                 geom="MultiPolygon", fields=len([c for c in sp.columns if c != "geometry"])))
pd.DataFrame(rows).to_csv(f"{INT}/round3_gpkg_manifest.csv", index=False)
print(f"wrote {OUT}")
for r in rows: print(f"  {r['layer']:<32} {r['features']:>7,}  {r['crs']}  {r['geom']}")
