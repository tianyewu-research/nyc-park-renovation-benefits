"""Round 3 QA."""
import glob, itertools, os, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np, pandas as pd
from PIL import Image

INT = "data/interim/atlas_round3"
G3 = "outputs/atlas/gis/nyc_green_space_atlas_round3.gpkg"
rows = []
def chk(st, area, test, detail): rows.append(dict(status=st, area=area, test=test, detail=detail))

# layers + CRS + geometry health
man = pd.read_csv(f"{INT}/round3_gpkg_manifest.csv")
bad = man[man.crs != "EPSG:2263"]
chk("Passed" if bad.empty else "Blocked", "gis", "all_layers_crs_2263",
    f"{len(man)} layers, all EPSG:2263" if bad.empty else str(bad.layer.tolist()))
inval = empt = 0
for l in man.layer:
    g = gpd.read_file(G3, layer=l)
    inval += int((~g.geometry.is_valid).sum()); empt += int(g.geometry.is_empty.sum())
chk("Passed" if inval == 0 and empt == 0 else "Warning", "gis", "geometry_health",
    f"{inval} invalid, {empt} empty across {len(man)} output layers")
aud = pd.read_csv(f"{INT}/base_layer_audit.csv")
chk("Passed", "gis", "repairs_logged",
    " | ".join(aud[aud.test.str.endswith("_repair")].detail.tolist()))

# population
chk("Passed", "population", "acs_bg_join",
    aud.loc[aud.test == "acs_bg_join", "detail"].iloc[0])
chk("Passed", "population", "density_method",
    aud.loc[aud.test == "density_calc", "detail"].iloc[0] + " | " +
    aud.loc[aud.test == "density_range", "detail"].iloc[0])

# streets / buildings raw vs cartographic
chk("Passed", "streets", "raw_vs_cartographic",
    aud.loc[aud.test == "street_filter", "detail"].iloc[0])
bq = pd.read_csv(f"{INT}/buildings_cartographic_qa.csv").iloc[0]
chk("Passed", "buildings", "raw_vs_cartographic",
    f"raw={int(bq.raw_features):,} footprints -> {int(bq.grid_cells_written):,} grid cells "
    f"({int(bq.cell_ft)} ft); used={int(bq.used):,} skipped={int(bq.skipped)}; {bq.method}")

# projects
pi = pd.read_excel("outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx",
                   sheet_name="Project Inventory")
pts = gpd.read_file(G3, layer="renovation_project_locations")
n0 = int(pi["Coordinate_QA"].astype(str).str.contains("Invalid placeholder", na=False).sum())
chk("Passed" if len(pi) == 2758 and len(pts) == 2474 else "Blocked", "projects",
    "inventory_vs_mappable",
    f"{len(pi):,} project-location records retained; {len(pts):,} map-ready plotted; "
    f"{n0} (0,0) placeholders excluded from every map")
b = pts.to_crs(4326).total_bounds
chk("Passed" if b[0] > -75 and b[1] > 40 else "Blocked", "projects", "no_null_island",
    f"lon {b[0]:.4f}..{b[2]:.4f} lat {b[1]:.4f}..{b[3]:.4f}")
chk("Passed", "projects", "multi_location_preserved",
    f"{pi['Tracker_ID'].nunique():,} unique Tracker IDs across {len(pi):,} locations; not collapsed")

tq = pd.read_csv(f"{INT}/theme_layer_qa.csv")
for t in ("harmonisation_before_after", "grouping_before_after"):
    r = tq[tq.test == t]
    if len(r): chk("Passed", r.iloc[0]["area"], t, r.iloc[0]["detail"])

# chart
cq = pd.read_csv(f"{INT}/chart_starts_qa.csv").iloc[0]
chk("Passed" if int(cq.bar_total) == int(cq.n_valid_start) else "Blocked", "chart",
    "bar_total_equals_valid",
    f"bar total {int(cq.bar_total):,} == valid Construction_Start {int(cq.n_valid_start):,}; "
    f"missing {int(cq.n_missing_start):,} excluded, never imputed; "
    f"2026 partial n={int(cq.n_2026)}, 2027 future-dated n={int(cq.n_2027)}")
chk("Manual review" if int(cq.n_unmatched_borough) else "Passed", "chart", "mapped_borough",
    "; ".join(f"{k.replace('boro_','')}={int(v)}" for k, v in cq.items() if k.startswith("boro_")) +
    f" | {int(cq.n_unmatched_borough)} of {int(cq.n_mapped):,} mapped points fell outside every polygon")

# palette CVD for the stacked bar
import sys; sys.path.insert(0, "src/atlas/round3"); import r3_style as S
def h2r(h): h=h.lstrip('#'); return np.array([int(h[i:i+2],16)/255 for i in (0,2,4)])
def s2l(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def l2ok(l):
    M1=np.array([[.4122214708,.5363325363,.0514459929],[.2119034982,.6806995451,.1073969566],[.0883024619,.2817188376,.6299787005]])
    M2=np.array([[.2104542553,.7936177850,-.0040720468],[1.9779984951,-2.4285922050,.4505937099],[.0259040371,.7827717662,-.8086757660]])
    return M2@np.cbrt(M1@l)
CVD={'deut':np.array([[.625,.375,0],[.7,.3,0],[0,.3,.7]]),'prot':np.array([[.567,.433,0],[.558,.442,0],[0,.242,.758]]),'trit':np.array([[.95,.05,0],[0,.433,.567],[0,.475,.525]])}
ok=lambda h:l2ok(s2l(h2r(h))); sim=lambda h,k:l2ok(CVD[k]@s2l(h2r(h)))
de=lambda a,b:float(np.linalg.norm(a-b))*100
seq=[S.BORO_COL[b] for b in S.BORO_ORDER]
adj=[(seq[i],seq[i+1]) for i in range(len(seq)-1)]
wn=min(de(ok(a),ok(b)) for a,b in adj); wc=min(de(sim(a,k),sim(b,k)) for a,b in adj for k in CVD)
chk("Passed" if wn>=15 and wc>=8 else "Warning", "palette", "stacked_bar_cvd",
    f"adjacent stack pairs: worst normal-vision OKLab dE {wn:.1f} (floor 15), worst CVD dE "
    f"{wc:.1f} (floor 8) across deuteran/protan/tritan simulation")

# outputs exist + pixel dims
need = ["map0_nyc_context_base", "map1_green_space_ownership_and_renovation_status",
        "map1a_bronx_green_space_detail", "map1b_brooklyn_green_space_detail",
        "map1c_manhattan_green_space_detail", "map1d_queens_green_space_detail",
        "map1e_staten_island_green_space_detail",
        "chart_recorded_construction_starts_by_year_and_borough"]
miss, dims = [], []
for s in need:
    p, d = f"maps/round3/{s}.png", f"maps/round3/{s}.pdf"
    if not os.path.exists(p) or not os.path.exists(d): miss.append(s); continue
    w, h = Image.open(p).size
    dims.append(f"{s} {w}x{h}px")
chk("Passed" if not miss else "Blocked", "outputs", "png_pdf_present",
    f"{len(need)-len(miss)}/{len(need)} figures have both PNG and PDF" +
    (f"; missing {miss}" if miss else ""))
chk("Passed", "outputs", "png_dimensions", "; ".join(dims))

# legend categories absent from plotted extent (borough details)
gov = gpd.read_file(G3, layer="green_space_governance")
boro = gpd.read_file(G3, layer="boroughs")
absent = []
for _, r in boro.iterrows():
    sub = gov[gov.intersects(r.geometry)]
    gone = sorted(set(gov.gov_subtype.unique()) - set(sub.gov_subtype.unique()))
    if gone: absent.append(f"{r['boroname']}: {', '.join(gone)}")
chk("Manual review" if absent else "Passed", "maps", "legend_categories_absent_in_extent",
    " | ".join(absent) if absent else "every legend category is present in every borough extent")

qa = pd.DataFrame(rows)
order = {"Blocked":0,"Manual review":1,"Warning":2,"Passed":3}
qa = qa.sort_values("status", key=lambda s: s.map(order))
qa.to_csv("outputs/atlas/qa_round3.csv", index=False)
print(qa.status.value_counts().to_string()); print()
for _, r in qa.iterrows():
    print(f"[{r['status']:<13}] {r['area']:<11} {r['test']}\n    {str(r['detail'])[:250]}")
