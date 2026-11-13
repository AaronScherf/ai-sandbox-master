# Documentation Probe: Correction Log (v1)

*Gemini (Antigravity), 2026-11-11. Bounded documentation probe evaluating candidate programmes for a retrospective desk audit of evidence use in recurrent crises. This document provides an audit trail of all corrections, rubric refinements, and factual updates made between `Documentation Probe - Scored Candidates - v1.md` and `Documentation Probe - Scored Candidates - v2.md`.*

---

## 1. Overview of the Correction Pass

Following an independent spot-check of the Kenya HSNP Phase 2 documentation by Claude, a thorough verification pass was conducted across all three candidate programmes. The review confirmed the majority of primary findings (including the 14-document DevTracker inventory, the seven-option appraisal structure, quantitative targeting index values, key academic citations, delivery-cost shares, and the completed ICR trail for Ethiopia). However, the spot-check identified two specific citation issues in Candidate C, highlighted a rubric ceiling effect that obscured programmatic differences, and required an updated operational status check for Somalia and Ethiopia as of 2026-11-11.

This log documents every correction made, explains transparently how citation errors entered v1, and details the structural updates in v2.

---

## 2. Structured Correction Table

| # | Item / Focus | Claim in v1 | Issue Identified / What Was Wrong | Correction in v2 | Document / Page / Section Opened |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Kenya HSNP 2: Coady, Grosh, & Hoddinott (2004) Citation** | Stated that Business Case 4857207 cites Coady, Grosh, & Hoddinott (2004) to compute targeting indices (1.21, 1.17, 1.15, 1.47) and justify the hybrid CBT-PMT model. | Claude's spot-check found that Table 3's source caption states "OPM (2010)" and questioned whether Coady et al. was merely inferred from the "CGH index" label. | **Verified and clarified:** The citation is explicitly present in the primary Business Case ODT text at endnote 63 (`_edn62` in XML), linked to paragraph 530: `Coady D., Grosh M., and Hodditnott J. (2004). Targeting of Transfers in Developing Countries: Review of Lessons and Experience. World Bank and IFPRI`. Endnotes reside in `<text:note>` XML structures rather than inline body text, which caused Claude's initial search to miss it. v2 retains the citation with exact endnote documentation. | `Kenya_HSNP2_Business_Case.odt`, paras 530–532, endnote 63. |
| **2** | **Kenya HSNP 2: Disasters Emergency Committee (DEC 2011) Citation** | Stated that Business Case 4857207 cites a "Disasters Emergency Committee (DEC 2011) Horn of Africa Evaluation" in para 61 to justify the pre-registered emergency scale-up mechanism. | Claude searched the Business Case and found no citation to the DEC. Re-checking `content.xml` revealed **0 occurrences** of "Disasters Emergency Committee" or "DEC". | **Marked UNVERIFIED and excised:** The attribution in v1 was a pure memory substitution / hallucination from general 2011 drought literature. In reality, para 61 and endnote 33 cite `DFID (2012) Kenya Multi-Hazard Disaster Risk Assessment`. The DEC citation has been removed from v2 and replaced with the verified DFID 2012 assessment. | `Kenya_HSNP2_Business_Case.odt`, para 61, endnote 33. |
| **3** | **Rubric: Split Criterion 1 (Options in Design)** | Criterion 1 ("Design document with options") awarded Kenya 2/2 because 7 options were appraised, yielding a maximum total score of 14/14. | The 7 options in the Business Case varied only caseload scale, speed, and GoK budget share of a single cash design. They did not represent alternatives differing in kind (e.g., cash vs. food, public works vs. grants). The rubric hit a ceiling and obscured qualitative differences across programmes. | **Criterion 1 split into 1a and 1b:**<br>- **1a. Options compared (0–2):** Formal comparison of options against a counterfactual.<br>- **1b. Options differ in kind (0–2):** 0 assigned if options are scale/speed/budget variants of one intervention. Kenya re-scored to 1a=2, 1b=0. Ethiopia re-scored to 1a=1, 1b=1 (compares cash vs. food and credit vs. asset grants). Somalia re-scored to 1a=1, 1b=0. | Business Case paras 273–355, 699–701; PAD1022 paras 57, 63; PAD3421 p. 86. |
| **4** | **Rubric: Finer Benchmark Anchors** | Criteria 1, 2, and 4 relied on general 0–2 scale definitions without explicit single-sentence benchmark anchors. | A second reader could score evidence traces or closeout evaluations inconsistently without precise operational criteria. | **Added three single-sentence benchmark anchors** to the rubric definitions for: (1) evidence base documented and opened, (2) rejection rationale recorded, and (3) closeout traces results to named design assumptions. | Section 2 of `Documentation Probe - Scored Candidates - v2.md`. |
| **5** | **Setting Fit Analysis** | v1 provided brief hindsight-bias notes for each candidate but lacked a systematic matrix evaluating crisis context. | Did not explicitly evaluate whether programmes were conflict-affected, displacement-related, or drought-only, or what Kenya HSNP 2 specifically can and cannot test for Aaron's research agenda. | **Added Section 3 (Setting Fit Matrix):** Systematically categorizes all three candidates across conflict, displacement, hazard type, and system transition. Explicitly documents that HSNP 2 cannot test decision-making under active armed conflict or complex displacement. | Section 3 of `Documentation Probe - Scored Candidates - v2.md`. |
| **6** | **Somalia Status Re-check (Date: 2026-11-11)** | Stated that parent project P171346 "remains active through December 31, 2025" and rated Somalia premature. | Today is 2026-11-11, so December 31, 2025 has passed. Furthermore, the web accessibility of World Bank project pages was not evaluated. | **Status re-checked via Projects and WDS APIs:** Projects API still returns `Status: Active`, `Closing Date: 12/31/2025`, with **0 disclosed ICRs** in WDS. P174065 closed March 31, 2024 with 0 disclosed ICRs. Direct HTTP GET to World Bank project pages loads an empty client-side JavaScript SPA shell (`<title>Projects</title>`, 27 words body) and is tagged **NOT OPENED**. Re-stated verdict as PREMATURE as of 2026-11-11. | World Bank Projects API; WDS Portal; static URLs for P171346 and P174065. |
| **7** | **Ethiopia PSNP 4 Closeout Trail** | Identified ICR6153 and IEG evaluation in narrative text. | Needed explicit verification of disclosed completion reports, dates, report numbers, and URLs opened. | **Verified and opened:** World Bank ICR6153 (disclosed 2023-12-09, 62 pp.), IEG ICR Review ICRR0023858 (disclosed 2024-08-08, 22 pp.), and IEG Country Program Evaluation FY2013–23. | `Ethiopia_PSNP4_ICR_ICR6153.pdf`; `Ethiopia_PSNP4_IEG_ICRR0023858.pdf`. |
| **8** | **Document Access Report** | Access status was reported informally in document inventory tables without unified categorization. | Did not provide a strict, standardized classification of access status across all cited sources. | **Added Section 7 (Document Access Report):** Systematically categorizes all 23 consulted documents as full text opened and read, abstract only, landing page only, or not opened. | Section 7 of `Documentation Probe - Scored Candidates - v2.md`. |

---

## 3. Account of How the Citation Errors Entered v1

A core requirement of this correction pass is to provide a candid, transparent account of how the two citation issues identified by Claude entered `Documentation Probe - Scored Candidates - v1.md`.

### 1. Coady, Grosh, & Hoddinott (2004): Nested XML Structure vs. Visible Table Caption
In v1, the report claimed that the DFID Business Case cited Coady, Grosh, & Hoddinott (2004) to calculate targeting efficiency scores (1.21 for CBT, 1.17 for Social Pension, 1.15 for Dependency Ratio, and 1.47 for PMT) and justify the hybrid targeting model.

When Claude spot-checked this claim against the downloaded text, Claude noted:
> *"The text uses the label 'CGH index' but its source line for Table 3 is 'OPM (2010)', and Coady et al. does not appear in the Business Case."*

**What actually occurred:**
- The citation to Coady, Grosh, & Hoddinott (2004) is genuine and exists within the primary document. In the original LibreOffice OpenDocument (`Kenya_HSNP2_Business_Case.odt`), endnotes are encoded in the document XML (`content.xml`) within `<text:note text:note-class="endnote">` elements rather than in the regular body text paragraphs.
- Specifically, paragraph 530 references endnote 63 (`text:id="edn62"` in XML), which reads:
  ```xml
  <text:note text:id="edn62" text:note-class="endnote">
    <text:note-citation text:label="63">63</text:note-citation>
    <text:note-body>
      <text:p text:style-name="Endnote">Coady D., Grosh M., and Hodditnott J. (2004). Targeting of Transfers in Developing Countries: Review of Lessons and Experience. World Bank and IFPRI</text:p>
    </text:note-body>
  </text:note>
  ```
- Because Table 3 directly below paragraph 532 bears the caption `Source: OPM (2010)`, a standard plain-text search across the body text or table captions fails to find the author names unless endnote structures are unpacked.
- **The flaw in v1:** While the substantive finding was factual, v1 failed to cite the exact endnote number (endnote 63) or explain that Table 3 was an OPM calculation derived from the Coady et al. (2004) methodology. This omission created an apparent discrepancy during independent replication. In v2, this has been explicitly documented with exact paragraph and endnote references.

### 2. Disasters Emergency Committee (DEC 2011): Memory Contamination and Lack of String Verification
In v1, the report claimed:
> *"Disasters Emergency Committee (DEC 2011) Horn of Africa Evaluation (cited para 61): Directly tied to designing the pre-registered emergency drought scale-up mechanism to bypass slow international appeals."*

When Claude spot-checked this claim, Claude found no citation to the DEC in the document.

**How this error entered v1:**
- This was an unforced error resulting from **latent memory substitution / hallucination**.
- During Turn 1 of the initial session, the agent recalled the broader academic and humanitarian policy debate following the 2011 Horn of Africa drought, where the Disasters Emergency Committee's real-time evaluation and synthesis reports were widely cited as justification for shifting from reactive appeals to pre-financed safety nets.
- When drafting the evidence synthesis for Candidate C, paragraph 61 of the Business Case was reviewed. Paragraph 61 discusses the severe humanitarian and economic costs of the 2011 drought and argues for pre-programmed scalable cash transfers to avoid delayed response.
- Instead of executing a strict string verification tool call on `content.xml` for paragraph 61's endnote, the agent conflated the generic background discussion of the 2011 drought with the well-known 2011 DEC evaluation from memory, erroneously attributing a formal citation to DEC in the text.
- **The actual text:** Re-inspection of `content.xml` confirmed that "Disasters Emergency Committee" and "DEC" appear **zero times** in the document. Paragraph 61 actually references endnote 33 (`text:id="edn32"`), which cites:
  `DFID (2012) Kenya Multi-Hazard Disaster Risk Assessment`.
- **Correction:** The DEC citation has been formally marked as **UNVERIFIED / HALLUCINATED** and completely excised from v2, replaced with the verified DFID (2012) assessment.

---

## 4. Summary of Rubric Score Changes

With the refinement of Criterion 1 into 1a (Options compared) and 1b (Options differ in kind), the total possible score increased from 14 to 16 points.

| Candidate Programme | v1 Score (out of 14) | v2 Score (out of 16) | Score Shift Explanation |
| :--- | :---: | :---: | :--- |
| **Candidate A: Somalia Baxnaano Sequence** | 11 / 14 (78.6%) | **11 / 16 (68.8%)** | Scored 1 on 1a (informal options mentioned), 0 on 1b (no comparison of alternative modalities differing in kind). Evidence and closeout remain at 1 due to active status and missing ICR. |
| **Candidate B: Ethiopia PSNP 4** | 13 / 14 (92.9%) | **14 / 16 (87.5%)** | Scored 1 on 1a (lacks whole-programme horse-race matrix), but awarded 1 on 1b because PAD1022 explicitly evaluates and compares distinct modalities differing in kind (cash vs. food; credit vs. asset grants). Maintained maximum scores (2) on evidence trace and candid closeout ICR. |
| **Candidate C: Kenya HSNP Phase 2** | 14 / 14 (100.0%) | **13 / 16 (81.3%)** | Scored 2 on 1a (rigorous 7-option comparative appraisal), but scored 0 on 1b because all 7 options are scale, speed, or financing variants of a single cash transfer intervention. This breaks the v1 ceiling effect and accurately reflects design limitations. |

---

## 5. Summary of Candidate Recommendation (v2)

For an initial single-case desk audit, **Kenya HSNP 2 (Candidate C)** remains the cleanest starting point because its design-to-closeout documentation is fully bounded, accessible, and structured under a single coherent bilateral standard (DFID Business Case, five Annual Reviews, and a Project Completion Review). While HSNP 2's options appraisal evaluated variants of a single cash design rather than options differing in kind, its explicit evidence section, quantitative targeting indices, and direct attribution to implementing suppliers (DAI, Equity Bank, OPM) provide an unambiguous paper trail. However, because HSNP 2 is a drought-only programme in a stable institutional setting, it cannot test how decision-makers use evidence amidst active armed conflict or complex displacement. Therefore, expanding to a **two-case comparative design** pairing Kenya with **Ethiopia PSNP 4 (Candidate B)** is strongly recommended and well worth the additional effort. This paired design leverages Kenya for its textbook ex-ante options trace and commercial contractor transparency, while using Ethiopia's candid closeout evaluation (ICR6153) and real-world modality comparisons (cash vs. food, credit vs. asset grants) to test how evidence holds up under conflict, macroeconomic shocks, and implementation failure.
