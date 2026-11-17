"""Trial-size and site-selection model for new N-response trials in Sudan and South Sudan, under a conflict-risk cap.

MODEL. Area-mean fertilizer response f(x) = grain gain (kg/ha) at N_RATE kg N/ha, as a Gaussian process over the seven
standardized OFRA-IT covariates (log AI, TS, elevation, |latitude|, pH, sand, log SOC). Calibrated on OFRA site means for the crop
(maize or sorghum, N response functions; gain = 1000 * b * (1 - c^rate)). Hyperparameters (mean, signal variance s2, lengthscale,
site noise n2) by marginal likelihood. n2 covers within-site and site-specific deviation; f is the smooth, covariate-explained part.
DOMAIN. Candidate/target cells = 0.25 degree cells with aridity index >= AI_MIN and soil data (14_candidate_cells.py). Cropland share is
NOT used for the domain: ESA WorldCover finds almost no cropland in South Sudan (shifting cultivation).
DESIGN. Greedy choice of new trial cells that most reduces the mean posterior variance of f over the country's domain cells, among
cells whose ACLED risk (violent events within 50 km in the last 24 months, weighted 1 + ln(1 + fatalities), per year) is at most the cap.
Each trial observes f(cell) + noise (variance n2).
POWER. Monte Carlo: truth f drawn from the posterior given OFRA; simulate trials; after k trials a cell is DECIDABLE when the 80%
interval of f excludes the break-even gain BE = N_RATE * VCR * price_ratio (kg grain/ha); report share decidable, and the share
of decisions (mean above BE or not) that match the truth.
Outputs: outputs/design_gp_fit.csv, design_curves.csv, design_domain_coverage.csv. Illustrative price ratios are assumptions (see report)."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.spatial.distance import cdist

from common import INTERIM, OUT

import os

N_RATE, VCR, AI_MIN = 50, 2.0, 2000
ELL_FIX = float(os.environ.get("ELL_FIX", 0)) or None  # optimistic scenario: lengthscale fixed (standardized units)
IMPOSED_SHARE = float(os.environ.get("IMPOSED_SHARE", 0)) or None  # ASSUMED share of site-mean variance explained by covariates
SUF = (f"_ell{ELL_FIX:g}" if ELL_FIX else "") + (f"_imposed{IMPOSED_SHARE:g}" if IMPOSED_SHARE else "")
PRICE_RATIOS = {"pre-spike (N $0.48/kg, grain $0.40/kg)": 1.2, "2026 spike (N $2.17/kg, grain $0.40/kg)": 5.4}
RISK_CAPS = [2, 10, 40, np.inf]
K_GRID = [0, 5, 10, 20, 30, 50, 80]
NDRAW, RNG = 40, np.random.default_rng(20261117)
FEATS = ["lAI", "TS", "elev", "dist", "pH10", "sand", "lsoc"]


def feats(d):
    return pd.DataFrame({"lAI": np.log(d.AI.clip(lower=1)), "TS": d.TS, "elev": d.elev, "dist": d.Latitude.abs(), "pH10": d.pH10,
                         "sand": d.sand, "lsoc": np.log(np.expm1(d.soc_raw / 10).clip(lower=0.5))}, index=d.index)


# ---------- calibration data: OFRA site-mean gain at N_RATE
o = pd.read_pickle(INTERIM / "ofra_raw.pkl")
iu = pd.read_pickle(INTERIM / "ofra_in_units.pkl")
o = o.join(iu[["poly_country"]])
sc = pd.read_pickle(INTERIM / "site_covariates.pkl")[["Latitude", "Longitude", "AI", "TS", "elev", "pH10", "sand", "soc_raw"]]
sc = sc.assign(klat=sc.Latitude.round(5), klon=sc.Longitude.round(5)).drop(columns=["Latitude", "Longitude"]).drop_duplicates(["klat", "klon"])


def calib(code):
    d = o[(o.Crop == code) & o.Nutrient.astype(str).str.startswith("N")].dropna(subset=["CoefB", "CoefC", "Latitude", "Longitude"])
    d = d[(d.CoefC >= 0) & (d.CoefC <= 1)].copy()
    d["klat"], d["klon"] = d.Latitude.round(5), d.Longitude.round(5)
    d = d.merge(sc, on=["klat", "klon"], how="left").dropna(subset=["AI", "pH10", "sand", "soc_raw"])
    d["gain"] = 1000 * d.CoefB * (1 - d.CoefC ** N_RATE)
    g = d.groupby(["klat", "klon"]).agg(gain=("gain", "mean"), nfun=("gain", "size"), country=("poly_country", "first"),
                                        Latitude=("Latitude", "first"), AI=("AI", "first"), TS=("TS", "first"),
                                        elev=("elev", "first"), pH10=("pH10", "first"), sand=("sand", "first"),
                                        soc_raw=("soc_raw", "first")).reset_index(drop=True)
    return g


def kern(A, B, s2, ell):
    return s2 * np.exp(-cdist(A, B, "sqeuclidean") / (2 * ell ** 2))


def fit_gp(X, y):
    if IMPOSED_SHARE and ELL_FIX:  # optimistic bound imposed by assumption, not fitted
        fit_gp.nll = float('nan')
        return y.mean(), IMPOSED_SHARE * y.var(), ELL_FIX, (1 - IMPOSED_SHARE) * y.var()
    def nll(p):
        mu, ls2, lell, ln2 = p
        lell = np.log(ELL_FIX) if ELL_FIX else lell
        K = kern(X, X, np.exp(ls2), np.exp(lell)) + np.exp(ln2) * np.eye(len(y))
        try:
            L = np.linalg.cholesky(K)
        except np.linalg.LinAlgError:
            return 1e10
        a = np.linalg.solve(L.T, np.linalg.solve(L, y - mu))
        return 0.5 * (y - mu) @ a + np.log(np.diag(L)).sum()
    best = None
    v = y.var()
    for ell0 in (0.7, 1.5, 3.0):
        for f0 in (0.2, 0.6):
            r = minimize(nll, [y.mean(), np.log(f0 * v), np.log(ell0), np.log((1 - f0) * v)], method="Nelder-Mead",
                         options={"maxiter": 2000, "xatol": 1e-3, "fatol": 1e-3})
            if best is None or r.fun < best.fun:
                best = r
    mu, ls2, lell, ln2 = best.x
    lell = np.log(ELL_FIX) if ELL_FIX else lell
    fit_gp.nll = best.fun
    return mu, np.exp(ls2), np.exp(lell), np.exp(ln2)


def post(X, y, Xs, mu, s2, ell, n2):
    Koo = kern(X, X, s2, ell) + n2 * np.eye(len(y))
    Kso = kern(Xs, X, s2, ell)
    A = np.linalg.solve(Koo, Kso.T)
    return mu + Kso @ np.linalg.solve(Koo, y - mu), kern(Xs, Xs, s2, ell) - Kso @ A


cells = pd.read_pickle(INTERIM / "candidate_cells.pkl")
cells = cells.rename(columns={"lat": "Latitude"})
dom = cells[(cells.AI >= AI_MIN) & cells.pH10.notna()].reset_index(drop=True)
print("domain cells:", dom.country.value_counts().to_dict())

fit_rows, curve_rows, cov_rows = [], [], []
for code, cname in (("Sorg", "sorghum"), ("Maiz", "maize")):
    g = calib(code)
    F = feats(g)
    mu_f, sd_f = F.mean(), F.std()
    Xo = ((F - mu_f) / sd_f).values
    y = g.gain.values
    mu, s2, ell, n2 = fit_gp(Xo, y)
    # leave-country-out check (hyperparameters from the full fit; a small leak, flagged)
    se_gp = se_mean = 0.0
    for c in g.country.unique():
        te = (g.country == c).values
        if te.sum() == 0 or (~te).sum() < 20:
            continue
        m, _ = post(Xo[~te], y[~te], Xo[te], mu, s2, ell, n2)
        se_gp += ((y[te] - m) ** 2).sum()
        se_mean += ((y[te] - y[~te].mean()) ** 2).sum()
    fit_rows.append({"crop": cname, "sites": len(g), "mean_gain_kg": round(y.mean()), "sd_site_means": round(y.std()),
                     "mu": round(mu), "signal_sd": round(np.sqrt(s2)), "lengthscale": round(ell, 2),
                     "noise_sd": round(np.sqrt(n2)), "signal_share": round(s2 / (s2 + n2), 2),
                     "leave_country_out_skill_vs_mean": round(1 - se_gp / se_mean, 3), "neg_loglik": round(fit_gp.nll, 1)})
    print(fit_rows[-1])

    Xd = ((feats(dom) - mu_f) / sd_f).values
    nn_oo = np.sort(cdist(Xo, Xo), axis=1)[:, 1]
    nn_do = cdist(Xd, Xo).min(axis=1)
    dom_c = dom.assign(nn_dist=nn_do)
    for ctry in ("Sudan", "South Sudan"):
        mk = (dom.country == ctry).values
        cov_rows.append({"crop": cname, "country": ctry, "domain_cells": int(mk.sum()),
                         "median_nn_dist_to_OFRA": round(float(np.median(nn_do[mk])), 2),
                         "median_nn_dist_OFRA_to_OFRA": round(float(np.median(nn_oo)), 2),
                         "share_cells_farther_than_90pct_of_OFRA_nn": round(float((nn_do[mk] > np.quantile(nn_oo, .9)).mean()), 2)})
        idx = np.where(mk)[0]
        m0, K0 = post(Xo, y, Xd[idx], mu, s2, ell, n2)
        risk = dom.risk_24m.values[idx]
        Ftrue = RNG.multivariate_normal(m0, K0 + 1e-6 * np.eye(len(idx)) * s2, size=NDRAW, method="cholesky")
        for cap in RISK_CAPS:
            cand = np.where(risk <= cap)[0]
            R, M, chosen = K0.copy(), np.tile(m0, (NDRAW, 1)), []
            Y_noise = RNG.normal(0, np.sqrt(n2), size=(NDRAW, K_GRID[-1]))
            for k in range(0, K_GRID[-1] + 1):
                if k in K_GRID:
                    sd = np.sqrt(np.clip(np.diag(R), 0, None))
                    row = {"crop": cname, "country": ctry, "risk_cap": cap, "eligible_cells": len(cand),
                           "eligible_share": round(len(cand) / len(idx), 2), "k": k if k <= len(cand) or k == 0 else np.nan,
                           "mean_post_sd_kg": round(float(sd.mean())), "mean_risk_chosen": round(float(risk[chosen].mean()), 1) if chosen else np.nan}
                    if k > len(cand):
                        row.update({"k": len(cand), "note": "all eligible cells used"})
                    for nm, pr in PRICE_RATIOS.items():
                        BE = N_RATE * VCR * pr
                        dec = np.abs(M - BE) > 1.2816 * sd
                        agree = np.sign(M - BE) == np.sign(Ftrue - BE)
                        row[f"decidable|{nm}"] = round(float(dec.mean()), 3)
                        row[f"match_when_decidable|{nm}"] = round(float(agree[dec].mean()), 3) if dec.any() else np.nan
                        row[f"truth_above_BE|{nm}"] = round(float((Ftrue > BE).mean()), 3)
                    curve_rows.append(row)
                if k == K_GRID[-1]:
                    break
                avail = [j for j in cand if j not in chosen]
                if not avail:
                    continue
                gains = (R[:, avail] ** 2).sum(axis=0) / (np.diag(R)[avail] + n2)
                j = avail[int(np.argmax(gains))]
                chosen.append(j)
                yj = Ftrue[:, j] + Y_noise[:, k]
                kg = R[:, j] / (R[j, j] + n2)
                M += np.outer(yj - M[:, j], kg)
                R = R - np.outer(R[:, j], R[:, j]) / (R[j, j] + n2)
        print(cname, ctry, "done", flush=True)

pd.DataFrame(fit_rows).to_csv(OUT / f"design_gp_fit{SUF}.csv", index=False)
C = pd.DataFrame(curve_rows).drop_duplicates(["crop", "country", "risk_cap", "k"])
C.to_csv(OUT / f"design_curves{SUF}.csv", index=False)
pd.DataFrame(cov_rows).to_csv(OUT / f"design_domain_coverage{SUF}.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30)
print(pd.DataFrame(fit_rows).to_string(index=False))
print(pd.DataFrame(cov_rows).to_string(index=False))
