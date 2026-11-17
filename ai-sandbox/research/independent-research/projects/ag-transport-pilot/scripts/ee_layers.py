"""Earth Engine proxies for the seven OFRA Inference Tool rasters (Wortmann et al. 2017, Nutr Cycl Agroecosyst
107:175-186). These are PROXIES, not the original files:
  AI   = annual precipitation / annual PET x 10000 (Zomer scale), TerraClimate 1991-2020 means
  TS   = WorldClim v1 bio04 (Hijmans et al. 2005, as the tool uses)
  GDD  = sum over months of max(0, mean of tmmx and tmmn - 10 C) x 30.4 days, TerraClimate 1991-2020 (proxy)
  elev = SRTM 30 m
  soil = iSDAsoil Africa 0-20 cm: pH x 10, sand %, organic carbon (raw band; transform checked in 12_*.py)
Call init() once (needs EE_PROJECT in the environment), then sample(feature_collections, scale)."""
import os

import ee
import pandas as pd

STACK = None


def init():
    global STACK
    ee.Initialize(project=os.environ["EE_PROJECT"])
    tc = ee.ImageCollection("IDAHO_EPSCOR/TERRACLIMATE").filterDate("1991-01-01", "2021-01-01")
    yrs = 30
    pr = tc.select("pr").sum().divide(yrs)
    pet = tc.select("pet").sum().multiply(0.1).divide(yrs)
    ai = pr.divide(pet).multiply(10000).rename("AI")
    gdd = (tc.map(lambda im: im.select("tmmx").add(im.select("tmmn")).multiply(0.05).subtract(10).max(0)
                  .multiply(30.4).rename("g")).sum().divide(yrs).rename("GDD"))
    ts = ee.Image("WORLDCLIM/V1/BIO").select("bio04").rename("TS")
    elev = ee.Image("USGS/SRTMGL1_003").select("elevation").rename("elev")
    ph = ee.Image("ISDASOIL/Africa/v1/ph").select("mean_0_20").rename("pH10")
    sand = ee.Image("ISDASOIL/Africa/v1/sand_content").select("mean_0_20").rename("sand")
    soc = ee.Image("ISDASOIL/Africa/v1/carbon_organic").select("mean_0_20").rename("soc_raw")
    STACK = ee.Image.cat([ai, ts, gdd, elev, ph, sand, soc])


def sample(geojson_parts, scale):
    out = []
    for part in geojson_parts:
        fc = ee.FeatureCollection(part)
        for f in STACK.reduceRegions(fc, ee.Reducer.mean(), scale=scale).getInfo()["features"]:
            out.append(f["properties"])
    return pd.DataFrame(out)
