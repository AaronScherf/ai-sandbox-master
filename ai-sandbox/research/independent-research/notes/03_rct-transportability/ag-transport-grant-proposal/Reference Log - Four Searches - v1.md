# Reference log: four searches for the agronomic-transport grant proposal (v1)

*2026-11-16. Scope: Design B (hold-out prediction on OFRA, transfer to Somalia / South Sudan / Sudan, grant funds new trial data). Method: standard web search, 6 rounds, thresholds as agreed (8 useful sources per search, or 6 rounds). "Useful" = georeferenced site- or plot-level data, a quantitative transfer or prediction result, or a reusable method.*

**Verification key.** **V** = DOI resolved in Crossref and title, journal, year and lead author match. **U** = not verified mechanically (grey literature, press, or DOI not checked). **Read** = full text or dataset page read in this session; otherwise the entry rests on search summaries or abstracts only, and no claim should be quoted from it before reading the paper.

**Outcome in one paragraph.** Searches 1 and 3 reached the threshold. Search 2 reached it by count (grey and unverified sources included) but only two entries carry georeferenced or yield data. **Search 4 did not find any public dataset that meets the conflict-and-non-conflict coverage test**; the best candidate (HarvestStat Africa) is public but could not be downloaded programmatically, so the ACLED test was not run on it.

---

## OFRA references (user-supplied)
- OFRA at UNL: https://agronomy.unl.edu/ofra/ · IFDC tools: https://ifdc.org/resources/ofra-analysis-tools/ · Dryad dataset: https://datadryad.org/dataset/doi:10.5061/dryad.tt6h5h1
- Liben, Midega, Tufa, Wortmann (2020), *Barley and wheat nutrient responses for Shewa, Ethiopia*, Agronomy Journal, https://doi.org/10.1002/agj2.20020 **[V]**
- Liben et al. (2020), *Maize and sorghum nutrient response functions for Ethiopia*, Nutrient Cycling in Agroecosystems, https://doi.org/10.1007/s10705-020-10077-7 **[V]** (Crossref lists Liben, Adisu, Atnafu, Bekele, Berhe, Wortmann)
- OFRA publication lists: [Jul 2023](https://agronomy.unl.edu/sites/unl.edu.ianr.agronomy-horticulture/files/media/file/OFRA-PAPERS-JUL2023.pdf), [Oct 2025](https://agronomy.unl.edu/research/OFRA/Publications_Oct25.pdf) **[U]**, to mine for more OFRA-based studies.

## Search 1: fertilizer and agronomic transport / generalization (threshold met: 10)
| Source | Type | Why useful | Status |
|---|---|---|---|
| Nziguheba, van Heerwaarden, Vanlauwe (2021), *Quantifying the prevalence of (non)-response to fertilizers in SSA using on-farm trial data*, Nutr Cycl Agroecosyst, 10.1007/s10705-021-10174-1 | Paper | 41 trials, 11 countries; non-response 0-1% cereals, 7-16% legumes; claims it may represent other agro-ecologies despite spatial bias | V |
| Kihara et al. (2016), *Understanding variability in crop response to fertilizer and amendments in SSA*, Agric Ecosyst Environ, 10.1016/j.agee.2016.05.012 | Paper | Diagnostic trials in 5 countries; up to 25% of maize fields non-responsive; micronutrient causes. **Conflicts with Nziguheba on how common non-response is** | V |
| Rurinda et al. (2020), *Science-based decision support for formulating crop fertilizer recommendations in SSA*, Agric Systems, 10.1016/j.agsy.2020.102790 | Paper | 735 nutrient-omission trials, 368 validation trials (Nigeria, Ethiopia, Tanzania); a calibrate-then-validate design | V |
| Liben et al. (2020) x2 (above) | Papers | OFRA-based response functions for Ethiopia | V |
| Desta, Amede, Gashaw (2022), *Sorghum yield response to NPKS and NPZn nutrients along sorghum-growing landscapes*, Exp Agric, 10.1017/s0014479722000072 | Paper | Sorghum response varies by landscape position (Amhara); site-level heterogeneity example | V |
| Vivalt (2020), *How much can we generalize from impact evaluations?*, JEEA, 10.1093/jeea/jvaa019 | Paper | Benchmark for how poorly effects generalize; the secondhand "61% correct sign" figure is **unverified** | V |
| Meager (2019), *Understanding the average impact of microcredit expansions: a Bayesian hierarchical analysis*, AEJ Applied, 10.1257/app.20170299 | Paper | Hierarchical model whose out-of-sample use is the proposal's core method | V |
| Ploton et al. (2020), *Spatial validation reveals poor predictive performance of large-scale ecological mapping models*, Nat Commun, 10.1038/s41467-020-18321-y | Paper | Standard CV overstates skill under spatial autocorrelation; argues for spatial validation | V |
| Wadoux, Heuvelink, de Bruin (2021), *Spatial cross-validation is not the right way to evaluate map accuracy*, Ecol Model, 10.1016/j.ecolmodel.2021.109692 | Paper | The counter-argument; the proposal must say which validation target it uses (map accuracy vs transfer to new sites) | V |
| CGIAR coordinated trials + meta-analysis (varietal turnover) | Web article | Design precedent for external validity via harmonized multi-site trials | U |
| McCullough (IFPRI) causal forest, leave-site-out validation | Slides | Closest match to the planned hold-out test; **find the published version** | U (slides only) |
| Wageningen random-forest / ML fertilizer work (Ghana, SSA) | Thesis, paper | Nested CV, R2 = 0.81 yield; soil more important than climate (per search summary) | U |

**Gap noted.** No paper found that runs leave-one-site-out transport prediction on OFRA itself. That supports the novelty claim, but the search was one pass and is not a systematic scan.

## Search 2: fertilizer and yield evidence in Somalia, South Sudan, Sudan
Threshold met by count only. Entries are mostly grey literature.
| Source | Country | Content | Status |
|---|---|---|---|
| Karongo et al. (2025), *Sorghum yield prediction ... conflict affected South Sudan*, Sci Rep, 10.1038/s41598-025-89030-z | South Sudan | 2,100 farmers, 15 villages (Upper Nile, W. Bahr el Ghazal), 2018-2021 | V, Read (open-access full text) |
| Lee et al. (2025), *HarvestStat Africa*, Sci Data, 10.1038/s41597-025-05001-z (data: Dryad 10.5061/dryad.vq83bk42w) | Somalia (district), Sudan and South Sudan (state) | Subnational yields from FEWS NET warehouse, mainly 1980-2022 | V, Read (open-access paper) |
| Aune and Ousman (2011), *Effect of seed priming and micro-dosing of fertilizer on sorghum and pearl millet in western Sudan*, Exp Agric, 10.1017/s0014479711000056 | Sudan | Sorghum +50 to +110%, millet +31 to +47% from micro-dosing (per search summary); confirm country in text | V, not read |
| El Mahi and Salih, rainfed sorghum N x P at Damazin, Blue Nile, Univ of Khartoum J Agric Sci ([PDF](https://onlinejournals.uofk.edu/index.php/uofkjas/article/download/1898/1707/1778)) | Sudan | Synergistic N x P response | U |
| Alio, MSU thesis, sorghum yield limits and fertilizer N, P, K at Afgoi, 1977 ([PDF](https://d.lib.msu.edu/etd/34383/FULL_TEXT/download)) | Somalia | Old, rainfed 200-600 mm | U |
| SATG Afgoi maize N placement, 81 farms, 2014; Ministry of Agriculture Afgoi 2017 N trial ([poster](https://scisoc.confex.com/crops/2015am/webprogram/Handout/Paper95263/ASA2015%20poster%20-%20ABIC.pdf)) | Somalia | Grey literature; 100 kg N/ha best in 2017 trial, repeat needed | U |
| ICRC (2021), 2020 post-harvest monitoring, 636 households ([PDF](https://www.icrc.org/en/download/file/163675/icrc_ssud_agro_phm_2020_report_external.pdf)) | South Sudan | Cereal yield -49% vs 2019; results indicative only | U, not read |
| KIT and IFDC (Dec 2025), A3SEED South Sudan evaluation ([PDF](https://www.kit.nl/wp-content/uploads/2026/02/A3SEED-SS-internal-project-evaluation-final.pdf)) | South Sudan | Seed aid had insignificant effect on maize yield in 2021; Torit, Magwi | U, not read |
| FAO/WFP CFSAM South Sudan special reports (2008-2024) | South Sudan | County-built production estimates; no dataset download found | U |

**Not found:** any fertilizer trial from South Sudan with plot-level data; any Somali sorghum N trial in a journal. Earlier note: the ILRI sorghum study is the Sudan Savanna of **Nigeria** and was removed.

## Search 3: yield remote sensing and crop-model comparison in smallholder / conflict settings (threshold met: 8 found, 5 verified)
| Source | Content | Status |
|---|---|---|
| Burke and Lobell (2017), PNAS, 10.1073/pnas.1616919114 | 1-m imagery vs field sampling, thousands of western Kenya maize plots; satellite detects fertilizer and hybrid-seed responses | V, not read |
| Lobell, Azzari, Burke et al. (2019/2020), *Eyes in the sky, boots on the ground*, AJAE, 10.1093/ajae/aaz051 (WB version 10.1596/37749) | Satellite yield measures vs crop cuts, farmer reports | V, not read |
| Karongo et al. (2025) (above) | Temporal hold-out (2021) R2 about 0.51-0.59, RMSE 172-226 kg/ha; conflict probability from UCDP added little | V, Read |
| [NASA Harvest yield models](https://www.nasaharvest.org/news/how-to-choose-between-nasa-harvest-crop-yield-models) | GEOCIF, ARYA, VeRCYe; an intercomparison dashboard is planned, not confirmed live | U |
| [FAO / NASA Harvest public crop type datasets](https://data.harvestportal.org/id/dataset/fao-bha-nasa-harvest-public-crop-type-datasets) | CC-BY; **Malawi and Namibia only**, 2022-2023; no Horn of Africa | Read |
| Tseng et al., CropHarvest (NeurIPS Datasets and Benchmarks 2021) | Global crop labels; notes SSA labels are sparse (a 474-field Kenya set) | U (Crossref match failed) |
| Kerner et al. (2024), Tigray cultivated area, [arXiv 2312.10819](https://arxiv.org/html/2312.10819v2); Sci Remote Sens 2024 Tigray study | Cropland area, not yield; estimates disagree (e.g. 543 vs 714 km2 net loss) | U |
| Malawi Sentinel-2 maize yield (R2 = 0.51, nRMSE = 20%), western Kenya multi-sensor comparison | Accuracy benchmarks for 10-20 m sensors on smallholder maize | U |

**Gap noted.** No Sentinel-2 yield study with crop cuts in Somalia, Sudan or South Sudan was found. Ground truth in these places is the stated bottleneck (also in the Burke and Lobell and Lobell framing).

## Search 4: agricultural datasets with enough coverage in conflict and non-conflict zones
**Test (agreed):** at least 100 site-years with 10+ ACLED events within 50 km, and at least as many non-exposed site-years, in Ethiopia, Kenya, Uganda, South Sudan, Sudan, Somalia and neighbours. **No dataset has been tested yet and none is confirmed to pass.**
| Candidate | Public? | Unit and yield? | Conflict link | Verdict |
|---|---|---|---|---|
| **HarvestStat Africa** (Dryad 10.5061/dryad.vq83bk42w; CC-BY-4.0) | Yes, but the Dryad file endpoint needs a login token | Admin units: Somalia districts (admin2), Sudan and South Sudan states (admin1), Ethiopia zones, Uganda districts, Kenya counties; yields, 574,204 records | None built in; no in-filling of gaps; Ethiopia 2021-22 Tigray values partly carried from earlier years | **Best candidate. Test on admin-unit-years once downloaded** |
| Nigeria GHS-Panel / LSMS-ISA (WB catalog [2734](https://microdata.worldbank.org/catalog/2734)) | Registered download; precise coordinates restricted (U) | Plot GPS collected; yields | Linked to ACLED in Amare et al. | Strong data but Nigeria is not proximal to the target |
| Amare et al. (2025), Agric Econ, 10.1111/agec.70078 | Paper | Maize response to N falls with conflict within 0-15 km | ACLED | **V**; a direct precedent for conflict x response, Nigeria only |
| Ayalew et al. (2025), Agric Econ, 10.1111/agec.70083 (IFPRI DP 02307) | Unclear | Ethiopia household and plot panel, 2019 and 2023; **inputs, not yields** | ACLED via georeferenced identifiers | **V**; Read (working-paper PDF) |
| Karongo et al. South Sudan yields | On request only | 2,100 farmers, 15 villages; village-level locations not given | UCDP forecasts; ACLED "confronted" | Fails public test; possible collaborator route (ICRC affiliation) |
| ICRC post-harvest monitoring 2020 | Not found | 636 households | n/a | Fails |
| CIMMYT Sudan 2023/24 crop cuts plus satellite | Unknown; repository blocked automated access | Unread | Unknown | Unverified |
| Ethiopia ESS plot geovariables (WB catalog [2247](https://microdata.worldbank.org/catalog/2247/data-dictionary)) | Registered | Topography variables only | None | Not a conflict-yield dataset |
| Mendeley dataset, Boko Haram and agriculture (10.17632/fyknfnb6vb.1) | Page lists no files | Not stated | ACLED | Unverified; the related paper is Adelaja and George (2019), World Dev, 10.1016/j.worlddev.2019.01.010 **[V]** |
| Northern Uganda panels (Mugizi and Matsumoto 2021; Acholi and Lango 2013-2018) | Unknown | Parcel-level 2015; yields not confirmed | n/a | Unverified |

**Reading.** Plot-level data with conflict gradients exists (Nigeria) but not near the target; near the target, yields exist only at admin-unit level (HarvestStat, FAO/WFP) or privately (ICRC). This supports the grant rationale (new plot-level data needed) and also suggests an **admin-unit-level hold-out test as the feasible preliminary analysis**.

---

## Open items
1. Download the HarvestStat CSV and boundary file in a browser (Dryad page), then run the ACLED test at admin-unit-year level (events inside the polygon, plus within 50 km).
2. Find the published McCullough et al. causal-forest paper and read it.
3. Read the full text of Burke and Lobell, Nziguheba and Meager before quoting any figure.
4. Locate original sources for the broken CIMMYT TAMASA Ethiopia and Nigeria links.
5. Check CIMMYT Sudan 2023/24 report access through the CIMMYT repository in a browser.
6. The ACLED extended-fetch results and OFRA exposure counts are in the scratchpad (`ofra3.py`); copy into the repo if wanted.
