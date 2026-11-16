"""Mean CHIRPS monthly rainfall (mm) per HarvestStat unit, 2010-2023. Output: data/interim/unit_month_rain.pkl"""
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features

from common import CHIRPS_DIR, HS_GPKG, INTERIM

u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
g = gpd.read_file(HS_GPKG)
g = g[g.fnid.isin(u.fnid.unique())].reset_index(drop=True)
first = "/vsigzip/" + (CHIRPS_DIR / "chirps-v2.0.2010.01.tif.gz").as_posix()
with rasterio.open(first) as r:
    tr, shape = r.transform, (r.height, r.width)
ids = features.rasterize(((geom, i + 1) for i, geom in enumerate(g.geometry)), out_shape=shape, transform=tr,
                         fill=0, all_touched=True, dtype="int32")
flat = ids.ravel()
n = len(g) + 1
cells = np.bincount(flat, minlength=n)
rows = []
for y in range(2010, 2024):
    for m in range(1, 13):
        with rasterio.open("/vsigzip/" + (CHIRPS_DIR / f"chirps-v2.0.{y}.{m:02d}.tif.gz").as_posix()) as r:
            a = r.read(1).astype("float64").ravel()
        ok = (a >= 0) & (flat > 0)
        s = np.bincount(flat[ok], weights=a[ok], minlength=n)
        c = np.bincount(flat[ok], minlength=n)
        rows.append(pd.DataFrame({"fnid": g.fnid.values, "year": y, "month": m,
                                  "rain": s[1:] / np.maximum(c[1:], 1),
                                  "valid_frac": c[1:] / np.maximum(cells[1:], 1)}))
R = pd.concat(rows)
R.loc[R.valid_frac == 0, "rain"] = np.nan
R.to_pickle(INTERIM / "unit_month_rain.pkl")
print(R.shape, "units with no grid cell:", int((cells[1:] == 0).sum()))
