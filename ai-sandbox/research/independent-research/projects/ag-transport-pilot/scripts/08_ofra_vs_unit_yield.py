"""EXPLORATORY: are OFRA trial coefficients consistent with the surrounding unit's yield, after rainfall?

ASSUMPTION (unverified; the response-function equation is in Wortmann and Sones 2017, which has not been read):
CoefA is the no-nutrient yield in t/ha. HarvestStat yields are in t/ha. A trial 'control' above the unit average
would suggest trials sit on better-than-average land or management. Treat every number here as a first look.
"""
import numpy as np
import pandas as pd

from common import INTERIM, OUT

o = pd.read_pickle(INTERIM / "ofra_in_units.pkl")
u = pd.read_pickle(INTERIM / "hs_chirps_u.pkl")[["fnid", "crop", "harvest_year", "yield", "srain", "country"]]
cm = {"Maiz": "Maize", "Sorg": "Sorghum"}
o = o[o.Crop.isin(cm) & o.fnid.notna() & o.Y.between(2010, 2023) & o.CoefA.gt(0)].copy()
o["crop"] = o.Crop.map(cm)
a = o.groupby(["fnid", "crop", "Y"]).agg(ofra_A=("CoefA", "median"), n_functions=("CoefA", "size")).reset_index()
m = a.merge(u, left_on=["fnid", "crop", "Y"], right_on=["fnid", "crop", "harvest_year"])
m["ratio"] = m.ofra_A / m["yield"]
print("matched unit-years:", len(m), "from", m.fnid.nunique(), "units")
rows = []
for crop, s in m.groupby("crop"):
    rows.append({"crop": crop, "unit_years": len(s), "units": s.fnid.nunique(), "median_ratio": s.ratio.median(),
                 "p25": s.ratio.quantile(.25), "p75": s.ratio.quantile(.75),
                 "spearman_A_vs_unit_yield": s.ofra_A.rank().corr(s["yield"].rank())})
summ = pd.DataFrame(rows).round(2)
summ.to_csv(OUT / "ofra_A_vs_unit_yield_summary.csv", index=False)
print(summ.to_string(index=False))
m.groupby(["country", "crop"]).agg(unit_years=("ratio", "size"), median_ratio=("ratio", "median")).round(2).to_csv(
    OUT / "ofra_A_vs_unit_yield_by_country.csv")
mm = m.dropna(subset=["srain"]).copy()
X = np.c_[np.ones(len(mm)), np.log(mm["yield"]), np.log(mm.srain + 1)]
y = np.log(mm.ofra_A)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X @ beta
r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
out = pd.Series({"n": len(mm), "intercept": beta[0], "b_log_unit_yield": beta[1], "b_log_season_rain": beta[2],
                 "R2": r2}).round(3)
out.to_csv(OUT / "ofra_A_regression.csv", header=["value"])
print(out.to_string())
