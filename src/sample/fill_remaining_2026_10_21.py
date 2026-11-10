"""Fill Q004 (Bland), fix Q017 type, finalize Q044/Q067/Q077 from NYC Parks site, 2026-10-21."""
import openpyxl, pathlib, shutil
R=pathlib.Path(__file__).resolve().parents[2]; F=R/'casestudy/Case_Inventory.xlsx'
shutil.copy(F, F.with_name('Case_Inventory_backup_2026-10-21b.xlsx'))
wb=openpyxl.load_workbook(F); ws=wb['Case Inventory']; h={c.value:i+1 for i,c in enumerate(ws[1])}
rows={ws.cell(r,1).value:r for r in range(2,ws.max_row+1)}
U={
'Q004':dict(eligible='yes',multi_site='no',non_dpr_overlap='none found',scope_extent='whole_site',area_share='NA',title_verb='reconstruction',primary_type='multi_element',
 am_play='UPG (H) - new 2-5 and 5-12 play equipment, 8 ft swings (4 bays), safety surface',am_spray='UPG (H) - spray area / spray showers',
 am_courts='UPG (H) - basketball court 75x45.5 color seal; handball court rebuilt',am_seating='UPG (H) - seating area w/ game tables, benches',
 am_shade_trees='ADD (H) - proposed trees',am_lighting='UPG (M) - light poles (schematic)',am_paths_entrances='UPG (H) - new entrances + paved paths',
 am_accessibility='UPG (M) - "improved accessibility" (CM Ung, PR)',am_planting_gi='ADD (H) - plantings',am_fencing='CHG (H) - tall chain link -> lower steel picket fence',
 am_other='ADD (H) - multi-purpose area w/ painted games (tai chi, jump rope, hopscotch, skelly); drinking fountains, bottle filler',
 layout_change='yes (M) - full redesign',funding_sources_named='Borough President; City Council ($6.0M)',reopening_date_reported='ribbon 2024-08-28 (Tracker ce 2024-06)',
 target_users='children + Bland Houses (NYCHA) families (PR)',evidence_status='as-built (PR 2024-08) + Tracker schematic',
 **{'Coder':'draft (web: Tracker schematic + PR)','Key sources (full list: codebook/pilot_coding_v0.xlsx > evidence)':'https://www.nycgovparks.org/planning-and-building/capital-project-tracker/project/8871\nhttps://www.nycgovparks.org/news/press-releases?id=22184'},
 _n='Only project at Q326. Imagery optional (not captured).'),
'Q017':dict(primary_type='court',am_seating='ADD (H) - bleachers',am_paths_entrances='UPG (H) - new steps to upper courts, permeable plant pavers',am_other='ADD (H) - bike racks, drinking fountains; handball existing (NC)',
 _n='Tracker schematic titled "Crowley Courts": project = courts section only (lower 84 ft HS court + 2 upper 80 ft courts, adult fitness zone, ADA ramp).'),
'Q044':dict(am_other='REP (M) - pool deck reconstructed (like-for-like)',evidence_status='tracker only',eligible='review - exclude',
 _n='Liberty Pool is in Det. Keith L. Williams Park (Q121). Construction 2021-10->2022-05 = pool off-season; no amenity change -> recommend exclude (or use as placebo). Q070 starts 2023-03 (43 wk later).'),
'Q067':dict(eligible='review - exclude',am_planting_gi='ADD (H) - living shoreline / marsh (Phase 2; Phase 1 w/ oyster habitat 2021-02->03)',evidence_status='tracker + Stantec project page',
 _n='Ecological, not visitor-facing; Q135 = 327 ac park so treatment tiny vs POI. Bayside Marina (Q013, same Q135) starts 2023-12 = ~26 wk after ce (borderline). Recommend exclude.'),
'Q077':dict(am_lighting='ADD (H) - new sports lighting (fields) + security lighting (Tracker); extends evening use',evidence_status='tracker 100% (2024-05) + news 2021-10',
 _n='Same park as Q039 (ce 2022-08, 40 wk earlier). News 10/2021: lighting, LED scoreboard, Linden Pl ped bridge funded. Expect time-of-day shift.'),
}
for cid,d in U.items():
    r=rows[cid]; n=d.pop('_n','')
    for k,v in d.items(): ws.cell(r,h[k]).value=v
    ws.cell(r,h['TW notes']).value=((ws.cell(r,h['TW notes']).value or '')+' | PARKS-SITE 2026-10-21: '+n).lstrip(' |')
wb.save(F); print('ok')
