"""Rule-based screening of Queens sample v2 (layers 1, 3, 4). Layer 2 (E3 dose) pending area_share.
Writes: eligible / excl_rule / flags columns in Case_Inventory.xlsx + data/interim/sample/queens_screening.csv
Rules (applied in order, ex ante, no outcome data):
  E2 not publicly usable  : title matches Greenstreets | Green Infrastructure | Living Shoreline
  E1 no visitor-facing change: no am_* field carries ADD/UPG/REP/REM/CHG
  E4 no pre-period (new park): primary_type == new_amenity and scope_extent == whole_site
Flags (kept in sample, used for robustness):
  F1 external concurrent works (non-DPR)   F2 nearby population shock   F3 COVID window
  F4 NYCHA land                            F5 multi-site / same-park sequential project
  F6 in-house DPR co-works                 F7 seasonal facility, off-season construction
  E3? candidate for dose screen (area_share < 5% & park >= 20 ac) - pending GIS
"""
import openpyxl, pathlib, shutil, re, csv
R=pathlib.Path(__file__).resolve().parents[2]; F=R/'casestudy/Case_Inventory.xlsx'
shutil.copy(F, F.with_name('Case_Inventory_backup_2026-10-21c.xlsx'))
wb=openpyxl.load_workbook(F); ws=wb['Case Inventory']; h={c.value:i+1 for i,c in enumerate(ws[1])}
for col in ('excl_rule','flags'):
    if col not in h: c=ws.max_column+1; ws.cell(1,c).value=col; h[col]=c
AM=[k for k in h if k and k.startswith('am_')]
CHANGE=re.compile(r'^(ADD|UPG|REP|REM|CHG)\b')
E2KW=re.compile(r'greenstreets|green infrastructure|living shoreline',re.I)
FLAGS={'F1':{'Q054','Q062'},'F2':{'Q037'},'F4':{'Q042','Q048','Q050'},
       'F5':{'Q036','Q024','Q051','Q055','Q079','Q039','Q077','Q044','Q070','Q008','Q022','Q015','Q082','Q021','Q046'},
       'F6':{'Q054','Q082'},'F7':{'Q044'},'E3?':{'Q013','Q020'}}
out=[]
for r in range(2,ws.max_row+1):
    cid=ws.cell(r,1).value; s=str(ws.cell(r,h['Sample v2 (2019-26 NYC Parks data)']).value or '')
    if not (cid and str(cid).startswith('Q') and s.startswith('in')): continue
    title=str(ws.cell(r,h['Project / site']).value or '')
    v=lambda k: str(ws.cell(r,h[k]).value or '')
    changed=any(CHANGE.match(v(a)) for a in AM)
    if E2KW.search(title): rule='E2'
    elif not changed: rule='E1'
    elif v('primary_type')=='new_amenity' and v('scope_extent').startswith('whole_site'): rule='E4'
    else: rule=''
    fl=[k for k,S in FLAGS.items() if cid in S]
    if 'COVID' in s: fl.insert(2,'F3')
    elig={'E1':'no - E1 no visitor-facing change','E2':'no - E2 not publicly usable','E4':'separate - E4 no pre-period (new park)'}.get(rule,'yes' if 'E3?' not in fl else 'yes (E3 pending)')
    ws.cell(r,h['eligible']).value=elig; ws.cell(r,h['excl_rule']).value=rule or None; ws.cell(r,h['flags']).value=','.join(fl) or None
    out.append(dict(case=cid,tracker=ws.cell(r,h['Tracker ID']).value,title=title,rule=rule,flags=','.join(fl),eligible=elig))
wb.save(F)
p=R/'data/interim/sample/queens_screening.csv'
with open(p,'w',newline='') as f: w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
from collections import Counter
print('N',len(out),Counter(o['rule'] for o in out))
main=[o for o in out if not o['rule']]
print('main',len(main),Counter(x for o in main for x in o['flags'].split(',') if x))
for k in ('E1','E2','E4'): print(k,[o['case'] for o in out if o['rule']==k])
