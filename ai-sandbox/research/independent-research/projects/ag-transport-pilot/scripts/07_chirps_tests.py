"""Initial CHIRPS validation: availability, within-unit rain-yield signal, out-of-country transfer of the pooled
slope, and rainfall-regime nearest neighbours of the target countries.
Outputs: CSVs in outputs/ and data/interim/hs_chirps_u.pkl"""
import numpy as np
import pandas as pd

from common import INTERIM, OUT, TARGET

u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
R = pd.read_pickle(INTERIM / "unit_month_rain.pkl")
u = u[u.crop.isin(["Sorghum", "Maize"]) & (u.harvest_year <= 2023)].copy()
rm = R.set_index(["fnid", "year", "month"]).rain


def season_rain(r):
    """Rain summed over the union of all seasons' planting-to-harvest months (NaN if none is valid or <80% have data)."""
    if not r.months:
        return np.nan
    vals = [rm.get((r.fnid, k // 12, k % 12 + 1), np.nan) for k in r.months]
    ok = [v for v in vals if not np.isnan(v)]
    return sum(ok) if len(ok) >= 0.8 * len(vals) else np.nan


u["srain"] = [season_rain(r) for r in u.itertuples()]
print("unit-crop-years with no valid season window:", int((u.months.str.len() == 0).sum()))
avail = u.groupby("country").agg(unit_crop_years=("srain", "size"), with_rain=("srain", lambda x: int(x.notna().sum())))
avail["share"] = (avail.with_rain / avail.unit_crop_years).round(2)
avail.to_csv(OUT / "chirps_availability.csv")
print("unit-crop-years:", len(u), "with seasonal CHIRPS:", int(u.srain.notna().sum()))
u = u.dropna(subset=["srain"])
u["ly"], u["lr"] = np.log(u["yield"]), np.log(u.srain + 1)
u = u[u.groupby(["fnid", "crop"]).ly.transform("size") >= 5].copy()
for c in ("ly", "lr"):
    u[c + "_a"] = u[c] - u.groupby(["fnid", "crop"])[c].transform("mean")
u["group"] = np.where(u.country.isin(TARGET), "target", "other")
u.to_pickle(INTERIM / "hs_chirps_u.pkl")

rows = []
for (c, cr), s in u.groupby(["country", "crop"]):
    if len(s) >= 40:
        b = np.polyfit(s.lr_a, s.ly_a, 1)
        rows.append((c, cr, len(s), round(b[0], 2), round(np.corrcoef(s.lr_a, s.ly_a)[0, 1] ** 2, 2)))
sig = pd.DataFrame(rows, columns=["country", "crop", "n", "slope", "R2"]).sort_values("R2", ascending=False)
sig.to_csv(OUT / "within_unit_rain_signal.csv", index=False)

res = []
for cr in ("Sorghum", "Maize"):
    tr = u[(u.group == "other") & (u.crop == cr)]
    b = np.polyfit(tr.lr_a, tr.ly_a, 1)
    for c in ("Somalia", "Sudan"):
        te = u[(u.country == c) & (u.crop == cr)]
        if len(te) < 20:
            continue
        pred = b[0] * te.lr_a + b[1]
        oos = 1 - ((te.ly_a - pred) ** 2).sum() / ((te.ly_a - te.ly_a.mean()) ** 2).sum()
        res.append((cr, c, len(te), round(b[0], 2), round(oos, 3), round(np.corrcoef(te.lr_a, te.ly_a)[0, 1] ** 2, 3)))
tr_df = pd.DataFrame(res, columns=["crop", "target", "n", "slope_from_others", "oos_R2", "within_target_R2"])
tr_df.to_csv(OUT / "chirps_transfer_oos.csv", index=False)
print(tr_df.to_string(index=False))

cl = u.groupby("fnid").agg(country=("country", "first"), mr=("srain", "mean"),
                           cv=("srain", lambda x: x.std() / x.mean()), ev=("events", "mean")).dropna()
cl["z_mr"] = (np.log(cl.mr) - np.log(cl.mr).mean()) / np.log(cl.mr).std()
cl["z_cv"] = (cl.cv - cl.cv.mean()) / cl.cv.std()
tg, ot = cl[cl.country.isin(["Somalia", "Sudan"])], cl[~cl.country.isin(TARGET)]
nn = []
for i, r in tg.iterrows():
    d = np.hypot(ot.z_mr - r.z_mr, ot.z_cv - r.z_cv)
    nn += [(r.country, ot.loc[x, "country"], bool(ot.loc[x, "ev"] >= 25), d[x]) for x in d.nsmallest(3).index]
N = pd.DataFrame(nn, columns=["target", "neighbour_country", "neighbour_exposed", "dist"])
N.groupby(["target", "neighbour_country"]).size().unstack(0).fillna(0).astype(int).to_csv(OUT / "rain_regime_neighbours.csv")
sm = cl[cl.country == "Somalia"]
within = float(np.median([np.hypot(sm.z_mr - r.z_mr, sm.z_cv - r.z_cv).drop(i).min() for i, r in sm.iterrows()]))
summary = pd.Series({"share_neighbours_exposed_somalia": N[N.target == "Somalia"].neighbour_exposed.mean(),
                     "share_neighbours_exposed_sudan": N[N.target == "Sudan"].neighbour_exposed.mean(),
                     "median_dist_to_neighbours": N.dist.median(), "median_dist_within_somalia": within}).round(2)
summary.to_csv(OUT / "rain_regime_summary.csv", header=["value"])
print(summary.to_string())
