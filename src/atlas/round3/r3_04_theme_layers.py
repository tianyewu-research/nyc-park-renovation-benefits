"""Round 3, step 4 — cartographic grouping for governance and renovation phase.

Source categories are NOT merged in the data. Two derived display fields are
added and documented; the original fields travel unchanged alongside them.

  gov_family    cartographic grouping of the 9 round-2 governance categories
                into 3 families (fill colour); gov_subtype keeps the original
  phase_display harmonisation of the raw Current_Phase values into 5 display
                classes; Current_Phase itself is untouched
"""
import os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
INT = "data/interim/atlas_round3"
CRS = "EPSG:2263"
qa = []

FAMILY = {
    "NYC Parks property": "public",
    "Other NYC agency public open space": "public",
    "State or federal park": "public",
    "Public authority or trust": "public",
    "Zoning POPS": "private_public",
    "Restrictive-declaration public space": "private_public",
    "Privately owned public-access park, non-POPS": "private_public",
    "DOT pedestrian plaza / BID-managed space": "private_public",
    "Community garden": "community",
}
GOV_LAYERS = ["parks_properties", "other_public_open_space", "public_authority_or_trust",
              "state_federal_open_space", "zoning_pops", "restrictive_declaration_sites",
              "waterfront_public_access_areas", "dot_pedestrian_plazas", "community_gardens"]

parts = []
before = {}
for l in GOV_LAYERS:
    g = gpd.read_file(R2, layer=l)
    cat = g["Governance_Category"].iloc[0]
    before[cat] = len(g)
    g["gov_subtype"] = g["Governance_Category"]
    g["gov_family"] = g["Governance_Category"].map(FAMILY)
    g["src_layer"] = l
    parts.append(g[["Site_Key", "Site_Name", "gov_subtype", "gov_family",
                    "src_layer", "geometry"]])
gov = pd.concat(parts, ignore_index=True)
gov = gpd.GeoDataFrame(gov, geometry="geometry", crs=CRS)
assert gov["gov_family"].notna().all(), "unmapped governance category"
gov.to_file(f"{INT}/green_space_governance.gpkg", layer="green_space_governance",
            driver="GPKG")
after = gov["gov_family"].value_counts().to_dict()
qa.append(dict(area="governance", test="grouping_before_after",
    detail="before (source categories): " + "; ".join(f"{k}={v}" for k, v in before.items()) +
           " | after (cartographic families): " + "; ".join(f"{k}={v}" for k, v in after.items()) +
           " | source categories retained in gov_subtype, nothing merged in the data"))

# ---- renovation phase display harmonisation -------------------------------
PHASE = {"completed": "Completed",
         "construction": "Construction",
         "procurement": "Procurement",
         "design": "Design / design-procurement",
         "design-procurement": "Design / design-procurement",
         "proposed": "Proposed / other / unknown"}
pts = gpd.read_file(R2, layer="renovation_project_locations")
pi = pd.read_excel(WB, sheet_name="Project Inventory")
raw_counts = pi["Current_Phase"].value_counts(dropna=False).to_dict()
pts["phase_display"] = pts["Current_Phase"].map(PHASE).fillna("Proposed / other / unknown")
xw = pd.read_csv("data/interim/atlas_round2/project_site_crosswalk.csv", dtype={"BBL": str})
pts = pts.merge(xw[["Map_ID", "Geometry_Role", "Geometry_Confidence"]], on="Map_ID", how="left")
pts.to_file(f"{INT}/renovation_project_locations.gpkg",
            layer="renovation_project_locations", driver="GPKG")
disp = pts["phase_display"].value_counts().to_dict()
qa.append(dict(area="phase", test="harmonisation_before_after",
    detail="raw Current_Phase (all 2,758 inventory rows): " +
           "; ".join(f"{k}={v}" for k, v in raw_counts.items()) +
           f" | display classes on {len(pts)} mapped points: " +
           "; ".join(f"{k}={v}" for k, v in disp.items()) +
           " | Current_Phase left unchanged in the source"))
qa.append(dict(area="phase", test="geometry_role_available",
    detail="; ".join(f"{k}={v}" for k, v in pts["Geometry_Role"].value_counts().items()) +
           " | citywide figure plots project-location POINTS over ownership polygons so a "
           "whole-park polygon cannot overstate a small intervention"))
pd.DataFrame(qa).to_csv(f"{INT}/theme_layer_qa.csv", index=False)
for r in qa: print(f"  [{r['area']}] {r['test']}\n     {r['detail'][:300]}")
