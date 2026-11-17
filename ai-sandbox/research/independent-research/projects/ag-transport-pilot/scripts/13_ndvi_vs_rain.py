"""Does MODIS NDVI add skill beyond CHIRPS rainfall for unit-level yield anomalies, and does either transfer?

Season window = union of planting-to-harvest months per unit-crop-year (as in 07). Season NDVI = peak (max) of the
monthly max-composite unit-mean NDVI in the window; season rain = sum of monthly CHIRPS. Everything is a within-unit
anomaly (unit-crop mean removed, logs). Models:
  within-unit R2 of rain, NDVI, both;
  transfer: fit on all countries except the target, apply to the target (out-of-sample R2 on its anomalies);
  leave-one-country-out for every country with at least 150 unit-years (a general benchmark).
Outputs: outputs/ndvi_*.csv"""
import numpy as np
import pandas as pd

from common import INTERIM, OUT, TARGET

u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
R = pd.read_pickle(INTERIM / "unit_month_rain.pkl").set_index(["fnid", "year", "month"]).rain
N = pd.read_pickle(INTERIM / "unit_month_ndvi.pkl").set_index(["fnid", "year", "month"]).ndvi
u = u[u.crop.isin(["Sorghum", "Maize"]) & (u.harvest_year <= 2023)].copy()


def season(r, ser, how):
    v = [ser.get((r.fnid, k // 12, k % 12 + 1), np.nan) for k in r.months]
    ok = [x for x in v if not np.isnan(x)]
    if not r.months or len(ok) < 0.8 * len(v):
        return np.nan
    return max(ok) if how == "max" else sum(ok)


u["rain"] = [season(r, R, "sum") for r in u.itertuples()]
u["ndvi"] = [season(r, N, "max") for r in u.itertuples()]
cov = u.groupby("country").agg(unit_crop_years=("yield", "size"), with_rain=("rain", lambda x: int(x.notna().sum())),
                               with_ndvi=("ndvi", lambda x: int(x.notna().sum())))
cov.to_csv(OUT / "ndvi_availability.csv")
print("unit-crop-years", len(u), "rain", int(u.rain.notna().sum()), "ndvi", int(u.ndvi.notna().sum()))
u = u.dropna(subset=["rain", "ndvi"])
u["ly"], u["lr"], u["ln"] = np.log(u["yield"]), np.log(u.rain + 1), np.log(u.ndvi.clip(lower=0.01))
u = u[u.groupby(["fnid", "crop"]).ly.transform("size") >= 5].copy()
for c in ("ly", "lr", "ln"):
    u[c + "_a"] = u[c] - u.groupby(["fnid", "crop"])[c].transform("mean")


def fit(tr, cols):
    X = np.c_[np.ones(len(tr)), tr[cols].values]
    return np.linalg.lstsq(X, tr.ly_a.values, rcond=None)[0]


def r2(te, cols, b):
    pred = np.c_[np.ones(len(te)), te[cols].values] @ b
    y = te.ly_a.values
    return 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()


specs = {"rain": ["lr_a"], "ndvi": ["ln_a"], "rain+ndvi": ["lr_a", "ln_a"]}
rows = []
for crop in ("Sorghum", "Maize"):
    d = u[u.crop == crop]
    for c in list(TARGET) + sorted(k for k, n in d.country.value_counts().items() if n >= 150 and k not in TARGET):
        te, tr = d[d.country == c], d[d.country != c]
        if len(te) < 40:
            continue
        row = {"crop": crop, "country": c, "n": len(te)}
        for nm, cols in specs.items():
            row[f"within_R2_{nm}"] = r2(te, cols, fit(te, cols))
            row[f"transfer_R2_{nm}"] = r2(te, cols, fit(tr, cols))
        rows.append(row)
T = pd.DataFrame(rows).round(3)
T.to_csv(OUT / "ndvi_vs_rain_by_country.csv", index=False)
print(T.to_string(index=False))
print("median transfer R2 over countries:", T[[c for c in T if c.startswith("transfer")]].median().round(3).to_dict())
