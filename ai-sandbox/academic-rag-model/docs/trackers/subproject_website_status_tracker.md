# Academic Hub Subproject, Status Doc, and Website Project Page Tracker

**Audit Date:** 2026-10-10

**Evaluator:** Gemini Agent (Antigravity); inventory/contract corrections by Codex, 2026-10-11

**Monorepo Checkout:** `ai-sandbox-master` (branch: `main`, commit: `8b0c7b7`)

**Website Repository:** `ai-sandbox/personal-website/AaronScherf.github.io` (branch: `main`, commit: `ebc836a`)

---

## 1. Executive Summary & Audit Overview

This tracker preserves the original three-tier audit and now plans full lifecycle traceability (section 8): specs -> implementation plans -> code/tests -> status evidence -> website material. The original audited tiers were:
1. **Subprojects in `academic-rag-model`**: Implementation code, tests, and local package documentation.
2. **Status Docs in `academic-rag-model/docs/status/`**: Historical and operational narrative logs recording architectural decisions, bug investigations, and empirical validation runs.
3. **Website Project Pages in `personal-website/AaronScherf.github.io/content/projects/`**: Public-facing portfolio documentation explaining tools, real-world context, empirical testing, and ongoing development.

### Key Audit Metrics
* **Corrected Original Matrix Count:** 22 component rows and one overview row. The website has 16 existing component pages and two overview pages; the research overview was omitted from this matrix. See section 7 for the expanded proposal.
* **Website Repository State:** The website repository has had **no commits since October 5, 2026** (`ebc836a` on 2026-10-05 22:56:18 EDT).
* **Monorepo State:** Between October 5 and October 10, 2026, **over 35 commits landed on `main`**, introducing major new subprojects and substantial pipeline evolutions.
* **Status Doc Currency:** The original audit identified one outdated status record (`agent/summary_enhance`, missing v2 extensions). This is an editorial finding, not a machine-verified count of all current records.
* **Original Website Coverage Gap:** **Six named components lack pages**, matching the matrix and section 3. The original count of eight was unsupported. Concept Graph is an additional proposed target from a later main baseline, not an unnamed original finding.
* **Website Currency Gap:** **3 existing project pages + 1 ecosystem overview page are materially outdated** due to advancements that landed between October 5 and October 10.

---

## 2. Master Alignment Matrix

| Subproject / Component | Code Path | Code Latest Git (main) | Status Docs in `docs/status/` | Website Project Page | Alignment Status & Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`core/indexer`**<br>(Source Indexer) | `core/indexer/` | `b24bbd9`<br>(2026-10-09) | • `indexer/2026-08-29-source-indexer-status.md`<br>• `indexer/2026-08-29-passage-embeddings-status.md`<br>• `indexer/2026-10-03-cross-offering-linkage-status.md` | `academic-hub/source_indexer/index.md` | **Page Outdated**: Page claims passage embeddings are "Still open" (shipped Aug 29); omits Cross-Offering Linkage (Oct 3) and Chunk Repair Adapter (Oct 9). |
| **`pipelines/transcribe_notes`**<br>(Notes Transcription) | `pipelines/transcribe_notes/` | `e272757`<br>(2026-10-10) | • `transcribe_notes/2026-08-24-notes-transcription-status.md` (Updated Oct 10, commit `fc7606e`) | `academic-hub/notes_transcription/index.md` | **Page Outdated**: Last updated Oct 5. Omits Agent-Driven mode (`--agent-mode`, Oct 10), Excalidraw transcription (Sept 9), and Subset Linking (Oct 3). |
| **`pipelines/convert_textbook`**<br>(Marker Conversion) | `pipelines/convert_textbook/` | `56b097a`<br>(2026-10-09) | • `convert_textbook/2026-08-22-chapter-aware-chunking-status.md`<br>• `convert_textbook/2026-08-23-image-description-status.md`<br>• `convert_textbook/2026-09-10-textbook-conversion-status.md` | `academic-hub/marker_conversion/index.md` | **Aligned**: Accurately describes GPU lifecycle, chunking, figure pass, OOM escalation ladder, and deduplication. |
| **`pipelines/postprocess_notes`**<br>(Notes ML Verification) | `pipelines/postprocess_notes/` | `36aae80`<br>(2026-10-09) | • `postprocess_notes/2026-08-27-notes-postprocessing-status.md` | `academic-hub/postprocess_notes/index.md` | **Aligned**: Accurately details GPT-2 surprisal, DistilBERT masked-LM check, and PDF image verification. |
| **`pipelines/generate_video_notes`**<br>(Video Notes Synthesis) | `pipelines/generate_video_notes/` | `a893750`<br>(2026-09-30) | • `generate_video_notes/2026-09-06-video-lecture-notes-status.md` | `academic-hub/video_notes/index.md` | **Aligned**: Accurately covers yt-dlp, faster-whisper, embeddings grouping, and local Ollama synthesis. |
| **`pipelines/convert_essays`**<br>(Research Notes) | `pipelines/convert_essays/` | `a893750`<br>(2026-09-30) | • `convert_essays/2026-09-01-research-notes-conversion-status.md` | `ai-research-assistant/research_notes_conversion/index.md` | **Aligned**: Accurately describes local `.docx` extraction and index card integration. |
| **`pipelines/convert_journal_articles`**<br>(Article Transcription) | `pipelines/convert_journal_articles/` | `a893750`<br>(2026-09-30) | • `convert_journal_articles/2026-09-01-journal-article-transcription-status.md` | `ai-research-assistant/journal_article_transcription/index.md` | **Aligned**: Accurately describes tiered routing reused for journal PDFs. |
| **`discovery/discover_journal_articles`**<br>(Literature Discovery) | `discovery/discover_journal_articles/` | `a893750`<br>(2026-09-30) | • `discover_journal_articles/2026-09-01-journal-discovery-status.md` (Updated Oct 4) | `ai-research-assistant/journal_discovery/index.md` | **Aligned**: Accurately describes OpenAlex discovery, CORE download, metadata reconciliation, and EZProxy fallback. |
| **`agent/rag` (Core Q&A)**<br>(Grounding & REPL) | `agent/rag/` | `5fb2303`<br>(2026-10-08) | • `agent/rag/2026-08-30-rag-agent-status.md`<br>• `agent/rag/2026-10-03-question-resolver-status.md` | `academic-hub/rag_analysis/index.md` | **Page Outdated**: Needs scoped descriptions of persisted diagnosis/summary records and separate problem-generation routing; full conversation restoration is not established. Omits Question Resolver (Oct 3). |
| **`agent/rag` (Tutor Diagnosis)**<br>(Hint & Draft Evaluation) | `agent/rag/tutor_diagnosis.py` | `5621aa6`<br>(2026-09-29) | • `agent/rag/2026-09-27-tutor-diagnosis-status.md` (Updated Oct 8) | `academic-hub/tutor_diagnosis/index.md` | **Aligned for REPL**: Accurately covers 3-axis rubric, hints, and verification. (Note: does not mention evolution into `agent/tutor`). |
| **`agent/tutor`**<br>(Socratic Tutor Gate) | `agent/tutor/` | `0ecfe1f`<br>(2026-10-10) | • `agent/tutor/2026-10-08-socratic-tutor-status.md` (Updated Oct 10, commit `d7782c0`) | *None* | **Missing Page**: Mature subproject completed Oct 8–10; has full CLI, FSM, claims ledger, and profile v2. No website page exists. |
| **`agent/viz`**<br>(Visualization Sub-Agent) | `agent/viz/` | `38239eb`<br>(2026-09-30) | • `agent/viz/2026-09-02-visualization-agent-status.md` | `academic-hub/visualization/index.md` | **Aligned**: Accurately describes Plotly templates and local LLM fallback. |
| **`agent/problem_gen`**<br>(Practice Problem Sub-Agent) | `agent/problem_gen/` | `38239eb`<br>(2026-09-30) | • `agent/problem_gen/2026-09-05-problem-generation-status.md` | `academic-hub/problem_generation/index.md` | **Aligned**: Accurately describes practice problem generation, textbook grounding, and verification. |
| **`agent/problem_corpus`**<br>(Problem Extraction) | `agent/problem_corpus/` | `38239eb`<br>(2026-09-30) | • `agent/problem_corpus/2026-09-06-problem-corpus-extraction-status.md` | `academic-hub/problem_corpus/index.md` | **Aligned**: Accurately describes problem/solution extraction from textbooks and problem sets. |
| **`agent/study_guide`**<br>(Quiz & Study Guide Pipeline) | `agent/study_guide/` | `bbcf843`<br>(2026-10-09) | • `agent/study_guide/study-guide-pipeline-status.md` (Centralized)<br>• `agent/study_guide/2026-10-05-quiz-study-guide-generation-status.md`<br>• `agent/2026-10-05-wald-guide-recovered-generation-status.md`<br>• `agent/2026-10-07-study-guide-comparison-status.md`<br>• `agent/2026-10-09-microecon-hw4-guide-status.md` | *None* | **Missing Page**: Complete 5-stage pipeline with TOML specs, source ledger, drafting, prompt caching, and revise pass. No website page exists. |
| **`agent/summary_enhance`**<br>(Summary Enhancement) | `agent/summary_enhance/` | `83996d1`<br>(2026-10-09) | • `agent/summary_enhance/2026-10-03-summary-enhancement-status.md` | *None* | **Status Outdated & Missing Page**: Status doc only covers v1; misses per-topic source sets, improve mode, worked examples, and prompt caching. No website page. |
| **`resume_manager`**<br>(Resume Tailoring) | `resume_manager/` | `a893750`<br>(2026-09-30) | • `resume_manager/2026-09-09-resume-manager-status.md`<br>• `resume_manager/2026-09-28-resume-manager-tailoring-guidance-status.md` | `resume_manager/index.md` | **Aligned**: Accurately describes YAML parser, Ollama tailoring, fact-checking, and interactive Q&A. |
| **`audio_generator`**<br>(Podcast Synthesis) | `audio_generator/` | `a893750`<br>(2026-09-30) | • `audio_generator/2026-09-09-audio-generator-status.md` | `academic-hub/audio_generator/index.md` | **Aligned**: Accurately covers Piper TTS, LaTeX density routing, and MP3 assembly. |
| **`tools/corpus_health`**<br>(Corpus Health Scanner) | `tools/corpus_health/` | `dbab9ff`<br>(2026-10-09) | • `academic_hub/2026-10-08-corpus-health-capability-inventory.md`<br>• `academic_hub/2026-10-09-corpus-health-apply-first-adapter-decision.md`<br>• `academic_hub/2026-10-09-corpus-health-implementation-retrospective.md` | *None* | **Missing Page**: Whole-corpus scanner, review server, PowerShell automation, and chunk repair adapter. No website page exists. |
| **`tools/project_steering`**<br>(Steering & Ranking) | `tools/project_steering/` | `0eea394`<br>(2026-10-10) | • `academic_hub/2026-10-10-project-steering-status.md` (Landed Oct 10, commit `8b0c7b7`) | *None* | **Missing Page**: Model-free tracker parser, deterministic scoring, review server, agent routing, and archival. No website page exists. |
| **`agent/problem_sets`**<br>(Guided Solutions & Proofs) | vault operational runs | 2026-10-06 runs | • `agent/problem_sets/2026-10-06-guided-solutions-proof-pipeline-status.md` | *None* | **Missing Page**: Formal collaborative proof architecture (`[gemini]` formal derivation + `[human]` economic intuition). No website page exists. |
| **`obsidian_git_sync`**<br>(Vault Sync & Tablet) | `.obsidian/` | `7bbb00c`<br>(2026-10-05) | • `2026-09-21-obsidian-git-sync-status.md`<br>• `2026-09-26-obsidian-git-sync-status.md` | `academic-hub/obsidian_git_sync/index.md` | **Aligned**: Accurately describes Obsidian Fit plugin API sync, gesture control CSS, and subset linking. Links directly to status docs. |
| **`academic-hub-overview`**<br>(Hub Portal Page) | *Portfolio Overview* | Monorepo root | Trackers in `docs/trackers/` | `academic-hub-overview/index.md` | **Page Outdated**: Hardcodes "Twelve subprojects" and omits all 6 new systems landed between Oct 5 and Oct 10. |

---

## 3. Original Missing Website Pages (6 Components)

The following six components have no website page at the audit baseline. Most have code implementations; Guided Solutions is documented operational work without a standalone code folder. Implementation and live-run claims must be revalidated before writing public prose:

1. **`agent/tutor` — Socratic Tutor Session Gate & Learner Profile**
   * *What it does:* CLI session gate that enforces a pedagogically strict finite state machine (FSM) for live tutoring sessions. An IDE agent handles dialogue while the CLI checks claims against prep-authored recognizers, seals/releases solution checkpoints, caps rubric ratings by logged evidence, and persists sessions and a learner profile v2 to the vault.
   * *Status documentation:* `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md`
   * *Target website location:* `content/projects/academic-hub/socratic_tutor/index.md`

2. **`agent/study_guide` — Quiz & Study Guide Generation & Revise Pipeline**
   * *What it does:* End-to-end 5-stage pipeline for turning course materials into comprehensive, verified study guides. Resolves TOML guide specs into source plans, drafts cited content with prompt caching, integrates summary enhancement, and executes multi-stage revision (relevance scoring, duplicate clustering, correctness audit with code execution rechecks, and outline organization).
   * *Status documentation:* `docs/status/agent/study_guide/study-guide-pipeline-status.md`, `docs/status/agent/study_guide/2026-10-05-quiz-study-guide-generation-status.md`, `docs/status/agent/2026-10-09-microecon-hw4-guide-status.md`
   * *Target website location:* `content/projects/academic-hub/study_guide_pipeline/index.md`

3. **`agent/summary_enhance` — Summary Enhancement Engine**
   * *What it does:* Post-processes RAG-generated summaries into standalone pedagogical study guides with per-topic source sets, improve mode, worked-example generator with verified code execution, display math formatting, and prompt-caching optimization.
   * *Status documentation:* `docs/status/agent/summary_enhance/2026-10-03-summary-enhancement-status.md`
   * *Target website location:* `content/projects/academic-hub/summary_enhancement/index.md` (separate page proposed; shared-page aggregation deferred pending a reviewed contract)

4. **`tools/corpus_health` — Academic Hub Corpus Health Scanner & Adapter Repair**
   * *What it does:* Automated scanner that verifies corpus health across hundreds of academic documents, index cards, and vector chunks. Features a local web review server for owner approvals, daily automated scanning via PowerShell, and exact-match chunk repair adapters.
   * *Status documentation:* `docs/status/academic_hub/2026-10-08-corpus-health-capability-inventory.md`, `docs/status/academic_hub/2026-10-09-corpus-health-implementation-retrospective.md`
   * *Target website location:* `content/projects/academic-hub/corpus_health/index.md`

5. **`tools/project_steering` — Project Steering & Ranked To-Do Engine**
   * *What it does:* Model-free engine that parses markdown task trackers, assigns stable task IDs, calculates deterministic multi-factor priority scores, serves an interactive local review page with live editing and agent routing, and manages task completion archival.
   * *Status documentation:* `docs/status/academic_hub/2026-10-10-project-steering-status.md`
   * *Target website location:* `content/projects/academic-hub/project_steering/index.md`

6. **`agent/problem_sets` — Guided Solutions & Formal Proof Pipeline**
   * *What it does:* Collaborative human-AI framework for graduate mathematical problem sets. Enforces rigorous, unabridged mathematical proofs in `[gemini]` blocks while preserving economic intuition and real-world interpretations for `[human]` student blocks, structured by hints rubrics.
   * *Status documentation:* `docs/status/agent/problem_sets/2026-10-06-guided-solutions-proof-pipeline-status.md`
   * *Target website location:* `content/projects/academic-hub/guided_solutions/index.md`

---

## 4. Existing Project Pages Requiring Content Updates

### 1. `academic-hub/source_indexer/index.md`
* **Contradiction:** Under *Ongoing Development* (line 39), the page states: *"Still open: passage-level (not just file-level) embeddings are the recommended next step..."*
* **Correction:** Passage-level chunking and embeddings were implemented on August 29, 2026 (`passage_chunker.py`, `chunk_embeddings.py`) and form the bedrock of the tutoring and study guide pipelines.
* **Missing Features:**
  * Cross-Offering Linkage (`cross_offering.py`, Oct 3): links courses across academic years and semesters.
  * Notes Subset Discovery integration (`subset_discovery.py`, Oct 3–4).
  * Corpus Health chunk repair adapter hook (`chunk_adapter.py`, Oct 9).

### 2. `academic-hub/notes_transcription/index.md`
* **Stale Scope:** Covers only the early PyMuPDF text extraction, font-baseline sub/superscript recovery, and regex defect routing.
* **Missing Features:**
  * **Agent-Driven Transcription Mode** (`--agent-mode`, `agent_transcribe.py`, merged Oct 10): interactive multi-agent dry-runs and prompt contracts for complex scans.
  * **Excalidraw Canvas Transcription** (`excalidraw_notes.py`, Sept 9): transcribes handwritten SVG/canvas notes into clean Markdown.
  * **Notes Subset Discovery** (`subset_discovery.py`, Oct 3): discovers and links related subsets of class notes.

### 3. `academic-hub/rag_analysis/index.md`
* **Stale Limitations:** Under *Ongoing Development* (lines 38–41), the page lists limitations that have since been resolved:
  * *"has no persistent memory across process runs"* -> Describe persisted diagnosis/gap events and summaries separately from full conversation restoration. The RAG REPL initializes conversation history anew; `agent/tutor` profiles belong to a separate component.
  * *"actively works against generating a genuinely new problem set"* -> Describe the separate `agent/problem_gen` route; do not imply that grounded retrieval itself now invents problems.
* **Missing Features:**
  * **Question Resolver** (`question_resolver.py`, Oct 3): disambiguates underspecified questions using syllabus and course schedule context.

### 4. `academic-hub-overview/index.md`
* **Stale Roster:** Hardcodes: *"Twelve subprojects currently make up the hub across conversion, indexing, and tutoring layers..."*
* **Correction:** Reconcile the roster with approved registry membership, including the six original missing-page components and any approved current-main additions. Do not hardcode an 18-system count before the scope decision.

---

## 5. Status Docs Requiring Updates

* **`agent/summary_enhance`**:
  * Existing status doc `docs/status/agent/summary_enhance/2026-10-03-summary-enhancement-status.md` covers only v1 from October 3.
  * Commits between October 6 and October 9 added:
    1. Per-topic source sets (`source_map` doc_type / offering).
    2. "Improve mode" (`--mode improve`) for existing guides.
    3. Worked-example generation with code execution (`--worked-example`, `--example-focus`).
    4. Prompt-caching token optimizations.
  * *Required Action:* Author `docs/status/agent/summary_enhance/2026-10-09-summary-enhancement-v2-status.md` or amend the October 3 record.

---

## 6. Linking & Automation Architecture

### Current Linking Analysis
An audit of frontmatter and content across all website project pages revealed:
1. **No Explicit Status Doc Links (except one):** Only `academic-hub/obsidian_git_sync/index.md` explicitly links to status docs in its frontmatter `links:` block. The relevant baseline contains 15 other component pages; verify their individual links during M2 rather than reusing the erroneous 13-page total.
2. **Inconsistent GitHub URL Granularity:**
   * 10 pages link directly to their specific subproject directory (e.g. `.../ai-sandbox/academic-rag-model/audio_generator`).
   * 5 pages link only to the top-level repository root (`.../ai-sandbox/academic-rag-model`), losing subproject traceability (`marker_conversion`, `notes_transcription`, `journal_article_transcription`, `journal_discovery`, `research_notes_conversion`).
3. **No Back-Links from Code/Docs:** Subproject READMEs and status docs do not link to their corresponding website pages.

### Canonical Linking and Verification Contract

The [amended design](../brainstorms/specs/2026-10-10-subproject-website-sync-design.md) is the sole schema/CLI proposal; the [implementation plan](../brainstorms/specs/2026-10-10-subproject-website-sync-plan.md) defines task gates. Do not implement a separate schema from this tracker.

The proposal uses immutable IDs, repo-root-relative paths, explicit current/historical status lists, operational/configuration/overview kinds, and a matching `params.subproject` projection. The proposed checker is `python -B -m tools.audit_website_sync`, invoked from the package root with an explicit website checkout. The old `audit_website_currency` name and conflicting top-level frontmatter example are superseded. The website is HugoBlox Academic CV.

Git timestamps produce **history warnings**, not semantic alignment verdicts. The [review](../brainstorms/2026-10-10-subproject-website-sync-codex-review.md) demonstrates timestamp flags for textbook/postprocess pages this editorial audit calls aligned. Conversely, committing metadata can advance page timestamps without repairing prose. Keep this content backlog independent: no checker or M2 metadata commit automatically resolves these findings. Each item needs source-backed editorial review before completion.

Correct the five generic component links listed above. Journal discovery's target is `ai-sandbox/academic-rag-model/discovery/discover_journal_articles`, not a pipelines directory. Preserve legitimate overview root links and Obsidian's status-file links. Metadata does not substitute for visible source/status links. Scheduling, steering ingestion and automated repairs are deferred; existing steering has no established website-report ingestion API.

## 7. Review Reconciliation and Expanded Scope Proposal

The original matrix above preserves its dated editorial scope. Corrections do not certify all prose or refresh every historical commit reference. Proposed additions/dispositions at the review baseline (`44046eb`, carried into `519a2f6`) are:

| Item | Evidence / correction | Proposed disposition |
| --- | --- | --- |
| Tutor diagnosis | Existing matrix row and website page; omitted by original plan | Separate stable identity from RAG Q&A |
| Obsidian sync | Existing matrix row/page; configuration outside Python package root | Configuration identity, source under `ai-sandbox/.obsidian/` |
| Research overview | Existing `ai-research-assistant-overview/index.md`, omitted from matrix | Explicit overview identity and membership |
| core/env | Original plan added it; initializer exists but no README | Owner-approved internal infrastructure with reason; no required page |
| agent/concept_graph | Code/status docs on later main; absent at 777f507 | Owner-approved additional required page; no implied live-run success |
| Guided Solutions | Operational status record, no `agent/problem_sets/` code folder | Operational identity with explained absent code/README |

The owner approved the **24-component plus two-overview** baseline on 2026-10-11. It includes 16 existing component pages, six original missing pages, one additional required concept-graph page, one internal component, and two existing overviews. M2 covers 16 existing components plus two overviews. Refresh the live inventory at M1 Task 1 rather than treating these review-baseline counts as immutable.

The owner approved D1 (scope/publication), D2 (schema/frontmatter and lifecycle backfill), D3 (runtime/dependencies and strict finding policy), and visible source/status links on 2026-10-11. The six original content tasks, newly scoped Concept Graph page, three page revisions, overview revision and summary-enhancement status update remain open. No code, website edits, checker run, build or publication is claimed by these documentation amendments.

## 8. Lifecycle Traceability Extension (2026-10-11)

Owner-requested and approved scope addition: track design specs and implementation plans as stable architectural baselines, associate tests, and make status records point back to the applicable specs/plans/tests. Canonical fields and backlink syntax live in the [design's lifecycle contract](../brainstorms/specs/2026-10-10-subproject-website-sync-design.md#lifecycle-traceability); implementation and backfill gates are in [T1/T3/T4/T6a of the plan](../brainstorms/specs/2026-10-10-subproject-website-sync-plan.md). No registry, scanner or backlink migration has run.

| Lifecycle surface | Required tracking | Change / evidence policy |
| --- | --- | --- |
| Specs | Explicit revision ID, separate spec paths, current/proposed/superseded relationships | Revise for architecture changes; no timestamp staleness inferred from routine code edits |
| Implementation plans | Separate plan paths tied to the applicable specs and tests | Track tasks/evidence without rewriting historical architecture; folder name does not define document type |
| Status docs | Lifecycle IDs plus human-readable local links to specs, plans and test paths | Preserve historical associations; current status referring only to superseded designs requires review |
| Tests | Explicit test files/directories associated with lifecycle records | Existence is not a passing run; record command, tested revision, date/outcome separately |
| Website | Existing source/status links and projected status lifecycle IDs | Trace through status to design/tests; do not copy private evidence into public pages |

Lifecycle coverage is separate from website coverage and history-gap warnings. The original matrix did not audit spec/plan/test associations, so none is marked complete by this extension. M1 inventories known relationships and reports unknown/missing/backlink gaps; T6a backfills scoped legacy status/plan links in reviewed monorepo batches. Missing legacy normalized sections, unknown lifecycle associations and heuristic history gaps are warnings, not strict blockers. An existing normalized section with invalid/differing references, missing configured targets, metadata conflicts and required missing pages block strict checks. Thus M1/M2 acceptance uses enumerated backlog and milestone checks rather than a globally clean strict run; defer a global strict hook/CI gate until those blockers are resolved. Operational components may explain genuine absence; unresearched mappings must remain unknown. No age-based SPEC_OUTDATED/PLAN_OUTDATED classification is added.

Sample evidence already in this repository: project-steering's status links its implementation plan; concept-graph's status names both plan and spec and separately qualifies fixture results versus untested live execution. These are useful precedents, not proof of complete machine-readable backlinks. The sync pipeline's own future implementation status must follow the same lifecycle contract when its code/tests exist.
