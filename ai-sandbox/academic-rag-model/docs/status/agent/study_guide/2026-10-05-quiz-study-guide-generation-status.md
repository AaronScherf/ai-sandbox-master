# Econometrics Quiz Study Guide Generation: Run Audit & Status

Date: 2026-10-05 · Package: `agent/study_guide` (and `agent/rag`) · Kind: Generation Run, Audit & Review
Builds on: `docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md`, `docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`, and `agent/summary_enhance/`.

---

## 1. Executive Summary

This document records the operational run, architectural evaluation, and quality audit of the exam-focused study guide generated for the graduate econometrics quiz (covering parameter-based test statistic calculations, linear and non-linear restrictions, the Delta method, and the testing trinity).

The study guide was produced following the transcription of new course materials from the preceding two weeks (two Excalidraw handwritten lecture notes from 2026-09-30 and 2026-10-05, their 16 resolved question sidecars, and three professor lecture PDFs from 09-21, 09-28, and 09-30).

---

## 2. Pipeline Provenance & Architectural Scope

### Is the generation script reusable or topic-specific?
The generation script created for this run (`academic-rag-model/agent/rag/generate_quiz_guide.py`) is an **ad-hoc, topic-specific procedural script**. 

* **Status:** It directly hardcodes the section specifications, retrieval queries, and exam question parameters for this specific econometrics topic (wage equation Mincer model with quadratic experience profile). It is **not** currently a generalized, course-agnostic CLI.
* **Precedent:** This mirrors the ad-hoc procedural script run by Codex on 2026-10-03 that originally drafted `wald_lm_lr_tests.md` before `summary_enhance` was built.
* **Planned Generalization:** The architectural design in `docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md` (on branch `claude/study-guide-spec`) defines the intended generalized framework (`agent.study_guide`). Under that design, study guides will be specified declaratively in TOML files (`guide_specs/<course>/<guide_id>.toml`), separating topic configuration from pipeline execution.

---

## 3. Operational Run Details

1. **New Course Ingestion:**
   * Transcribed and expanded:
     * `Econometrics 2026-09-30 10.09.59.excalidraw.md` (Wald Test, $R'\beta = r$ vs $r(\beta) = 0$).
     * `Econometrics 2026-10-05 10.09.00.excalidraw.md` (Testing Trinity: Wald, LR, LM, slides integration).
     * `092126.pdf`, `092826.pdf`, `093026.pdf` (Professor lecture PDFs).
   * Resolved questions: 16 open handwritten tags resolved into 2 sidecar files via `agent.rag.resolve_questions` with `gemini-3.6-flash`.
   * Index reconciliation: Ran `index_search rebuild` and `index_search chunk --course econometrics` (chunking 12 new/updated files into `.index/chunks/econometrics.json`).
2. **Study Guide Synthesis:**
   * Script: `agent/rag/generate_quiz_guide.py`
   * Model: `gemini-3.8-flash` on `PAID_GEMINI_KEY`, temperature 0.2.
   * Retrieval: 12 passages per section (textbooks, recitations, new notes, and question sidecars).
   * Primary Deliverable: `academic_notes/econometrics/summaries/wald_hypothesis_testing_quiz_prep.enhanced.md` (151,743 bytes, 7 sections).

---

## 4. Critical Quality Audit & Evaluation

An evaluation of the generated artifact (`wald_hypothesis_testing_quiz_prep.enhanced.md`) against the user's requirements reveals clear strengths alongside critical structural deficiencies:

### What Succeeded
1. **Mathematical Correctness on Exam Problem Q3:**
   * **Part i:** Correct point estimate $\hat{\theta}_1 = 100(0.118) = 11.8\%$ and standard error $\operatorname{SE}(\hat{\theta}_1) = 100(0.008) = 0.8$.
   * **Part ii:** Correct linear combination $\hat{\theta}_2 = 1.16$, robust variance expansion $\widehat{\operatorname{Var}}(\hat{\theta}_2) = 0.4176 + 4,000 \widehat{V}_{23}$, Wald statistic $W = \frac{0.0256}{0.4176 + 4,000 \widehat{V}_{23}}$, $\chi^2(1)$ reference distribution, and 3.84 critical value.
   * **Part iii:** Proper optimization FOC $\theta_3 = -\frac{50 \beta_2}{\beta_3} \approx 36.36$ years, Delta method Jacobian gradient evaluation $\widehat{G} = [0, 2272.73, 1652.89, 0]'$, analytical variance form $\widehat{\operatorname{Var}}(\hat{\theta}_3) = 579.37 + 7.513 \times 10^6 \widehat{V}_{23}$, and 95% confidence interval formula.
2. **Grounded Explanations:**
   * Strong coverage of the Delta method, Taylor expansions, and the Gregory-Veall non-invariance pathology of the non-linear Wald test.

### Critical Deficiencies & Failure Modes

1. **Disproportionate Focus on the Wald Test:**
   * Out of 7 sections, 5 focus almost exclusively on the Wald test. The Likelihood Ratio and Lagrange Multiplier tests are relegated to a single comparison section, leaving the study guide unbalanced for a quiz covering general hypothesis testing.
2. **Over-Indexing on Student Margin Questions:**
   * Because the newly generated question sidecars had high semantic relevance to the queries, retrieval ranked sidecar passages very high. As a result, the synthesis disproportionately echoed specific student margin queries (e.g., repeating explanations of $R'\beta = r$ and "why $R' V_\beta R$ appears") rather than maintaining an authoritative graduate lecture tone.
3. **Topic Scattering & Unnecessary Repetition:**
   * The asymptotic normality setup ($\sqrt{n}(\hat{\beta} - \beta) \xrightarrow{d} \mathcal{N}(0, V_\beta)$) and regularity conditions are restated from scratch in Sections 1, 2, 4, and 5. This makes the guide feel like separate independent answers rather than a cohesive, structured study guide.
4. **Markdown Table & LaTeX Formatting Corruption:**
   * Unescaped pipe characters (`|`) inside LaTeX math blocks (such as conditional expectations $\mathbb{E}[Y \mid X]$, conditioning bars, or matrix column dividers) were interpreted by Markdown renderers as table column delimiters, severely corrupting markdown tables.
5. **Reader-Facing In-Text Citation Clutter:**
   * Inline citation brackets referencing internal note filenames and raw question IDs (e.g. `[§q4-11e5aef8...]` and `[Econometrics 2026-09-30...]`) cluttered the reading experience. Following the `summary_enhance` design standard, provenance belongs in the YAML frontmatter (`indexer_source_refs` / `source_map`), keeping the body clean and readable.
6. **ASCII Diagram Rendering Failure:**
   * The procedural script attempted to render the geometry of the Testing Trinity via ASCII art in a code block. This failed to align cleanly across Markdown viewers and looked primitive. Mathematical and conceptual geometry requires either rich interactive Plotly figures via `agent.viz` or high-resolution LLM-generated scientific diagrams.

---

## 5. Visualization Integration & Pipeline Recommendation

* **Connect `agent.viz` to `agent.study_guide`:** The existing visualization sub-agent (`agent/viz`) generates interactive Plotly visualizations and static exports. Study guides should be able to invoke `agent.viz` to dynamically render econometric graphs (such as likelihood curvature, rejection regions, and joint confidence ellipses) based on retrieved course parameters.
* **Support LLM-Generated Conceptual Diagrams:** For abstract theoretical geometry (such as the concave log-likelihood function contrasting Wald horizontal distance, LR vertical drop, and LM score tangent), pure data plotting in Plotly is often less communicative than clean pedagogical textbook illustrations. The pipeline should support generating and embedding high-resolution scientific diagrams alongside Plotly objects.

---

## 6. Evolution across Iterative Versions (v1 to v4)

1. **v1 Ad-Hoc Draft (`wald_hypothesis_testing_quiz_prep.enhanced.md`):**
   * *Outcome:* 151 KB initial draft from `generate_quiz_guide.py`.
   * *Deficiencies:* Heavy bias toward Wald test (5 of 7 sections); over-indexed on student margin questions; unescaped LaTeX pipes broke markdown tables; cluttered in-text citation UUIDs.
2. **v2 Cleaned Target (`wald_hypothesis_testing_quiz_prep.v2.cleaned.md`):**
   * *Outcome:* 30 KB curated clean target.
   * *Refinements:* Reorganized into a 5-part structure; eliminated repetitive asymptotic setups; converted in-text question tags to YAML frontmatter; escaped table pipes.
3. **v3 Comprehensive Exploration (`wald_hypothesis_testing_quiz_prep.v3.comprehensive.md`):**
   * *Outcome:* 42 KB expanded theoretical version.
   * *Refinements:* Added high-resolution Testing Trinity visual diagram (`assets/testing_trinity_geometry.jpg`); added independent LR and LM theoretical sections; explored advanced PhD econometrics (QMLE sandwich theory, Pitman drift, boundary mixtures, GMM distance metrics).
   * *Audit Finding:* While theoretically sound, external topics (Pitman drift, boundary problems, GMM) exceeded the student's actual current course boundaries.
4. **v4 Grounded Final Target (`wald_hypothesis_testing_quiz_prep.v4.final.md`):**
   * *Outcome:* 46 KB definitive gold-standard reference.
   * *Key Refinements:*
     * **Strict Grounding:** Pruned ungrounded external topics (Pitman drift, boundary mixtures, GMM).
     * **General Problem-Solving Recipes (Part 6):** Step-by-step shorthand walkthroughs for Linear Wald, Non-Linear Wald (Delta Method), Likelihood Ratio, and LM Auxiliary Regression based on what prompt info is given.
     * **Recitation Nuances (Recitation 5 & TA Notes 07/08):** Integrated Song's covariance hierarchy (Homoskedastic vs. HC0 vs. HC1), 4th-moment regularity conditions ($\mathbb{E}[\|X_i\|^4] < \infty$), GLS Wald form, Chen's asymptotic pivots, normal mean known variance exact agreement case, and multiplier recovery formulas.
     * **Dedicated Formula Dictionary & Variable Glossary (Part 8):** Term-by-term breakdown explaining every matrix, vector, and scalar ($R$, $\hat{\beta}$, $\widehat{\mathbf{V}}_{\hat{\beta}}$, $r_0$, $\hat{d}$, $RSS_U$, $RSS_R$, $\dot{\ell}_n$, $\tilde{\lambda}$).
     * **Pure Frontmatter Provenance:** Completely removed in-text section and note citations from the prose, concentrating all attribution cleanly in YAML frontmatter (`source_basis`, `source_map`).

---

## 7. Pipeline Architecture Blueprint for `agent.study_guide`

This iterative process provides a concrete specification for the reproducible, declarative study guide generator designed in `claude/study-guide-spec` (`docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`). The automated pipeline should follow this five-stage execution architecture:

```
[ TOML Spec ] ---> [ Dual-Tier Retrieval ] ---> [ Multi-Stage Generation ]
                            |                             |
                            v                             v
                   (Course Notes > Sidecars)    (Theory -> Recipes -> Cheatsheet)
                                                          |
                                                          v
                                               [ Post-Process & Linters ]
                                                          |
                                                 * Escape LaTeX pipes in tables (\mid)
                                                 * Strip in-text citations -> Frontmatter
                                                 * Embed Visual Assets (assets/*.jpg)
                                                          |
                                                          v
                                            [ Permanent Vault Deliverable ]
```

### Stage 1: Declarative Topic Specification (`guide_specs/<course>/<id>.toml`)
* Separate the study guide prompt, required sections, and problem parameters from pipeline code.
* Define target assessments, required tests (e.g., Wald, LR, LM), and specific worked problem configurations.

### Stage 2: Dual-Tier Retrieval Filtering
* **Corpus Hierarchy:** Weight instructor materials (lecture notes, professor slides, recitation notes) above student margin question sidecars to prevent the synthesis from over-indexing on student queries.
* **Scope Guard:** Restrict retrieval to current-semester modules to prevent premature introduction of future topics (e.g., GMM or panel methods).

### Stage 3: Modular Generation Stages
* **Section 1: Foundations & Geometry:** Unified principle and likelihood geometry.
* **Section 2–4: Independent Deep-Dives:** Balanced standalone treatments of each test principle.
* **Section 5: Problem-Solving Recipes:** Shorthand recipe walkthroughs categorized by given problem inputs.
* **Section 6: Worked Exam Problems:** Numerical walkthroughs with exact parameter calculations.
* **Section 7: Formula Glossary & Cheatsheets:** Equation dictionary and quick-recall tables.

### Stage 4: Automated Linters & Post-Processing
* **Table Pipe Escaping:** Automatically scan all markdown tables and replace unescaped math pipes (`|`) with `\mid`, `\vert`, or `\|` to preserve markdown table rendering.
* **Provenance Sanitization:** Automatically extract inline source tags (e.g., `[§q4-...]`, `(Recitation 5)`) and aggregate them into YAML frontmatter (`source_map`), keeping human-facing text clean and readable.

### Stage 5: Visual Asset Pipeline Integration
* Call `agent.viz` for parameterized Plotly curves or generate high-resolution scientific diagrams for theoretical geometry.
* Persist images permanently to `<vault>/<course>/summaries/assets/` rather than leaving them in transient agent workspaces.
