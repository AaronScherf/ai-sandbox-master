"""Static covariates for OFRA trial sites and HarvestStat units, mirroring the seven OFRA Inference Tool rasters
(Wortmann et al. 2017, Nutr Cycl Agroecosyst 107:175-186): aridity index, temperature seasonality, growing degree
days, elevation, distance from the equator, soil pH, sand, soil organic carbon. Earth Engine equivalents, so these are
PROXIES for the original rasters, not the same files:
  AI   = annual precipitation / annual PET x 10000 (Zomer scale), TerraClimate 1991-2020 means
  TS   = WorldClim v1 bio04 (Hijmans et al. 2005, as the tool uses)
  GDD  = sum over months of max(0, mean of tmmx and tmmn - 10 C) x days in month, TerraClimate 1991-2020 (proxy)
  elev = SRTM 30 m; lat = latitude; soil from iSDAsoil Africa 0-20 cm (pH x 10, sand %, organic C g/kg)
Output: data/interim/site_covariates.pkl, unit_covariates.pkl. Needs EE_PROJECT in the environment.
"""
import os

import ee
import geopandas as gpd
import pandas as pd

from common import HS_GPKG, INTERIM

ee.Initialize(project=os.environ["EE_PROJECT"])
tc = (ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").filterDate("1991-01-01", "2021-01-01"))
yrs = 30
pr = tc.select("pr").sum().divide(yrs)
pet = tc.select("pet").sum().multiply(0.1).divide(yrs)
ai = pr.divide(pet).multiply(10000).rename("AI")
tmean = tc.map(lambda im: im.select("tmmx").add(im.select("tmmn")).multiply(0.05).rename("t")
               .subtract(10).max(0).multiply(30.4).rename("g"))
gdd = tmean.sum().divide(yrs).rename("GDD")
ts = ee.Image("WORLDCLIM/V1/BIO").select("bio04").rename("TS")
elev = ee.Image("USGS/SRTMGL1_003").select("elevation").rename("elev")
ph = ee.Image("ISDASOIL/Africa/v1/ph").select("mean_0_20").rename("pH10")
sand = ee.Image("ISDASOIL/Africa/v1/sand_content").select("mean_0_20").rename("sand")
soc = ee.Image("ISDASOIL/Africa/v1/carbon_organic").select("mean_0_20").rename("soc_raw")
stack = ee.Image.cat([ai, ts, gdd, elev, ph, sand, soc])


def sample(fc_geojson_parts, scale):
    out = []
    for part in fc_geojson_parts:
        fc = ee.FeatureCollection(part)
        for f in stack.reduceRegions(fc, ee.Reducer.mean(), scale=scale).getInfo()["features"]:
            out.append(f["properties"])
    return pd.DataFrame(out)


o = pd.read_pickle(INTERIM / "ofra_raw.pkl")
s = o[["Latitude", "Longitude"]].dropna().drop_duplicates().reset_index(drop=True)
s["site"] = s.index
pts = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s.Longitude, s.Latitude), crs="EPSG:4326")
parts = [pts.iloc[i:i + 400].__geo_interface__ for i in range(0, len(pts), 400)]
sc = sample(parts, 1000).rename(columns={"mean": "x"})
sc.to_pickle(INTERIM / "site_covariates.pkl")
print("sites", len(sc), sc.describe().loc[["count", "mean"]].round(1).to_string())

u = pd.read_pickle(INTERIM / "hs_unit_years.pkl")
g = gpd.read_file(HS_GPKG)
g = g[g.fnid.isin(u.fnid.unique())][["fnid", "geometry"]].reset_index(drop=True)
g["geometry"] = g.geometry.simplify(0.005)
parts = [g.iloc[i:i + 100].__geo_interface__ for i in range(0, len(g), 100)]
uc = sample(parts, 1000)
uc.to_pickle(INTERIM / "unit_covariates.pkl")
print("units", len(uc))
