"""Replicate the OFRA Inference Tool (OFRA-IT) of Wortmann et al. 2017 (Nutr Cycl Agroecosyst 107:175-186) for maize N.

Part A (reproduction check): for the paper's nine query sites (its Table 3), select OFRA maize-N response functions
with the paper's default query rules applied to Earth Engine proxy rasters (see ee_layers.py), pool them, and fit
gain = b (1 - c^r) at N rates 25..150 kg/ha (the paper's six levels) by nonlinear least squares. Compare b, c, n and
pseudo-R2 with the paper's Table 4. The workbook is the Aug 2023 update, the paper used about 5,500 functions.
Part B (new, not in the paper): leave-site-out and leave-country-out prediction. For each held-out OFRA maize-N site,
select similar sites by the same rules (excluding the site, or its whole country) and predict the site's own mean gain
curve. Skill = 1 - MSE(tool) / MSE(pooled curve of all other sites); also split by ACLED exposure of the site.
ASSUMPTIONS (flagged in the report): the proxy rasters differ from the tool's; organic C = expm1(band/10) g/kg
(iSDAsoil scaling, unchecked); GDD is not queried (the tool uses elevation as its proxy); function parameters are used
as recorded (a = plateau yield, b = max gain, c = curvature), negative b kept.
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

import ee_layers
from common import INTERIM, OUT

RATES = np.arange(25, 151, 25.0)
PAPER = {  # Table 3 query sites and Table 4 results: lat, lon, b, c, n, pseudo R2
    "Farako-ba BF": (11.100, -4.333, 1.802, 0.973, 104, 0.36), "Achefer ET": (11.341, 36.939, 2.279, 0.972, 24, 0.53),
    "Wenchi GH": (7.690, -2.100, 1.144, 0.975, 141, 0.22), "Siaya KE": (-0.094, 34.235, 1.473, 0.965, 78, 0.34),
    "Mwanza MW": (-15.600, 34.500, 2.135, 0.972, 25, 0.47), "Bougouni ML": (11.387, -7.477, 1.859, 0.973, 98, 0.39),
    "Mlingano TZ": (-5.140, 38.870, 0.987, 0.975, 106, 0.19), "Nyakunguru TZ": (-1.417, 34.517, 1.246, 0.967, 80, 0.30),
    "Kapchorwa UG": (1.400, 34.610, 1.094, 0.959, 38, 0.20),
}
PAPER_ALL = (1.378, 0.970, 786, 0.24)


def tool_units(d):
    """Covariates in the units the tool's rules use."""
    return pd.DataFrame({"AI": d.AI, "TS": d.TS, "elev": d.elev, "dist": d.Latitude.abs() * 1000, "pH10": d.pH10,
                         "sand": d.sand, "soc": np.expm1(d.soc_raw / 10)})


def similar(q, S):
    """Boolean mask of rows of S similar to query row q under the paper's default OFRA-IT rules."""
    m = (S.AI.between(q.AI - 1000, q.AI + 1000) if q.AI < 6000 else S.AI > 5000)
    m &= S.TS.between(q.TS - 1000, q.TS + 1000)
    m &= (S.soc.between(q.soc - 10, q.soc + 10) if q.soc <= 35 else S.soc > 25)
    m &= (S.pH10.between(q.pH10 - 4, q.pH10 + 4) if q.pH10 < 54 else S.pH10 > 50)
    m &= (S.sand.between(q.sand - 20, q.sand + 20) if q.sand > 75 else S.sand < 80)
    m &= (S.elev.between(q.elev - 250, q.elev + 250) if q.elev > 700 else S.elev < 1000)
    m &= S.dist.between(q.dist - 3000, q.dist + 3000)
    return m


def curve(f, r, b, c):
    return b * (1 - c ** r)


def pooled(F):
    """Pooled fit of gain = b(1-c^r) over the six N rates for a set of functions F (b, c columns)."""
    r = np.tile(RATES, len(F))
    y = (F.CoefB.values[:, None] * (1 - F.CoefC.values[:, None] ** RATES[None, :])).ravel()
    p, _ = curve_fit(lambda rr, b, c: b * (1 - c ** rr), r, y, p0=(1.0, 0.95), bounds=([-10, 0.5], [20, 0.9999]))
    sse, sst = ((y - curve(0, r, *p)) ** 2).sum(), ((y - y.mean()) ** 2).sum()
    return p[0], p[1], 1 - sse / sst


o = pd.read_pickle(INTERIM / "ofra_raw.pkl")
iu = pd.read_pickle(INTERIM / "ofra_in_units.pkl")  # same row index as o; carries the polygon country
o = o.join(iu[["poly_country"]])
sc = pd.read_pickle(INTERIM / "site_covariates.pkl")[["Latitude", "Longitude", "AI", "TS", "elev", "pH10", "sand", "soc_raw"]]
print("Nutrient labels (maize):", o[o.Crop == "Maiz"].Nutrient.value_counts().head(8).to_dict())
mz = o[(o.Crop == "Maiz") & o.Nutrient.astype(str).str.startswith("N")].copy()
mz = mz.dropna(subset=["CoefB", "CoefC", "Latitude", "Longitude"])
mz = mz[(mz.CoefC >= 0) & (mz.CoefC <= 1)]
for d in (mz, sc):  # coordinates went through Earth Engine JSON: merge on rounded values, not exact floats
    d["klat"], d["klon"] = d.Latitude.round(5), d.Longitude.round(5)
mz = (mz.merge(sc.drop(columns=["Latitude", "Longitude"]).drop_duplicates(["klat", "klon"]), on=["klat", "klon"], how="left")
      .dropna(subset=["AI", "pH10", "sand", "soc_raw"]))
mz = pd.concat([mz.reset_index(drop=True), tool_units(mz.reset_index(drop=True)).add_suffix("_t")], axis=1)
T = mz[["AI_t", "TS_t", "elev_t", "dist_t", "pH10_t", "sand_t", "soc_t"]].rename(columns=lambda c: c[:-2])
print("maize N functions with covariates:", len(mz), "sites:", mz[["Latitude", "Longitude"]].drop_duplicates().shape[0])

# ---------- Part A ----------
cache = INTERIM / "query_site_covariates.pkl"
if cache.exists():
    Q = pd.read_pickle(cache)
else:
    ee_layers.init()
    import geopandas as gpd
    pts = gpd.GeoDataFrame({"name": list(PAPER)}, geometry=gpd.points_from_xy([v[1] for v in PAPER.values()],
                                                                               [v[0] for v in PAPER.values()]), crs="EPSG:4326")
    Q = ee_layers.sample([pts.__geo_interface__], 1000)
    Q = Q.set_index("name") if "name" in Q else Q
    Q.to_pickle(cache)
rows = []
b, c, r2 = pooled(mz)
pos = lambda F: F[F.CoefB > 0]  # variant: drop functions with no positive response
bp, cp, rp = pooled(pos(mz))
rows.append({"domain": "All", "paper_b": PAPER_ALL[0], "b": round(b, 3), "paper_c": PAPER_ALL[1], "c": round(c, 3),
             "paper_n": PAPER_ALL[2], "n": len(mz), "paper_R2": PAPER_ALL[3], "R2": round(r2, 2),
             "n_pos": len(pos(mz)), "b_pos": round(bp, 3), "R2_pos": round(rp, 2)})
for name, (la, lo, pb, pc, pn, pr) in PAPER.items():
    q = tool_units(pd.DataFrame([{**Q.loc[name].to_dict(), "Latitude": la}])).iloc[0]
    sel = mz[similar(q, T).values]
    if len(sel) < 5:
        rows.append({"domain": name, "paper_b": pb, "paper_n": pn, "n": len(sel)})
        continue
    b, c, r2 = pooled(sel)
    sp = pos(sel)
    bp, cp, rp = pooled(sp) if len(sp) >= 5 else (np.nan, np.nan, np.nan)
    rows.append({"domain": name, "paper_b": pb, "b": round(b, 3), "paper_c": pc, "c": round(c, 3), "paper_n": pn,
                 "n": len(sel), "paper_R2": pr, "R2": round(r2, 2), "n_pos": len(sp), "b_pos": round(bp, 3),
                 "R2_pos": round(rp, 2)})
A = pd.DataFrame(rows)
A.to_csv(OUT / "ofra_it_reproduction_table4.csv", index=False)
print(A.to_string(index=False))

# ---------- Part B ----------
mz["site"] = mz.Latitude.round(5).astype(str) + "," + mz.Longitude.round(5).astype(str)
obs = mz.assign(**{f"g{int(r)}": mz.CoefB * (1 - mz.CoefC ** r) for r in RATES}).groupby("site")[[f"g{int(r)}" for r in RATES]].mean()
site_info = mz.groupby("site").agg(country=("poly_country", "first"), nfun=("CoefB", "size"), idx=("CoefB", lambda s: s.index[0]))
ex = pd.read_pickle(INTERIM / "ofra_site_year_exposure.pkl")
ex["site"] = ex.lat.round(5).astype(str) + "," + ex.lon.round(5).astype(str)
exs = ex.groupby("site").n50.max().rename("max_events_50km")
MIN_FUN = 10
res = []
for s, row in site_info.iterrows():
    q = T.loc[row.idx]
    pool = mz.site != s
    pool_country = pool & (mz.poly_country != row.country)
    y = obs.loc[s].values
    for scheme, base in (("leave-site-out", pool), ("leave-country-out", pool_country)):
        sel = mz[base & similar(q, T).values]
        fallback = len(sel) < MIN_FUN
        if base.sum() < 30:
            continue
        pb, pc, _ = pooled(mz[base])
        gl = curve(0, RATES, pb, pc)
        if fallback:
            tl = gl
        else:
            tb, tc, _ = pooled(sel)
            tl = curve(0, RATES, tb, tc)
        res.append({"site": s, "country": row.country, "scheme": scheme, "n_selected": len(sel), "fallback": fallback,
                    "mse_tool": ((y - tl) ** 2).mean(), "mse_global": ((y - gl) ** 2).mean()})
B = pd.DataFrame(res).merge(exs, left_on="site", right_index=True, how="left")
B.to_csv(OUT / "ofra_it_heldout_sites.csv", index=False)


def skill(d):
    return 1 - d.mse_tool.sum() / d.mse_global.sum()


S = []
for scheme, d in B.groupby("scheme"):
    S.append({"scheme": scheme, "group": "all sites", "sites": len(d), "with_selection": int((~d.fallback).sum()),
              "skill_vs_global": round(skill(d), 3)})
    dd = d[~d.fallback]
    S.append({"scheme": scheme, "group": "sites with >=10 similar functions", "sites": len(dd), "with_selection": len(dd),
              "skill_vs_global": round(skill(dd), 3) if len(dd) else np.nan})
    e = dd[dd.max_events_50km.notna()]
    for nm, g in (("exposed (>=10 events within 50 km)", e[e.max_events_50km >= 10]),
                  ("not exposed (<10 events)", e[e.max_events_50km < 10])):
        S.append({"scheme": scheme, "group": nm, "sites": len(g), "with_selection": len(g),
                  "skill_vs_global": round(skill(g), 3) if len(g) else np.nan})
S = pd.DataFrame(S)
S.to_csv(OUT / "ofra_it_heldout_summary.csv", index=False)
print(S.to_string(index=False))
