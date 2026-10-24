# Study Guide Generation & Revision Pipeline (`agent/study_guide`): Comprehensive Status & Evaluation

**Pipeline:** `agent/study_guide` (and companion `agent/summary_enhance`)  
**Status as of:** 2026-10-24  
**Primary Specs:** [`docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`](../../../superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md)  
**Implementation Plans:** [`docs/superpowers/plans/2026-10-05-study-guide-pipeline.md`](../../../superpowers/plans/2026-10-05-study-guide-pipeline.md), [`docs/superpowers/plans/2026-10-08-guide-revise-pipeline.md`](../../../superpowers/plans/2026-10-08-guide-revise-pipeline.md)  
**Trackers:** [`docs/trackers/academic_hub_to_do.md`](../../trackers/academic_hub_to_do.md) (TODO-0002 through TODO-0009, TODO-0084)

---

## 1. Executive Summary & Holistic Purpose

This document serves as the **central, holistic status document** for the study guide generation and revision pipeline (`agent/study_guide`). It consolidates the operational history, empirical quality audits, cost metrics, and architectural evolution across all generation attempts from early econometrics prototypes through multi-unit graduate microeconomics syntheses.

The pipeline's core mandate is to transform indexed course materials (lecture notes, Excalidraw whiteboards, textbook chapters, problem sets, and TA solutions) into mathematically rigorous, pedagogically authoritative, exam-focused study guides without requiring students to wade through fragmented source files.

---

## 2. Pipeline Architecture & Execution Stages

The production architecture consists of five distinct, decoupled stages designed for reproducibility, budget control, and checkpointed recovery:

1. **Specification (`guide_specs/<course>/<id>.toml`):**
   Declarative configuration defining topic sequence, student focus instructions, source retrieval rules (`section` for pinned textbooks, `file` for pinned notes/slides, `discover` for bounded vector search), target models, prompt templates, and optional revision criteria.
2. **Source Planning (`plan` & `apply-review`):**
   Resolves TOML rules against the hub index (`indexer.index_search`). Generates an explicit source plan ledger (`<id>.plan.json`) and an interactive review artifact (`<id>.review.json`). Discovered passages require explicit approval before entering the draft.
3. **Grounded Drafting (`draft`):**
   Synthesizes section content strictly from accepted plan passages using Gemini models (`gemini-3.8-flash` default). Features mid-run cost estimation, automatic stopping (`--max-cost`), and partial recovery (`<guide>.recovered.md`).
4. **Worked Example Enhancement (`enhance` via `agent.summary_enhance`):**
   Optionally expands selected topics with step-by-step mathematical recipes, code-executed worked examples, and deep conceptual expositions.
5. **Multi-Stage Revision & Auditing (`revise` & `apply-revise`):**
   Audits full drafts across four modular criteria:
   - *Relevance:* Embedding-based score filtering against course evidence.
   - *Dedup:* Identifies and consolidates redundant formulations across sections.
   - *Correctness:* Audits mathematical derivations against source passages, rechecking calculations via Python code execution.
   - *Organization:* Normalizes heading hierarchy and cross-references.
   Edits are emitted to an interactive review ledger and applied deterministically by `apply-revise`.

---

## 3. Chronological Run History & Quality Milestones

### Phase 1: Econometrics Test Statistics & Initial Comparisons (2026-10-03 to 2026-10-07)
* **Initial Ad-Hoc Script (2026-10-03 / 2026-10-05):** Drafted `wald_lm_lr_tests.md` and `wald_hypothesis_testing_quiz_prep.enhanced.md` via topic-specific procedural scripts. Revealed the need for declarative TOML specs and general CLI tooling.
* **Comparison Matrix Runs (B0, B1, B2, E1 — 2026-10-07):**
  - *B0, B1, B2 (Draft-only):* Found to be excessively conceptual, lacking complete derivations, and disrupted by inline source lists.
  - *E1 (`enhance` improve mode on `gemini-3.8-flash`):* Produced 23,000+ words with full proofs, display equations, and worked examples. The guide owner designated E1 as the **minimum acceptable quality floor** for PhD-level study.
  - *Key Lesson:* Thorough derivations can be condensed by a reader, but an underspecified derivation cannot be reconstructed during exam preparation.

### Phase 2: First Non-Econometrics Run — Microeconomics HW4 (2026-10-09)
* **Scope:** 11 topics covering budget sets, Lagrangian/Kuhn-Tucker primers, preference theory, demand systems, and duality.
* **Metrics:** Full pipeline run cost ~$2.50 ($0.62 draft, $0.38 enhance, $1.51 revise across 499k prompt tokens and 279k thinking tokens).
* **Key Findings:**
  - *Econometrics Prompt Bias:* The `guide_v1` prompt demanded "the statistic, its distribution, and decision rule", causing the model to invent an econometrics hypothesis-testing block inside non-rational choice theory.
  - *Relevance Floor Miscalibration:* The 0.68 similarity floor flagged 29 necessary primer blocks for deletion because foundational math is lightly represented in course-specific notes.
  - *Discrepancy with Problem Sets:* The draft omitted 4 of 5 utility demand derivations and all CES limiting cases asked for in HW4 Q3.
  - *Assignment Check Step:* A post-revise manual cross-check against problem set solutions was required to catch the missing demands, a broken aggregation example, and an uncorrected textbook typo.

### Phase 3: Multi-Unit Synthesis & Adversarial Auditing (2026-10-24)
* **Scope:** Two comprehensive multi-unit guides generated via Gemini in Antigravity:
  1. `micro_foundations_choice_and_revealed_preference_study_guide.md` (Homeworks 1–3: Binary relations, order theory, WARP/SARP, Expected Utility, Allais Paradox, Machina's Triangle, Anscombe-Aumann).
  2. `micro_stochastic_choice_demand_and_duality_study_guide.md` (Homeworks 3–5 / Lectures 4–7: Random Utility Models, Block-Marschak polynomials, ARSP, Bounded Rationality consideration sets, 5 Classic Demand Systems, Market Aggregation failures, Preferences Over Menus / Flexibility, Duality, Slutsky Matrix).
* **Delivery:** Both guides were verified, corrected in-place, and landed on `main` in the permanent `academic_notes` vault repository.

---

## 4. Holistic Synthesis of Critical Deficiencies & Failure Modes

Across the three evaluation phases, several systemic limitations and failure modes have been identified:

### 1. Critical Mathematical Defects in Raw Gemini First Passes
Raw first-pass drafts generated by Gemini exhibit fluid, superficially authoritative mathematical prose that frequently conceals severe conceptual and algebraic errors:
- **Mathematically Invalid Counterexamples:** In the stochastic/duality guide (§3.1), the raw draft attempted to construct a two-consumer aggregation counterexample violating market WARP. However, the invented choice bundles produced cross-expenditures $p^A \cdot Y = 10 > 8 = w$, meaning bundle $Y$ was unaffordable under budget $A$. Consequently, $X$ was never revealed preferred to $Y$, completely invalidating the cycle proof. The example had to be replaced with the exact calibrated numbers from HW4 Q4 ($p^A \cdot Y = p^B \cdot X = 7 < 8$).
- **Algebraic Non-Sequiturs in Limits:** In the CES demand analysis (§2.5.2), the draft evaluated $\lim_{\rho \to -\infty} x_1/x_2 \to 1$ and falsely asserted this proved the Leontief kink condition $\alpha_1 x_1 = \alpha_2 x_2$ for general weights $\alpha_1, \alpha_2$ (a deduction valid only for the symmetric case $\alpha_1 = \alpha_2$).
- **Structural Omissions of Proof Bodies:** The draft omitted the entire mathematical proof body of Module 3 (§3.2, Preferences Over Menus / HW5 Q4), supplying section headers and trapdoors without the four core proofs (reflexivity/transitivity of $\succeq^*$, sandwich property, representation theorem, and state-dependent flexibility counterexamples).
- **Missing Theoretical Qualifiers & Axioms:** Homothetic demand characterizations omitted necessary preference axioms (completeness and strict monotonicity, Lecture 6 p. 21); the exposition of Rubinstein's "Story of the Turtle" (§4.1) omitted the two explicit physical prerequisites from Lecture 7 (Local Non-Satiation and Continuity) that prevent indifference-curve teleportation.
- **Vague Model Formulations:** Bounded rationality (§1.7) substituted a generic two-stage description for the exact stochastic consideration-set model from HW4 Q1 ($p(a, A) = \gamma(a) \prod_{b \succ a} (1 - \gamma(b))$).

> [!IMPORTANT]
> **Takeaway:** Raw generation from LLMs cannot be trusted for graduate-level microeconomics or econometrics without independent line-by-line verification against course lecture slides, homework problem sets, and TA solutions.

### 2. Multi-Unit Granularity Limits & Thematic Clustering Gap
The pipeline's current architecture assumes a flat list of topics, each querying the index independently. When applied to multi-unit review (e.g. Microeconomics HW 1–3 spanning 36 concepts across 4 lectures), this creates three major bottlenecks:
- *Excessive Granularity:* Generating 30+ standalone topic sections produces a fragmented, repetitive guide rather than a cohesive conceptual narrative.
- *Disconnected Proof Flow:* Isolated top-$k$ chunk retrieval misses cross-assignment theoretical arcs (e.g., how Szpilrajn extension and preorder peeling connect incomplete preferences to multi-utility representation).
- *Prohibitive Metered Cost:* Scaling flat topic drafting and revision linearly would cost $10–$15 per guide in metered API calls and produce unwieldy review ledgers.
- *Solution (TODO-0084):* Group atomic concepts from the course concept graph into 3–5 cohesive macro-modules, utilizing subscription agents with large-context window ingestion of complete problem sets.

### 3. Subject-Specific Prompt Biases & Relevance Tuning
- Econometrics-specific wording in base prompts (`guide_v1`) forces irrelevant test-statistic headers into pure theory topics. Needs subject-neutral `guide_v2` prompt IDs (TODO-0008).
- Fixed cosine-similarity relevance thresholds prune necessary primer material when course lecture evidence is sparse (TODO-0002).

### 4. Revision Pipeline Overhead & Unapplied Notes
- In `revise`, thinking tokens bill as output tokens and constituted 91% of total spend in full runs. Capping non-audit stages at `light_thinking = "low"` is required to keep revise economical (TODO-0022).
- The `apply-revise` stage records `note` edits as acknowledged in the changelog but leaves guide text unchanged, allowing subtle flaws to survive into final text unless repaired manually (TODO-0005).
- Markdown citation strippers leave dangling fragments (`(§3.B, p. 52;`, empty backticks, stray semicolons) requiring dedicated post-processing regexes (TODO-0004).

---

## 5. Architectural Decisions & Long-Term Roadmap

1. **Shift Default Drafting to Subscription Agents (TODO-0007 / TODO-0075):**
   - Use subscription-backed agents (Antigravity / Claude Code) with full-context window ingestion of course materials for multi-unit drafting.
   - Maintain the declarative TOML spec, source plan, and validation checks to preserve structural rigor and reproducibility.
2. **Mandatory Assignment-Solution Cross-Checking Step (TODO-0003):**
   - Formalize an automated or agentic verification stage comparing the finished guide against the specific problem set questions and TA solutions.
   - Every mathematical example, limit, and counterexample must be validated for internal numerical consistency and boundary conditions.
3. **Adversarial Peer Review Gate:**
   - Institutionalize independent adversarial auditing (verifying sign conventions, Slutsky negative semidefiniteness, preference qualifiers, and affordability conditions) before study guides are landed to `main`.
4. **Hierarchical Concept-Graph Clustering (TODO-0084):**
   - Integrate with `agent/concept_graph` to automatically cluster related concept nodes into macro-modules before spec generation.

---

## 6. Lifecycle & Documentation References

- **Run Reports:**
  - [`docs/status/agent/study_guide/2026-10-05-quiz-study-guide-generation-status.md`](2026-10-05-quiz-study-guide-generation-status.md) (Econometrics quiz guide)
  - [`docs/status/agent/2026-10-07-study-guide-comparison-status.md`](../2026-10-07-study-guide-comparison-status.md) (B0–E1 comparison matrix)
  - [`docs/status/agent/2026-10-09-microecon-hw4-guide-status.md`](../2026-10-09-microecon-hw4-guide-status.md) (HW4 first non-econometrics run)
  - Vault Audit Deliverables: `academic_notes/microecon/summaries/`
- **Specs & Plans:**
  - [`docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`](../../../superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md)
  - [`docs/superpowers/plans/2026-10-05-study-guide-pipeline.md`](../../../superpowers/plans/2026-10-05-study-guide-pipeline.md)
  - [`docs/superpowers/plans/2026-10-08-guide-revise-pipeline.md`](../../../superpowers/plans/2026-10-08-guide-revise-pipeline.md)
- **Unit & Contract Tests:**
  - `tests/agent/study_guide/test_study_guide_cli.py`
  - `tests/agent/summary_enhance/`
