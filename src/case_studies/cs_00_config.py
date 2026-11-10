"""Shared configuration for the three-case content package."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "outputs/case_studies_content_v1")
SHARED = os.path.join(OUT, "00_shared")
INTERIM = os.path.join(ROOT, "data/interim/case_studies")
os.makedirs(INTERIM, exist_ok=True)

sys.path.insert(0, os.path.join(ROOT, "src/atlas/round4"))

CASES = {
    "BP":  dict(name="Bryant Park", park_id="M008", folder_key="01_bryant_park",
                src=os.path.expanduser("~/Desktop/Bryant Park"),
                pip_match="exact"),
    "WSP": dict(name="Washington Square Park", park_id="M098",
                folder_key="02_washington_square_park",
                src=os.path.expanduser("~/Desktop/Washington Square Park"),
                pip_match="prefix"),
    "MCP": dict(name="McCarren Pool / McCarren Park", park_id="B058",
                folder_key="03_mccarren_pool",
                src=os.path.expanduser("~/Desktop/McCarren Pool"),
                pip_match="prefix"),
}
BOARDS = ["board_1_history_profile", "board_2_renovation", "board_3_use_outcomes"]

# raw / derived inputs, all read-only
P = dict(
    tracker="data/raw/capital_projects/capital_project_tracker.csv",
    parks_props="data/raw/capital_projects/parks_properties.csv",
    pip_insp="data/raw/park_quality_pip/pip_inspections.csv",
    pip_inv="data/raw/park_quality_pip/pip_inventory.csv",
    sp_events="data/raw/events_permits/parks_special_events.csv",
    permitted="data/raw/events_permits/nyc_permitted_events.csv",
    poi_week="data/interim/poi_week.csv.gz",
    crosswalk="data/raw/crosswalks/poi_property_crosswalk_canonical_100ft.csv",
    advan_dir="data/raw/advan_vintage_202606",
    acs="data/interim/reused_walkability/acs_cbg.csv",
    cbg="data/interim/reused_walkability/cbg_nyc.gpkg",
    atlas_r4="outputs/atlas/gis/nyc_green_space_atlas_round4.gpkg",
    atlas_r2="outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg",
    round3="data/interim/atlas_round3",
    mcp_att_old=os.path.expanduser("~/Downloads/jvwx-xnsr.csv"),
    mcp_att_new=os.path.expanduser("~/Downloads/82jf-bykm.csv"),
)
def p(key): return os.path.join(ROOT, P[key]) if not os.path.isabs(P[key]) else P[key]

# a saved webpage, cookie banner or browser chrome is not project evidence
EXCLUDE_AS_EVIDENCE = ["Januay102018_FCRC_Public_Meeting_Documents.pdf"]
EXCLUDE_REASON = ("January 2018 FCRC packet: not a Bryant Park agreement; excluded "
                  "from Bryant Park evidence by explicit instruction")

CRS_ANALYSIS, CRS_EXCHANGE = "EPSG:2263", "EPSG:4326"
BUFFERS_M = [400, 800]
FT_PER_M = 3.280839895
ADVAN_VINTAGE = "202606"
ADVAN_COVERAGE = "2023-01-02 to 2025-12-29 (157 weeks)"
RADIUS_LABEL = "{d} m radius study area"     # never 'walking catchment'

ASPECTS = {"4:3": (8.0, 6.0), "3:2": (9.0, 6.0), "1:1": (7.0, 7.0), "4:5": (6.4, 8.0)}

def board_dir(case_id, board):
    return os.path.join(OUT, CASES[case_id]["folder_key"], board)
