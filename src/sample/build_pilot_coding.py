"""Pilot coding v0 (draft, 2026-10-05). All values require TW verification."""
import pandas as pd, pathlib
R = pathlib.Path(__file__).resolve().parents[2]
s = pd.read_csv(R/"data/interim/sample/sample_list_v1.csv", dtype=str)
IDS = ["8872", "7277", "8882", "1482111", "1534111"]
AM = ["am_play","am_spray","am_sports_surface","am_courts","am_track","am_fitness","am_seating","am_shade_trees",
      "am_lighting","am_paths_entrances","am_accessibility","am_restroom_building","am_planting_gi","am_fencing"]
TR = "https://www.nycgovparks.org/planning-and-building/capital-project-tracker/project/"
U = dict(
 hs_pr="https://prd2.nycgovparks.org/news/press-releases?id=22195",
 sk_news="https://php1-84.nycgovparks.org/parks/sankofa-park/news",
 sk_hist="https://php1-84.nycgovparks.org/parks/B261/history",
 sk_bp="https://www.brooklynpaper.com/east-new-york-park-overhaul-community/",
 se_pr="https://php-cms.nycgovparks.org/news/press-releases?id=22214",
 se_bx="https://www.bxtimes.com/parks-dept-officially-opens-new-skate-park-and-fitness-area-at-seton-park",
 se_rp="https://riverdalepress.com/stories/adult-fitness-area-and-skate-park-coming-to-seton-park,129178",
 hero="https://php1-84.nycgovparks.org/parks/R011",
 escr="https://www.nyc.gov/assets/escr/downloads/pdf/20231213_escr_cb3_parks.pdf")
def am(**kw):
    d = {a: "NM" for a in AM}; d.update({f"am_{k}": v for k, v in kw.items()}); return d
P = {
"8872": dict(eligible="yes", multi_site="no", non_dpr_overlap="unknown", scope_extent="whole_site", area_share="NA",
  title_verb="reconstruction", primary_type="playground", layout_change="unknown", entrance_change="unknown",
  target_users="children_0_5; children_5_12 (stated); adults_fitness (stated)", community_request="unknown",
  funding_sources_named="City Council; Queens Borough President (Katz)", reopening_date_reported="ribbon cutting announced 2024-10-28",
  co_works="", am_other="drinking fountains ADD/CHG; bike racks ADD (M)", evidence_status="as-built",
  **am(play="UPG|M", spray="CHG|M", fitness="UPG|M", seating="UPG|M", shade_trees="CHG|L", paths_entrances="UPG|M",
       accessibility="CHG|L", planting_gi="UPG|L")),
"7277": dict(eligible="yes", multi_site="no", non_dpr_overlap="unknown", scope_extent="whole_site", area_share="NA",
  title_verb="reconstruction", primary_type="multi_element; commemorative", layout_change="yes", entrance_change="unknown",
  target_users="children (inferred); teens_athletes (inferred); general", community_request="partial (2019 reinterment ceremony; no design meetings found)",
  funding_sources_named="CM Barron; Brooklyn BP; Mayor; NY State", reopening_date_reported="not found",
  co_works="electrical, drainage, paving", am_other="African Burial Ground commemorative area ADD (oval lawn, stone assembly area, granite marker, interpretive signage)",
  evidence_status="planned (all sources at construction start, Nov 2023)",
  **am(play="UPG|M", courts="CHG|M", seating="CHG|M", restroom_building="UPG|M", fencing="CHG|M", paths_entrances="CHG|L", planting_gi="CHG|L")),
"8882": dict(eligible="yes", multi_site="no", non_dpr_overlap="unknown", scope_extent="single_area", area_share="NA",
  title_verb="construction", primary_type="new_amenity", layout_change="yes", entrance_change="unknown",
  target_users="teens_athletes (skate, inferred); adults_fitness (stated); children (multi-use space, stated); all ages (stated)",
  community_request="yes (stated by Parks)", funding_sources_named="City Council; Bronx BP; Mayor; NYS DASNY grant",
  reopening_date_reported="completion announced 2025-01-31; ribbon cutting postponed",
  co_works="drainage, water supply (pre-construction source only)", am_other="skate park ADD coded under sports_surface; water fountain w/ bottle filler; trash receptacles",
  evidence_status="as-built",
  **am(sports_surface="ADD|H", fitness="ADD|M", play="ADD|M", seating="CHG|M", shade_trees="CHG|M", lighting="CHG|M", accessibility="UPG|M", restroom_building="NM")),
"1482111": dict(eligible="yes", multi_site="no", non_dpr_overlap="likely (ESCR, DDC-led, adjacent; verify)", scope_extent="single_area", area_share="NA",
  title_verb="reconstruction", primary_type="sports_field", layout_change="no", entrance_change="no",
  target_users="teens_athletes (inferred)", community_request="unknown", funding_sources_named="Mayoral",
  reopening_date_reported="not found", co_works="", am_other="", evidence_status="tracker only",
  **am(sports_surface="REP|H")),
"1534111": dict(eligible="yes", multi_site="no", non_dpr_overlap="unknown", scope_extent="unknown", area_share="NA",
  title_verb="reconstruction", primary_type="path_access", layout_change="no", entrance_change="unknown",
  target_users="general (inferred)", community_request="unknown", funding_sources_named="Mayoral",
  reopening_date_reported="not found", co_works="", am_other="WWI memorial park; park page says 'No recent capital investment' (conflicts with Tracker)",
  evidence_status="tracker only", **am(paths_entrances="REP|M")),
}
rows = []
for tid in IDS:
    base = s[s.trackerid == tid].iloc[0]
    r = {"trackerid": tid, "title": base.title, "parkid": base.parkid, "borough": base.borough,
         "construction_start": base.construction_start, "construction_completion_admin": base.construction_completion_admin,
         "totalfunding_snapshot_2026-08-31": base.totalfunding, "fundingsource": base.fundingsource, "url": TR + tid}
    r.update(P[tid]); r["coder"] = "draft"; r["verified_by_TW"] = ""
    rows.append(r)
proj = pd.DataFrame(rows)
E = [
 ("8872","scope","Tracker: 'reconstruct Harold Schneiderman Playground'; construction 2023-10 to 2024-09; $3.5M",TR+"8872","2026-10-05 read","tracker","B","as-built","H"),
 ("8872","amenities","'upgraded play and water features, fitness and open play spaces, updated landscaping and seating'; equipment for ages 2-5 and 5-12; 'New spray features'; 'Added benches, water fountains, bike racks and paved pathways'",U["hs_pr"],"2024-10-28","parks_press","A","as-built","H"),
 ("8872","before_state","Press release does not state what was removed or replaced; UPG vs REP vs ADD needs imagery",U["hs_pr"],"2024-10-28","parks_press","A","as-built","L"),
 ("7277","scope","Tracker: 'reconstruct the playground and construct an African Burial Ground commemorative area'; construction 2023-11 to 2024-12; $4.889M",TR+"7277","2026-10-05 read","tracker","B","as-built","H"),
 ("7277","amenities","'new play equipment', 'a new basketball court', 'reconstruct the public restroom building façade', 'electrical and drainage improvements, paving, seating, and fencing'",U["sk_news"],"2023-11-22","parks_press","A","planned","M"),
 ("7277","commemorative","Oval lawn, circular stone assembly area, black granite Sankofa marker, interpretive signage (undated plan text)",U["sk_hist"],"undated","parks_page","A","planned","M"),
 ("7277","source_check","Release and Brooklyn Paper also describe Lion's Pride Playground (Brownsville) - its spray shower, ADA play, fitness etc. must NOT be attributed to Sankofa",U["sk_bp"],"2023-11","news","D","planned","H"),
 ("8882","amenities","Skate park 'with both street and bowl elements'; GFRC play boulders; on-ground agility/cardio markings; 'multi-use space for kids'; 'new tree plantings', benches, 'ramps for ADA access', lighting, water fountain",U["se_pr"],"2025-01-31","parks_press","A","as-built","H"),
 ("8882","funding","Tracker page shows $4,590,000; Open Data snapshot (2026-08-31) shows $4,100,000 - discrepancy",TR+"8882","2026-10-05 read","tracker","B","as-built","H"),
 ("8882","before_state","'upgrading the amenities available in that area currently' - prior amenities not described",U["se_rp"],"~2023-09/10","news","D","planned","L"),
 ("8882","extent","Additions complement existing amenities across Seton Park's 11 acres -> partial",U["se_bx"],"2025-02-03","news","D","as-built","H"),
 ("1482111","scope","Tracker: 'reconstruct the synthetic turf field'; construction 2024-02 to 2024-03; $480k",TR+"1482111","2026-10-05 read","tracker","B","as-built","H"),
 ("1482111","non_dpr_overlap","Park lies within/adjacent to East Side Coastal Resiliency (DDC) works; check closures 2023-2024",U["escr"],"2023-12-13","agency_doc","C","planned","L"),
 ("1534111","scope","Tracker: 'reconstruct paths in Hero Park'; construction 2024-04 to 2024-05; $195k",TR+"1534111","2026-10-05 read","tracker","B","as-built","H"),
 ("1534111","conflict","Park page Vital Signs: 'No recent capital investment'",U["hero"],"2026-10-05 read","parks_page","A","as-built","M"),
]
ev = pd.DataFrame(E, columns=["trackerid","field","value","source_url","source_date","source_type","evidence_grade","status","confidence"])
ev["coder"] = "draft"
V = [
 ("8872","Harold Schneiderman Playground, Queens (Q408, 0.88 ac)","40.665003, -73.850427","2023-10 → 2024-09",
  "2022-06 → 2023-08 (summer 2023 best)","2025-04 → 2025-09 (or latest)",
  "Whole playground. Before vs after: (1) spray shower present before? (2) adult fitness equipment before? (3) count benches (4) play equipment footprint/layout moved? (5) paved paths added? (6) tree count"),
 ("7277","Sankofa Park, Brooklyn (B261, 0.85 ac)","40.665642, -73.886326","2023-11 → 2024-12",
  "2022-06 → 2023-09","2025-04 → 2025-09 (or latest)",
  "Whole park. (1) basketball court existed before? same location/size? (2) playground equipment & layout (3) commemorative oval lawn / stone circle built? (4) restroom building facade (Street View) (5) fencing replaced?"),
 ("8882","Seton Park, Bronx (X201, 11.7 ac)","40.886074, -73.916492 (find the concrete skate bowl in AFTER image, then go back in time)","2023-09 → 2024-12",
  "2022-06 → 2023-08","2025-04 → 2025-09 (or latest)",
  "Partial. (1) what was on the skate/fitness footprint before (lawn? asphalt? old play area?) (2) rough footprint share of the park (e.g. <10%, 10-25%) (3) new ramps/paths, new trees"),
 ("1482111","Corlears Hook Park, Manhattan (M017, 4.4 ac)","40.711902, -73.979511","2024-02 → 2024-03 (very short)",
  "2023-06 → 2023-10","2024-05 → 2024-09",
  "Partial. (1) turf field same outline before/after (expect yes = REP) (2) field share of park (3) ESCR: any fencing/staging/construction across the park or its edges 2022-2025? park closed?"),
 ("1534111","Hero Park, Staten Island (R011, 3.0 ac)","40.630376, -74.087736","2024-04 → 2024-05 (very short)",
  "2023-06 → 2024-02","2024-07 → 2025-09",
  "(1) which paths look newly paved (all vs some) (2) any path re-routing or new entrance"),
]
vis = pd.DataFrame(V, columns=["trackerid","park","lat_lon (paste into Google Earth / Maps)","construction_tracker",
  "BEFORE image window","AFTER image window","what_to_look_for"])
for c in ["before_image_date_used","after_image_date_used","image_source (GE Pro / GE web / Street View)","findings_TW","codes_to_change"]:
    vis[c] = ""
I = [
 ("Press releases list additions only; REP vs UPG vs ADD rarely decidable from text","Code CHG and resolve with imagery; keep CHG count as data-quality indicator"),
 ("Small projects (turf, paths, lighting) have only a 1-line Tracker scope and no press release","Allow 'tracker only' coding with type-based defaults (e.g., turf reconstruction = REP); mark confidence M"),
 ("Sources written at construction start describe plans, not as-built","evidence_status field; prefer completion-era sources; imagery confirms"),
 ("Combined press releases mention other parks (Sankofa + Lion's Pride); search results include wrong-park articles","Mandatory source_check before coding"),
 ("Skate park has no category","v0 codes under sports_surface; candidate new category 'wheel sports / skate' for v1"),
 ("Tracker funding changes across snapshots (Seton $4.1M vs $4.59M)","Record funding with read date; analysis uses one fixed snapshot"),
 ("Non-DPR works (ESCR at Corlears Hook) not visible in DPR contamination check","Add non_dpr_overlap check for waterfront/large parks; consider excluding Corlears Hook"),
 ("Infrastructure co-works (drainage, electrical) inside amenity projects","co_works text field; not in amenity matrix"),
 ("Large-park partial projects (Seton, Corlears Hook, Hero?) may not show in park-level mobility signal","area_share + scope_extent used to stratify; expect weaker signal"),
]
iss = pd.DataFrame(I, columns=["issue","proposed_rule_for_v1"])
out = R/"casestudy/codebook/pilot_coding_v0.xlsx"
with pd.ExcelWriter(out, engine="openpyxl") as w:
    proj.to_excel(w, sheet_name="projects", index=False)
    ev.to_excel(w, sheet_name="evidence", index=False)
    vis.to_excel(w, sheet_name="visual_checks_TW", index=False)
    iss.to_excel(w, sheet_name="issues", index=False)
    for ws in w.book.worksheets:
        ws.freeze_panes = "B2"
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 2, 60)
print("ok", proj.shape, ev.shape)
