"""Assign ACLED violent events to HarvestStat units and build the unit-crop-year yield table with exposure.

Exposure of a unit-crop-year = violent events inside the unit in the calendar years spanning the crop season
(planting year and harvest year). Yields: qc_flag = 0 only; one value per unit, crop and harvest year
(production/area where both exist, else mean yield); harvest years 2010-2025.
Outputs: data/interim/hs_unit_years.pkl, data/interim/unit_year_events.pkl
"""
import geopandas as gpd
import pandas as pd

from common import HS_CSV, HS_GPKG, INTERIM, load_events

pts = load_events()
print("violent events used:", len(pts))
g = gpd.read_file(HS_GPKG)
j = gpd.sjoin(pts[["year", "geometry"]], g[["fnid", "geometry"]], predicate="within", how="inner")
cnt = j.groupby(["fnid", "year"]).size().rename("n").reset_index()
cnt.to_pickle(INTERIM / "unit_year_events.pkl")
area_km2 = g.to_crs("EPSG:6933").set_index("fnid").geometry.area / 1e6

d = pd.read_csv(HS_CSV)
d = d[d.qc_flag == 0]


def crop_group(p):
    p = str(p).lower()
    return "Sorghum" if "sorghum" in p else "Maize" if "maize" in p else "Millet" if "millet" in p else None


d["crop"] = d["product"].map(crop_group)
d = d[d.crop.notna() & d.harvest_year.between(2010, 2025) & d["yield"].gt(0)]


def agg(x):
    ok = x.area.notna() & x.production.notna() & (x.area > 0)
    y = x.production[ok].sum() / x.area[ok].sum() if ok.any() else x["yield"].mean()
    # months (as year*12+month-1) covered by ANY season's planting-to-harvest window in this unit-crop-harvest year;
    # a unit with several seasons (Somalia's Gu and Deyr) gets the union, so rainfall matches the pooled yield
    hy, months = int(x.name[2]), set()
    for py, pm, hm in zip(x.planting_year, x.planting_month, x.harvest_month):
        if pd.notna(py) and pd.notna(pm) and pd.notna(hm):
            t, h = int(py) * 12 + int(pm) - 1, hy * 12 + int(hm) - 1
            if 0 <= h - t <= 11:
                months.update(range(t, h + 1))
    return pd.Series({"yield": y, "planting_year": x.planting_year.min(), "months": sorted(months),
                      "country": x.country.iloc[0]})


u = d.groupby(["fnid", "crop", "harvest_year"]).apply(agg, include_groups=False).reset_index()
cs = cnt.set_index(["fnid", "year"]).n
u["events"] = [sum(cs.get((r.fnid, y), 0) for y in {int(r.planting_year), int(r.harvest_year)}) for r in u.itertuples()]
u["km2"] = u.fnid.map(area_km2)
u["density"] = u.events / u.km2 * 10000
u.to_pickle(INTERIM / "hs_unit_years.pkl")
print("unit-crop-years:", len(u))
