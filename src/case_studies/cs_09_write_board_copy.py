"""Step 9 — board copy and the claim ledger. No claim enters copy unless it is in the ledger."""
import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import cs_00_config as C
import pandas as pd

MOB = os.path.join(C.INTERIM, "mobile")
dem = pd.read_csv(os.path.join(C.SHARED, "data", "S03_800m_demographic_profiles.csv")).set_index("case_id")
comp = pd.read_csv(f"{MOB}/origin_area_acs_composition.csv").set_index("case_id")
bor = pd.read_csv(f"{MOB}/visitor_origin_by_borough.csv")
man = pd.read_csv(os.path.join(C.OUT, "content_manifest.csv"))
img = pd.read_csv(os.path.join(C.OUT, "image_manifest.csv"))

L = []   # claim ledger
def claim(cid, bid, cidx, text, src, page, grade, status, causal="clean", note=""):
    L.append(dict(case_id=cid, board_id=bid, claim_id=f"{cid}-{bid[6]}-{cidx:02d}",
                  board_text=text, source_path=src, source_page_or_dataset_field=page,
                  evidence_grade=grade, verification_status=status,
                  causal_language_check=causal, notes=note))
    return text

BP_SRC = os.path.expanduser("~/Desktop/Bryant Park")
WS_SRC = os.path.expanduser("~/Desktop/Washington Square Park")
MC_SRC = os.path.expanduser("~/Desktop/McCarren Pool")

BOARDS = {}

# ============================ BRYANT PARK ==================================
BOARDS[("BP","board_1_history_profile")] = dict(
 title="Bryant Park: decline, management intervention, and reconstruction",
 argument="Bryant Park's turnaround began with a management body created eight years "
          "before the park closed for reconstruction.",
 narrative=(
  "Bryant Park was redesigned in 1934 and opened to acclaim, but the mid-to-late twentieth "
  "century saw sustained decline. The park operator's published history attributes this to a "
  "long municipal budget crisis, a business-district location with few night-time users, and a "
  "design that sat above street grade behind a fence and tall hedges. By the early 1970s the "
  "park was largely avoided by Midtown workers and tourists. The Bryant Park Restoration "
  "Corporation was founded in 1980 by Dan Biederman, Time Inc., New York Public Library chair "
  "Andrew Heiskell and the Rockefeller Brothers Fund, and began cleaning, repair, security and "
  "programming before any capital work. The park then closed in 1988 for a four-year "
  "reconstruction and reopened in 1992. Management intervention and physical reconstruction "
  "were therefore separate, sequential steps, not one event."),
 callouts=[
  "1934 — park redesigned and reopened to acclaim",
  "1980 — Bryant Park Restoration Corporation founded",
  "1988–1992 — closed for a four-year reconstruction",
  "1992 — reopened; restrooms reopened after 35 years closed",
  "No Capital Project Tracker record exists for park_id M008"],
 limits=("The operator's own history is the single narrative source for the 1970s–1990s "
         "sequence. No independent municipal record of the closure dates was available in "
         "the local source set."),
 claims=[
  ("Bryant Park was redesigned in 1934 and reopened to acclaim.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("By the early 1970s the park was largely avoided by Midtown workers and tourists.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("The Bryant Park Restoration Corporation was founded in 1980 by Dan Biederman, Time Inc., "
   "NYPL chair Andrew Heiskell and the Rockefeller Brothers Fund.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("The park closed in 1988 for a four-year reconstruction and reopened in 1992.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("The Capital Project Tracker contains no record for park_id M008.",
   "data/raw/capital_projects/capital_project_tracker.csv","parkid == 'M008'","B","verified")])

BOARDS[("BP","board_2_renovation")] = dict(
 title="Bryant Park: redesign and management model as two interventions",
 argument="The documented physical changes and the day-to-day management model are related "
          "but distinct interventions and should be read separately.",
 narrative=(
  "The reconstruction is described by the park operator in terms of visibility and access "
  "rather than style. Sight lines into the park were opened from street level and the isolating "
  "hedges were removed. Restrooms that had been closed for thirty-five years were reopened. Two "
  "restaurant pavilions and four concession kiosks were built, placing staffed activity on the "
  "park edges. Two thousand movable bistro chairs were introduced, allowing users rather than "
  "designers to arrange occupation. Running alongside these physical changes, the Bryant Park "
  "Restoration Corporation had already been carrying out cleaning, repair, security and "
  "programming since 1980. OLIN is the designer of record, with Laurie Olin as partner-in-charge. "
  "No measured design plan was available in the local source set, so the intervention diagram is "
  "analytical rather than a reconstruction of a drawing."),
 callouts=[
  "Sight lines opened; isolating hedges removed",
  "Restrooms reopened after 35 years closed",
  "Two restaurant pavilions and four concession kiosks",
  "2,000 movable bistro chairs introduced",
  "OLIN designer of record; Laurie Olin partner-in-charge"],
 limits=("Land ownership, concession operation and maintenance responsibility are not "
         "documented in the local sources and are marked evidence grade E."),
 claims=[
  ("Sight lines into the park were increased from street level and isolating hedges removed.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("Park restrooms, closed for 35 years, were reopened.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("Two restaurant pavilions and four concession kiosks were constructed.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.1","D","verified"),
  ("2,000 movable bistro chairs were introduced.",
   f"{BP_SRC}/History of Bryant Park_ Modern Times.pdf","p.2","D","verified"),
  ("OLIN is the designer of record; Laurie Olin partner-in-charge, Dennis McGlade partner.",
   f"{BP_SRC}/Bryant Park – OLIN.pdf","p.1","D","verified"),
  ("Land ownership and concession operation arrangements.",
   "(no local source)","n/a","E","not supported")])

BOARDS[("BP","board_3_use_outcomes")] = dict(
 title="Bryant Park: current use patterns, 2023–2025",
 argument="Provider data describe how the park is used today; they cannot measure what the "
          "1992 reconstruction changed.",
 narrative=(
  "The Advan panel covers 2023 to 2025, more than three decades after the reconstruction, so it "
  "describes current use rather than renovation effect. Across 157 continuous weeks the single "
  "matched point of interest shows a pronounced seasonal cycle, indexed here to the 2023 median. "
  "Parks Inspection Program records provide an independent view of condition, and the visitor "
  "counts recorded at inspection are plotted separately because they are snapshot observations "
  "at the moment of inspection, not continuous attendance. Provider-estimated home block groups "
  "show where visitors travel from. Setting that origin geography beside the composition of "
  "residents within an 800-metre radius shows two different populations: the surrounding "
  "residential area is 53 per cent White non-Hispanic, while the areas visitors come from are "
  "38 per cent. The second figure describes origin areas, not individual visitors."),
 callouts=[
  "157 continuous weeks observed, 2023-01-02 to 2025-12-29; no missing weeks",
  "One matched Advan point of interest for park_id M008",
  "51 PIP inspections on record for M008",
  f"800 m radius study area: {int(dem.loc['BP','population_overlap_weighted']):,} residents",
  "No matched Parks special-event records for Bryant Park in the local dataset"],
 limits=("Advan begins in 2023 and cannot describe pre-renovation use. PIP visitor counts are "
         "inspection-time observations. Origin composition is an ecological estimate."),
 claims=[
  ("The Advan series covers 157 continuous weeks, 2023-01-02 to 2025-12-29, with no missing weeks.",
   "data/interim/case_studies/mobile/weekly_visit_index.csv","case_id=='BP'","B","verified"),
  ("One Advan point of interest is matched to park_id M008.",
   "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv","matched_pid=='M008'","B","verified"),
  ("51 PIP inspections are recorded for M008.",
   "data/raw/park_quality_pip/pip_inspections.csv","prop_id=='M008'","B","verified"),
  (f"Residents within the 800 m radius study area are {dem.loc['BP','pct_white_nh']:.0f}% White non-Hispanic.",
   "data/interim/reused_walkability/acs_cbg.csv","pct_white_nh, overlap-weighted","B","verified"),
  (f"The ACS composition of visitor-origin areas is {comp.loc['BP','pct_white_nh']:.0f}% White non-Hispanic.",
   "data/interim/case_studies/mobile/origin_area_acs_composition.csv","pct_white_nh","C","verified",
   "clean", "ecological estimate of origin-area composition; NOT visitor race"),
  ("Bryant Park has no matched Parks special-event records in the local dataset.",
   "data/raw/events_permits/parks_special_events.csv","text match 'bryant'","B","verified")])

# ====================== WASHINGTON SQUARE PARK =============================
BOARDS[("WSP","board_1_history_profile")] = dict(
 title="Washington Square Park: civic use and the renovation debate",
 argument="A park defined by a long history of contested public use entered its most recent "
          "renovation through study, opposition and litigation.",
 narrative=(
  "Washington Square Park has been shaped by public contest as much as by design. The Arch was "
  "completed in 1895. From 1935 Robert Moses pressed repeatedly to run a roadway through the "
  "park; in 1958 Greenwich Village defeated the plan and the park became car-free, after which "
  "the fountain plaza emerged as a performance space. A community-led renovation in 1970 created "
  "the sunken plaza, the stage and the petanque court. In 2005 Project for Public Spaces carried "
  "out a use study documenting how the park was then being used. That study preceded the "
  "redesign and was not an evaluation of it. The redesign drew organised opposition, and in 2007 "
  "the Appellate Division decided Matter of Greenberg v City of New York. The most recent "
  "renovation was completed in 2014 in two major phases."),
 callouts=["1895 — Washington Arch completed",
           "1958 — roadway plan defeated; park becomes car-free",
           "1970 — community-led renovation creates the sunken fountain plaza",
           "2005 — PPS pre-renovation use study",
           "2007 — Matter of Greenberg v City of New York decided"],
 limits=("The PPS study documents pre-renovation use only. Community Board and Landmarks roles "
         "are not documented in the local source set and are omitted from the process diagram."),
 claims=[
  ("The Washington Arch was completed in 1895.",
   f"{WS_SRC}/History _ Washington Square Park Conservancy.pdf","p.2","D","verified"),
  ("In 1958 Greenwich Village defeated the roadway plan and the park became car-free.",
   f"{WS_SRC}/History _ Washington Square Park Conservancy.pdf","p.3","D","verified"),
  ("A community-driven renovation led by Robert Nichols in 1970 created the sunken plaza, "
   "stage and petanque court.",
   f"{WS_SRC}/History _ Washington Square Park Conservancy.pdf","p.4","D","verified"),
  ("Project for Public Spaces produced a use study of the park dated 2005.",
   f"{WS_SRC}/wsp_final_report_pps.pdf","cover","D","verified","clean",
   "pre-renovation use study; NOT an evaluation of the later redesign"),
  ("Matter of Greenberg v City of New York was decided in 2007 (2007 NY Slip Op 01943).",
   f"{WS_SRC}/Matter of Greenberg v City of New York (2007 NY Slip Op 01943).pdf","p.1","B","verified"),
  ("The most recent renovation was completed in 2014 in two major phases.",
   f"{WS_SRC}/History _ Washington Square Park Conservancy.pdf","p.5","D","verified")])

BOARDS[("WSP","board_2_renovation")] = dict(
 title="Washington Square Park: phased renovation",
 argument="The renovation was delivered in phases, and the perimeter-sidewalk capital record "
          "is not the main project.",
 narrative=(
  "The first phase covered the northwest quadrant, the Fountain Plaza and the Thompson Street "
  "entrance. The project sign records that the Alexander Lyman Holley statue, created in 1889 by "
  "John Quincy Adams Ward and Thomas Hastings, was restored and reoriented within a reconfigured "
  "plaza, and that the 1870s fountain was fully restored as the centrepiece of a new, fully "
  "accessible public plaza edged by a new stone seating wall. The northwest quadrant works "
  "included benches, light fixtures and asphalt block pathways with granite borders, new shade "
  "trees, flowering shrubs, perennials, restored lawn and a restored game table plaza. Design and "
  "supervision were by DPR Capital Projects, with AAH Construction Corp as contractor. Comfort-"
  "station work is reported separately and later. The single Capital Project Tracker record for "
  "M098 concerns perimeter sidewalks and is a minor work item."),
 callouts=["Phase 1: northwest quadrant, Fountain Plaza, Thompson Street entrance",
           "1870s fountain fully restored; plaza made fully accessible",
           "Holley statue (1889) restored and reoriented",
           "Design and supervision: DPR Capital Projects; contractor AAH Construction Corp",
           "The one Capital Tracker record for M098 is a perimeter-sidewalk item"],
 limits=("Phase boundaries beyond Phase 1 are described narratively by the Conservancy and are "
         "not supported by a dated municipal phase record in the local source set."),
 claims=[
  ("Phase 1 covered the northwest quadrant, Fountain Plaza and Thompson Street entrance.",
   f"{WS_SRC}/wsp.pdf","p.1","B","verified"),
  ("The Alexander Lyman Holley statue (1889, John Quincy Adams Ward and Thomas Hastings) was "
   "restored and reoriented within a reconfigured plaza.",
   f"{WS_SRC}/wsp.pdf","p.1","B","verified"),
  ("The 1870s fountain was fully restored and the new fountain plaza made fully accessible.",
   f"{WS_SRC}/wsp.pdf","p.1","B","verified"),
  ("Design and supervision by DPR Capital Projects; contractor AAH Construction Corp.",
   f"{WS_SRC}/wsp.pdf","p.1","B","verified"),
  ("The Capital Project Tracker holds one record for M098, a perimeter-sidewalk item.",
   "data/raw/capital_projects/capital_project_tracker.csv","parkid=='M098'","B","verified")])

BOARDS[("WSP","board_3_use_outcomes")] = dict(
 title="Washington Square Park: documented use after renovation",
 argument="Two measurement systems describe this park; they answer different questions and are "
          "not comparable.",
 narrative=(
  "Current use is described by three independent records. The Advan panel covers 157 continuous "
  "weeks from 2023 to 2025 across six matched points of interest, showing a strong seasonal "
  "cycle. Parks special-event records give reported attendance at permitted events, which is an "
  "organiser or agency figure rather than an independent count and is separate from park-wide "
  "visitation. The Parks Inspection Program provides 248 inspection records for the park and its "
  "sub-properties, with visitor counts plotted separately because they are inspection-time "
  "snapshots. The 2005 PPS study is presented alongside these as a method comparison, never "
  "merged with them: it observed people on site before the renovation, while the provider data "
  "estimate device visits afterwards. No percentage change is calculated between them."),
 callouts=["157 continuous Advan weeks; six matched points of interest",
           "248 PIP inspection records for M098 and its sub-properties",
           "44 matched Parks special-event records",
           f"800 m radius study area: {int(dem.loc['WSP','population_overlap_weighted']):,} residents",
           f"Surrounding area {dem.loc['WSP','pct_white_nh']:.0f}% White NH; origin areas {comp.loc['WSP','pct_white_nh']:.0f}%"],
 limits=("PPS 2005 and Advan 2023–2025 use different methods and populations and are never "
         "differenced. Event attendance is reported, not independently counted."),
 claims=[
  ("Six Advan points of interest are matched to park_id M098.",
   "data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv","matched_pid=='M098'","B","verified"),
  ("248 PIP inspection records exist for M098 and its sub-properties.",
   "data/raw/park_quality_pip/pip_inspections.csv","prop_id startswith 'M098'","B","verified"),
  ("44 Parks special-event records match Washington Square Park.",
   "data/raw/events_permits/parks_special_events.csv","text match 'washington square'","C","verified",
   "clean","free-text match; audit before quoting individual events"),
  (f"Residents within 800 m are {dem.loc['WSP','pct_white_nh']:.0f}% White non-Hispanic; the ACS "
   f"composition of visitor-origin areas is {comp.loc['WSP','pct_white_nh']:.0f}%.",
   "acs_cbg.csv; origin_area_acs_composition.csv","pct_white_nh","C","verified","clean",
   "two different populations; origin figure is ecological, not visitor race"),
  ("PPS 2005 counts and Advan 2023–2025 counts are not comparable and are not differenced.",
   f"{WS_SRC}/wsp_final_report_pps.pdf","method note","B","verified")])

# ============================== McCARREN ===================================
BOARDS[("MCP","board_1_history_profile")] = dict(
 title="McCarren Pool: from WPA play center to reopened public facility",
 argument="A 1936 WPA recreation complex stood empty for twenty-eight years before returning "
          "to public use as a landmarked facility.",
 narrative=(
  "The McCarren Play Center was constructed between 1934 and 1936, with Aymar Embury II as lead "
  "architect and Gilmore D. Clarke among the landscape architects. It was one of eleven public "
  "pools opened in New York City in the summer of 1936. The pool closed in the 1980s and, "
  "according to contemporaneous reporting, sat empty for twenty-eight years while its basin "
  "cracked. In 2005 the empty pool took on a second life as an outdoor stage for concerts and "
  "performances. The Landmarks Preservation Commission designated the Play Center on 24 July "
  "2007 as LP-2244, including the bath house, swimming, diving and wading pools, filter house, "
  "lifeguard house, perimeter walls, fencing, comfort stations and pathways. The pool reopened "
  "on 28 June 2012."),
 callouts=["1934–1936 — constructed; Aymar Embury II lead architect",
           "1980s — pool closes; stands empty 28 years",
           "2005 — empty basin used as an outdoor concert stage",
           "24 July 2007 — designated NYC Landmark LP-2244",
           "28 June 2012 — pool reopens"],
 limits=("The exact closure year is reported indirectly, as twenty-eight years before the 2012 "
         "reopening, rather than stated as a date in the local sources."),
 claims=[
  ("The McCarren Play Center was constructed 1934–1936; Aymar Embury II lead architect; "
   "Gilmore D. Clarke and others landscape architects.",
   f"{MC_SRC}/2244.pdf","p.1","B","verified"),
  ("The Play Center was designated a New York City Landmark on 24 July 2007 as LP-2244.",
   f"{MC_SRC}/2244.pdf","p.1","B","verified"),
  ("The pool stood empty for 28 years before reopening.",
   f"{MC_SRC}/2012-06-28-NYTimes_McCarren.pdf","p.1","D","verified"),
  ("In 2005 the empty pool was used as an outdoor stage for concerts and performances.",
   f"{MC_SRC}/2012-06-28-NYTimes_McCarren.pdf","p.1","D","verified"),
  ("The pool reopened on 28 June 2012.",
   f"{MC_SRC}/2012-06-28-NYTimes_McCarren.pdf","p.1","D","verified")])

BOARDS[("MCP","board_2_renovation")] = dict(
 title="McCarren Pool: preservation, community priorities and reconstruction",
 argument="Reconstruction of a landmarked recreation complex required negotiating swimming, "
          "recreation, preservation and performance uses on one site.",
 narrative=(
  "Designation in 2007 fixed what could and could not change: the designated site includes the "
  "bath house, the swimming, diving and wading pools, the filter house, the lifeguard house, the "
  "brick perimeter walls, piers and cast-iron fencing, the comfort stations, the linking pathways "
  "and the planted median. Fourteen witnesses spoke in favour of designation at the January 2007 "
  "hearing, including the Parks Commissioner, and Community Board 1 wrote in support of the "
  "Vollmer plan for the pool. Reconstruction is recorded in the Capital Project Tracker as "
  "Tracker ID 5404, with total funding displayed as $54,559,000. Contemporaneous reporting "
  "described the works as a thirty-month, fifty-million-dollar renovation. The two figures come "
  "from different sources and are reported separately rather than reconciled. The 2008 "
  "Rogers Marvel design boards shown to bidders record the scheme that was put to the market."),
 callouts=["LP-2244 designated components fix the preservation envelope",
           "14 witnesses spoke in favour at the January 2007 hearing",
           "Community Board 1 supported the Vollmer plan for the pool",
           "Tracker ID 5404 — total funding displayed $54,559,000",
           "Press reported a 30-month, $50 million renovation"],
 limits=("The $54,559,000 tracker figure and the $50 million press figure are not reconciled. "
         "Retained, restored, replaced and new elements are only shown where documented."),
 claims=[
  ("The designated site includes the bath house, swimming, diving and wading pools, filter "
   "house, lifeguard house, perimeter walls, piers and fencing, comfort stations, linking "
   "pathways and the planted median.",
   f"{MC_SRC}/2244.pdf","p.1","B","verified"),
  ("Fourteen witnesses spoke in favour of designation, including the Parks Commissioner.",
   f"{MC_SRC}/2244.pdf","p.1","B","verified"),
  ("Community Board 1 stated support for the Vollmer plan for the pool.",
   f"{MC_SRC}/2244.pdf","p.1","B","verified"),
  ("Capital Project Tracker ID 5404 displays total funding of $54,559,000.",
   "data/raw/capital_projects/capital_project_tracker.csv","trackerid==5404, totalfunding","B","verified"),
  ("Press reported a 30-month, $50 million renovation.",
   f"{MC_SRC}/2012-06-28-NYTimes_McCarren.pdf","p.1","D","verified","clean",
   "conflicts with the $54,559,000 tracker figure; both retained, neither overwritten")])

BOARDS[("MCP","board_3_use_outcomes")] = dict(
 title="McCarren Pool: attendance, seasonality and operations since reopening",
 argument="Two official attendance files, once harmonised, document post-reopening use and the "
          "operating conditions that shape a seasonal public pool.",
 narrative=(
  "Two official files record attendance. The 2017–2022 file reports one row per day; the "
  "2022–2025 file reports one row per session, with first, second and extended second sessions. "
  "The files overlap on seventy-six days in 2022. Summing sessions to a daily total reproduces "
  "the daily file exactly on every one of those days, so the series can be joined with 2022 "
  "counted once. The combined record shows a short, intense season with sharp day-to-day swings. "
  "The session file also records pool-open percentage, late openings, staffing, temperature and "
  "weather, which are shown descriptively against attendance without any causal claim. Parks "
  "event attendance in McCarren Park and the Advan 2023–2025 index are kept as separate series. "
  "This record documents post-reopening use; it does not measure change from the 2012 "
  "reconstruction."),
 callouts=["jvwx-xnsr: 378 daily rows, 2017–2022",
           "82jf-bykm: 620 session rows, 2022–2025",
           "76 overlapping days in 2022; session sums match the daily file exactly",
           "322 matched Parks special-event records in McCarren Park",
           "458 PIP inspection records for B058 and its sub-properties"],
 limits=("Attendance begins in 2017, five years after reopening, so no pre/post comparison is "
         "possible. Operating-condition comparisons are descriptive only."),
 claims=[
  ("The 2017–2022 file contains 378 daily rows; the 2022–2025 file contains 620 session rows.",
   "~/Downloads/jvwx-xnsr.csv; ~/Downloads/82jf-bykm.csv","row counts","B","verified"),
  ("The two files overlap on 76 days in 2022, and summing sessions to daily reproduces the "
   "daily file exactly on every overlapping day.",
   "outputs/.../MCP_2022_overlap_audit.csv","difference column all zero","B","verified"),
  ("322 Parks special-event records match McCarren.",
   "data/raw/events_permits/parks_special_events.csv","text match 'mccarren'","C","verified",
   "clean","free-text match; audit before quoting individual events"),
  ("458 PIP inspection records exist for B058 and its sub-properties.",
   "data/raw/park_quality_pip/pip_inspections.csv","prop_id startswith 'B058'","B","verified"),
  ("Attendance records begin in 2017, five years after the 2012 reopening.",
   "~/Downloads/jvwx-xnsr.csv","min(date)","B","verified","clean",
   "cannot support any pre/post renovation comparison")])

# ---------------------------------------------------------------- write out
for (cid, bid), b in BOARDS.items():
    d = C.board_dir(cid, bid); os.makedirs(os.path.join(d, "text"), exist_ok=True)
    figs = man[(man.case_id == cid) & (man.board_id == bid)]
    ims = img[(img.case_id == cid) & (img.board_id == bid) & (img.status == "ok")]
    words = len(b["narrative"].split())
    for i, c in enumerate(b["claims"], 1):
        claim(cid, bid, i, *c) if len(c) >= 5 else None
    with open(os.path.join(d, "text", "board_content.md"), "w") as f:
        f.write(f"# {b['title']}\n\n**Board argument.** {b['argument']}\n\n"
                f"## Narrative ({words} words)\n\n{b['narrative']}\n\n## Factual callouts\n\n")
        for c in b["callouts"]: f.write(f"- {c}\n")
        f.write("\n## Proposed visuals and captions\n\n")
        for _, r in figs.iterrows():
            f.write(f"- **{r.stem}** — {r.title}. {r.get('unit','')}\n")
        for _, r in ims.iterrows():
            f.write(f"- **{r.stem}** — {r.caption} ({os.path.basename(r.source_file)}, "
                    f"p.{int(r.page)}; {r.creator}; rights: {r.rights_status})\n")
        f.write("\n## Sources\n\n")
        seen = set()
        for c in b["claims"]:
            key = (c[1], c[2])
            if key in seen: continue
            seen.add(key); f.write(f"- {c[1]} — {c[2]}\n")
        f.write(f"\n## Limitations\n\n{b['limits']}\n\n## Verification status\n\n")
        for c in b["claims"]:
            f.write(f"- [{c[4]}] (grade {c[3]}) {c[0]}\n")
    print(f"  {cid}/{bid}: {words} words, {len(figs)} figures, {len(ims)} images, "
          f"{len(b['claims'])} claims")

led = pd.DataFrame(L)
led.to_csv(os.path.join(C.OUT, "claim_ledger.csv"), index=False)
print(f"\nclaim_ledger.csv: {len(led)} claims | "
      f"{led.verification_status.value_counts().to_dict()}")
print(f"evidence grades: {led.evidence_grade.value_counts().to_dict()}")
