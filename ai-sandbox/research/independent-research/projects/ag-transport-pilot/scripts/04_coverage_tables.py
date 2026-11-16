"""Coverage of exposed vs non-exposed unit-years, unit sizes, yield variability and reporting coverage by exposure."""
import geopandas as gpd
import numpy as np
import pandas as pd

from common import HS_GPKG, INTERIM, OUT, TARGET

u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
fetched = ["Somalia", "Sudan", "South Sudan", "Ethiopia", "Kenya", "Uganda", "Nigeria", "Tanzania, United Republic of",
           "Rwanda", "Malawi", "Burundi", "Ghana", "Zambia", "Mozambique", "Zimbabwe", "Togo", "Cameroon", "South Africa",
           "Mali", "Burkina Faso", "Niger", "Chad", "Central African Republic", "Congo, The Democratic Republic of the"]
u = u[u.country.isin(fetched)].copy()
u["exp50"], u["exp200"], u["dens5"] = u.events >= 50, u.events >= 200, u.density >= 5
for crop in ("Sorghum", "Maize"):
    s = u[u.crop == crop]
    t = s.groupby("country").agg(unit_years=("yield", "size"), units=("fnid", "nunique"), exposed_50=("exp50", "sum"),
                                 exposed_200=("exp200", "sum"), dense_5=("dens5", "sum"),
                                 nonexposed_50=("exp50", lambda x: (~x).sum()))
    t["both_ge_100"] = (t.exposed_50 >= 100) & (t.nonexposed_50 >= 100)
    t.sort_values("exposed_50", ascending=False).to_csv(OUT / f"coverage_{crop.lower()}.csv")
    print(crop); print(t.sort_values("exposed_50", ascending=False).to_string())

# yield variability: log-yield anomaly relative to own unit mean (units with >= 4 years)
s = u[u.crop.isin(["Sorghum", "Maize"])].copy()
s["ly"] = np.log(s["yield"])
s = s[s.groupby(["fnid", "crop"]).ly.transform("size") >= 4]
s["anom"] = s.ly - s.groupby(["fnid", "crop"]).ly.transform("mean")
s["group"] = np.where(s.country.isin(TARGET), "target", "other")
s.groupby(["group", "exp50"]).anom.agg(["size", "mean", "std"]).round(3).to_csv(OUT / "anomaly_target_vs_other.csv")
oc = s[s.group == "other"].groupby(["country", "exp50"]).anom.agg(["size", "mean", "std"]).round(3).unstack("exp50")
oc.to_csv(OUT / "anomaly_by_country.csv")

# reporting coverage by exposure (sorghum): share of country-years each unit reports, split at the country median
a = u[u.crop == "Sorghum"].copy()
cy = a.groupby("country").harvest_year.agg(["min", "max"])
a["span"] = a.country.map(lambda c: cy.loc[c, "max"] - cy.loc[c, "min"] + 1)
b = a.groupby(["country", "fnid"]).agg(yrs=("harvest_year", "nunique"), span=("span", "first"), ev=("events", "mean")).reset_index()
b["share"] = b.yrs / b.span
b["high"] = b.ev >= b.groupby("country").ev.transform("median")
m = b.groupby(["country", "high"]).share.mean().unstack().round(2)
m.columns = ["low_exposure_units", "high_exposure_units"]
m.to_csv(OUT / "reporting_coverage_by_exposure_sorghum.csv")

# unit sizes for sorghum units
g = gpd.read_file(HS_GPKG)
g["km2"] = g.to_crs("EPSG:6933").geometry.area / 1e6
t = a.merge(g[["fnid", "km2"]].rename(columns={"km2": "unit_km2"}), on="fnid")
sz = t.groupby("country").agg(units=("fnid", "nunique"), median_km2=("unit_km2", "median"), min_km2=("unit_km2", "min"),
                              max_km2=("unit_km2", "max")).round(0)
sz["approx_side_km"] = np.sqrt(sz.median_km2).round(0)
sz.sort_values("median_km2").to_csv(OUT / "unit_sizes_sorghum.csv")
print(sz.sort_values("median_km2").to_string())
