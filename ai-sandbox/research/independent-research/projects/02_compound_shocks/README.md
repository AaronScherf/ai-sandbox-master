# Project 02: compounded shocks

## Current scope

The first reproducible unit is a **Somalia exploratory analysis**, based on the [three-shock case-study note](../../notes/Somalia%20Three-Shock%20Case%20Study.md): approximately 2021–2023, with prices, rainfall, conflict, and displacement as initial data streams. The 3R roadmap also proposes a later Ukraine phase and a comparative paper. Neither that expansion nor a causal specification is fixed by this scaffold.

The [data-sources note](../../notes/Data%20Sources%20-%20Climate%20Displacement%20Cash%20Conflict.md) names candidate datasets. Verify the provider, download endpoint, release/version, coverage, variables, geographic identifiers, and reuse terms against the actual files and provider documentation before analysis. Do not infer that a reported cash-program location equals a completed transfer, or that a recorded displacement reason is a causal attribution.

## Layout

| Path | Purpose | Git policy |
| --- | --- | --- |
| `data/source_register.csv` | One row per acquisition or proposed source | Tracked; no credentials or private URLs |
| `data/raw/` | Original downloads, unchanged | Ignored |
| `data/derived/` | Rebuildable transformations | Ignored |
| `outputs/` | Rebuildable tables, figures, logs | Ignored |
| `scripts/inventory.py` | Deterministic SHA-256 inventory of local raw files | Tracked |
| `protocol.md` | Research decisions and verification gates | Tracked |

## First data-intake procedure

1. Download only from the provider under your account and save the original file in `data/raw/<provider>/<release-or-date>/`. Do not put API keys, passwords, or private download links in tracked files.
2. Add a distinct row for each acquired export in `data/source_register.csv` (retain earlier rows when a source is refreshed). Record the provider's own title and identifier, landing page, acquisition date in UTC, release/version as supplied, spatial and temporal coverage as verified, file path, access class, and reuse terms or terms URL. Mark unknown fields `unverified`.
3. Run `python scripts/inventory.py` from this folder. Save its JSON output locally in `outputs/raw_inventory.json`. Compare each `path` and `sha256` with the source register. Re-run after any download changes. The inventory describes local bytes; it does not verify that a provider's data are complete or authentic.
4. Keep the original file untouched. All cleaning code should read from `data/raw/`, write to `data/derived/`, and document input hashes, parameters, software versions, and output hashes. Add a command and pinned environment only when the first transformation exists.

Example from this directory: `python scripts/inventory.py > outputs/raw_inventory.json`.

## Release gate

A public replication release needs an explicit code license, an executable end-to-end entry point, locked software environment, documented source versions and licenses, a codebook for generated tables, tests of joins and geographic/time aggregation, and a clean-room run from permitted inputs. None of those are implied by this initial data-intake scaffold. If raw data cannot be redistributed, provide acquisition instructions and synthetic fixtures for tests, and confirm that derived outputs may be shared. Do not publish ACLED records or geolocated sensitive observations until their terms and disclosure risk have been reviewed.
