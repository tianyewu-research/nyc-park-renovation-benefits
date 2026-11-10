"""Round 4, step 3 — the two derived polygon layers.

5.1 governance_display_polygons : every mapped geometry is a polygon. The nine
    source gov_subtypes are preserved; a cartographic display_family of five is
    added. No centroids, representative points or triangles stand in for a space.

5.2 renovation_site_status      : matched site polygons dissolved to ONE row per
    site, so overlapping project records cannot darken a polygon. Completed and
    active are tracked as separate booleans because they are not mutually
    exclusive in the source.
"""
import os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd

R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
XW = "data/interim/atlas_round2/project_site_crosswalk.csv"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
OUT = "data/interim/atlas_round4"
CRS = "EPSG:2263"

FAMILY = {
    "NYC Parks property": "NYC Parks",
    "Other NYC agency public open space": "Other public parkland",
    "State or federal park": "Other public parkland",
    "Public authority or trust": "Other public parkland",
    "Zoning POPS": "Privately owned public access",
    "Restrictive-declaration public space": "Privately owned public access",
    "Privately owned public-access park, non-POPS": "Privately owned public access",
    "Community garden": "Community-managed green space",
    "DOT pedestrian plaza / BID-managed space": "Street-based public space",
}
FAMILY_ORDER = ["NYC Parks", "Other public parkland", "Privately owned public access",
                "Community-managed green space", "Street-based public space"]

# ---- 5.1 governance display polygons --------------------------------------
POLY_LAYERS = ["parks_properties", "other_public_open_space", "public_authority_or_trust",
               "restrictive_declaration_sites", "waterfront_public_access_areas",
               "dot_pedestrian_plazas", "community_gardens"]
parts = []
for l in POLY_LAYERS:
    g = gpd.read_file(R2, layer=l)
    g["geometry_role"] = "official_site_polygon"
    g["geometry_qa"] = "official register geometry for the designated space"
    parts.append(g[["Site_Key", "Site_Name", "Governance_Category", "geometry_role",
                    "geometry_qa", "geometry"]])
pp = gpd.read_file(f"{OUT}/pops_parcels.gpkg", layer="pops_parcels")
pp = pp.rename(columns={"source_site_id": "Site_Key", "source_site_name": "Site_Name",
                        "source_subtype": "Governance_Category"})
parts.append(pp[["Site_Key", "Site_Name", "Governance_Category", "geometry_role",
                 "geometry_qa", "geometry"]])
sf = gpd.read_file(f"{OUT}/state_federal_polygons.gpkg", layer="state_federal_polygons")
sf = sf.rename(columns={"role": "geometry_role", "qa": "geometry_qa"})
parts.append(sf[["Site_Key", "Site_Name", "Governance_Category", "geometry_role",
                 "geometry_qa", "geometry"]])

gov = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=CRS)
gov["gov_subtype"] = gov["Governance_Category"]
gov["display_family"] = gov["gov_subtype"].map(FAMILY)
assert gov["display_family"].notna().all()
bad = ~gov.geometry.is_valid
if bad.any(): gov.loc[bad, "geometry"] = gov.loc[bad, "geometry"].buffer(0)
gov = gov[~(gov.geometry.is_empty | gov.geometry.isna())]
npt = int(gov.geom_type.isin(["Point", "MultiPoint"]).sum())
assert npt == 0, f"{npt} point geometries leaked into the governance display layer"
gov.to_file(f"{OUT}/governance_display_polygons.gpkg",
            layer="governance_display_polygons", driver="GPKG")
print(f"governance_display_polygons: {len(gov)} polygons, 0 points")
print(gov["display_family"].value_counts().to_string())

# ---- 5.2 renovation site status -------------------------------------------
sp = gpd.read_file(R2, layer="renovation_site_polygons")
pi = pd.read_excel(WB, sheet_name="Project Inventory")
xw = pd.read_csv(XW, dtype={"BBL": str})
PH = {"completed": "completed", "construction": "construction",
      "procurement": "procurement", "design": "design",
      "design-procurement": "design", "proposed": "proposed_unknown"}
ph = pi.set_index("Map_ID")["Current_Phase"].map(PH).fillna("proposed_unknown")
sp["phase"] = sp["Map_ID"].map(ph)
sp["Tracker_ID"] = sp["Map_ID"].map(pi.set_index("Map_ID")["Tracker_ID"])
sp["display_site_key"] = (sp["Matched_Site_ID"].fillna("") + "|" + sp["Geometry_Role"].fillna(""))

agg = []
for key, grp in sp.groupby("display_site_key"):
    flags = {f"has_{p}": bool((grp.phase == p).any())
             for p in ("completed", "design", "procurement", "construction", "proposed_unknown")}
    active = ("Construction" if flags["has_construction"] else
              "Procurement" if flags["has_procurement"] else
              "Design" if flags["has_design"] else
              "Proposed/unknown" if flags["has_proposed_unknown"] else None)
    agg.append(dict(display_site_key=key,
        Matched_Site_ID=grp["Matched_Site_ID"].iloc[0],
        Geometry_Role=grp["Geometry_Role"].iloc[0],
        Geometry_Source=grp["Geometry_Source"].iloc[0],
        Geometry_Confidence=grp["Geometry_Confidence"].iloc[0],
        n_project_locations=len(grp), n_unique_tracker_ids=grp["Tracker_ID"].nunique(),
        map_ids="|".join(map(str, grp["Map_ID"])),
        tracker_ids="|".join(map(str, sorted(set(grp["Tracker_ID"].dropna())))),
        **flags,
        active_phase_display=active,
        phase_mix=";".join(f"{k}={v}" for k, v in grp.phase.value_counts().items()),
        geometry=grp.geometry.union_all()))
site = gpd.GeoDataFrame(pd.DataFrame(agg), geometry="geometry", crs=CRS)
bad = ~site.geometry.is_valid
if bad.any(): site.loc[bad, "geometry"] = site.loc[bad, "geometry"].buffer(0)
site.to_file(f"{OUT}/renovation_site_status.gpkg", layer="renovation_site_status",
             driver="GPKG")
assert int(site["n_project_locations"].sum()) == len(sp)
print(f"\nrenovation_site_status: {len(site)} dissolved sites from {len(sp)} site polygons")
print(f"  project locations conserved: {int(site.n_project_locations.sum())} == {len(sp)}")
print(f"  has_completed True: {int(site.has_completed.sum())}")
print("  active_phase_display:",
      site["active_phase_display"].value_counts(dropna=False).to_dict())
site.drop(columns="geometry").to_csv(f"{OUT}/renovation_site_status.csv", index=False)
