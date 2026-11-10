"""Round 4 GeoPackage — only the layers the four figures use."""
import os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd
I3, I4 = "data/interim/atlas_round3", "data/interim/atlas_round4"
OUT = "outputs/atlas/gis/nyc_green_space_atlas_round4.gpkg"
if os.path.exists(OUT): os.remove(OUT)
SRC = [(f"{I3}/boroughs.gpkg","boroughs"), (f"{I3}/population_bg_2023.gpkg","population_bg_2023"),
       (f"{I3}/buildings_cartographic.gpkg","buildings_cartographic"),
       (f"{I3}/streets_principal.gpkg","streets_principal"),
       (f"{I3}/subway_routes.gpkg","subway_routes"), (f"{I3}/subway_stations.gpkg","subway_stations"),
       (f"{I4}/governance_display_polygons.gpkg","governance_display_polygons"),
       (f"{I4}/renovation_site_status.gpkg","renovation_site_status"),
       (f"{I4}/pops_parcels.gpkg","pops_parcels"),
       (f"{I4}/state_federal_polygons.gpkg","state_federal_polygons")]
rows=[]
for f,l in SRC:
    g=gpd.read_file(f,layer=l); assert str(g.crs)=="EPSG:2263", f"{l} {g.crs}"
    for c in g.columns:
        if c!="geometry" and g[c].dtype=="object":
            g[c]=g[c].astype(str).replace({"nan":None,"None":None,"<NA>":None})
    g.to_file(OUT,layer=l,driver="GPKG")
    rows.append((l,len(g),str(g.crs),",".join(sorted(map(str,g.geom_type.dropna().unique())))))
print(f"wrote {OUT}")
for l,n,c,t in rows: print(f"  {l:<32} {n:>7,}  {c}  {t}")
pd.DataFrame(rows,columns=["layer","features","crs","geom"]).to_csv(
    f"{I4}/round4_gpkg_manifest.csv",index=False)
