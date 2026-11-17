# Taking stock: what the exploratory pilot shows, and what it does not (v4)

*2026-11-17. Supersedes [v3](Reference%20Log%20-%20Four%20Searches%20-%20v3.md) where stated in section 1; v3 still holds sections 2 to 4.4 and 4.6. Code, tables and checksums: [`projects/ag-transport-pilot/`](../../projects/ag-transport-pilot/README.md), reproducible from the scripts. Every result is **run on acquired data** by one analyst; none is independently reproduced.*

## 1. Corrections to v3
1. **OFRA control versus plateau (v3 section 4.5 is superseded).** OFRA response functions are Y = a - b c^r (Wortmann et al. 2017): **a is the plateau yield, b the maximum gain**, so the unfertilised control is **a - b**. v3 and the idea summary treated a as the control and reported trials at "1.9 times (maize) and 1.7 times (sorghum)" the surrounding unit's yield; those are the plateau ratios. The control ratios are **1.43 (maize, 60 unit-years, interquartile 0.99-2.57)** and **1.26 (sorghum, 34, 0.94-2.01)**. Trial controls sit only modestly above their surroundings and often not at all, so the selection story (trials on better land) is weaker than I reported. Regression of log control on log unit yield and log season rain: 0.42 and 0.46, R2 0.15 (n = 94, 48 units; unstable).
2. Soil-organic-carbon scaling for the new covariates is an assumption (section 3). The CHIRPS transfer figures in v3 (about 0.02) used non-target countries only; section 2.2 uses all countries except the target, so the numbers differ (0.05-0.06 for sorghum).

## 2. New results
### 2.1 NDVI versus rainfall (MODIS MOD13Q1 v6.1, 250 m, monthly maximum; Earth Engine)
All 828 units, 2010-2023, extracted without a gap (139,104 unit-months). Season NDVI is the peak in the unit's planting-to-harvest window, no crop mask. Within-unit R2 of yield anomalies (logs, unit means removed) and out-of-country transfer R2 (fit on all other countries):

| | Somalia sorghum | Sudan sorghum | Somalia maize |
|---|---|---|---|
| within-unit R2, rain | 0.19 | 0.15 | 0.13 |
| within-unit R2, NDVI | 0.15 | 0.21 | 0.07 |
| within-unit R2, both | 0.20 | 0.24 | 0.13 |
| transfer R2, rain / NDVI / both | 0.05 / 0.04 / 0.06 | 0.06 / 0.06 / 0.07 | 0.02 / 0.02 / 0.03 |

Across 21 country-crop sets the median transfer R2 is 0.03 (rain), 0.02 (NDVI), 0.04 (both). The pooled slope fails badly where the yield-weather relation is different: Niger sorghum and maize -0.4 to -1.0. **Reading:** NDVI carries information comparable to rainfall within a unit and is somewhat better for Sudan sorghum, the target of the CIMMYT work; but neither transfers across countries and the two together add only a little. NDVI is worth keeping as a covariate; it is not a breakthrough. No crop mask yet, so unit means include non-cropland.

### 2.2 The OFRA Inference Tool, replicated
**Method (Wortmann et al. 2017, Crossref-verified, full text read).** OFRA-IT (an ArcGIS script) selects maize-N response functions from sites whose seven raster values fall within fixed windows of the query site: aridity index (within 1,000 on Zomer's x10,000 scale, or above 5,000 if the site is at 6,000 or more), temperature seasonality (within 1,000), organic carbon (within 10 g/kg, or above 25 if the site is above 35), pH x 10 (within 4, or above 50 above 54), sand (within 20 above 75%, else below 80%), elevation (within 250 m above 700 m, else below 1,000 m), distance from the equator (within 3 degrees). The selected functions are pooled and fitted as gain = b(1 - c^r) at six N rates. The paper's evidence for the tool is **in-sample**: mean pseudo-R2 of 33% (OFRA-IT) against 23% (Harvest Choice zones) and 31% (Global Yield Gap Atlas domains) for N, and 5.6% for K; no held-out prediction test.

**Reproduction attempt (Table 4, nine query sites; proxy rasters; Aug 2023 workbook, 934 maize N functions at 271 sites against the paper's 786).** Partial. Pooled b across the nine sites correlates 0.56 (all functions) or 0.59 (positive-response only) with the paper's; absolute b is 25-40% lower (all: 0.89 against 1.38); selected-set sizes track the paper (correlation 0.87); **pseudo-R2 does not reproduce (0.01-0.06 against 0.19-0.53)**. Possible causes I cannot separate: different rasters (mine are proxies), a different filter on functions, a different R2 definition. Treat the replication as a working approximation, not a confirmation.

**Held-out prediction (new; maize N; 271 sites).** For each site, select similar sites by the same rules, excluding the site (leave-site-out) or its whole country (leave-country-out), and predict the site's mean gain curve. Skill is 1 - MSE(tool) / MSE(pooled curve of all other sites):

| Scheme | Sites with enough similar functions (at least 10) | Skill versus pooled curve |
|---|---|---|
| leave-site-out | 254 of 271 | **+0.04** |
| leave-country-out | 220 of 271 | **-0.02** |
| leave-site-out, ACLED-exposed site (at least 10 events within 50 km) | 15 | +0.06 |
| leave-site-out, not exposed | 81 | +0.10 |

**Reading.** On this proxy setup, selecting by environmental similarity predicts a held-out site's response only a few percent better than the pooled average, and not at all across countries. The exposed and non-exposed numbers rest on 15 and 81 sites and cannot be told apart. The OFRA data therefore cannot show how prediction degrades in conflict, because it has too few exposed trials, and the baseline itself shows little skill to degrade.

## 3. Assumptions and limits (new)
Proxy rasters (TerraClimate 1991-2020 aridity, WorldClim v1 bio04, SRTM, iSDAsoil 0-20 cm) stand in for the tool's; organic C = expm1(band / 10) g/kg is my reading of the band scaling and was not checked against iSDA documentation; GDD was computed but, as in the tool, elevation is the query variable; functions with c at the boundaries were kept; many sites have one or two functions, so site means are noisy; the skill metric weights sites equally by squared error; NDVI has no crop mask; units are administrative and 5,700 to 57,000 km2.

## 4. What the data can build now
- **Unit-year panel (12,899 unit-crop-years, 828 units, 20+ countries):** yield, season rain, season NDVI, ACLED exposure, static covariates (aridity, seasonality, elevation, soil). Resolution: administrative unit; Somali districts about 5,700 km2, Sudanese states about 57,000.
- **OFRA site panel (928 sites, 6,146 function rows):** all inside a unit, so each can carry unit context; 954 rows (113 unit-years) share a unit-crop-year with a yield; none in the Horn; 17 of 517 trial site-years with 50 or more violent events within 50 km.
- **Finest resolution:** point sites for OFRA, unit for yields. Joining them is possible only where they share a unit-year; that is the main constraint on the HarvestStat-informed adjustment (H4).

## 5. Literature additions
Wortmann et al. 2017, *Maize-nutrient response information applied across Sub-Saharan Africa*, Nutr Cycl Agroecosyst 107:175-186, [doi:10.1007/s10705-017-9827-0](https://doi.org/10.1007/s10705-017-9827-0) (Crossref **V**, read). Tesfahunegn and Wortmann 2017, [doi:10.1007/s10705-017-9887-1](https://doi.org/10.1007/s10705-017-9887-1) (Crossref **V**, not read). No source found for continuation of the USAID-funded CIMMYT programme.

## 6. Open items
1. Obtain the tool's own rasters (or document why proxies suffice) and test the pseudo-R2 definition; contact the OFRA team if needed.
2. Add a crop mask to NDVI and test a hierarchical model with unit random effects.
3. Check whether Sudan and South Sudan predictions would be used (smallholder counts, decision-makers).
4. Fetch ACLED for HarvestStat countries still missing; threshold sensitivity.
