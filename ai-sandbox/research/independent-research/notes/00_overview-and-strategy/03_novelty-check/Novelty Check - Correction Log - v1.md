# Novelty Check: Correction Log and Verification Audit

**Document:** `Novelty Check - Correction Log - v1.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Full reconciliation and error audit of citations, DOIs, substance, and claims in the v1 novelty check series, answering Claude's spot-check findings.

---

## 1. Error Report: How the Errors Occurred in v1

Aaron and Claude requested a plain, transparent explanation of how incorrect DOIs and substantive errors were introduced in the v1 notes:

1. **Reconstruction of Identifiers from Memory instead of Primary Resolution:**
   In the v1 pass, while `search_web` was used to survey general concepts, I did not make tool calls to resolve individual DOIs against authoritative bibliographic registries (such as Crossref or DataCite) or directly open and copy publisher landing-page metadata. Instead, when assembling the bibliography in Markdown, I reconstructed DOIs, volume numbers, issue numbers, and page ranges from memory and pattern extrapolation. Because academic journals share common DOI prefixes (e.g., `10.1257/aer.` for AER, `10.1016/j.jdeveco.` for JDE, `10.2165/` for Adis/PharmacoEconomics), hallucinated numeric suffixes happened to match real but completely different papers published in the same journal (e.g., Claxton & Sculpher 2006 resolving to Weinstein; DellaVigna & Pope 2018 resolving to an unrelated philosophy paper; Lopez et al. 2020 resolving to another weather paper).
2. **Substantive Conflation (Crost et al.):**
   In RQ3, I conflated two separate papers by Benjamin Crost and Joseph Felter:
   * *Crost, Felter, & Johnston (2014, AER 104(6): 1833–1856):* Evaluated a community-driven development (CDD) infrastructure project (KALAHI-CIDSS) and found that project preparation *increased* insurgent attacks because rebels attempted to sabotage implementation.
   * *Crost, Felter, & Johnston (2016, JDE 118: 171–182):* Evaluated the Pantawid conditional cash transfer (CCT) and found that cash transfers *decreased* insurgent influence and violent conflict incidents in treated villages.  
   In v1, I cited Crost, Felter, & "Mansour" (2016) in AER and erroneously claimed that cash transfers *increased* insurgent violence, mixing up the intervention, co-author, journal, and substantive finding.
3. **Misattribution of Titles and Venues from Working Papers:**
   * *Meager (2019):* I cited an early 2015 working paper title ("Understanding the Average and Heterogeneity of Treatment Effects from Six Randomised Trials...") and an incorrect page range (282–318), rather than the published *AEJ: Applied Economics* title ("Understanding the Average Impact of Microcredit Expansions: A Bayesian Hierarchical Analysis of Seven Randomized Experiments", pp. 57–91).
   * *Hummelbrunner (2010):* I cited this from memory as a journal article in *Evaluation* or *Development Policy Review* with a fake SAGE DOI, whereas it is actually a book chapter published by FASID in Tokyo (*Beyond Logframe: Using Systems Concepts in Evaluation*, pp. 1–33).
   * *Montiel Olea et al. (2024):* I cited an invented arXiv identifier (`arXiv:2307.03901`, which resolved in DataCite to a theoretical physics paper on Carroll Scalars) instead of the actual preprint identifier (`arXiv:2408.09187`).
4. **Indiscriminate Tagging as `[VERIFIED]`:**
   I tagged all v1 references as `[VERIFIED]` based on conceptual familiarity rather than verifying that the source landing page or full text was directly opened and audited against displayed metadata.

In this v2 pass, all 38 citations across the notes were queried directly against Crossref and DataCite APIs and verified via primary publisher landing pages.

---

## 2. Table of Item-by-Item Corrections

| Key / Author | What Was in v1 | What Was Wrong | Correction in v2 | Primary Page / Resolution Method |
|---|---|---|---|---|
| **Brown, Salisbury, & Ball (2025)** | `10.1257/pandp.20251068`, AEA P&P 115: 308–312 | DOI resolved to an unrelated paper on gender asset gaps. | Correct DOI: `10.1257/pandp.20251021`, Vol. 115, pp. 308–312. | Crossref API verified; AEA landing page confirmed. |
| **Claxton (1999)** | `10.1002/(SICI)1099-1050(199906)8:4<341::AID-HEC449>3.0.CO;2-9`, *Health Economics* | Wrong journal, truncated DOI. | *Journal of Health Economics*, 18(3): 341–364 (1999). DOI: `10.1016/s0167-6296(98)00039-3`. | Crossref API verified; ScienceDirect opened. |
| **Claxton & Sculpher (2006)** | `10.2165/00019053-200624110-00002` | Suffix `00002` resolved to Weinstein et al. | Correct DOI: `10.2165/00019053-200624110-00003`, *PharmacoEconomics*, 24(11): 1055–1068. | Crossref API verified; Springer/Adis confirmed. |
| **Coughlan de Perez et al. (2015)** | `10.5194/nhess-15-2651-2015` | DOI did not exist in NHESS registry. | Correct DOI: `10.5194/nhess-15-895-2015`, NHESS, 15(4): 895–904. | Crossref API verified; Copernicus/NHESS opened. |
| **Fenwick, Claxton, & Sculpher (2008)** | `10.1177/0272989X07312719`, MDM 28(2): 162–179 | DOI resolved to prostate-cancer screening paper; wrong volume/pages. | Correct DOI: `10.1177/0272989x07308751`, *Medical Decision Making*, 28(1): 21–32 (2008; online 2007). | Crossref API verified; SAGE landing page opened. |
| **IDinsight (2022)** *(Added)* | Omitted from v1 references | Missing from literature check on development VOI. | Allier-Gagneur et al. (2022), "Improving decisions about evidence: IDinsight’s new Value of Information work", IDinsight Blog. | URL: `https://www.idinsight.org/blog/idinsights-new-value-of-information-work/` opened. |
| **Lopez et al. (2020)** | `10.1016/j.ijdrr.2020.101524`, *IJDRR* 45: 101524 | Wrong journal; DOI resolved to a labor-market paper. | Published in *Weather and Climate Extremes*, Vol. 27, Art. 100167. DOI: `10.1016/j.wace.2018.03.006`. | Crossref API verified; ScienceDirect opened. |
| **Andrews, Pritchett, & Woolcock (2013)** | `10.1016/j.worlddev.2013.06.014` | DOI did not resolve. | Correct DOI: `10.1016/j.worlddev.2013.05.011`, *World Development*, 51: 234–244. | Crossref API verified; ScienceDirect opened. |
| **Barbrook-Johnson & Penn (2022)** | `10.1007/978-3-030-80860-0`, cited as 2021 guide | ISBN/DOI was unresolvable; cited earlier report title. | Book title: *Systems Mapping: How to Build and Use Causal Models of Systems*, Palgrave Macmillan, Cham (2022). DOI: `10.1007/978-3-031-01919-7`. | Crossref API verified; SpringerLink opened. |
| **Ben-Haim (2006)** | `10.1016/B978-012088529-9/50002-3` | Unresolvable DOI. | Book: *Info-Gap Decision Theory: Decisions Under Severe Uncertainty* (2nd ed.), Academic Press (2006), ISBN: 978-0-12-373552-2. Linked via ScienceDirect. | ScienceDirect book page opened. |
| **Bowen et al. (2020)** | `10.1596/978-1-4648-1549-2` | Unresolvable DOI (wrong ISBN suffix). | Correct DOI: `10.1596/978-1-4648-1575-1`, World Bank (2020). | Crossref API verified; World Bank Open Knowledge opened. |
| **Hausmann, Rodrik, & Velasco (2008)** | `10.1093/acprof:oso/9780199236589.003.0016` | Unresolvable DOI. | Correct DOI: `10.1093/acprof:oso/9780199534081.003.0015`, in *The Washington Consensus Reconsidered*, pp. 324–355. | Crossref API verified; Oxford Scholarship opened. |
| **Hummelbrunner (2010)** | `10.1177/0268588410375945`, cited as *Evaluation* 16(4) | Hallucinated journal venue and SAGE DOI. | Book chapter: In N. Fujita (Ed.), *Beyond Logframe; Using Systems Concepts in Evaluation* (pp. 1–33), FASID, Tokyo (2010). No Crossref DOI exists. | SCIRP / FASID publication records opened. |
| **Kok (2009)** | `10.1016/j.envsoft.2008.05.004`, subtitle "West Africa" | Wrong journal; resolved to air quality paper. | Published in *Global Environmental Change*, 19(1): 122–133 (2009), subtitle "...example from Brazil". DOI: `10.1016/j.gloenvcha.2008.08.003`. | Crossref API verified; ScienceDirect opened. |
| **Altmejd et al. (2019)** *(Added)* | Omitted from v1 references | Missing from literature check on pre-registered prediction models. | Altmejd et al. (2019), "Predicting the replicability of social science lab experiments", *PLOS ONE*, 14(12): e0225826. DOI: `10.1371/journal.pone.0225826`. | Crossref API verified; PLOS ONE opened. |
| **Crost, Felter, & Johnston (2016)** | `10.1257/aer.20141098`, AER 106(1), authors "Crost, Felter & Mansour" | Conflated with Crost et al. 2014 CDD paper; wrong author, wrong venue, reversed finding. | Authors: Benjamin Crost, Joseph H. Felter, Patrick B. Johnston. *Journal of Development Economics*, 118: 171–182 (2016). DOI: `10.1016/j.jdeveco.2015.08.005`. Finding: CCT *decreased* insurgent influence and incidents. | Crossref API verified; ScienceDirect opened; abstract verified. |
| **Dahabreh et al. (2020)** | `10.1093/aje/kwaa040` | Resolved to AJE editorial list. | Correct DOI: `10.1111/biom.13009`, *Biometrics*, 75(2): 685–694 (2019/2020). | Crossref API verified; Wiley Online Library opened. |
| **DellaVigna & Pope (2018)** | `10.1086/697746` | Suffix `697746` resolved to Philosophy of Science paper. | Correct DOI: `10.1086/699976`, *Journal of Political Economy*, 126(6): 2410–2456. | Crossref API verified; University of Chicago Press opened. |
| **Gechter (2024)** | `10.1080/07350015.2022.2081600`, JBES 41(3): 839–851 (2023) | Unresolvable DOI, wrong volume/pages/year. | Correct DOI: `10.1080/07350015.2023.2241529`, *Journal of Business & Economic Statistics*, 42(2): 801–811 (2024; online 2023). | Crossref API verified; Taylor & Francis opened. |
| **Hotz, Imbens, & Mortimer (2005)** | `10.1016/j.jeconom.2004.02.004` | Suffix `02.004` resolved to Vogelsang & Franses trends paper. | Correct DOI: `10.1016/j.jeconom.2004.04.009`, *Journal of Econometrics*, 125(1–2): 241–270. | Crossref API verified; ScienceDirect opened. |
| **Kastner et al. (2009)** | `10.1186/1471-2288-9-67`, BMC Med Res Methodol | Resolved to unrelated Kastner paper on journal selection. | Published in *Journal of Clinical Epidemiology*, 62(2): 149–157 (2009). Title: "The capture–mark–recapture technique can be used as a stopping rule when searching in systematic reviews". DOI: `10.1016/j.jclinepi.2008.06.001`. | Crossref API verified; ScienceDirect opened. |
| **Meager (2019)** | Title: "...Six Randomised Trials of Social Programs...", pp. 282–318 | Cited early working paper title and incorrect page range. | Title: "Understanding the Average Impact of Microcredit Expansions: A Bayesian Hierarchical Analysis of Seven Randomized Experiments", *AEJ: Applied Economics*, 11(1): 57–91 (2019). DOI: `10.1257/app.20170299`. | Crossref API verified; AEA landing page opened. |
| **Montiel Olea et al. (2024)** | `10.48550/arXiv.2307.03901` | Suffix resolved in DataCite to physics paper on Carroll Scalars. | Correct arXiv identifier: `arXiv:2408.09187 [econ.EM]`. DOI: `10.48550/arXiv.2408.09187`. | DataCite API verified; arXiv page opened. |
| **Pritchett & Sandefur (2015)** | `10.1257/aer.p20151034` | Suffix `1034` resolved to paper on coercion and high pay. | Correct DOI: `10.1257/aer.p20151016`, *American Economic Review*, 105(5): 471–475. | Crossref API verified; AEA landing page opened. |
| **Rosenzweig & Udry (2020)** | `10.1093/restud/rdaa008`, REStud 87(5): 2457–2481 | Resolved to paper on commitment in organizations. | Correct DOI: `10.1093/restud/rdz021`, *The Review of Economic Studies*, 87(1): 343–381 (2020; online 2019). | Crossref API verified; OUP landing page opened. |
| **Saran & White (2018) / White et al. (2020)** | `10.1186/s13750-018-0122-2`, *Environmental Evidence* | Unresolvable DOI. | Core methods paper: White, Saran, & Welch (2020), "Evidence and gap maps", *Campbell Systematic Reviews*, 16(1): e1075. DOI: `10.1002/cl2.1075`. | Crossref API verified; Wiley opened. |
| **Vivalt (2020)** | `10.1093/jeea/jvz054` | Resolved to Danish job-displacement paper. | Correct DOI: `10.1093/jeea/jvaa019`, *Journal of the European Economic Association*, 18(6): 3045–3089 (2020). | Crossref API verified; OUP landing page opened. |

---

## 3. Substantive Corrections and Verdict Adjustments

1. **Crost et al. (2016) Cash Transfer and Conflict Findings:**
   * *v1 Error:* Claimed the paper showed cash transfers *increased* insurgent violence due to sabotage.
   * *Correction:* Crost, Felter, & Johnston (2016, JDE) evaluated the Pantawid Pamilyang Pilipino Program (4Ps) in the Philippines using an RDD/RCT design across municipalities. They found that CCT eligibility caused a statistically significant **decrease** in conflict incidents and reduced insurgent influence during the first 9 months. The mechanism was that cash transfers improved local economic welfare and increased community cooperation with the government, reducing rebel support. (The *increase* in violence was reported by Crost, Felter, & Johnston 2014 in AER for *community-driven infrastructure projects*, where rebels sabotaged project construction to prevent government credit-claiming).
   * *Implication for RQ3:* Cash transfers under conflict do not uniformly increase violence; rather, whether cash reduces conflict (via economic relief/hearts-and-minds) or increases conflict (via predation, extortion, or sabotage) depends sensitively on program visibility, delivery mechanics, and territorial control. Unadjusted transfer from peaceful natural disasters to conflict settings remains fundamentally invalid because the direction and magnitude of the conflict feedback mechanism vary across conflict types.

2. **Surprise 1 (Value of Information in Aid):**
   * *v1 Error:* Claimed a "total absence" of VOI in aid, contradicting mentions of GiveWell and IDinsight.
   * *Correction:* IDinsight (Allier-Gagneur et al., 2022) has published simulation-based VOI methodologies specifically evaluating whether to commission an evaluation before deciding whether to scale up, defund, or redesign an international development program. GiveWell (Brown et al., 2025) has institutionalized a VOI framework for philanthropic grantmaking.
   * *Adjusted Claim:* Value of Information is **well developed for global philanthropic grant allocation and stable development scale-up decisions**, but remains **unapplied to operational, frontline program design in protracted or recurrent humanitarian crises**, where acute delivery constraints, displacement churn, and compound shocks alter the decision space.
   * *Verdict for RQ1:* Updated from "Partly answered" to **"Substantially answered in adjacent domains (health economics, development evaluation consulting, philanthropic grant allocation); open for operational crisis adaptation."**

3. **Surprise 2 (Participatory Causal Mapping vs. Acyclic Graphs):**
   * *v1 Error:* Claimed that feedback loops make causal identification "mathematically impossible" and that there is "virtually no literature" on participatory DAGs.
   * *Correction:* Cyclic structural causal models are formally defined in mathematics (e.g., Spirtes, 1995; Bongers et al., 2021) using $\sigma$-separation and equilibrium conditions. Furthermore, dynamic feedback can be represented without cycles by unrolling time in dynamic Bayesian networks ($X_t \to Y_t \to X_{t+1}$). Participatory DAG elicitation protocols also exist in public health and epidemiology (e.g., Tennant et al., 2021).
   * *Adjusted Claim:* While cyclic causal models exist mathematically and time-unrolling is standard in theory, participatory systems mapping in development practice (PSM, CLDs, FCMs) overwhelmingly defaults to static cyclic loops. Bridging frontline practitioner mental models into time-indexed, identification-compliant DAGs or scenario-specific log-frames remains an unstandardized, high-friction operational bottleneck.

4. **Surprise 3 (Pre-Registered Transport Models):**
   * *v1 Error:* Claimed "no one has ever" pre-registered a prediction model and that pre-registration only exists for "human hunches."
   * *Correction:* Altmejd et al. (2019, *PLOS ONE*) pre-registered statistical and machine-learning models to predict replication outcomes in the Social Science Replication Project. CEGA and SSPP have pre-registered thousands of forecasts. Montiel Olea et al. (2024) developed minimax-regret site-selection functions to bound external validity error.
   * *Adjusted Claim:* While statistical models have been pre-registered to predict *binary replication success* of lab experiments, and human forecasts of field trials are common, **I found no example** in development or humanitarian aid where a researcher calibrated an ex-ante causal transport model (selection diagram, Dahabreh IPPW/g-computation, or Gechter bounds), pre-registered numerical effect predictions and bounds for an unstudied crisis target population, built an evaluation into implementation, and prospectively tested the realized effect against the ex-ante prediction.

5. **Cross-Cutting: Evidence Gap Maps vs. Capture-Recapture:**
   * *v1 Error:* Unreconciled claims between capture-recapture search stopping rules and Evidence Gap Maps lacking stopping metrics.
   * *Correction:* Capture-recapture (CMR; Kastner et al., 2009) has been explored in clinical systematic reviews to estimate the number of missed studies across database overlaps. However, **in Evidence and Gap Maps (EGMs; White et al., 2020; Saran & White, 2018), CMR has not been operationalized as a routine stopping rule**. EGMs classify cells as "gaps" purely based on retrieved studies without statistical metrics establishing whether an empty cell reflects true evidence absence or search under-powering.
