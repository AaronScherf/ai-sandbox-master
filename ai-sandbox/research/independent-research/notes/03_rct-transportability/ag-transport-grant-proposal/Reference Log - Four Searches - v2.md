# Reference log: update after the HarvestStat, ACLED, OFRA-overlap and MCP checks (v2)

*2026-11-16. Delta on [v1](Reference%20Log%20-%20Four%20Searches%20-%20v1.md); v1 entries not repeated here. Everything below was computed in this session from public data; scripts and intermediate files are in the session scratchpad (`hs_acled.py`, `hs_analyze.py`, `hs_geo.py`, `ofra3.py`) and are **not yet in the repo**.*

## Corrections to v1
- **CIMMYT Sudan report:** it covers the **2024/25** season (not 2023/24 as v1 implied). Sorghum in Gedaref, White Nile, Blue Nile and New Halfa (Kassala); satellite pixels classified as sorghum, peak NDVI regressed on crop-cut yields, regression applied to all sorghum pixels. Reported: state-level rainfed productivity about 0.9 t/ha; production 2.65 million t (Gedaref 1.57, White Nile 0.70, Blue Nile 0.31, New Halfa 0.07). Kassala: area only (734,000 ha), no yield. Local PDF: `ai-sandbox/research/journal-articles/68714.pdf` (**executive summary only read, via the owner's paste**). Open questions: held-out validation of the NDVI-yield curve; funder (owner notes USAID) and whether the programme continues.
- **ILRI sorghum study** is the Sudan Savanna of Nigeria, not Sudan (already removed in v1 text).

## HarvestStat Africa (10.1038/s41597-025-05001-z) now analysed
Data: `hvstat_africa_data_v1.2.csv` (topline; raw FEWS NET files per country also provided), boundaries `hvstat_africa_boundary_v1.2.gpkg`. Local copy: `projects/compound-shocks-panel/instances/doi_10_5061_dryad_vq83bk42w__v20260717/`.

**Method.** Violent ACLED events (Battles, Violence against civilians, Explosions/Remote violence), 2008-2025, deduplicated, assigned to HarvestStat units by point-in-polygon. A unit-year is **exposed** if it has 50 or more events in the calendar years spanning that crop season (sensitivity: 200; and a density measure). Yields: qc_flag = 0 only; one value per unit, crop and harvest year (production/area where available); harvest years 2010-2025. ACLED was fetched for 24 countries (the OFRA set, South Sudan, and Mali, Burkina Faso, Niger, Chad, CAR, DRC); HarvestStat countries without ACLED pulls (for example Benin, Senegal) are excluded.

**Coverage (exposed / non-exposed unit-years).** Test agreed earlier: at least 100 of each.
| Country | Sorghum | Maize |
|---|---|---|
| Somalia | 190 / 322 **passes** | 226 / 337 **passes** |
| Nigeria | 73 / 210 | 106 / 370 **passes** |
| Sudan | 65 / 188 | not reported |
| Burkina Faso | 42 / 572 | 40 / 570 |
| Mali | 19 / 70 | 13 / 63 |
| Ethiopia | 9 / 547 | 9 / 653 |
| Kenya | 0 / 441 | 20 / 684 |
| South Sudan | 0 / 2 | none after 2012 (only a "Cereal Crops" aggregate, 2013-2022, 90 rows) |
| All others | under 15 exposed | under 15 exposed |
Ethiopia's low exposure partly reflects zone-sized units and the paper's note that Tigray 2021-22 values were partly carried forward.

**Geographic specificity (median unit area, sorghum units; admin level per paper Tables 3-4).**
| Country | Level | Units | Median area (km2) | About (km side) |
|---|---|---|---|---|
| Kenya | admin1 (counties) | 47 | 3,551 | 60 |
| Burkina Faso | admin2 | 45 | 5,321 | 73 |
| Somalia | admin2 (districts) | 39 | 5,713 | 76 |
| Ethiopia | admin2 (zones) | 68 | 9,102 | 95 |
| Nigeria | admin1 (states) | 27 | 31,738 | 178 |
| Sudan | admin1 (states) | 18 | 57,263 | 239 |
| South Sudan | admin1 (states) | 2 (sorghum) | about 62,000 | about 249 |
| Mali | admin1 | 8 | 81,389 | 285 |
**Scale mismatch to design around:** Somalia units are about 10 times smaller in area than Sudan's states, so a model trained on Somali districts and applied to Sudanese states mixes scales (a scale-of-study vs scale-of-inference issue). The same applies across all proxies.

**Selective missingness.** In most countries high-exposure units report as many years as low-exposure ones, or more (Somalia 0.78 vs 0.86; Nigeria 0.63 vs 0.86; Sudan 0.96 vs 0.92). Coverage check only; says nothing about sampling quality inside insecure units.

**Variability.** Within-unit log-yield SD: target countries (Somalia, Sudan, South Sudan) 0.73-0.87; all others about 0.35-0.37. Exposure shifts within-country yield only inconsistently (Burkina Faso SD 0.28 to 0.54; Ethiopia 0.22 to 0.11; Kenya mean -0.095). Not evidence for or against conflict effects; Somalia's variability is plausibly climatic.

## Yield data vs fertilizer-response data (OFRA overlap)
- All 6,146 OFRA rows fall inside a HarvestStat unit; **2,922 are maize, sorghum or millet.**
- Cereal OFRA rows sit in units that also have HarvestStat yields (2010+) in 24 country-crop groups; the largest are maize in Ethiopia, Kenya and Tanzania (7 units each), maize in Ghana and Rwanda and millet in Niger (6 each). Malawi, Uganda and Zimbabwe have OFRA cereal sites but no matching 2010+ unit yields in the filtered set.
- Same unit, crop **and year** (2010+): 946 OFRA rows over 112 unit-years (Tanzania maize 6 unit-years, Ghana maize 5, Nigeria maize 5, plus others).
- **Limits.** OFRA is point trials with response-function coefficients; HarvestStat is unit-wide averages at 3,500-80,000 km2. They overlap in space but at very different scales, and the trial years are mostly earlier than 2010. No OFRA site is in Somalia, Sudan or South Sudan. Linking them can test whether unit yield level predicts trial response; it cannot validate a treatment-effect prediction in the target countries.

## Harvest Portal MCP
`https://mcp.harvestportal.org/mcp`: streamable HTTP; public access without a token (verified by direct protocol calls, settings unchanged). Tools: `search_datasets`, `get_dataset`, `list_resources`, `get_resource`, `datastore_search`, `datastore_search_sql`, `list_organizations`, `whoami`. A search for "Ethiopia crop cut" returned 8 items including FAO / NASA Harvest Public Yield Datasets and Public Crop Cut Yield Dataset Metadata; "South Sudan" and "Somalia crop" returned none. To enable persistently: `claude mcp add --transport http harvest https://mcp.harvestportal.org/mcp`.

## Open items (carried and new)
1. CHIRPS rainfall test on HarvestStat units (in progress).
2. Read the CIMMYT Sudan PDF for validation design and funder; check programme continuity.
3. Check that predictions in Sudan and South Sudan would be used: number of smallholders and actors who could act on them.
4. Fetch ACLED for HarvestStat countries not yet pulled; add a threshold-sensitivity table to this log.
5. v1 open items 2-5 remain.
