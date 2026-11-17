"""EXPLORATORY: are OFRA trial yields consistent with the surrounding unit's yield, after rainfall?

OFRA response function (Wortmann et al. 2017, Nutr Cycl Agroecosyst 107:175-186): Y = a - b*c^r, with a the plateau
yield, b the maximum gain from the nutrient and r the nutrient rate, so the unfertilised (control) yield is a - b and
the plateau is a. (An earlier version of this script wrongly treated a as the control yield.) Units are t/ha, as in
HarvestStat. Compares both control (a - b) and plateau (a) with the unit yield. First look only.
"""
import numpy as np
import pandas as pd

from common import INTERIM, OUT

o = pd.read_pickle(INTERIM / "ofra_in_units.pkl")
u = pd.read_pickle(INTERIM / "hs_chirps_u.pkl")[["fnid", "crop", "harvest_year", "yield", "srain", "country"]]
cm = {"Maiz": "Maize", "Sorg": "Sorghum"}
o = o[o.Crop.isin(cm) & o.fnid.notna() & o.Y.between(2010, 2023) & o.CoefA.gt(0)].copy()
o["crop"] = o.Crop.map(cm)
o["ctrl"] = o.CoefA - o.CoefB
o = o[o.ctrl > 0]
a = o.groupby(["fnid", "crop", "Y"]).agg(ofra_A=("CoefA", "median"), ofra_ctrl=("ctrl", "median"),
                                          n_functions=("CoefA", "size")).reset_index()
m = a.merge(u, left_on=["fnid", "crop", "Y"], right_on=["fnid", "crop", "harvest_year"])
m["ratio"] = m.ofra_A / m["yield"]
m["ratio_ctrl"] = m.ofra_ctrl / m["yield"]
print("matched unit-years:", len(m), "from", m.fnid.nunique(), "units")
rows = []
for crop, s in m.groupby("crop"):
    rows.append({"crop": crop, "unit_years": len(s), "units": s.fnid.nunique(),                  "plateau_ratio_median": s.ratio.median(), "control_ratio_median": s.ratio_ctrl.median(),
                 "control_ratio_p25": s.ratio_ctrl.quantile(.25), "control_ratio_p75": s.ratio_ctrl.quantile(.75),
                 "spearman_plateau_vs_unit": s.ofra_A.rank().corr(s["yield"].rank()),
                 "spearman_control_vs_unit": s.ofra_ctrl.rank().corr(s["yield"].rank())})
summ = pd.DataFrame(rows).round(2)
summ.to_csv(OUT / "ofra_A_vs_unit_yield_summary.csv", index=False)
print(summ.to_string(index=False))
m.groupby(["country", "crop"]).agg(unit_years=("ratio", "size"), plateau_ratio=("ratio", "median"), control_ratio=("ratio_ctrl", "median")).round(2).to_csv(
    OUT / "ofra_A_vs_unit_yield_by_country.csv")
mm = m.dropna(subset=["srain"]).copy()
X = np.c_[np.ones(len(mm)), np.log(mm["yield"]), np.log(mm.srain + 1)]
y = np.log(mm.ofra_ctrl)
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X @ beta
r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
out = pd.Series({"n": len(mm), "intercept": beta[0], "b_log_unit_yield": beta[1], "b_log_season_rain": beta[2],
                 "R2": r2}).round(3)
out.to_csv(OUT / "ofra_A_regression.csv", header=["value"])
print(out.to_string())
