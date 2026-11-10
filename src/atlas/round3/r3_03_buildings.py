"""Round 3, step 3 — cartographic derivative of the 1.08M building footprints.

The full raw file is preserved untouched at data/raw/atlas_round3/buildings.geojson.
Individual footprints are not legible at citywide scale and will not be pretended
to be. This builds ONE documented derivative:

  buildings_cartographic : a 500 ft grid holding the share of each cell covered
                           by building footprint, i.e. built mass, not buildings.

Footprints are streamed with fiona so the 1 GB file is never fully loaded, and
are reprojected per feature. Cell coverage is capped at 1.0.
"""
import json, os, warnings
warnings.filterwarnings("ignore")
import fiona, geopandas as gpd, numpy as np, pandas as pd
from pyproj import Transformer
from shapely.geometry import box, shape

RAW, INT = "data/raw/atlas_round3", "data/interim/atlas_round3"
R2 = "outputs/atlas/gis/nyc_green_space_renovation_atlas_round2.gpkg"
CELL = 500.0     # feet
CRS = "EPSG:2263"

boro = gpd.read_file(R2, layer="boroughs")
minx, miny, maxx, maxy = boro.total_bounds
nx = int(np.ceil((maxx - minx) / CELL)); ny = int(np.ceil((maxy - miny) / CELL))
acc = np.zeros((ny, nx), dtype=np.float64)
print(f"grid {nx} x {ny} cells at {CELL:.0f} ft")

tf = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
n_read = n_used = n_bad = 0
with fiona.open(f"{RAW}/buildings.geojson") as src:
    total = len(src)
    for feat in src:
        n_read += 1
        try:
            g = shape(feat["geometry"])
            if g.is_empty: n_bad += 1; continue
            c = g.centroid
            x, y = tf.transform(c.x, c.y)
            a = float(feat["properties"].get("shape_area") or 0)   # source sq ft
            if a <= 0:
                n_bad += 1; continue
            j = int((x - minx) // CELL); i = int((y - miny) // CELL)
            if 0 <= i < ny and 0 <= j < nx:
                acc[i, j] += a; n_used += 1
        except Exception:
            n_bad += 1
        if n_read % 200_000 == 0:
            print(f"  {n_read:,}/{total:,}", flush=True)

cov = np.clip(acc / (CELL * CELL), 0, 1.0)
cells, vals = [], []
for i in range(ny):
    for j in range(nx):
        if cov[i, j] > 0.004:
            cells.append(box(minx + j*CELL, miny + i*CELL, minx + (j+1)*CELL, miny + (i+1)*CELL))
            vals.append(cov[i, j])
grid = gpd.GeoDataFrame({"built_coverage": vals}, geometry=cells, crs=CRS)
land = boro.union_all()
grid = grid[grid.intersects(land)].copy()
grid.to_file(f"{INT}/buildings_cartographic.gpkg", layer="buildings_cartographic",
             driver="GPKG")

qa = dict(raw_features=total, streamed=n_read, used=n_used, skipped=n_bad,
          grid_cells_written=len(grid), cell_ft=CELL,
          method=("streamed with fiona; per-feature centroid reprojected 4326->2263; "
                  "source shape_area (sq ft) accumulated per 500 ft cell; "
                  "built_coverage = accumulated footprint area / cell area, capped at 1.0; "
                  "cells below 0.4% coverage dropped"),
          coverage_min=float(grid.built_coverage.min()),
          coverage_median=float(grid.built_coverage.median()),
          coverage_max=float(grid.built_coverage.max()))
pd.DataFrame([qa]).to_csv(f"{INT}/buildings_cartographic_qa.csv", index=False)
print(f"\nraw {total:,} -> used {n_used:,} (skipped {n_bad:,}) -> {len(grid):,} grid cells")
print(f"coverage median {qa['coverage_median']:.3f}  max {qa['coverage_max']:.3f}")
