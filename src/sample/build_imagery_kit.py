"""Google Earth KML + per-project imagery folders for visual coding.
Output: casestudy/imagery/sample_v1_projects.kml ; casestudy/imagery/<trackerid>_<park>/ (empty, for screenshots)."""
import pandas as pd, pathlib, re, html
R = pathlib.Path(__file__).resolve().parents[2]
s = pd.read_csv(R/"data/interim/sample/sample_list_v1.csv", dtype=str)
s = s[s.status == "confirmed"].copy()
p = pd.read_csv(R/"data/raw/capital_projects/parks_properties.csv", dtype=str, usecols=["gispropnum","signname","acres","multipolygon"]).drop_duplicates("gispropnum").set_index("gispropnum")
t = pd.read_csv(R/"data/raw/capital_projects/capital_project_tracker.csv", dtype=str).drop_duplicates("trackerid").set_index("trackerid")
out = R/"casestudy/imagery"; out.mkdir(exist_ok=True)
pilot = {"8872","7277","8882","1482111","1534111"}
def rings(wkt):
    for ring in re.findall(r"\(([^()]+)\)", wkt or ""):
        pts = [q.split() for q in ring.split(",")]
        yield " ".join(f"{x},{y},0" for x, y in pts)
pm = []
for _, r in s.iterrows():
    cs, ce = pd.Timestamp(r.construction_start), pd.Timestamp(r.construction_completion_admin)
    b0, b1 = (cs - pd.DateOffset(months=15)).strftime("%Y-%m"), (cs - pd.DateOffset(months=3)).strftime("%Y-%m")
    a0, a1 = (ce + pd.DateOffset(months=1)).strftime("%Y-%m"), (ce + pd.DateOffset(months=13)).strftime("%Y-%m")
    park = p.loc[r.parkid] if r.parkid in p.index else None
    pname = park.signname if park is not None else r.location_name
    folder = f"{r.trackerid}_{re.sub(r'[^A-Za-z0-9]+','_',str(pname)).strip('_')}"
    (out/folder).mkdir(exist_ok=True)
    tag = "[PILOT] " if r.trackerid in pilot else ""
    desc = (f"<b>{html.escape(r.title)}</b><br/>Tracker {r.trackerid} | Park {r.parkid} | {park.acres if park is not None else '?'} ac<br/>"
            f"Construction (Tracker): {cs:%Y-%m} to {ce:%Y-%m}<br/><b>BEFORE image:</b> {b0} to {b1}<br/><b>AFTER image:</b> {a0} to {a1}<br/>"
            f"Folder: casestudy/imagery/{folder}<br/>Scope: {html.escape(str(r.summary))}")
    lat, lon = t.loc[r.trackerid, "latitude"], t.loc[r.trackerid, "longitude"]
    geom = "".join(f"<LineString><tessellate>1</tessellate><coordinates>{c}</coordinates></LineString>" for c in rings(park.multipolygon)) if park is not None else ""
    pm.append(f"""<Placemark><name>{tag}{html.escape(str(pname))} ({r.trackerid})</name><description><![CDATA[{desc}]]></description><styleUrl>#s</styleUrl>
<LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude><altitude>0</altitude><range>350</range><tilt>0</tilt><heading>0</heading></LookAt>
<MultiGeometry><Point><coordinates>{lon},{lat},0</coordinates></Point>{geom}</MultiGeometry></Placemark>""")
kml = f"""<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Sample v1 - confirmed projects ({len(pm)})</name>
<Style id="s"><LineStyle><color>ff00ffff</color><width>3</width></LineStyle><IconStyle><scale>0.9</scale></IconStyle></Style>
{''.join(pm)}</Document></kml>"""
(out/"sample_v1_projects.kml").write_text(kml)
print(len(pm), "placemarks;", len([d for d in out.iterdir() if d.is_dir()]), "folders")
