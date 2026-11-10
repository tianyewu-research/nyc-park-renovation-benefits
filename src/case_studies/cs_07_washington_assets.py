"""Washington Square Park case assets."""
import os, sys, textwrap, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C, cs_fig as F, cs_assets_lib as L
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

CID, B1, B2, B3 = "WSP", "board_1_history_profile", "board_2_renovation", "board_3_use_outcomes"
S_CONS = "History | Washington Square Park Conservancy (PDF), p.1–8"
S_WSP1 = "wsp.pdf, p.1 (NYC Parks Phase 1 project sign)"
S_GREEN = "Matter of Greenberg v City of New York, 2007 NY Slip Op 01943 (PDF), p.1–9"

TL = [(1895,"Washington Arch completed and anchors the park",S_CONS,"D"),
      (1935,"Robert Moses begins repeated attempts to run a roadway through the park",S_CONS,"D"),
      (1958,"Greenwich Village defeats the roadway plan; the park becomes car-free",S_CONS,"D"),
      (1970,"Community-driven renovation led by Robert Nichols creates the sunken fountain plaza, stage and petanque court",S_CONS,"D"),
      (2004,"Washington Square Arch restored and rededicated 30 April",S_CONS,"D"),
      (2005,"Project for Public Spaces pre-renovation use study",
            "wsp_final_report_pps.pdf","D"),
      (2007,"Appellate Division decision in Matter of Greenberg v City of New York",S_GREEN,"B"),
      (2012,"Washington Square Park Conservancy founded",S_CONS,"D"),
      (2014,"Most recent renovation completed in two major phases",S_CONS,"D")]
tl = pd.DataFrame(TL, columns=["year","event","source","evidence_grade"])
fig, ax = plt.subplots(figsize=(9.6, 6.0))
ax.hlines(0, 1888, 2022, color=F.MUTED, lw=1.0)
for i, r in tl.iterrows():
    up = i % 2 == 0; y = .6 if up else -.6
    hot = r.year in (2005, 2007, 2014)
    ax.vlines(r.year, 0, y, color=F.RUST if hot else F.TEAL_M, lw=1.2)
    ax.plot(r.year, 0, "o", ms=6, color=F.RUST if hot else F.TEAL)
    ax.text(r.year, y + (.11 if up else -.11), f"{r.year}\n" +
            "\n".join(textwrap.wrap(r.event, 30)), ha="center",
            va="bottom" if up else "top", fontsize=6.9, color=F.INK)
ax.set_xlim(1888, 2022); ax.set_ylim(-2.3, 2.3); ax.axis("off")
ax.set_title("Washington Square Park: civic use, debate and renovation",
             fontsize=11.5, color=F.INK, loc="left", weight="bold")
F.source_line(fig, f"{S_CONS}; {S_GREEN}; PPS report. Each date is page-referenced in the claim ledger.")
fig.tight_layout(rect=(0, .07, 1, 1))
F.export(fig, os.path.join(C.board_dir(CID,B1),"figures"), "WSP_F00_timeline",
  "Washington Square Park: civic use, debate and renovation",
  "Verified dates from the Conservancy history, the 2007 court decision and the PPS report.",
  "Manual transcription from named primary sources.", "year",
  f"{S_CONS}; {S_GREEN}", tl, case_id=CID, board=B1)

# process diagram
fig, ax = plt.subplots(figsize=C.ASPECTS["4:3"]); ax.axis("off")
ax.set_xlim(0,10); ax.set_ylim(0,8)
nodes = [(2.0,6.3,"Community groups and\npark users","#E6EFE9",F.TEAL),
         (5.0,6.3,"NYC Parks\n(project sponsor)","#E6EFE9",F.TEAL),
         (8.0,6.3,"Design and\ncapital delivery","#E6EFE9",F.TEAL),
         (3.5,3.9,"Public review and\nlocal opposition","#F6E3D4",F.ORANGE),
         (6.5,3.9,"Approvals and\nproject start","#F6E3D4",F.ORANGE),
         (5.0,1.7,"Litigation:\nMatter of Greenberg v City of New York (2007)","#F2DCCB",F.RUST)]
for x,y,t,fc,ec in nodes:
    ax.add_patch(FancyBboxPatch((x-1.45,y-.6),2.9,1.2,boxstyle="round,pad=.10",fc=fc,ec=ec,lw=1.1))
    ax.text(x,y,t,ha="center",va="center",fontsize=7.8,color=F.INK)
for a,b in [((2.0,5.7),(3.5,4.5)),((5.0,5.7),(3.5,4.5)),((5.0,5.7),(6.5,4.5)),
            ((8.0,5.7),(6.5,4.5)),((3.5,3.3),(5.0,2.3)),((6.5,3.3),(5.0,2.3))]:
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color=F.MUTED, lw=1.0))
ax.text(5.0,7.5,"Washington Square Park: renovation decision process",ha="center",
        fontsize=10.5,weight="bold",color=F.INK)
ax.text(5.0,.5,"ANALYTICAL DIAGRAM. Only actors named in the local sources are shown.",
        ha="center",fontsize=7.2,color=F.INK_2,style="italic")
F.source_line(fig, f"{S_GREEN}; {S_CONS}. CB2 and LPC roles are not documented in the local source set and are therefore not shown.")
F.export(fig, os.path.join(C.board_dir(CID,B1),"figures"), "WSP_F01_process_diagram",
  "Washington Square Park: renovation decision process",
  "Actors and steps named in the local sources, ending in the 2007 Appellate Division decision.",
  "Schematic; unnamed actors deliberately omitted.", "process step", S_GREEN,
  pd.DataFrame([dict(node=t.replace("\n", " "), role_group=("public" if fc=="#E6EFE9" else
      "review/approval" if fc=="#F6E3D4" else "litigation")) for x,y,t,fc,ec in nodes]),
  case_id=CID, board=B1)

# ---- B2 phase matrix + intervention table ---------------------------------
PH = [("Phase 1","Northwest quadrant, Fountain Plaza and Thompson Street entrance",
       "Holley statue restored and reoriented; 1870s fountain fully restored; new stone seating wall; accessible fountain plaza",S_WSP1,"B"),
      ("Later park phases","Remaining quadrants",
       "Renovation completed in two major phases; new and expanded lawns and planting beds, repaved paths, new benches and lighting",S_CONS,"D"),
      ("Comfort station","Separate later project",
       "Comfort-station work reported separately from the park renovation",
       "news-ribbon-washington-square-park-comfort.pdf, p.1","D")]
ph = pd.DataFrame(PH, columns=["phase","extent","documented_work","source","evidence_grade"])
ph.to_csv(os.path.join(C.board_dir(CID,B2),"data","WSP_phase_matrix.csv"), index=False)
fig, ax = plt.subplots(figsize=(9.2, 4.6)); ax.axis("off")
for i,r in ph.iterrows():
    y = 3.4 - i*1.15
    ax.add_patch(FancyBboxPatch((.3,y-.45),2.2,.9,boxstyle="round,pad=.08",
                                fc="#F2DCCB" if i==0 else "#E6EFE9",
                                ec=F.RUST if i==0 else F.TEAL, lw=1.0))
    ax.text(1.4,y,r.phase,ha="center",va="center",fontsize=8.6,weight="bold",color=F.INK)
    ax.add_patch(FancyBboxPatch((2.7,y-.45),6.8,.9,boxstyle="round,pad=.08",fc=F.BG,ec=F.MUTED,lw=.8))
    ax.text(2.9,y+.15,r.extent,ha="left",va="center",fontsize=7.8,weight="bold",color=F.INK)
    ax.text(2.9,y-.18,"\n".join(textwrap.wrap(r.documented_work,88))[:180],
            ha="left",va="center",fontsize=6.9,color=F.INK_2)
ax.set_xlim(0,10); ax.set_ylim(0,4.4)
ax.text(.3,4.15,"Washington Square Park: phased renovation",fontsize=11,weight="bold",color=F.INK)
F.source_line(fig, f"{S_WSP1}; {S_CONS}. The perimeter-sidewalk Capital Tracker record for M098 is a separate, minor work item and is NOT the main renovation.")
fig.tight_layout(rect=(0,.10,1,1))
F.export(fig, os.path.join(C.board_dir(CID,B2),"figures"), "WSP_F10_phase_matrix",
  "Washington Square Park: phased renovation",
  "Phases and documented work, each traced to a named source.",
  "Only work explicitly described in the local sources is listed.", "phase",
  f"{S_WSP1}; {S_CONS}", ph, case_id=CID, board=B2)

# ---- B3 --------------------------------------------------------------------
ev = pd.read_csv(f"{C.INTERIM}/tables/{CID}_special_events.csv", low_memory=False)
dcol = next((c for c in ev.columns if "date" in c.lower()), None)
acol = next((c for c in ev.columns if "attend" in c.lower()), None)
if dcol:
    ev["_d"] = pd.to_datetime(ev[dcol], errors="coerce")
    ev = ev[ev._d.notna()]
    ev["year"] = ev._d.dt.year
    ev = ev[ev.year.between(2018, 2024)]
    tcol = next((c for c in ("event_type","category","classification") if c in ev.columns), None)
    g = ev.groupby(["year"] + ([tcol] if tcol else []), as_index=False).agg(
        n_events=("_d","size"), attendance=(acol,"sum") if acol else ("_d","size"))
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    if tcol and g[tcol].nunique() <= 6:
        p = g.pivot_table(index="year", columns=tcol, values="attendance", aggfunc="sum").fillna(0)
        bot = np.zeros(len(p)); cols = [F.TEAL,F.TEAL_M,F.ORANGE,"#C9A227",F.RUST,F.MUTED]
        for i,c in enumerate(p.columns):
            ax.bar(p.index, p[c], bottom=bot, color=cols[i%6], label=str(c)[:24], width=.7)
            bot += p[c].values
        ax.legend(frameon=False, fontsize=7, ncol=2)
    else:
        ax.bar(g.year, g.attendance, color=F.TEAL, width=.7)
    ax.set_ylabel("Reported event attendance", fontsize=9, color=F.INK_2); L._ax(ax)
    ax.set_title("Washington Square Park: Parks special-event attendance, 2018–2024",
                 fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, "NYC Parks special events (6v4b-5gp4), matched on free-text location. "
                  "Reported event attendance is an organiser/agency figure, not an "
                  "independent count, and is separate from park-wide visitation.")
    fig.tight_layout(rect=(0,.08,1,1))
    F.export(fig, os.path.join(C.board_dir(CID,B3),"figures"), "WSP_F07_special_events",
      "Washington Square Park: Parks special-event attendance, 2018–2024",
      "Reported attendance at Parks special events held in the park.",
      "Free-text location match, then grouped by year and event type.",
      "reported event attendance", "NYC Parks special events 6v4b-5gp4", g,
      case_id=CID, board=B3)

# PPS vs current: side-by-side method comparison, values never merged
cmpt = pd.DataFrame([
 dict(dimension="Source", pps_2005="Project for Public Spaces study, 2005",
      current="Advan mobile-location panel, 2023–2025 (vintage 202606)"),
 dict(dimension="What is counted", pps_2005="Observed people, on-site counts and surveys",
      current="Provider-estimated device visits, dwell-qualified"),
 dict(dimension="Coverage", pps_2005="Selected observation periods",
      current="157 continuous weeks"),
 dict(dimension="Population", pps_2005="All people present during observation",
      current="Devices in the provider panel only"),
 dict(dimension="Relation to renovation", pps_2005="PRE-renovation use study",
      current="POST-renovation current use"),
 dict(dimension="Comparability", pps_2005="—",
      current="NOT comparable: no percentage change may be computed between them")])
cmpt.to_csv(os.path.join(C.board_dir(CID,B3),"data","WSP_method_comparison.csv"), index=False)
fig, ax = plt.subplots(figsize=(9.4, 4.4)); ax.axis("off")
t = ax.table(cellText=cmpt.values, colLabels=["", "PPS 2005", "Advan 2023–2025"],
             loc="center", cellLoc="left", colWidths=[.22,.39,.39])
t.auto_set_font_size(False); t.set_fontsize(7.6); t.scale(1, 1.55)
for (r,c),cell in t.get_celld().items():
    cell.set_edgecolor("#E2E4DF"); cell.set_linewidth(.6)
    if r==0: cell.set_facecolor("#E6EFE9"); cell.set_text_props(weight="bold")
    elif r%2==0: cell.set_facecolor("#FAF9F6")
ax.set_title("Two different measurement systems, shown separately",
             fontsize=11, color=F.INK, loc="left", weight="bold", pad=14)
F.source_line(fig, "The 2005 PPS counts and the 2023–2025 Advan series use different "
              "methods and different populations. They are presented side by side and "
              "are never merged into one line or differenced into a percentage change.")
fig.tight_layout(rect=(0,.10,1,1))
F.export(fig, os.path.join(C.board_dir(CID,B3),"figures"), "WSP_F08_method_comparison",
  "Two different measurement systems, shown separately",
  "Method comparison between the 2005 PPS pre-renovation study and current provider data.",
  "Descriptive comparison table; no values merged.", "method dimension",
  "wsp_final_report_pps.pdf; Advan vintage 202606", cmpt, case_id=CID, board=B3)

L.advan_index(CID,B3); L.advan_season(CID,B3); L.pip_timelines(CID,B3)
L.origin_and_composition(CID,B3)
n = F.flush_manifest(); print(f"\nWSP assets done; manifest {n}")
