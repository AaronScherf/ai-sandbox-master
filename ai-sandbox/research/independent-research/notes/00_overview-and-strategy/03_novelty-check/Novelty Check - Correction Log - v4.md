# Novelty Check: Correction Log (v4)

**Document:** `Novelty Check - Correction Log - v4.md`  
**Author:** Gemini (Antigravity Session)  
**Date:** 2026-11-11  
**Scope:** Record of substantive corrections, claim decouplings, scope boundaries, and epistemic tag promotions applied in the v4-to-v5 pass across the PhD Research Agenda novelty assessment files, based on `Novelty Check - Claim Spot Check - v1.md`.

---

## 1. Item 1: Crost, Felter, & Johnston (2016) Cash in Conflict Correction

### What Was Wrong in v4
In `Novelty Check - Summary - v4.md` (line 71) and `Novelty Check - RQ3 Transfer - v4.md` (line 58), the finding of Crost, Felter, & Johnston (2016, *JDE*, `1-s2.0-S0304387815000966-main`) was erroneously summarized as:
> *"CCTs in the Philippines increased insurgent violence due to rebel sabotage incentives"*

### Primary Evidence from Transcript Audit
* **File Audited:** `ai-sandbox/research/journal-articles/novelty-check/processed_outputs/1-s2.0-S0304387815000966-main.md`
* **Verbatim Findings (Page 1):**
  > *"We find that cash transfers caused a substantial decrease in conflict-related incidents in treatment villages relative to control villages in the first 9 months of the program. Using unique data on local insurgent influence, we also find that the program reduced insurgent influence in treated villages. An analysis of possible spillovers yields inconclusive results. While we find no statistical evidence of spillovers, we also cannot rule out that the village-level effect was due to displacement of insurgent activity from treatment to control villages."*
* **Root Cause:** Conflation with an earlier paper by the same authors: Crost, Felter, & Johnston (2014, *AER* 104(6): 1833–1856), which evaluated the KALAHI-CIDSS community-driven development infrastructure project and found that project preparation *increased* insurgent attacks because rebels attempted to sabotage infrastructure construction to prevent government credit-claiming.
* **Correction Applied in v5:**
  - Corrected `Novelty Check - Summary - v5.md` (Table 1, Section 2 Insight 3, Table 3 line 71).
  - Corrected `Novelty Check - RQ3 Transfer - v5.md` (Sub-Question 12).
  - Explicitly recorded that cash transfers *decreased* conflict incidents and reduced insurgent influence in treated villages during the first 9 months (with displacement to control villages not ruled out), attributing the sabotage finding to the 2014 CDD study.
  - Promoted to `[FULL-TEXT-READ]`.

---

## 2. Item 2: Groh et al. (2016) and DellaVigna & Pope (2018) Decoupling

### What Was Wrong in v4
In `Novelty Check - Summary - v4.md` (line 70) and `Novelty Check - RQ3 Transfer - v4.md` (line 44), Groh et al. (2016) and DellaVigna & Pope (2018) were conflated into a single claim:
> *"Experts overestimate wage subsidy persistence in Jordan; DellaVigna & Pope trial"*

### Primary Evidence from Transcript Audit
* **Files Audited:**
  - `rest_a_00584.md`: Groh, Krishnan, McKenzie, & Vishwanath (2016), *"Do Wage Subsidies Provide a Stepping-Stone to Employment for Recent College Graduates? Evidence from a Randomized Experiment in Jordan"*, *Review of Economics and Statistics*, 98(3): 488–502.
  - `10-1086-699976.md`: DellaVigna & Pope (2018), *"Predicting Experimental Results: Who Knows What?"*, *Journal of Political Economy*, 126(6): 2410–2456.
* **Verbatim Findings:**
  - Groh et al. (2016, p. 1): *"The wage voucher led to a 38 percentage point increase in employment in the short run, but the average effect is much smaller and no longer statistically significant after the voucher period has expired. The extra job experience gained as a result of the wage subsidy does not provide a stepping-stone to new jobs for these recent graduates..."* Groh et al. contains **no expert forecasting survey or overestimation finding** (terms "expert" and "forecast" do not appear in the study design).
  - DellaVigna & Pope (2018, p. 2): *"We analyze how 208 experts forecast the results of 15 treatments involving monetary and non-monetary motivators in a real-effort task. We compare these forecasts to those made by PhD students and non-experts..."*
* **Correction Applied in v5:**
  - Decoupled the two papers in `Summary - v5.md` and `RQ3 Transfer - v5.md`.
  - Clarified that Groh et al. (2016) is a wage-subsidy RCT in Jordan finding a 38 pp short-term gain that vanished post-subsidy.
  - Retained DellaVigna & Pope (2018) for experimental expert forecasting methodology and crowd-wisdom results.
  - Both promoted to `[FULL-TEXT-READ]`.

---

## 3. Item 3: Tennant et al. (2021) Systematic Review Classification

### What Was Wrong in v4
In `Novelty Check - Summary - v4.md` (line 23), Tennant et al. (2021) was cited under RQ2 as a precedent for "Epidemiological DAG Elicitation" alongside participatory workshop methods.

### Primary Evidence from Transcript Audit
* **File Audited:** `10-1093-ije-dyaa213.md`: Tennant, Murray, Arnold, et al. (2021), *"Use of directed acyclic graphs (DAGs) to identify confounders in applied health research: review and recommendations"*, *International Journal of Epidemiology*, 50(2): 620–632.
* **Verbatim Findings (Page 1):**
  > *"This review examined the use of DAGs in applied health research to inform recommendations for improving their transparency and utility in future research. Methods: Original health research articles published during 1999–2017 mentioning 'directed acyclic graphs' (or similar) or citing DAGitty were identified... A total of 234 articles were identified that reported using DAGs."*
* **Correction Applied in v5:**
  - Removed Tennant et al. (2021) as a precedent for participatory or expert-elicited DAGs.
  - Clarified in `Summary - v5.md` that Tennant et al. is strictly a literature-based systematic review of 234 applied health studies evaluating how authors report and adjust for DAGs.
  - Highlighted that a field-ready workshop protocol to elicit acyclic DAGs from non-technical practitioners remains completely open.
  - Promoted to `[FULL-TEXT-READ]`.

---

## 4. Item 4: Bongers et al. (2021) Scope Strictly Bounded

### What Was Wrong in v4
In `Novelty Check - Summary - v4.md` (lines 23, 38), Bongers et al. (2021) was discussed in connection with participatory systems mapping feedback loops.

### Primary Evidence from Transcript Audit
* **File Audited:** `10-1214-21-aos2064.md`: Bongers, Forré, Peters, & Mooij (2021), *"Foundations of Structural Causal Models with Cycles and Latent Variables"*, *The Annals of Statistics*, 49(5): 2715–2748.
* **Verbatim Findings (Pages 1–2):**
  > *"In this paper, we investigate SCMs in a more general setting, allowing for the presence of both latent confounders and cycles... We introduce the class of simple SCMs that extends the class of acyclic SCMs to the cyclic setting, while preserving many of the convenient properties of acyclic SCMs."*
  > The paper deals strictly with mathematical solvability conditions, $\sigma$-separation, and equilibrium states of random differential equations. The words "participat*" and "elicit*" do not appear in the text (0 occurrences).
* **Correction Applied in v5:**
  - Stated strictly that Bongers et al. (2021) provides mathematical foundations for cyclic SCMs with latent variables via $\sigma$-separation and unique solvability.
  - Removed any claim or implication that it addresses participatory systems mapping or practical elicitation.
  - Promoted to `[FULL-TEXT-READ]`.

---

## 5. Item 5: Brown et al. (2025) Philanthropic VoI Scope & Precision

### What Was Wrong in v4 / Drafts
Earlier draft text asserted that "Brown et al. assume post-trial certainty across decade-long horizons" as an unsupported combined claim.

### Primary Evidence from Transcript Audit
* **File Audited:** `brown-et-al-2025-valuing-information-as-a-philanthropic-funder.md`: Brown, Salisbury, & Ball (2025), *"Valuing Information as a Philanthropic Funder"*, *AEA Papers and Proceedings*, 115: 308–312.
* **Verbatim Findings:**
  - Page 1: *"One reason is that the information generated by new research itself has value if it enables us to direct substantially larger volumes of funding more cost-effectively in future."*
  - Page 3: Identifies parameters for an ORS/zinc trial in Nigeria (\$3.4M grant) with a 23% chance of positively updating, which would unlock \$19 million/year for 10 years (\$190 million total).
  - Page 4: *"Finally, the framework outlined in this paper assumes posttrial certainty—that is, that we find out the 'true' ORS usage rate from funding this trial. This is an oversimplification, as study estimates can deviate from true estimates through sampling error or biases in data collection."*
  - Pages 1–5: Covers global health and development interventions (ORS, bed nets, vaccines, migration loans). Contains no coverage of acute crisis settings, frontline program-design choices, or decision-specific evidence audits.
* **Correction Applied in v5:**
  - Dropped ungrounded combined assertions. Grounded the description strictly in verified transcript text and page numbers.
  - Confirmed GiveWell's VoI model evaluates research-versus-grant capital allocation, leaving frontline operational knowledge audits in crises completely unaddressed.
  - Promoted to `[FULL-TEXT-READ]`.

---

## 6. Item 6: Epistemic Re-tagging Summary (Audit of 14 Papers)

Following the transcript spot-check in `Novelty Check - Claim Spot Check - v1.md`, 14 references were promoted to `[FULL-TEXT-READ]`. The remaining references remain unchanged.

### Complete 51-Reference Epistemic Inventory

| Tag | v4 Count | v5 Count | Change | Description |
| :--- | :---: | :---: | :---: | :--- |
| **`[FULL-TEXT-READ]`** | 0 | **14** | +14 | Full text transcripts audited directly in `processed_outputs/`. |
| **`[REGISTRY-MATCHED]`** | 41 | **28** | -13 | DOIs programmatically resolved at Crossref/DataCite (metadata matched 100%). |
| **`[INSTITUTIONAL-URL]`** | 9 | **9** | 0 | Official institutional publication or book overview page verified. |
| **`[ABSTRACT-READ]`** | 1 | **0** | -1 | Montiel Olea et al. promoted to `[FULL-TEXT-READ]`. |
| **`[UNVERIFIED]`** | 0 | **0** | 0 | All 51 references verified. |
| **Total** | **51** | **51** | 0 | |

### List of 14 `[FULL-TEXT-READ]` References in v5
1. **Altmejd et al. (2019)** – `10-1371-journal-pone-0225826.md` (70% ML accuracy, 65.5% market accuracy, pp. 1, 3).
2. **Bongers et al. (2021)** – `10-1214-21-aos2064.md` (mathematical foundations of cyclic SCMs via $\sigma$-separation, pp. 1–2).
3. **Brown, Salisbury, & Ball (2025)** – `brown-et-al-2025-valuing-information-as-a-philanthropic-funder.md` (GiveWell VoI for grants vs research, pp. 1–5).
4. **Crost, Felter, & Johnston (2016)** – `1-s2.0-S0304387815000966-main.md` (CCT decreased conflict incidents & insurgent influence, p. 1).
5. **DellaVigna & Pope (2018)** – `10-1086-699976.md` (experimental forecasting trial with 208 academic experts, p. 2).
6. **DellaVigna, Pope, & Vivalt (2019)** – `science.aaz1704.md` (Social Science Prediction Platform, p. 2).
7. **Egger et al. (2022)** – `10-3982-ecta17945.md` (unconditional cash transfer local fiscal multiplier 2.52 with minimal price inflation, p. 21).
8. **Gechter (2024)** – `Generalizing the Results from Social Experiments  Theory and Evidence from India.md` (partial identification bounds on ATE across contexts, p. 2).
9. **Groh et al. (2016)** – `rest_a_00584.md` (wage subsidy RCT in Jordan, 38 pp gain dissipating post-voucher, p. 1).
10. **Hjort et al. (2021)** – `hjort-et-al-2021-how-research-affects-policy-experimental-evidence-from-2-150-brazilian-municipalities.md` (BDM WTP elicitation, p. 13; 10 pp reminder letter effect, pp. 1, 4).
11. **Kastner et al. (2009)** – `1-s2.0-S0895435608001509-main.md` (capture-mark-recapture stopping rule in systematic reviews, p. 1).
12. **Montiel Olea et al. (2024)** – `10-48550-arxiv-2408-09187.md` (minimax site selection equivalent to $k$-median problem with site-level covariates, pp. 1, 29).
13. **Tennant et al. (2021)** – `10-1093-ije-dyaa213.md` (systematic review of 234 health articles on DAG reporting, pp. 1–2).
14. **White, Saran, & Welch (2020)** – `saran-2020-evidence-and-gap-maps.md` (Campbell EGM scoping without quantitative stopping rules, pp. 1–2).
