"""OFRA trial sites vs ACLED exposure, and OFRA vs HarvestStat overlap.

OFRA's 'Country' column is a 3-letter code that is ambiguous (Nig = Nigeria or Niger, Mal = Malawi or Mali,
Bur = Burundi or Burkina Faso), so the country used here is the HarvestStat polygon each site falls in.
Exposure = violent ACLED events within 25/50 km of the site in the trial year or the year before (trial year 2010+).
"""
import geopandas as gpd
import numpy as np
import pandas as pd

from common import HS_GPKG, INTERIM, OFRA_XLSX, OUT, load_events

o = pd.read_excel(OFRA_XLSX, sheet_name="Raw")
o["Y"] = pd.to_numeric(o.Year, errors="coerce")
o.to_pickle(INTERIM / "ofra_raw.pkl")
g = gpd.read_file(HS_GPKG)
pts = gpd.GeoDataFrame(o[["Country", "Crop", "Y", "Nutrient", "CoefA", "CoefB", "CoefC"]],
                       geometry=gpd.points_from_xy(o.Longitude, o.Latitude), crs="EPSG:4326")
j = gpd.sjoin(pts, g[["fnid", "country", "geometry"]].rename(columns={"country": "poly_country"}),
              predicate="within", how="left")
j = j[~j.index.duplicated()]
j["lat"], j["lon"] = j.geometry.y, j.geometry.x
j.drop(columns="geometry").to_pickle(INTERIM / "ofra_in_units.pkl")
print("OFRA rows:", len(o), "inside a HarvestStat unit:", int(j.fnid.notna().sum()))

# exposure of trial site-years (2010+)
ev = load_events()
ev = ev[ev.year >= 2010]
ex = np.c_[ev.geometry.y.values, ev.geometry.x.values]
yrs = ev.year.values.astype(int)
sy = j[j.Y.between(2010, 2025)][["poly_country", "lat", "lon", "Y"]].drop_duplicates().reset_index(drop=True)


def hav(lat, lon, la2, lo2):
    p = np.pi / 180
    a = np.sin((la2 - lat) * p / 2) ** 2 + np.cos(lat * p) * np.cos(la2 * p) * np.sin((lo2 - lon) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


n25, n50 = [], []
for r in sy.itertuples():
    m = (yrs == int(r.Y)) | (yrs == int(r.Y) - 1)
    dd = hav(r.lat, r.lon, ex[m, 0], ex[m, 1])
    n25.append(int((dd <= 25).sum()))
    n50.append(int((dd <= 50).sum()))
sy["n25"], sy["n50"] = n25, n50
sy.to_pickle(INTERIM / "ofra_site_year_exposure.pkl")
t = sy.groupby("poly_country").agg(site_years=("Y", "size"), any_event_50km=("n50", lambda x: int((x > 0).sum())),
                                   ge10_events_50km=("n50", lambda x: int((x >= 10).sum())),
                                   ge50_events_50km=("n50", lambda x: int((x >= 50).sum())),
                                   ge10_events_25km=("n25", lambda x: int((x >= 10).sum())))
t.loc["TOTAL"] = t.sum()
t.to_csv(OUT / "ofra_acled_exposure_by_country.csv")
print(t.to_string())

# overlap with HarvestStat unit yields
u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
cm = {"Maiz": "Maize", "Sorg": "Sorghum", "Mill": "Millet", "Pear": "Millet", "Fing": "Millet"}
c = j[j.fnid.notna()].copy()
c["crop"] = c.Crop.map(cm)
c = c[c.crop.notna()]
print("cereal OFRA rows:", len(c))
c.groupby(["poly_country", "crop"]).agg(rows=("fnid", "size"), units=("fnid", "nunique")).to_csv(
    OUT / "ofra_cereal_rows_by_country_crop.csv")
c10 = c[c.Y.between(2010, 2025)]
m = c10.merge(u[["fnid", "crop", "harvest_year", "yield"]], left_on=["fnid", "crop", "Y"],
              right_on=["fnid", "crop", "harvest_year"])
print("OFRA x HarvestStat same unit-crop-year:", len(m), "rows,", m.groupby(["fnid", "crop", "Y"]).ngroups, "unit-years")
m.groupby(["poly_country", "crop"]).agg(rows=("fnid", "size"), unit_years=("Y", "nunique"),
                                        units=("fnid", "nunique")).to_csv(OUT / "ofra_hs_same_unit_year.csv")
both = c.merge(u[["fnid", "crop"]].drop_duplicates(), on=["fnid", "crop"])
both.groupby(["poly_country", "crop"]).fnid.nunique().rename("units_with_both").to_csv(OUT / "ofra_hs_units_with_both.csv")
