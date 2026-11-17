"""Per-unit monthly NDVI (MODIS MOD13Q1 v6.1, 250 m) for the HarvestStat units, via Google Earth Engine.

Needs a one-time `earthengine authenticate` and a Cloud project id in env EE_PROJECT. Only unit-level monthly
means leave Earth Engine (small); unit polygons are the public HarvestStat boundaries. Output:
data/interim/unit_month_ndvi.pkl (fnid, year, month, ndvi) and outputs/ndvi_extraction_log.txt.
Monthly composite = per-pixel max over the 16-day images in the month (suppresses cloud), then mean over each unit's
cropland-agnostic pixels (no crop mask yet: a stated limitation; a mask comes later).
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import ee
import geopandas as gpd
import pandas as pd

from common import HS_GPKG, INTERIM, OUT

Y0, Y1 = 2010, 2023
ee.Initialize(project=os.environ["EE_PROJECT"])
u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
g = gpd.read_file(HS_GPKG)
g = g[g.fnid.isin(u.fnid.unique())][["fnid", "geometry"]].reset_index(drop=True)
g["geometry"] = g.geometry.simplify(0.005)  # about 500 m; keeps request size small
coll = ee.ImageCollection("MODIS/061/MOD13Q1").select("NDVI")
t0 = time.time()


def one_month(ym):
    y, m = ym
    img = (coll.filterDate(f"{y}-{m:02d}-01", ee.Date(f"{y}-{m:02d}-01").advance(1, "month"))
           .max().multiply(0.0001).rename("ndvi"))
    out = []
    for i in range(0, len(g), 150):  # batches keep each request under Earth Engine's size limit
        fc = ee.FeatureCollection(g.iloc[i:i + 150].__geo_interface__)
        for f in img.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=250).getInfo()["features"]:
            p = f["properties"]
            out.append((p["fnid"], y, m, p.get("mean")))
    print(y, m, f"{time.time() - t0:.0f}s", flush=True)
    return out


with ThreadPoolExecutor(max_workers=4) as ex:
    rows = [r for part in ex.map(one_month, [(y, m) for y in range(Y0, Y1 + 1) for m in range(1, 13)]) for r in part]
R = pd.DataFrame(rows, columns=["fnid", "year", "month", "ndvi"])
R.to_pickle(INTERIM / "unit_month_ndvi.pkl")
(OUT / "ndvi_extraction_log.txt").write_text(
    f"MODIS/061/MOD13Q1 NDVI, monthly max composite, unit mean at 250 m, {Y0}-{Y1}; rows {len(R)}; "
    f"missing {int(R.ndvi.isna().sum())}; run {time.strftime('%Y-%m-%d')}\n", encoding="utf-8")
print(R.shape)
