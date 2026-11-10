"""Add Queens sample v2 (Advan 2019-01..2026-09 NYC Parks POIs) rows to Case_Inventory; next Q IDs by construction start.
Also adds column 'Sample v2 (2019-26)' for all rows, folders casestudy/Queens/<name (tid)>, KML casestudy/imagery/queens_v2_to_code.kml."""
import pandas as pd, openpyxl, re, pathlib, html
from copy import copy
R=pathlib.Path(__file__).resolve().parents[2]
q=pd.read_csv(R/'data/interim/sample/queens_sample_v2.csv',dtype=str)
t=pd.read_csv(R/'data/raw/capital_projects/capital_project_tracker.csv',dtype=str).drop_duplicates('trackerid').set_index('trackerid')
p=pd.read_csv(R/'data/raw/capital_projects/parks_properties.csv',dtype=str,usecols=['gispropnum','signname','acres','multipolygon']).drop_duplicates('gispropnum').set_index('gispropnum')
F=R/'casestudy/Case_Inventory.xlsx'; wb=openpyxl.load_workbook(F); ws=wb['Case Inventory']
h={c.value:i+1 for i,c in enumerate(ws[1])}
COL='Sample v2 (2019-26 NYC Parks data)'
if COL not in h:
    c=ws.cell(1,ws.max_column+1,COL); s=ws.cell(1,12); c.font,c.fill,c.alignment,c.border=copy(s.font),copy(s.fill),copy(s.alignment),copy(s.border); h[COL]=c.column
    ws.column_dimensions[openpyxl.utils.get_column_letter(c.column)].width=24
tidof=lambda r: (m.group(0) if (m:=re.match(r'\d+',str(ws.cell(r,h['Tracker ID']).value or ''))) else None)
qs=q.set_index('trackerid')
for r in range(2,ws.max_row+1):
    tid=tidof(r)
    ws.cell(r,h[COL]).value=('in (26wk' + (', 52wk' if qs.loc[tid,'ok52']=='True' else '') + (', COVID window' if qs.loc[tid,'covid']=='True' else '')+')') if tid in qs.index else ('n/a (not Queens)' if ws.cell(r,3).value!='Queens' else 'out')
have={tidof(r) for r in range(2,ws.max_row+1)}
used=[int(ws.cell(r,1).value[1:]) for r in range(2,ws.max_row+1) if re.match(r'^Q\d{3}$',str(ws.cell(r,1).value))]
nxt=max(used)+1
EXCL={'1313111':'telecom lines (infrastructure)','1386111':'telecom lines (infrastructure)','8740':'sediment application (ecological works, no user facility)',
 '7297':'administration building','9976':'historic house porches','8713':'multi-site green infrastructure','7377':'Greenstreets (street plantings, not park use)'}
new=q[~q.trackerid.isin(have)].sort_values(['cs','trackerid'])
ref=ws.max_row
out=R/'casestudy/Queens'; pm=[]
for _,x in new.iterrows():
    r0=t.loc[x.trackerid]; ws.append([None]*ws.max_column); n=ws.max_row
    for c in range(1,ws.max_column+1):
        s=ws.cell(ref,c); d=ws.cell(n,c); d.font,d.alignment,d.border,d.number_format=copy(s.font),copy(s.alignment),copy(s.border),s.number_format
    cid=f'Q{nxt:03d}'; nxt+=1
    pk=p.loc[x.parkid] if x.parkid in p.index else None
    vals={1:cid,2:r0.title,3:'Queens',4:'',5:f"Construction: {pd.Timestamp(x.cs):%b %Y}–{pd.Timestamp(x.ce):%b %Y} (administrative)",
          6:str(r0['name']) if isinstance(r0['name'],str) else '',7:f"{r0.totalfunding}; park {pk.acres if pk is not None else '?'} ac",8:'NYC Parks (DPR)',
          9:'https://www.nycgovparks.org/planning-and-building/capital-project-tracker/project/'+x.trackerid,10:'Queens sample v2 (2019-26 data). '+str(r0.summary),
          11:float(r0.latitude),12:float(r0.longitude)}
    for c,v in vals.items(): ws.cell(n,c).value=v
    for k,v in {'Tracker ID':x.trackerid,'Park ID':x.parkid,'52wk robustness':'yes' if x.ok52=='True' else 'no','Study area':'Queens',
                COL:ws.cell(n,h[COL]).value or ('in (26wk'+(', 52wk' if x.ok52=='True' else '')+(', COVID window' if x.covid=='True' else '')+')'),
                'Old Case ID':'','Sample status (v1, 2026-10-07)':'(v1 n/a)'}.items():
        if k in h: ws.cell(n,h[k]).value=v
    if x.trackerid in EXCL: ws.cell(n,h['eligible']).value='review - likely exclude: '+EXCL[x.trackerid]
    pname=(pk.signname if pk is not None else r0['name'])
    short=re.sub(r'[/:]','-',str(r0.title))[:60]
    if x.trackerid not in EXCL: (out/f"{short} ({x.trackerid})").mkdir(exist_ok=True)
    cs,ce=pd.Timestamp(x.cs),pd.Timestamp(x.ce)
    b0,b1=(cs-pd.DateOffset(months=15)).strftime('%Y-%m'),(cs-pd.DateOffset(months=3)).strftime('%Y-%m')
    a0,a1=(ce+pd.DateOffset(months=1)).strftime('%Y-%m'),(ce+pd.DateOffset(months=13)).strftime('%Y-%m')
    if x.trackerid not in EXCL:
        geom=''
        if pk is not None:
            for ring in re.findall(r"\(([^()]+)\)",pk.multipolygon or ''):
                geom+="<LineString><tessellate>1</tessellate><coordinates>"+" ".join(f"{a},{b},0" for a,b in (q.split() for q in ring.split(",")))+"</coordinates></LineString>"
        desc=f"<b>{cid} {html.escape(r0.title)}</b><br/>Tracker {x.trackerid} | {x.parkid} | {pk.acres if pk is not None else '?'} ac<br/>Construction: {cs:%Y-%m} to {ce:%Y-%m}<br/><b>BEFORE:</b> {b0} to {b1}<br/><b>AFTER:</b> {a0} to {a1}<br/>Folder: casestudy/Queens/{html.escape(short)} ({x.trackerid})"
        pm.append(f"<Placemark><name>{cid} {html.escape(str(pname))}</name><description><![CDATA[{desc}]]></description><styleUrl>#s</styleUrl><LookAt><longitude>{r0.longitude}</longitude><latitude>{r0.latitude}</latitude><altitude>0</altitude><range>350</range><tilt>0</tilt><heading>0</heading></LookAt><MultiGeometry><Point><coordinates>{r0.longitude},{r0.latitude},0</coordinates></Point>{geom}</MultiGeometry></Placemark>")
ws.auto_filter.ref=f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{ws.max_row}"
wb.save(F)
(R/'casestudy/imagery/queens_v2_to_code.kml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Queens v2 to code ({len(pm)})</name><Style id="s"><LineStyle><color>ff00ffff</color><width>3</width></LineStyle></Style>{"".join(pm)}</Document></kml>')
print('added',len(new),'IDs up to',f'Q{nxt-1:03d}','KML placemarks',len(pm))
