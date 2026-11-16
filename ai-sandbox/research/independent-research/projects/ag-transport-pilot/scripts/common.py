"""Shared paths and helpers for the ag-transport pilot. All paths are relative to the project root."""
from pathlib import Path

# NOTE: intermediate results are pickled in data/interim/ (git-ignored). Only files written by these scripts are read
# back, never pickles from outside sources, so loading them is safe.
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "outputs"
HS_CSV = RAW / "harveststat" / "hvstat_africa_data_v1.2.csv"
HS_GPKG = RAW / "harveststat" / "hvstat_africa_boundary_v1.2.gpkg"
OFRA_XLSX = RAW / "ofra" / "OFRA_RespFunc_Dataset_Updated_Aug_2023.xlsx"
ACLED_DIR = RAW / "acled"
CHIRPS_DIR = RAW / "chirps"

# ACLED event types counted as violent; years used throughout
VIOLENT = ["Battles", "Violence against civilians", "Explosions/Remote violence"]
EVENT_YEAR_MIN = 2008
TARGET = ["Somalia", "Sudan", "South Sudan"]

# HarvestStat country names for the ACLED countries fetched (ACLED name differs for a few)
ACLED_COUNTRIES = [
    "South Sudan", "Ethiopia", "Kenya", "Uganda", "Nigeria", "Tanzania", "Rwanda", "Malawi", "Burundi", "Ghana",
    "Zambia", "Mozambique", "Zimbabwe", "Togo", "Cameroon", "South Africa",
    "Mali", "Burkina Faso", "Niger", "Chad", "Central African Republic", "Democratic Republic of Congo",
]  # Somalia and Sudan come from the two country exports already downloaded

for d in (INTERIM, OUT):
    d.mkdir(parents=True, exist_ok=True)


def load_events():
    """All ACLED violent events since EVENT_YEAR_MIN as a GeoDataFrame (EPSG:4326), deduplicated."""
    import geopandas as gpd
    import pandas as pd

    cols = ["event_date", "event_type", "latitude", "longitude", "fatalities", "country"]
    frames = [pd.read_csv(f, usecols=cols, encoding="utf-8-sig", low_memory=False) for f in sorted(ACLED_DIR.glob("*.csv"))]
    e = pd.concat(frames, ignore_index=True)
    e["year"] = pd.to_datetime(e.event_date, errors="coerce").dt.year
    for c in ("latitude", "longitude"):
        e[c] = pd.to_numeric(e[c], errors="coerce")
    e = e.dropna(subset=["year", "latitude", "longitude"])
    e = e[(e.year >= EVENT_YEAR_MIN) & e.event_type.isin(VIOLENT)]
    e = e.drop_duplicates(subset=["event_date", "event_type", "latitude", "longitude", "fatalities"])
    return gpd.GeoDataFrame(e[["year", "country"]], geometry=gpd.points_from_xy(e.longitude, e.latitude), crs="EPSG:4326")
