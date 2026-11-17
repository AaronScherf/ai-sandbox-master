# ag-transport-pilot

Exploratory pilot behind the environmental-science grant-proposal idea ([summary](../../notes/03_rct-transportability/ag-transport-grant-proposal/Proposal%20Idea%20Summary%20-%20v2.md), [reports](../../notes/03_rct-transportability/ag-transport-grant-proposal/)). It asks whether shared environmental covariates and conflict exposure could carry crop-yield (and, later, fertilizer-response) predictions into conflict-affected, data-poor regions such as Sudan and South Sudan. **Everything here is a first look, not a result.**

## What is in this folder
| Path | Contents | In Git |
|---|---|---|
| `scripts/` | Numbered pipeline (below) and `common.py` | yes |
| `outputs/` | CSV tables written by the scripts, plus `run_log.txt` | yes |
| `data/manifest.json` | Source, version, access date and sha256 of every raw file | yes |
| `data/raw/` | Downloaded sources (about 1 GB): HarvestStat, OFRA, ACLED, CHIRPS, the CIMMYT PDF | **no** (ACLED forbids redistribution; the rest is large) |
| `data/interim/` | Pickles written between steps | **no** |

## Reproduce
Python 3.13 with `requirements.txt`. Run from any directory.
1. Put the raw files in `data/raw/` (see `data/manifest.json` for sources and checksums). HarvestStat and the OFRA workbook are downloaded by hand; ACLED needs an account (`ENV_FILE=<path to .env with ACLED_EMAIL and ACLED_PASSWORD> python scripts/01_fetch_acled.py`); CHIRPS: `python scripts/02_fetch_chirps.py`. The Somalia and Sudan ACLED exports are the hand-downloaded files from `compound-shocks-panel`.
2. `python scripts/03_events_to_units.py` through `09_manifest.py`.
3. Scripts 10, 11 and 12 (first run) need Google Earth Engine: a one-time `gcloud auth application-default login --scopes="https://www.googleapis.com/auth/earthengine,https://www.googleapis.com/auth/cloud-platform"`, a Cloud project registered for Earth Engine, and its id in the environment variable `EE_PROJECT` (never commit it). Then run `10_ndvi_earthengine.py`, `11_site_covariates_ee.py`, `12_ofra_it_replication.py`, `13_ndvi_vs_rain.py`.

| Script | Does |
|---|---|
| `03_events_to_units` | ACLED violent events to HarvestStat units; unit-crop-year yields with season exposure |
| `04_coverage_tables` | Exposed vs non-exposed unit-years by country and crop; unit sizes; yield variability; reporting coverage |
| `05_ofra_exposure_overlap` | OFRA trial-site exposure to ACLED; OFRA vs HarvestStat overlap |
| `06_chirps_zonal` | Monthly CHIRPS rainfall per unit |
| `07_chirps_tests` | Rain availability, within-unit signal, out-of-country slope transfer, rainfall-regime neighbours |
| `08_ofra_vs_unit_yield` | **Exploratory**: OFRA trial control (a - b) and plateau (a) yields vs the surrounding unit's yield |
| `09_manifest` | Source, access date and sha256 for every raw file |
| `10_ndvi_earthengine` | Monthly MODIS NDVI (MOD13Q1 v6.1, 250 m) per unit, 2010-2023, via Earth Engine |
| `11_site_covariates_ee` + `ee_layers` | Proxies for the seven OFRA Inference Tool rasters at OFRA sites and units |
| `12_ofra_it_replication` | Replicates the OFRA Inference Tool for maize N (Wortmann et al. 2017) and tests it on held-out sites |
| `13_ndvi_vs_rain` | Does NDVI add skill beyond rainfall, within units and out of country |

## Definitions
- **Exposure:** a unit-crop-year is exposed if at least 50 violent ACLED events (Battles, Violence against civilians, Explosions/Remote violence) fall inside the unit in the calendar years spanning the crop season. Thresholds are arbitrary; 200 events and a density measure are also written.
- **Yields:** HarvestStat `qc_flag = 0` only; one value per unit, crop and harvest year; 2010-2025.
- **OFRA country codes** are ambiguous (Nig = Nigeria or Niger; Mal = Malawi or Mali; Bur = Burundi or Burkina Faso), so country is taken from the HarvestStat polygon a site falls in.

## Licensing and hygiene
Do not commit `data/raw/` or `data/interim/` (git-ignored). The Earth Engine project id and credentials stay out of the repo. ACLED data may not be redistributed. The ACLED API step reads credentials from the environment; never print or commit them. `run_log.txt` contains only counts and table output.
