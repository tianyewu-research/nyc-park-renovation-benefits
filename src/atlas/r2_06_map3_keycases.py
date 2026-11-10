"""Round 2 Map 3 — selected candidate projects, labelled by Map_Label_No only."""
import os, sys, warnings
warnings.filterwarnings("ignore")
import geopandas as gpd, pandas as pd, matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
sys.path.insert(0, os.path.dirname(__file__))
import atlas_style_round2 as S

G = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
rd = lambda l: gpd.read_file(G, layer=l)
boro, parks, kc = rd("boroughs"), rd("parks_properties"), rd("key_case_projects")
kc["Map_Label_No"] = pd.to_numeric(kc["Map_Label_No"], errors="coerce").astype("Int64")
kc = kc.sort_values("Map_Label_No")

fig = plt.figure(figsize=(21.5, 14.2))
gs = GridSpec(1, 2, figure=fig, width_ratios=[1.28, 1.0], wspace=.03,
              left=.022, right=.985, top=.885, bottom=.10)
ax = fig.add_subplot(gs[0, 0])
boro.plot(ax=ax, facecolor=S.LAND, edgecolor="white", lw=1.6, zorder=1)
parks.plot(ax=ax, facecolor="#e3ece0", edgecolor="none", zorder=2)
boro.boundary.plot(ax=ax, color=S.SHORE, lw=1.0, zorder=3)
kc.plot(ax=ax, color=S.KEY_CASE, markersize=210, edgecolor="white",
        linewidth=1.5, zorder=6)
for _, r in kc.iterrows():
    ax.annotate(str(r["Map_Label_No"]), (r.geometry.x, r.geometry.y), fontsize=8.6,
                weight="bold", color="white", ha="center", va="center", zorder=7)
S.blank(ax); S.north_arrow(ax, x=.94); S.scale_bar(ax, 2, x=.045, y=.035)
for _, r in boro.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r["boroname"], (c.x, c.y), fontsize=10.5, weight="bold",
                color="#878984", ha="center", zorder=5)

# companion table
axt = fig.add_subplot(gs[0, 1]); axt.axis("off")
pi = pd.read_excel("outputs/atlas/NYC_Green_Space_Renovation_Inventory_round2.xlsx",
                   sheet_name="Key Cases View")
pi["Map_Label_No"] = pd.to_numeric(pi["Map_Label_No"], errors="coerce").astype("Int64")
pi = pi.sort_values("Map_Label_No")
yr = pd.to_datetime(pi["Administrative_Completion_Date"], errors="coerce").dt.year
tbl = pd.DataFrame({
    "No": pi["Map_Label_No"].astype(str),
    "Project": pi["Project_Title"].astype(str).str.slice(0, 40),
    "Borough": pi["Borough"].astype(str).str.split(r"[,/]").str[0].str.slice(0, 13),
    "Adm. yr": yr.astype("Int64").astype(str).replace("<NA>", "—"),
    "Ownership": pi["Ownership_Model"].astype(str).str.slice(0, 26),
    "Designer / firm": pi["Designer_or_Firm"].fillna("not verified").astype(str).str.slice(0, 16),
})
t = axt.table(cellText=tbl.values, colLabels=tbl.columns, loc="upper center",
              cellLoc="left", colWidths=[.045, .335, .115, .075, .245, .155])
t.auto_set_font_size(False); t.set_fontsize(8.0); t.scale(1, 1.42)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#e2e4df"); cell.set_linewidth(.6)
    if r == 0:
        cell.set_facecolor(S.TEAL_L); cell.set_text_props(weight="bold", color=S.INK)
    elif r % 2 == 0:
        cell.set_facecolor("#faf9f6")
axt.text(.0, .985 - .0385 * (len(tbl) + 2),
         "Opening year is ADMINISTRATIVE completion, not a verified public opening.\n"
         "Designer / firm is blank because no open dataset carries it; these are\n"
         "enrichment targets, not findings. 'Candidate — unverified' means the row\n"
         "was selected by the stated filter, not confirmed as a high-profile project.",
         transform=axt.transAxes, fontsize=8.4, va="top", color=S.INK_2, linespacing=1.6)

S.title_block(fig, "Selected High-Profile and Representative Green-Space Projects",
    f"{len(kc)} candidate projects, {2010}–{2026}, balanced across boroughs and governance "
    "models. Labelled by number only; names are in the companion table.", ts=20)
S.footer(fig,
    "This is an ILLUSTRATIVE candidate set chosen by a stated, auditable filter "
    "(borough balance x governance model x largest recorded exact funding), not a "
    "thesis sample and not a ranking. No award, PDC or design-publication evidence has "
    "been checked yet, so every row carries Key_Case_Flag = 'Candidate — unverified'. "
    "Map_Label_No matches the Key Cases View sheet one-to-one.", y0=.068)
S.save(fig, "map3_key_projects_2010_2026")
print(f"  labelled {len(kc)} cases; labels unique: {kc['Map_Label_No'].is_unique}")
print("  boroughs:", pi['Borough'].astype(str).str.split(r'[,/]').str[0].value_counts().to_dict())
