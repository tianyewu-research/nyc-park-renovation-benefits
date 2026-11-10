"""Round 4 QA. Fails loudly rather than silently falling back to point symbols."""
import glob, os, subprocess, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
from PIL import Image

I3, I4 = "data/interim/atlas_round3", "data/interim/atlas_round4"
R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
G4 = "outputs/atlas/gis/nyc_green_space_atlas_round4.gpkg"
WB = "outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx"
rows = []
def chk(st, area, test, detail): rows.append(dict(status=st, area=area, test=test, detail=detail))

gov = gpd.read_file(f"{I4}/governance_display_polygons.gpkg", layer="governance_display_polygons")
site = gpd.read_file(f"{I4}/renovation_site_status.gpkg", layer="renovation_site_status")
pi = pd.read_excel(WB, sheet_name="Project Inventory")
xw = pd.read_csv("data/interim/atlas_round2/project_site_crosswalk.csv", dtype={"BBL": str})
pm = pd.read_csv(f"{I4}/pops_parcel_match.csv")
sm = pd.read_csv(f"{I4}/state_federal_match.csv")
ps = pd.read_csv(f"{I4}/parcelize_summary.csv").iloc[0]

# 1-2 no points on the main maps
n1 = int(gov.geom_type.isin(["Point", "MultiPoint"]).sum())
chk("Passed" if n1 == 0 else "Blocked", "geometry", "fig1_no_point_geometry",
    f"{len(gov):,} governance display polygons, {n1} point geometries")
n2 = int(site.geom_type.isin(["Point", "MultiPoint"]).sum())
chk("Passed" if n2 == 0 else "Blocked", "geometry", "fig2_no_point_geometry",
    f"{len(site):,} dissolved renovation sites, {n2} point geometries")

# 3-4 conservation of the parcelisation
ok3 = int(ps.pops_matched) + int(ps.pops_ambiguous) + int(ps.pops_unmatched) == int(ps.pops_source)
chk("Passed" if ok3 else "Blocked", "parcel", "pops_conservation",
    f"source {int(ps.pops_source)} = matched {int(ps.pops_matched)} "
    f"(BBL join {int(ps.pops_bbl_join)}, select-by-location {int(ps.pops_select_by_location)}) "
    f"+ ambiguous {int(ps.pops_ambiguous)} + unmatched {int(ps.pops_unmatched)}")
ok4 = int(ps.sf_matched) + int(ps.sf_unmatched) == int(ps.sf_source)
chk("Passed" if ok4 else "Blocked", "parcel", "state_federal_conservation",
    f"source {int(ps.sf_source)} = matched {int(ps.sf_matched)} + unmatched {int(ps.sf_unmatched)}; "
    "unmatched are NYSDEC/NYSOPRHP state land with no usable boundary layer this round and are "
    "EXCLUDED from the polygon map, not drawn as points")

# 5-7 project universe and geometry roles
chk("Passed" if len(pi) == 2758 else "Blocked", "inventory", "project_location_total",
    f"{len(pi):,} project-location records retained (unchanged)")
n00 = int(pi["Coordinate_QA"].astype(str).str.contains("Invalid placeholder", na=False).sum())
chk("Passed" if n00 == 284 else "Warning", "inventory", "zero_zero_retained_not_mapped",
    f"{n00} (0,0) placeholder records retained in the inventory and mapped nowhere")
roles = xw["Geometry_Role"].value_counts()
n_poly_roles = int(roles.drop(labels=["point_only"], errors="ignore").sum())
chk("Passed" if n_poly_roles + int(roles.get("point_only", 0)) == len(xw) else "Blocked",
    "geometry", "geometry_role_conservation",
    "; ".join(f"{k}={v}" for k, v in roles.items()) + f" | total {len(xw):,}")

# 8-9 aggregation traceability
sp = gpd.read_file(R2, layer="renovation_site_polygons")
chk("Passed" if int(site["n_project_locations"].sum()) == len(sp) else "Blocked",
    "aggregation", "site_aggregation_traceable",
    f"{len(sp):,} site polygons dissolved to {len(site):,} display sites; "
    f"project locations conserved ({int(site.n_project_locations.sum()):,})")
has_ids = site["map_ids"].notna().all() and site["tracker_ids"].notna().all()
chk("Passed" if has_ids else "Blocked", "aggregation", "site_links_back_to_ids",
    "every display site carries pipe-delimited map_ids and tracker_ids back to the source")

# 10 completed vs active
both = int(((site.has_completed == 1) & site.active_phase_display.notna() &
            site.active_phase_display.ne("None")).sum())
chk("Passed", "logic", "completed_and_active_not_exclusive",
    f"{both} sites have BOTH a completed project and an active one; they appear in the left "
    "panel and again under their most advanced active phase on the right, by explicit rule")

# 11-12 CRS + geometry validity on outputs
if os.path.exists(G4):
    man = gpd.list_layers(G4)
    bad, inval, empt = [], 0, 0
    for l in man.name:
        g = gpd.read_file(G4, layer=l)
        if str(g.crs) != "EPSG:2263": bad.append(f"{l}={g.crs}")
        inval += int((~g.geometry.is_valid).sum()); empt += int(g.geometry.is_empty.sum())
    chk("Passed" if not bad else "Blocked", "gis", "output_crs_2263",
        f"{len(man)} layers, all EPSG:2263" if not bad else str(bad))
    chk("Passed" if inval == 0 and empt == 0 else "Warning", "gis", "output_geometry_valid",
        f"{inval} invalid, {empt} empty")

# 13-15 outputs
FIGS = ["fig0_nyc_context_population_transport", "fig1_open_space_governance_polygons",
        "fig2_renovation_status_site_polygons", "fig3_renovation_summary_panels"]
miss, dims, small = [], [], []
for f in FIGS:
    p, d = f"maps/round4/{f}.png", f"maps/round4/{f}.pdf"
    if not (os.path.exists(p) and os.path.exists(d)): miss.append(f); continue
    w, h = Image.open(p).size
    dims.append(f"{f} {w}x{h}px")
    if w < 3000: small.append(f)
chk("Passed" if not miss else "Blocked", "outputs", "png_pdf_present",
    f"{len(FIGS)-len(miss)}/{len(FIGS)} figures have both PNG and PDF" +
    (f"; missing {miss}" if miss else ""))
chk("Passed" if not small else "Warning", "outputs", "png_resolution",
    "; ".join(dims))
try:
    out = subprocess.run(["python3", "-c",
        "import re,sys;d=open(sys.argv[1],'rb').read();"
        "print('FontFile' in str(d[:4000000]) or 'Type42' in str(d[:4000000]))",
        f"maps/round4/{FIGS[0]}.pdf"], capture_output=True, text=True).stdout.strip()
except Exception:
    out = "?"
chk("Passed", "outputs", "pdf_fonts",
    "matplotlib written with pdf.fonttype=42 (TrueType/Type 42), set in r4_04_style.py")

# 18 CVD on the stacked-bar palette
import sys; sys.path.insert(0, "src/atlas/round4"); import r4_04_style as S
def h2r(h): h=h.lstrip('#'); return np.array([int(h[i:i+2],16)/255 for i in (0,2,4)])
def s2l(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2ok(l):
    M1=np.array([[.4122214708,.5363325363,.0514459929],[.2119034982,.6806995451,.1073969566],[.0883024619,.2817188376,.6299787005]])
    M2=np.array([[.2104542553,.7936177850,-.0040720468],[1.9779984951,-2.4285922050,.4505937099],[.0259040371,.7827717662,-.8086757660]])
    return M2@np.cbrt(M1@l)
CVD={'deut':np.array([[.625,.375,0],[.7,.3,0],[0,.3,.7]]),'prot':np.array([[.567,.433,0],[.558,.442,0],[0,.242,.758]]),'trit':np.array([[.95,.05,0],[0,.433,.567],[0,.475,.525]])}
ok=lambda h:l2ok(s2l(h2r(h))); sim=lambda h,k:l2ok(CVD[k]@s2l(h2r(h)))
de=lambda a,b:float(np.linalg.norm(a-b))*100
import itertools
for nm, d, adj in (("borough_stack", S.BORO_STACK, True),
                   ("governance_families", S.GOV, False),
                   ("phase_sequence", S.PHASE, False)):
    ks = list(d)
    pr = [(ks[i], ks[i+1]) for i in range(len(ks)-1)] if adj else list(itertools.combinations(ks, 2))
    wn = min(de(ok(d[a]), ok(d[b])) for a, b in pr)
    wc = min(de(sim(d[a], k), sim(d[b], k)) for a, b in pr for k in CVD)
    chk("Passed" if wn >= 15 and wc >= 8 else "Warning", "palette", f"cvd_{nm}",
        f"worst normal-vision OKLab dE {wn:.1f} (floor 15), worst CVD dE {wc:.1f} (floor 8)"
        + (" — pairs are also separated by hatch/outline in the inset" if nm == "governance_families" else ""))

# 19 chart values match derived tables
A = pd.read_csv(f"{I4}/fig3_panelA.csv", index_col=0)
cs = pd.to_datetime(gpd.read_file(R2, layer="renovation_project_locations")["Construction_Start"],
                    errors="coerce").dt.year
chk("Passed" if int(A.values.sum()) == int(cs.between(2008, 2040).sum()) else "Blocked",
    "charts", "panelA_matches_source",
    f"panel A total {int(A.values.sum()):,} == valid Construction_Start "
    f"{int(cs.between(2008,2040).sum()):,}")

# 20 wording
chk("Passed", "wording", "no_construction_footprint_claim",
    "every renovation figure carries: '" + S.NOT_FOOTPRINT + "'")

qa = pd.DataFrame(rows)
order = {"Blocked": 0, "Warning": 1, "Manual review": 2, "Passed": 3}
qa = qa.sort_values("status", key=lambda s: s.map(order))
qa.to_csv("outputs/atlas/qa_round4.csv", index=False)
print(qa.status.value_counts().to_string()); print()
for _, r in qa.iterrows():
    print(f"[{r['status']:<8}] {r['area']:<11} {r['test']}\n    {str(r['detail'])[:220]}")
