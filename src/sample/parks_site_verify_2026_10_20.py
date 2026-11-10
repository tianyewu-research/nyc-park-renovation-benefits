"""NYC Parks website verification (Tracker schematics, facility pages, PIP inspections), 2026-10-20 (2nd pass)."""
import openpyxl, pathlib, shutil
R=pathlib.Path(__file__).resolve().parents[2]; F=R/'casestudy/Case_Inventory.xlsx'
shutil.copy(F, F.with_name('Case_Inventory_backup_2026-10-20b.xlsx'))
wb=openpyxl.load_workbook(F); ws=wb['Case Inventory']; h={c.value:i+1 for i,c in enumerate(ws[1])}
rows={ws.cell(r,1).value:r for r in range(2,ws.max_row+1)}
TS='Tracker schematic'
U={
'Q024':dict(am_sports_surface='REP (H) - synthetic turf sports field; baseball lines painted on turf, dugouts/bleacher kept ('+TS+')',displaced_use='none (diamond kept as painted lines; infield dirt arc removed)',am_spray='UPG (H) - spray shower area + sports steel spray fixture ('+TS+')',am_paths_entrances='UPG (H) - promenade rebuilt w/ hex pavers',am_fencing='REP (H) - new chain-link fabric',am_other='ADD (H) - swings (3 bays), drinking fountain, 1939 WF benches',_n='Schematic reverses img-based CHG: field still baseball-capable.'),
'Q029':dict(non_dpr_overlap='none in Tracker within window (other Q023 projects: 2015-16, telecom 2022, 10069 future)',_n='PEP/comfort station not a Tracker project in window.'),
'Q035':dict(displaced_use='construction staging on upper lawn next to Windmuller/Doughboy dog run ~2021-05 (access disrupted, M)'),
'Q037':dict(am_sports_surface='UPG (H) - natural turf baseball field, skinned infield, 90 ft bases ('+TS+')',displaced_use='grass-infield baseball -> skinned-infield baseball; QNS 2024: used for softball, no mound (M)',reopening_date_reported='open by 2022-12 (PIP inspection 2022-12-08); QNS says 2023',am_fitness='NC (H) - existing fitness equipment kept',am_seating='ADD (H) - 5-tier bleachers, picnic tables, WF benches',am_fencing='REP (H) - 16 ft chain link new mesh + timber rail',_n='Tracker ce 2022-06 supported by PIP inspection 2022-12.'),
'Q039':dict(am_sports_surface='ADD (H) - new natural-turf football field on vegetated/wetland edge ('+TS+'; Tracker 100% 2022-08)',displaced_use='vegetated/wetland-edge land -> football field (H)',am_seating='ADD (H) - bleachers w/ companion seating',am_paths_entrances='ADD (H) - new connector paths to Linden Pl',am_lighting='ADD (H) - security lights along connector path',am_planting_gi='ADD (H) - wetland mitigation planting',am_fencing='ADD (H) - 4 ft chain link around field',evidence_status='tracker 100% + schematic',_n='No re-capture needed.'),
'Q043':dict(am_courts='REP (H) - basketball courts reconstructed, new backstops, color seal ('+TS+')',am_shade_trees='ADD (H) - new trees + transplanted trees',am_seating='ADD (H) - benches + game tables',am_other='ADD (H) - drinking fountains; light poles painted',non_dpr_overlap='',_n='Courts ARE in Tracker scope -> no contamination.'),
'Q045':dict(am_courts='UPG (H) - 2 full basketball courts (MPPA -> court) + handball',am_track='ADD (H) - running track around N court ('+TS+')',am_shade_trees='NC (M) - existing canopy retained in plan',am_seating='ADD (H) - S entrance seating plaza',entrance_change='yes (H) - multiple new entrances'),
'Q049':dict(am_sports_surface='UPG (H) - informal baseball/kickball field + informal soccer zone painted',am_courts='UPG (H) - full-size junior basketball + half courts; handball reconstructed',am_track='ADD (H) - painted walking path',am_accessibility='ADD (H) - ADA ramp + main entrance ramp/stairs',am_other='ADD (H) - painted maze/games, hi-lo fountain',_n='West-edge white roof = outside project (private residence side).'),
'Q051':dict(am_fitness='REP (H) - full adult fitness station set + bottle filler ('+TS+')'),
'Q032':dict(am_play='NC (H)',am_lighting='NC (M) - existing Parks lights retained in schematic',am_other='ADD (H) - game tables, 1964 WF benches',am_fencing='ADD (H) - picket fence + 1 ft fence on piers',am_paths_entrances='UPG (H) - colored/scored concrete + asphalt'),
'Q048':dict(am_fitness='ADD (H) - adult + youth fitness',am_spray='ADD (H) - spray shower',am_paths_entrances='ADD (H) - walking loop (NYCHA)',am_other='ADD (H) - picnic/grill area, plaza'),
'Q053':dict(am_courts='NM (L) - NE area now 5-12 play + swings; prior use unknown; handball court kept',am_lighting='ADD (H) - light poles',am_other='ADD (H) - cantilevered shade, picnic tables, game tables, rinsing station, climbing dome'),
'Q054':dict(am_restroom_building='REP (H) - brick comfort station rebuilt (rendering), ADA, changing tables (facility page 2025)',am_courts='UPG (M) - Parks-logo color-coated court in schoolyard (park photo) painted 2021-05->2023-05; not in Tracker (in-house)',co_works='in-house court color-coat inside Q389 during window (M)'),
'Q055':dict(non_dpr_overlap='Q079 (9844) starts 2024-09, 65 wk after ce -> outside +-26 wk',_n='Resolved via Tracker 9844 dates.'),
'Q056':dict(reopening_date_reported='ribbon 2025-04 (PR); Tracker ce 2023-01 used',_n='No other Tracker project in window (1975111 future restroom). Use Tracker 2023-01.'),
'Q057':dict(am_courts='ADD (M) - "New Basketball Court" ('+TS+'); prior court location unclear',am_lighting='ADD (H) - new lighting',am_paths_entrances='ADD (H) - new asphalt paths',am_shade_trees='ADD (H) - new tree plantings'),
'Q060':dict(_n='Second project 9551 restroom building Q509: constr 2024-10->2026-07 (outside 52-wk post if ce 2023-09; flag for long windows).'),
'Q062':dict(am_paths_entrances='UPG (H) - new asphalt pavement, reduced connection',am_seating='ADD (H) - 1964 WF benches, companion seating',am_fencing='ADD (H) - sea rail',am_planting_gi='ADD (H) - new planted areas + trees',am_other='ADD (H) - drinking fountain/bottle filler, bike racks',evidence_status='tracker 100% + final design plan',_n='Esplanade near Rockaway ferry dock; scope from final plan, no re-capture needed.'),
'Q066':dict(evidence_status='tracker 100% (2024-02) + schematic',_n='No re-capture needed (Tracker complete).'),
'Q069':dict(am_lighting='ADD (H) - pedestrian pole w/ 1964 WF luminaire',am_other='ADD (H) - dog runs 1,500 + 770 sf, bottle filler w/ dog bowl, game tables, seat wall, stairs'),
'Q072':dict(am_fencing='ADD (H) - 4 ft steel fence + double gates enclosing 2 play areas ('+TS+')',scope_extent='single_area',_n='S red area = existing play area.'),
'Q073':dict(am_paths_entrances='UPG (H) - 3 entrances w/ curb cuts (117th, 119th, mid-block) + new concrete sidewalk',am_seating='ADD (H) - 119th St entry plaza w/ planting & seating',am_planting_gi='ADD (H)'),
'Q079':dict(am_courts='ADD (H) - 2 volleyball courts in track, HS-length basketball, bankshot court ('+TS+')',am_fitness='ADD (H) - adult fitness + agility course',am_track='ADD (H) - running/walking track',am_seating='ADD (H) - steel tables/chairs, 1964 WF benches',am_other='ADD (H) - painted games, bottle filler, bike rack'),
'Q081':dict(_n='Tracker now 100%, completed 2025-09.'),
'Q082':dict(co_works='small court beside school likely converted to 2 pickleball courts (Parks listing), not in Tracker (L)',_n='Tracker now 100%, completed 2025-11.'),
'Q083':dict(_n='Tracker completed 2025-12.'),
}
for cid,d in U.items():
    r=rows[cid]; n=d.pop('_n','')
    for k,v in d.items(): ws.cell(r,h[k]).value=v
    old=ws.cell(r,h['TW notes']).value or ''
    ws.cell(r,h['TW notes']).value=old+' | PARKS-SITE 2026-10-20: '+(n or 'verified via nycgovparks.org.')
wb.save(F); print('updated',len(U))
