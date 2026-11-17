"""How much farming is in cells that are climatically suitable and below a conflict-risk cap?

Sudan: ESA WorldCover cropland (share of cell x cell area) by ACLED risk class (candidate cells from 14_*.py).
South Sudan: WorldCover finds almost no cropland (scattered plots, shifting cultivation), so use the FAO/WFP CFSAM 2025
(19 March 2026) Table 2 state totals of farming households and cereal hectares, spread over each state's cells (GAUL 2015
level-1 states; Ruweng -> Unity, Pibor -> Jonglei, Abyei -> Warrap). Assumes households are spread evenly over a state's
cells, so eligible-household figures are rough upper bounds, not counts.
Outputs: outputs/farming_base_by_risk_sudan.csv, farming_base_by_risk_south_sudan.csv. Needs EE_PROJECT."""
import os

import ee
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from common import INTERIM, OUT

CAPS = [2, 10, 40, np.inf]
AI_MIN = 2000
# CFSAM 2025 Table 2 (mid-2025): farming households, cereal hectares, by state (Ruweng/Pibor/Abyei folded into parent state)
SS = {"Central Equatoria": (147785, 120600), "Eastern Equatoria": (150295, 155634), "Jonglei": (111973 + 26681, 70829 + 20710),
      "Lakes": (139777, 186953), "Northern Bahr el Ghazal": (145451, 111530), "Unity": (43416 + 13587, 19698 + 7763),
      "Upper Nile": (112948, 88816), "Warrap": (183991 + 8241, 181463 + 7005), "Western Bahr el Ghazal": (100374, 91504),
      "Western Equatoria": (152627, 196380)}

ee.Initialize(project=os.environ["EE_PROJECT"])
g = ee.FeatureCollection("FAO/GAUL/2015/level1").filter(ee.Filter.inList("ADM0_NAME", ["Sudan", "South Sudan"]))
st = [(f["properties"]["ADM0_NAME"], f["properties"]["ADM1_NAME"], shape(f["geometry"]))
      for f in g.getInfo()["features"]]
C = pd.read_pickle(INTERIM / "candidate_cells.pkl")
ALIAS = {"warab": "warrap", "el buheyrat": "lakes"}
C["state"] = None
for i, r in C.iterrows():
    p = Point(r.lon, r.lat)
    for c, n, geom in st:
        if c == r.country and geom.contains(p):
            n = ALIAS.get(n.lower(), n.lower())
            C.at[i, "state"] = n
            break
print("cells without a state:", int(C.state.isna().sum()), "of", len(C), "| states:", sorted(C.state.dropna().unique())[:40])
C["area_ha"] = 0.25 * 111.32 * 0.25 * 111.32 * np.cos(np.radians(C.lat)) * 100
C["crop_ha"] = C.crop * C.area_ha
C["suitable"] = (C.AI >= AI_MIN) & C.pH10.notna()

# ---- Sudan: WorldCover cropland by risk class
C["state"] = C.state.str.title()
S = C[C.country == "Sudan"]
rows = []
for cap in CAPS:
    for nm, d in (("all cells", S), ("climate-suitable cells (AI>=0.2)", S[S.suitable])):
        e = d[d.risk_24m <= cap]
        rows.append({"risk_cap": cap, "domain": nm, "cells": len(e), "cropland_Mha": round(e.crop_ha.sum() / 1e6, 2),
                     "share_of_sudan_cropland": round(e.crop_ha.sum() / S.crop_ha.sum(), 3)})
R = pd.DataFrame(rows)
R.to_csv(OUT / "farming_base_by_risk_sudan.csv", index=False)
print("Sudan WorldCover cropland total (Mha):", round(S.crop_ha.sum() / 1e6, 2))
print(R.to_string(index=False))
bs = S.groupby("state").apply(lambda d: pd.Series({"cropland_Mha": d.crop_ha.sum() / 1e6, "median_risk": d.risk_24m.median(),
                                                   "share_cells_risk<=10": (d.risk_24m <= 10).mean()}), include_groups=False)
print(bs.sort_values("cropland_Mha", ascending=False).head(10).round(2).to_string())
bs.round(3).to_csv(OUT / "farming_base_sudan_by_state.csv")

# ---- South Sudan: CFSAM households spread over a state's cells
T = C[C.country == "South Sudan"]
rows = []
for s, (hh, ha) in SS.items():
    d = T[T.state.str.lower() == s.lower()]
    if not len(d):
        rows.append({"state": s, "farming_hh": hh, "cereal_ha": ha, "cells": 0})
        continue
    row = {"state": s, "farming_hh": hh, "cereal_ha": ha, "cells": len(d), "median_risk": round(d.risk_24m.median(), 1)}
    for cap in CAPS[:3]:
        row[f"hh_in_cells_risk<={cap:g}"] = round(hh * (d.risk_24m <= cap).mean())
    rows.append(row)
B = pd.DataFrame(rows)
B.to_csv(OUT / "farming_base_by_risk_south_sudan.csv", index=False)
tot = B[["farming_hh", "cereal_ha"] + [c for c in B if c.startswith("hh_in")]].sum()
print(B.to_string(index=False))
print("TOTAL", tot.round().to_dict())
