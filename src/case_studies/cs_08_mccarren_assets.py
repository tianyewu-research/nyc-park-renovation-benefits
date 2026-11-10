"""McCarren Pool case assets."""
import os, sys, textwrap, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C, cs_fig as F, cs_assets_lib as L
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

CID, B1, B2, B3 = "MCP", "board_1_history_profile", "board_2_renovation", "board_3_use_outcomes"
T = os.path.join(C.INTERIM, "tables")
S_LPC = "LPC Designation Report LP-2244, 24 July 2007, p.1"
S_NYT = "The New York Times, 28 June 2012 (Lisa W. Foderaro), p.1"

TL = [(1934,"Construction of the McCarren Play Center begins; Aymar Embury II lead architect, Gilmore D. Clarke landscape architect",S_LPC,"B"),
      (1936,"Play Center completed and opened",S_LPC,"B"),
      (1984,"Pool closes; it will stand empty for 28 years",S_NYT,"D"),
      (1990,"Site heard by the Landmarks Preservation Commission (LP-1789)",S_LPC,"B"),
      (2005,"Empty pool adopted as an outdoor stage for concerts and performances",S_NYT,"D"),
      (2007,"Designated a New York City Landmark, LP-2244, 24 July",S_LPC,"B"),
      (2012,"Pool reopens 28 June after a 30-month renovation",S_NYT,"D")]
tl = pd.DataFrame(TL, columns=["year","event","source","evidence_grade"])
fig, ax = plt.subplots(figsize=(9.4, 5.6))
ax.hlines(0, 1928, 2020, color=F.MUTED, lw=1.0)
for i,r in tl.iterrows():
    up = i%2==0; y = .6 if up else -.6
    hot = r.year in (1984, 2012)
    ax.vlines(r.year,0,y,color=F.RUST if hot else F.TEAL_M,lw=1.2)
    ax.plot(r.year,0,"o",ms=6,color=F.RUST if hot else F.TEAL)
    ax.text(r.year, y+(.11 if up else -.11), f"{r.year}\n"+"\n".join(textwrap.wrap(r.event,32)),
            ha="center", va="bottom" if up else "top", fontsize=6.9, color=F.INK)
ax.axvspan(1984,2012,color=F.MUTED,alpha=.10)
ax.set_xlim(1928,2020); ax.set_ylim(-2.3,2.3); ax.axis("off")
ax.set_title("McCarren Pool: WPA construction, 28-year closure, reopening",
             fontsize=11.5,color=F.INK,loc="left",weight="bold")
F.source_line(fig, f"{S_LPC}; {S_NYT}. Shaded band = the 1984–2012 period the pool stood empty.")
fig.tight_layout(rect=(0,.07,1,1))
F.export(fig, os.path.join(C.board_dir(CID,B1),"figures"), "MCP_F00_timeline",
  "McCarren Pool: WPA construction, 28-year closure, reopening",
  "Verified dates from the Landmarks designation report and contemporaneous press.",
  "Manual transcription from named primary sources.", "year",
  f"{S_LPC}; {S_NYT}", tl, case_id=CID, board=B1)

# site-structure diagram
fig, ax = plt.subplots(figsize=C.ASPECTS["4:3"]); ax.axis("off")
ax.set_xlim(0,10); ax.set_ylim(0,8)
ax.add_patch(FancyBboxPatch((.6,1.0),8.8,5.6,boxstyle="round,pad=.12",fc="#EDF0EA",ec=F.TEAL_M,lw=1.1))
ax.text(5.0,6.2,"McCarren Park (park site, park_id B058)",ha="center",fontsize=9.2,
        weight="bold",color=F.INK_2)
ax.add_patch(FancyBboxPatch((1.6,1.9),6.8,3.5,boxstyle="round,pad=.10",fc="#F2DCCB",ec=F.RUST,lw=1.2))
ax.text(5.0,5.05,"McCarren Play Center — NYC Landmark LP-2244 (2007)",ha="center",
        fontsize=8.8,weight="bold",color=F.INK)
for x,y,t in [(3.0,3.9,"Bath house"),(7.0,3.9,"Swimming pool"),
              (3.0,2.7,"Diving pool /\nwading pool"),(7.0,2.7,"Filter house,\nlifeguard house")]:
    ax.add_patch(FancyBboxPatch((x-1.2,y-.45),2.4,.9,boxstyle="round,pad=.07",fc=F.BG,ec=F.ORANGE,lw=.9))
    ax.text(x,y,t,ha="center",va="center",fontsize=7.6,color=F.INK)
ax.text(5.0,7.3,"McCarren: distinguishing park, landmarked complex and facilities",
        ha="center",fontsize=10.5,weight="bold",color=F.INK)
ax.text(5.0,.55,"ANALYTICAL DIAGRAM — nesting of entities, not a site plan.",
        ha="center",fontsize=7.2,color=F.INK_2,style="italic")
F.source_line(fig, f"Designated components listed in {S_LPC}: bath house, swimming pool, "
              "diving pool, wading pool, filter house, lifeguard house, brick perimeter "
              "walls, piers and cast-iron fencing, comfort stations, linking pathways and "
              "the planted median.")
F.export(fig, os.path.join(C.board_dir(CID,B1),"figures"), "MCP_F01_site_structure",
  "McCarren: distinguishing park, landmarked complex and facilities",
  "Entity diagram separating the park site, the landmarked Play Center and its components.",
  "Schematic nesting diagram; components as listed in the designation report.",
  "entity", S_LPC,
  pd.DataFrame([dict(level="park site", entity="McCarren Park (park_id B058)"),
                dict(level="landmarked complex", entity="McCarren Play Center, LP-2244 (2007)"),
                dict(level="facility", entity="Bath house"),
                dict(level="facility", entity="Swimming pool"),
                dict(level="facility", entity="Diving pool / wading pool"),
                dict(level="facility", entity="Filter house, lifeguard house")]),
  case_id=CID, board=B1)

# ---- B2 tracker 5404 phase + funding ---------------------------------------
trk = pd.read_csv(f"{T}/{CID}_tracker.csv", low_memory=False)
t5404 = trk[trk["trackerid"].astype(str) == "5404"]
if len(t5404):
    r = t5404.iloc[0]
    ph = []
    for lbl, s, e in (("Design","designstart","designactualcompletion"),
                      ("Procurement","procurementstart","procurementactualcompletion"),
                      ("Construction","constructionstart","constructionactualcompletion")):
        a, b = pd.to_datetime(r.get(s), errors="coerce"), pd.to_datetime(r.get(e), errors="coerce")
        if pd.notna(a): ph.append(dict(phase=lbl, start=a, end=b))
    pdf_ = pd.DataFrame(ph)
    pdf_["funding_raw_displayed"] = r.get("totalfunding")
    pdf_.to_csv(os.path.join(C.board_dir(CID,B2),"data","MCP_tracker_5404_phases.csv"), index=False)
    fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
    cols = {"Design":F.TEAL_M,"Procurement":F.ORANGE,"Construction":F.RUST}
    for i,p in pdf_.iterrows():
        end = p.end if pd.notna(p.end) else pd.Timestamp("2012-06-28")
        ax.barh(i, (end-p.start).days, left=p.start, color=cols[p.phase], height=.52)
        ax.text(p.start, i+.42, p.phase, fontsize=8, color=F.INK)
    ax.axvline(pd.Timestamp("2012-06-28"), color=F.INK_2, lw=1.1, ls="--")
    ax.text(pd.Timestamp("2012-06-28"), len(pdf_)-.3, " reopened 28 Jun 2012",
            fontsize=7.6, color=F.INK_2)
    ax.set_yticks([]); L._ax(ax)
    ax.set_title("McCarren Pool reconstruction: Tracker ID 5404 phases",
                 fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
    F.source_line(fig, f"NYC Parks Capital Project Tracker (4hcv-tc5r), trackerid 5404. "
                  f"Total funding as displayed in the local record: {r.get('totalfunding')}. "
                  "The New York Times reported the renovation as '30-month, $50 million' "
                  "(28 June 2012); the two figures come from different sources and are "
                  "reported separately, not reconciled.")
    fig.tight_layout(rect=(0,.10,1,1))
    F.export(fig, os.path.join(C.board_dir(CID,B2),"figures"), "MCP_F10_tracker5404_phases",
      "McCarren Pool reconstruction: Tracker ID 5404 phases",
      "Design, procurement and construction phases recorded for the pool and bathhouse "
      "reconstruction, against the reported reopening date.",
      "Phase dates read directly from the Capital Project Tracker record.",
      "project phase", "NYC Parks Capital Project Tracker 4hcv-tc5r; NYT 28 Jun 2012",
      pdf_, case_id=CID, board=B2)
    print(f"    5404 totalfunding displayed: {r.get('totalfunding')}")

# ---- B3 attendance ---------------------------------------------------------
o = pd.read_csv(f"{T}/MCP_attendance_jvwx-xnsr.csv", low_memory=False)
n = pd.read_csv(f"{T}/MCP_attendance_82jf-bykm.csv", low_memory=False)
o["date"] = pd.to_datetime(o["date"]).dt.normalize()
n["date"] = pd.to_datetime(n["observationdate"]).dt.normalize()
# several operational columns arrive as text; coerce before any aggregation
for c in ("attendance", "poolopenpercent", "lifeguardcount", "supervisorcount", "temperature"):
    if c in n.columns:
        n[c] = pd.to_numeric(n[c], errors="coerce")
nd = n.groupby("date", as_index=False).agg(
    attendance=("attendance","sum"), sessions=("sessiontype","size"),
    poolopenpercent=("poolopenpercent","mean"), lateopen=("lateopen","max"),
    lifeguardcount=("lifeguardcount","sum"), temperature=("temperature","mean"),
    weatherconditions=("weatherconditions","first"))
ov = sorted(set(o.date) & set(nd.date))
aud = o[o.date.isin(ov)][["date","attendance"]].rename(columns={"attendance":"jvwx_daily"}) \
        .merge(nd[["date","attendance"]].rename(columns={"attendance":"82jf_session_sum"}), on="date")
aud["difference"] = aud["82jf_session_sum"] - aud["jvwx_daily"]
aud.to_csv(os.path.join(C.board_dir(CID,B3),"data","MCP_2022_overlap_audit.csv"), index=False)
equiv = bool((aud.difference == 0).all())
print(f"    2022 overlap: {len(aud)} days, identical after session-sum = {equiv}")

comb = pd.concat([o[~o.date.isin(ov)][["date","attendance"]].assign(source="jvwx-xnsr (daily)"),
                  nd[["date","attendance"]].assign(source="82jf-bykm (sessions summed to daily)")],
                 ignore_index=True).sort_values("date")
comb["year"] = comb.date.dt.year
yr = comb.groupby(["year","source"], as_index=False).agg(
    total_attendance=("attendance","sum"), open_days=("date","nunique"))
yr.to_csv(os.path.join(C.board_dir(CID,B3),"data","MCP_annual_attendance.csv"), index=False)
fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
p = yr.pivot_table(index="year", columns="source", values="total_attendance", aggfunc="sum").fillna(0)
bot = np.zeros(len(p))
for i,c in enumerate(p.columns):
    ax.bar(p.index, p[c], bottom=bot, color=[F.TEAL,F.ORANGE][i], width=.66, label=c)
    bot += p[c].values
for x,v in zip(p.index, bot):
    ax.text(x, v*1.02, f"{int(v):,}", ha="center", fontsize=7.4, color=F.INK)
ax.set_ylabel("Total recorded attendance", fontsize=9, color=F.INK_2); L._ax(ax)
ax.legend(frameon=False, fontsize=7.4, loc="upper left")
ax2 = ax.twinx()
od = yr.groupby("year")["open_days"].sum()
ax2.plot(od.index, od.values, color=F.INK_2, lw=1.2, marker="o", ms=3.4, ls="--")
ax2.set_ylabel("Open days", fontsize=8.6, color=F.INK_2); ax2.tick_params(labelsize=7.6, colors=F.INK_2)
for sp in ("top","left"): ax2.spines[sp].set_visible(False)
ax.set_title("McCarren Pool: recorded attendance and open days by season",
             fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
F.source_line(fig, "NYC Parks pool attendance: jvwx-xnsr (2017–2022, daily) and 82jf-bykm "
              f"(2022–2025, by session). Sessions summed to daily. 2022 overlap audited on "
              f"{len(aud)} shared days: session sums reproduce the daily file exactly "
              f"({'0 differences' if equiv else 'DIFFERENCES PRESENT'}), so 2022 is counted "
              "once from the session file. This documents post-reopening use only; it does "
              "not measure change from the 2012 renovation.")
fig.tight_layout(rect=(0,.12,1,1))
F.export(fig, os.path.join(C.board_dir(CID,B3),"figures"), "MCP_F07_annual_attendance",
  "McCarren Pool: recorded attendance and open days by season",
  "Seasonal totals from the two official attendance files, harmonised to a daily unit "
  "after an audited 2022 overlap.",
  "82jf-bykm summed from session to daily; the 2022 overlap verified to reproduce "
  "jvwx-xnsr exactly, then counted once.",
  "recorded attendance; open days", "NYC Parks jvwx-xnsr; 82jf-bykm", yr, case_id=CID, board=B3)

# seasonal daily curves by year
fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
comb["doy"] = comb.date.dt.dayofyear
cmap = plt.cm.YlGnBu(np.linspace(.35, .95, comb.year.nunique()))
for i,(y,g) in enumerate(comb.groupby("year")):
    g = g.sort_values("doy")
    ax.plot(g.doy, g.attendance, lw=1.2, color=cmap[i], label=str(y))
ax.set_xlabel("Day of year", fontsize=9, color=F.INK_2)
ax.set_ylabel("Daily attendance", fontsize=9, color=F.INK_2); L._ax(ax)
ax.legend(frameon=False, fontsize=7.2, ncol=3, title="season", title_fontsize=7.4)
ax.set_title("McCarren Pool: daily attendance within each season",
             fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
F.source_line(fig, "NYC Parks pool attendance files. Seasons differ in length and in "
              "operating conditions; curves are not normalised.")
fig.tight_layout(rect=(0,.08,1,1))
F.export(fig, os.path.join(C.board_dir(CID,B3),"figures"), "MCP_F08_seasonal_curves",
  "McCarren Pool: daily attendance within each season",
  "Daily recorded attendance plotted by day of year for every observed season.",
  "Harmonised daily series; no smoothing.", "daily attendance",
  "NYC Parks jvwx-xnsr; 82jf-bykm", comb[["date","year","doy","attendance","source"]],
  case_id=CID, board=B3)

# operations: attendance vs pool-open percent / late open
ops = nd.dropna(subset=["attendance"]).copy()
ops["lateopen_flag"] = ops["lateopen"].astype(str).str.lower().isin(["true","1"])
grp = ops.groupby("lateopen_flag", as_index=False).agg(
    n_days=("date","size"), median_attendance=("attendance","median"),
    median_open_pct=("poolopenpercent","median"))
grp.to_csv(os.path.join(C.board_dir(CID,B3),"data","MCP_operations_summary.csv"), index=False)
fig, ax = plt.subplots(figsize=C.ASPECTS["3:2"])
sc = ax.scatter(ops.poolopenpercent, ops.attendance, s=16,
                c=ops.lateopen_flag.map({True:F.RUST, False:F.TEAL}), alpha=.7)
ax.set_xlabel("Pool open percent (daily mean across sessions)", fontsize=9, color=F.INK_2)
ax.set_ylabel("Daily attendance", fontsize=9, color=F.INK_2); L._ax(ax)
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([],[],ls="",marker="o",ms=5,color=F.TEAL,label="opened on time"),
                   Line2D([],[],ls="",marker="o",ms=5,color=F.RUST,label="late opening")],
          frameon=False, fontsize=7.6)
ax.set_title("McCarren Pool: attendance against operating conditions",
             fontsize=11, color=F.INK, loc="left", pad=8, weight="bold")
F.source_line(fig, "NYC Parks 82jf-bykm (2022–2025). Descriptive association only; no "
              "causal claim is made about operating conditions and attendance.")
fig.tight_layout(rect=(0,.08,1,1))
F.export(fig, os.path.join(C.board_dir(CID,B3),"figures"), "MCP_F09_operations",
  "McCarren Pool: attendance against operating conditions",
  "Daily attendance plotted against pool-open percent, distinguishing late openings.",
  "Session records aggregated to daily; descriptive only.",
  "daily attendance; pool open percent", "NYC Parks 82jf-bykm",
  ops[["date","attendance","poolopenpercent","lateopen_flag","lifeguardcount","temperature"]],
  case_id=CID, board=B3)

L.advan_index(CID,B3); L.advan_season(CID,B3); L.pip_timelines(CID,B3)
L.origin_and_composition(CID,B3)
n_ = F.flush_manifest(); print(f"\nMCP assets done; manifest {n_}")
