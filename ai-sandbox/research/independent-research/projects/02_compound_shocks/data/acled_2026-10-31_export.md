# ACLED Somalia CSV export: local source record

**Status:** Raw file inventoried; export settings and repeated event IDs need resolution before analysis. This page records what was observed on 2026-10-31. It does not certify completeness or provider authenticity.

## Identity and custody

- Provider: ACLED (Armed Conflict Location & Event Data).
- Acquisition route: User-supplied CSV saved in the main checkout's ignored `data/raw/` directory; the exact ACLED export screen, filters, and provider release identifier were not supplied. [ACLED's download page](https://acleddata.com/conflict-data/download-data) describes its export tool.
- Original filename: `ACLED Data_2026-10-31_event_date_from_1997-01-01_event_date_to_2025-10-31.csv`.
- Local project path: `data/raw/ACLED Data_2026-10-31_event_date_from_1997-01-01_event_date_to_2025-10-31.csv`. The worktree holds an ignored, byte-identical copy at the same relative path; the user-saved original in the main checkout was left untouched.
- Size: 54,656,965 bytes. SHA-256: `b97dc491ffbd06b5ce6535805731212c7cb09e94ee6e7c843b46e993da128565` in both locations.
- Main-checkout filesystem creation time observed: `2026-10-31T18:50:00Z`; modification time: `2026-10-31T18:49:33Z`. These timestamps do not establish when ACLED generated the export. Exact acquisition time and data release/version remain unverified.
- Raw file is excluded from Git. Preserve it unchanged; create any filtered or cleaned copy under `data/derived/` with a recorded transformation.

## Observed contents

Read locally with Python's `csv.DictReader` using UTF-8 with optional BOM. No event-level records were printed or added to Git.

| Check | Observation |
| --- | --- |
| Data rows | 101,144; no malformed CSV rows detected by `DictReader` |
| Columns | 28; see header below |
| Observed event dates | 1997-02-15 through 2025-10-31 |
| `country` labels | Somalia: 100,883 rows; Indian Ocean: 261 rows |
| Somalia rows in 2021–2023 | 20,453 before any quality filtering or deduplication |
| Missing `event_id_cnty`, `event_date`, latitude, longitude | Zero in each field |
| `year` versus `event_date` year | Zero mismatches |
| Geographic precision codes | 1: 81,011; 2: 17,681; 3: 2,452 |
| Time precision codes | 1: 99,751; 2: 1,160; 3: 233 |
| Distinct `event_id_cnty` values | 52,925; 48,219 IDs occur twice |
| Exact duplicate rows | 1,820 excess rows beyond distinct full-row tuples |

Header: `event_id_cnty`, `event_date`, `year`, `time_precision`, `disorder_type`, `event_type`, `sub_event_type`, `actor1`, `assoc_actor_1`, `inter1`, `interaction`, `civilian_targeting`, `iso`, `region`, `country`, `admin1`, `admin2`, `admin3`, `location`, `latitude`, `longitude`, `geo_precision`, `source`, `source_scale`, `notes`, `fatalities`, `tags`, `timestamp`.

Among the 48,219 repeated-ID pairs, 1,820 match across all parsed columns. Other pairs have the same event date and timestamp but differ in `actor1` (46,281 pairs), `inter1` (43,992), and/or `assoc_actor_1` (11,183). These column-change counts overlap. The reason is unknown. ACLED's [API schema](https://acleddata.com/api-documentation/acled-endpoint) describes `event_id_cnty` as a stable event identifier and lists `actor2`, `assoc_actor_2`, and `inter2`; those three columns are absent here. This may reflect export column selection or another upstream process. **Do not silently deduplicate, count these rows as independent events, or infer actor roles until the export settings and provider format are checked.**

The filename indicates a requested lower date bound of 1997-01-01 and upper bound of 2025-10-31. The observed minimum is later; the exact filter settings are unverified. The file does not cover events after 2025-10-31, so a current-period analysis would need a new, separately registered export.

## Source interpretation and reuse

- Apply ACLED's [codebook](https://acleddata.com/methodology/acled-codebook) when interpreting event types and precision flags. A coded coordinate or date can be approximate; retain `geo_precision` and `time_precision` in processing.
- ACLED's [EULA](https://acleddata.com/eula) permits certain noncommercial transformative outputs but restricts access to and redistribution of underlying licensed content. Its [Content Usage Terms](https://acleddata.com/contentusage) require clear documentation of manipulations and responsible use. Keep the raw CSV private; review any derived data release for reversibility and disclosure risk.
- The [Attribution Policy](https://acleddata.com/attributionpolicy) calls for the access date, subset filters, and transformations in citations; visualizations should acknowledge ACLED on the figure. It also specifies an academic dataset citation. Add the actual access date and final filters once confirmed.

## Open provenance checks

1. Record the actual download/access date and save the export settings or a screenshot privately: geography, date range, event/actor filters, and selected columns. Do not store account tokens or private download URLs.
2. Determine why 48,219 IDs appear twice and whether the missing actor columns were intentionally omitted. Compare a small sample against a fresh export or ask ACLED if the export settings do not explain it.
3. Decide and document a justified event identity rule before computing counts, monthly exposure, fatalities, or actor-specific measures.
4. If a new file is downloaded, keep this snapshot and add a new source-register row with its own checksum. Never replace this raw file in place.
