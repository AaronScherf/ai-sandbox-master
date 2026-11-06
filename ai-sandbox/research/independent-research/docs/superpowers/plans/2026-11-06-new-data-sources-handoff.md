# New data sources for the next compound-shocks phase: handoff

Written 2026-11-06. **Plan and verification only.** Do not write adapters, change `compound-shocks-panel`, or add data to the panel. Confirm scope with Aaron first. Facts below come from web searches on 2026-11-06; items marked *unverified* come from a third-party page or from the Gemini Literature Gap Memo and must be checked at the source.

## Already in hand (do not re-plan)

ACLED events (Somalia, Sudan), CHIRPS rainfall, WFP prices, PRMN displacement (Somalia), IOM DTM displacement (Sudan, via HDX), OCHA COD-AB boundaries, OCHA COD-PS population. See `instances/*/config.yaml` in `compound-shocks-panel`.

## Read first

`notes/01_compound-shocks-panel/review-gate/Review Gate - Part C Decision Note.md`, then `Literature Gap Memo.md` section 6 (the eight candidates; Gemini output, unverified), and `ACLED Terms - Redistribution Findings.md` for how credentials must be handled.

## What this session does

For each source below, confirm from the provider's own documentation: current access route, whether credentials are needed and how they are obtained, licence and redistribution terms, geography level, date coverage for 2021-01 to 2025-10, file format or endpoint, and update cadence. Open endpoints may be probed read-only with a few requests to confirm coverage. Do not request credentials on Aaron's behalf. Record findings in one new note, `notes/01_compound-shocks-panel/data-sources/New Data Sources - Access Verification.md`, and draft (do not build) a source descriptor sketch for each scriptable source.

## A. Scriptable with no new account

| Source | Used by | Link | Check |
| --- | --- | --- | --- |
| World Bank Pink Sheet (monthly commodity prices) | B | [World Bank commodities page](http://www.worldbank.org/commodities) | Monthly Excel; download URL carries a hash that changes monthly (third-party report, *unverified*), so the plan must say how a script finds the current file. Which wheat, maize and rice series, and their units. |
| UNHCR Refugee Data Finder API | context for B, C | [Explainer](https://www.unhcr.org/refugee-statistics/insights/explainers/forcibly-displaced-api.html) | Described as open with no credentials. Confirm endpoints, the flows dataset, and whether Somalia and Sudan origin queries return usable annual or monthly series. |
| NOAA STAR Vegetation Health Index | B, C (climate exposure) | [STAR VHI directories](https://www.star.nesdis.noaa.gov/data/mapper/SNPP/VIIRS/vhi/) | Gridded files, not district values; the plan must cover clipping to COD-AB. Marked experimental by NOAA. Confirm no login. |
| OCHA humanitarian access overviews (HDX) | C, Sudan check | [HDX](https://data.humdata.org) (search "access severity") | Existence and coverage *unverified* (from the Gap Memo only). |

## B. Scriptable after a new account, token or key (Aaron has to do the sign-up)

| Source | Used by | Link | Step for Aaron |
| --- | --- | --- | --- |
| UCDP GED API | B, C | [API docs](https://ucdp.uu.se/apidocs/) | Email the maintainer with a short description of the research; token goes in header `x-ucdp-access-token`. Official page dates the token requirement to Feb 2026; a third-party page says 2025. Free. |
| IOM DTM API (`dtmapi`) | C, Sudan check | [dtmapi on PyPI](https://pypi.org/project/dtmapi) | Register on the DTM API portal (linked from the PyPI page), copy the primary key from the profile. Never commit it. First task after the key exists: list which countries and operations the API serves, and whether Somalia is among them. We have not called this API yet. |
| IPC acute food insecurity API | B, C (outcome) | [ripc vignette](https://stat.ethz.ch/CRAN/web/packages/ripc/vignettes/ipc-api.html) | The R wrapper expects a key in `IPC_API_KEY`. Find the official key-request route. Somalia and Sudan coverage *unverified*. |
| VIIRS monthly night lights (EOG) | C | [EOG registration](https://eogdata.mines.edu/register/) | A third-party page says a free account is needed, with 1 to 2 days approval. *Unverified*; confirm on EOG's site. Alternative: NASA Black Marble via a free [LAADS DAAC](https://ladsweb.modaps.eosdis.nasa.gov/) token. |
| UNHCR Operational Data Portal API | context | [API registration](https://data.unhcr.org/en/api/api-registration) | The page shows a registration form but does not say what a key covers. Only needed if the Refugee Data Finder lacks border-point arrivals. |

Credentials must be read from environment variables and must never be committed.

## C. Manual download or request

| Source | Used by | Link | Note |
| --- | --- | --- | --- |
| Baxnaano cash transfers | C | [World Bank design paper](https://openknowledge.worldbank.org/entities/publication/4d209ccd-8ac3-5bab-b98f-a96f5c67d687/full) | No microdata or district-level data found. Ask the World Bank task team or the Ministry of Labour and Social Affairs. Project ID P171346 *unconfirmed*. |
| REACH Somalia MSNA (household needs) | C | [2023 factsheet](https://repository.impact-initiatives.org/document/impact/9de768f6/REACH_SOM_Factsheet_-2302_MSNA_Somalia_Key-findings_Dec_2023.pdf), [2025 ToR](https://repository.impact-initiatives.org/document/impact/1f71574d/REACH_SOM2503_MSNA_2025_ToR-1.pdf) | Annual rounds, not monthly. Terms say anonymised datasets go on HDX or the REACH Resource Centre; whether each round is actually published is *unverified*. |
| DTM Somalia baseline assessments | C | [HDX dataset](https://data.humdata.org/dataset/somalia-displacement-idps-returnees-baseline-assessment-iom-dtm/resource/bc837fb4-0390-411c-91eb-01bafe4e8052) | Rounds cover some states only. Check coverage against the 74 districts. |
| DTM Sudan MSNA (Aug 2025) | Sudan check | [ReliefWeb](https://reliefweb.int/report/sudan/sudan-multisector-needs-assessment-msna-august-2025), [2022 on HDX](https://data.humdata.org/m/dataset/sudan-2022-multisector-needs-assessment-msna) | Locality-representative, 187 localities; the 2022 household file is "by request". The "HNA" waves in Aaron's to-do are not confirmed. |
| DTM Sudan cross-border flows | Sudan check | ReliefWeb reports (search "DTM Sudan cross-border") | Reports, not API; keep flows and stocks in separate columns. |
| UNHCR refugee MSNA 2025 | Sudan check | [World Bank Microdata Library](https://microdata.worldbank.org/index.php/catalog/8248) | Refugee-focused, not DTM; likely needs a data-access request. |

## Ground rules

- Verify at the provider; mark anything not confirmed as unverified.
- No adapters, no panel changes, no committed credentials, no data files in git.
- Report what each source adds relative to what the panel already has, and which of B or C needs it.
