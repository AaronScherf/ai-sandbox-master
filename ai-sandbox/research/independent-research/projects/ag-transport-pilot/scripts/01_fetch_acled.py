"""Download ACLED events 2010-2025 per country into data/raw/acled/ (needs ACLED_EMAIL / ACLED_PASSWORD).

Credentials come from the environment or from the .env file named in ENV_FILE. Never printed.
ACLED terms forbid redistribution: data/raw/ is git-ignored. Somalia and Sudan exports were downloaded by hand into
the compound-shocks-panel project and are copied into data/raw/acled/ unchanged.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import requests

from common import ACLED_COUNTRIES, ACLED_DIR

env = os.environ.get("ENV_FILE")
if env:
    for line in Path(env).read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
tok = requests.post("https://acleddata.com/oauth/token", timeout=60, data={
    "username": os.environ["ACLED_EMAIL"], "password": os.environ["ACLED_PASSWORD"],
    "grant_type": "password", "client_id": "acled"})
if tok.status_code != 200:
    sys.exit(f"ACLED login failed: HTTP {tok.status_code}")
headers = {"Authorization": "Bearer " + tok.json()["access_token"]}
for country in ACLED_COUNTRIES:
    out = ACLED_DIR / f"{country.replace(' ', '_')}.csv"
    if out.exists():
        continue
    r = requests.get("https://acleddata.com/api/acled/read", headers=headers, timeout=300, params={
        "country": country, "event_date": "2010-01-01|2025-10-31", "event_date_where": "BETWEEN",
        "_format": "json", "limit": 0})
    rows = r.json()["data"]
    pd.DataFrame(rows).to_csv(out, index=False)
    print(country, r.status_code, len(rows))
