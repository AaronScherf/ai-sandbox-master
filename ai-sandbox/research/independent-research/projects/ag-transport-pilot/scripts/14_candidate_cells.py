"""Candidate trial cells for Sudan and South Sudan: environmental covariates, cropland share and ACLED risk.

Grid of 0.25 degree cells (about 28 km) whose centres fall inside Sudan or South Sudan (USDOS LSIB boundaries, Earth Engine).
Per cell:
  covariates  the seven OFRA-IT proxy layers (ee_layers.py), mean over the cell at 1 km;
  cropland    ESA WorldCover v200 class 40 share (mean of the indicator at 1 km);
  risk        ACLED violent events within RISK_KM of the cell centre in the last RISK_MONTHS months of the data, each event
              weighted 1 + ln(1 + fatalities), per year. Sensitivity windows (12 and 60 months) are stored too.
Outputs: data/interim/candidate_cells.pkl, outputs/candidate_cells_summary.csv. Needs EE_PROJECT in the environment.
ACLED rows are read only for the two target countries; no raw ACLED data is written to outputs.
"""
import os

import ee
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape
from shapely.prepared import prep

import ee_layers
from common import ACLED_DIR, INTERIM, OUT, VIOLENT

STEP = 0.25
RISK_KM = 50

ee.Initialize(project=os.environ["EE_PROJECT"])
lsib = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017").filter(ee.Filter.inList("country_na", ["Sudan", "South Sudan"]))
geo = {f["properties"]["country_na"]: shape(f["geometry"]) for f in lsib.getInfo()["features"]}
print({k: round(v.area, 1) for k, v in geo.items()}, "(deg2)")

cells = []
for name, poly in geo.items():
    pp = prep(poly)
    x0, y0, x1, y1 = poly.bounds
    for la in np.arange(np.floor(y0 / STEP) * STEP, y1, STEP):
        for lo in np.arange(np.floor(x0 / STEP) * STEP, x1, STEP):
            if pp.contains(Point(lo + STEP / 2, la + STEP / 2)):
                cells.append({"country": name, "lat": la + STEP / 2, "lon": lo + STEP / 2})
C = pd.DataFrame(cells)
print(C.country.value_counts().to_dict(), "cells")

# ---- Earth Engine covariates + cropland share
ee_layers.init()
crop = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map").eq(40).rename("crop")
stack = ee_layers.STACK.addBands(crop)
rows = []
for i in range(0, len(C), 300):
    part = C.iloc[i:i + 300]
    feats = [ee.Feature(ee.Geometry.Rectangle([r.lon - STEP / 2, r.lat - STEP / 2, r.lon + STEP / 2, r.lat + STEP / 2]),
                        {"k": int(j)}) for j, r in part.iterrows()]
    out = stack.reduceRegions(ee.FeatureCollection(feats), ee.Reducer.mean(), scale=1000).getInfo()["features"]
    rows += [f["properties"] for f in out]
    print("EE batch", i, flush=True)
E = pd.DataFrame(rows).set_index("k")
C = C.join(E)

# ---- ACLED risk
cols = ["event_date", "event_type", "latitude", "longitude", "fatalities", "country"]
ev = pd.concat([pd.read_csv(f, usecols=cols, encoding="utf-8-sig", low_memory=False) for f in sorted(ACLED_DIR.glob("*.csv"))])
ev = ev[ev.country.isin(["Sudan", "South Sudan"]) & ev.event_type.isin(VIOLENT)]
ev["date"] = pd.to_datetime(ev.event_date, errors="coerce")
for c in ("latitude", "longitude", "fatalities"):
    ev[c] = pd.to_numeric(ev[c], errors="coerce")
ev = ev.dropna(subset=["date", "latitude", "longitude"]).drop_duplicates(["event_date", "event_type", "latitude", "longitude", "fatalities"])
ev["w"] = 1 + np.log1p(ev.fatalities.fillna(0))
end = ev.date.max()
print("ACLED violent events", len(ev), "last date", end.date())


def haversine(lat, lon, la, lo):
    p = np.pi / 180
    a = np.sin((la - lat) * p / 2) ** 2 + np.cos(lat * p) * np.cos(la * p) * np.sin((lo - lon) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


for months in (12, 24, 60):
    e = ev[ev.date > end - pd.DateOffset(months=months)]
    la, lo, w = e.latitude.values, e.longitude.values, e.w.values
    C[f"risk_{months}m"] = [(w[haversine(r.lat, r.lon, la, lo) <= RISK_KM].sum()) / (months / 12) for r in C.itertuples()]
    print("risk window", months, "done", flush=True)
C["risk_end"] = end
C.to_pickle(INTERIM / "candidate_cells.pkl")
s = C.groupby("country").agg(cells=("lat", "size"), cropland_cells_5pct=("crop", lambda x: int((x >= 0.05).sum())),
                             median_risk24=("risk_24m", "median"), p75_risk24=("risk_24m", lambda x: x.quantile(.75)))
s.to_csv(OUT / "candidate_cells_summary.csv")
print(s.to_string())
