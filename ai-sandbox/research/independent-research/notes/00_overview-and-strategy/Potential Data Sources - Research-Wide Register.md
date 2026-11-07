# Potential Data Sources — Research-Wide Register

**Updated:** 2026-11-06
**Purpose:** A single intake list for sources that might serve more than one independent-research project. An entry is a lead, not a verified dataset, access grant, or decision to ingest it. Add a specific dataset, version/DOI, geography, time range, unit, license, and access result before calling it usable.

The older [climate/displacement/cash/conflict source note](../01_compound-shocks-panel/data-sources/Data%20Sources%20-%20Climate%20Displacement%20Cash%20Conflict.md) is a project-spanning narrative candidate list, but it includes outdated project descriptions. The retired monorepo scaffold's `source_register.csv` recorded one acquired ACLED export and planned sources; it was **not** a complete inventory of the separate live `projects/compound-shocks-panel` repository. This register is the cross-project intake point, while project-specific registers and manifests retain acquisition/version detail. The [Bangladesh insurance trial](../02_literature-and-evidence-map/Machine-Readable%20Literature%20Sources%20-%20Evidence%20Mapping%20and%20Trial%20Eligibility.md) is a potential replication/NDVI project, with local survey data but no village coordinates identified in that file.

## Already used by the compound-shocks panel

These source families are named in the live panel's `instances/somalia/config.yaml`, `instances/sudan/config.yaml`, and `README.md`, and appear in its Somalia and Sudan verification notes (inspected 2026-11-06). “Used” refers to that project's panel inputs, not blanket verification of every source's license or suitability for a new study. Somalia and Sudan retain distinct displacement series and country-specific file versions.

| Source family | Role and current panel use | Status here |
| --- | --- | --- |
| ACLED | Geolocated conflict-event exports for Somalia and Sudan; conflict and fatality measures. | **Used** in both panels; account-dependent data and redistribution terms remain project-specific. |
| UCSB Climate Hazards Center CHIRPS v2.0 | Monthly Africa rainfall rasters, aggregated to panel districts/localities. | **Used** in both panels; record the exact raster vintage in the project manifest. |
| WFP food prices via HDX | Monthly market prices: `wfp-food-prices-for-somalia`, `wfp-food-prices-for-sudan`. | **Used** in both panels; market coverage and commodity definitions differ by country. |
| OCHA COD-AB via HDX | Somalia district and Sudan locality boundaries/codes: `cod-ab-som`, `cod-ab-sdn`. | **Used** in both panels as the spatial join frame. |
| OCHA COD-PS via HDX | Administrative population estimates: `cod-ps-som`, `cod-ps-sdn`. | **Used** in both panels; these are population denominators, not current-month census counts. |
| UNHCR/NRC PRMN via HDX | Somalia internally displaced persons flow/arrival data: `somalia-internally-displaced-persons-idps`. | **Used** in Somalia; its displacement measure is not interchangeable with Sudan's DTM stock series. |
| IOM DTM via HDX | Sudan displaced-person presence/stock by locality: `sdn-iom-dtm-from-api`. | **Used** in Sudan; the panel selects the Armed Clashes Overview operation. |

For exact slugs, dates, transformations, and checksums, consult the live repository's country configs and `docs/verification/` notes. This table is a research-wide pointer, not a second operational source register.

## World Bank discovery leads

The [World Bank Data Catalog's guide](https://datacatalog.worldbank.org/getting-started) describes it as a cross-catalog search point that can link to external resources; the [FAQ](https://datacatalog.worldbank.org/faq) distinguishes it from the survey-focused Microdata Library and the time-series DataBank, and says terms can differ by dataset. These four links are discovery surfaces for future screening, **not inputs already used in the compound-shocks panel**.

| Resource | Short description and possible use | Access / verification status |
| --- | --- | --- |
| [World Bank Data Catalog search](https://datacatalog.worldbank.org/search) | Search across World Bank development datasets and linked catalogs by topic, country, collection, or license; a starting point for future source discovery. | Official catalog and guide verified. The dynamic search page did not render results in this browser, so counts and specific matches are **unverified**. Inspect each dataset's original source and terms. |
| [Ukraine collection](https://datacatalog.worldbank.org/search/collections/UKRAINE) | Curated Ukraine-data discovery page, relevant to the later Ukraine phase of the compound-shocks research. | The [catalog homepage](https://datacatalog.worldbank.org/) identifies “Ukraine Datasets” as a collection. Its dynamic listing showed no usable results here; contents and current count are **unverified**, not established as empty. |
| [World Bank Microdata Library](https://microdata.worldbank.org/index.php/home) | Searchable survey and administrative microdata catalog, including World Bank and partner studies; useful for trial replication, sampling, outcomes, and access requests. | Homepage and its [metadata API link](https://microdata.worldbank.org/api-documentation/catalog/index.html) verified; each study's file access, geographic detail, and license need separate checks. |
| [World Bank DataBank](https://databank.worldbank.org/home) | Query and visualize development time-series databases, including World Development Indicators; useful for country-level context or covariates. | Official homepage verified. Select a named database and indicator before use; this is not a trial microdata repository. |

## IFPRI leads

| Resource | Short description and possible use | Access / verification status |
| --- | --- | --- |
| [IFPRI Dataverse](https://dataverse.harvard.edu/dataverse/IFPRI) | IFPRI's collection of research datasets; screen its study metadata for impact evaluations, crop insurance, social protection, Bangladesh, Somalia, and Sudan, then inspect promising file lists. | The collection page triggered browser verification here; its current dataset count, specific trial matches, licenses, and file restrictions are **unverified**. [Dataverse's Search API](https://guides.dataverse.org/en/latest/api/search.html) documents `subtree=IFPRI`, `type=dataset`, pagination, and JSON metadata. [Its Data Access API](https://guides.dataverse.org/en/latest/api/dataaccess.html) documents file downloads by ID; access to restricted files can require authentication or a request. Harvard's live API behavior for this collection was **not tested**. |
| [Food Security Portal](https://www.foodsecurityportal.org/) | IFPRI-facilitated hub for food-crisis monitoring, food-price tools, commodity views, and linked data sets; useful for price and food-security context. | Its homepage links to a data catalog, but that catalog returned 403 in this check. Dataset-level coverage, export route, API, and terms are **unverified**. |
| [MapSPAM](https://www.mapspam.info/) | Spatial Production Allocation Model crop-distribution and production estimates; candidate baseline crop mask or agricultural context when defining rice pixels around trial villages. | The site advertises downloadable global crop maps and a SPAM 2020 V2R2 release. Its linked Dataverse deposit could not be opened here; files, resolution, dates, and terms need item-level verification. These modeled maps are **not trial outcomes or village coordinates**. |
| [IFPRI modeling tools](https://www.ifpri.org/modeling-tools/) | Directory of modeling systems including RIAPA and IMPACT for policy, investment, climate, food-system, and economywide scenarios; useful for mechanisms and context. | This is a tools overview, **not a single downloadable dataset**. Inspect each model's inputs, outputs, documentation, and reuse terms separately. |
| [IFPRI food prices](https://www.ifpri.org/topic/food-prices/) | Topic page aggregating food-price research and links to monitoring tools, including the Food Security Portal; a discovery route for price-shock evidence. | Topic page verified; it is **not itself a data feed**. Follow named tools or publications to specific series and access terms. |
| [IFPRI food security](https://www.ifpri.org/topic/food-security/) | Topic page for food-security research, social protection, crisis monitoring, and related policy models; a discovery route for outcomes and intervention literature. | Topic page verified; individual studies or indicators need separate data-access checks. |
| [IFPRI fragility and conflict](https://www.ifpri.org/topic/fragility-and-conflict/) | Topic page for research on conflict, displacement, food systems, crisis response, and social-protection evaluations, including work in Somalia and Sudan. | Topic page verified; individual studies, microdata, and geographic detail need separate checks. |

## How to screen the Dataverse lead

Dataverse's documented search endpoint supports a metadata-only query such as `GET https://dataverse.harvard.edu/api/search?q=insurance&subtree=IFPRI&type=dataset&per_page=100&start=0`. The `subtree` filter and pagination make automated search possible in principle; search results can expose dataset identifiers and file counts. For a promising record, inspect the dataset metadata and file-level access terms, then use the documented Data Access API only for files permitted by that record. This is an API capability documented by Dataverse, **not a verified IFPRI search result or permission for bulk downloading**. No datasets were downloaded for this register.

**Next verification fields for each specific dataset:** persistent ID and version; title/authors; country and dates; intervention/outcome relevance; observation and assignment units; geographic identifiers; file formats; open/restricted status; license/terms; access test; and how it differs from sources already held by a project.
