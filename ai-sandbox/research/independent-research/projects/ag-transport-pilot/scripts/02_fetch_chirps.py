"""Download CHIRPS v2.0 Africa monthly GeoTIFFs (gzipped) for 2010-2023 into data/raw/chirps/ (about 0.7 GB)."""
from concurrent.futures import ThreadPoolExecutor

import requests

from common import CHIRPS_DIR

BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs"
names = [f"chirps-v2.0.{y}.{m:02d}.tif.gz" for y in range(2010, 2024) for m in range(1, 13)]


def get(name):
    out = CHIRPS_DIR / name
    if out.exists() and out.stat().st_size > 1_000_000:
        return name, "cached"
    r = requests.get(f"{BASE}/{name}", timeout=300)
    r.raise_for_status()
    out.write_bytes(r.content)
    return name, "ok"


with ThreadPoolExecutor(8) as ex:
    for name, status in ex.map(get, names):
        print(name, status)
