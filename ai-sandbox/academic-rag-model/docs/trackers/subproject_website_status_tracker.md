# Academic Hub Subproject, Status Doc, and Website Project Page Tracker

**Audit Date:** 2026-10-10  
**Evaluator:** Gemini Agent (Antigravity)  
**Monorepo Checkout:** `ai-sandbox-master` (branch: `main`, commit: `8b0c7b7`)  
**Website Repository:** `ai-sandbox/personal-website/AaronScherf.github.io` (branch: `main`, commit: `ebc836a`)

---

## 1. Executive Summary & Audit Overview

This tracker monitors alignment across the three functional tiers of the portfolio and knowledge repository:
1. **Subprojects in `academic-rag-model`**: Implementation code, tests, and local package documentation.
2. **Status Docs in `academic-rag-model/docs/status/`**: Historical and operational narrative logs recording architectural decisions, bug investigations, and empirical validation runs.
3. **Website Project Pages in `personal-website/AaronScherf.github.io/content/projects/`**: Public-facing portfolio documentation explaining tools, real-world context, empirical testing, and ongoing development.

### Key Audit Metrics
* **Total Subprojects & Components Audited:** 21 substantive components (+ 2 ecosystem overview portals).
* **Website Repository State:** The website repository has had **no commits since October 5, 2026** (`ebc836a` on 2026-10-05 22:56:18 EDT).
* **Monorepo State:** Between October 5 and October 10, 2026, **over 35 commits landed on `main`**, introducing major new subprojects and substantial pipeline evolutions.
* **Status Doc Currency:** 20 components have current status docs; **1 component has an outdated status doc** (`agent/summary_enhance` stops at v1 and misses v2 extensions).
* **Website Coverage Gap:** **8 substantive subprojects are completely missing website project pages**.
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
| **`agent/rag` (Core Q&A)**<br>(Grounding & REPL) | `agent/rag/` | `5fb2303`<br>(2026-10-08) | • `agent/rag/2026-08-30-rag-agent-status.md`<br>• `agent/rag/2026-10-03-question-resolver-status.md` | `academic-hub/rag_analysis/index.md` | **Page Outdated**: Lists lack of memory and lack of problem generation as limitations (both solved); omits Question Resolver (Oct 3). |
| **`agent/rag` (Tutor Diagnosis)**<br>(Hint & Draft Evaluation) | `agent/rag/tutor_diagnosis.py` | `5621aa6`<br>(2026-09-29) | • `agent/rag/2026-09-27-tutor-diagnosis-status.md` (Updated Oct 8) | `academic-hub/tutor_diagnosis/index.md` | **Aligned for REPL**: Accurately covers 3-axis rubric, hints, and verification. (Note: does not mention evolution into `agent/tutor`). |
| **`agent/tutor`**<br>(Socratic Tutor Gate) | `agent/tutor/` | `0ecfe1f`<br>(2026-10-10) | • `agent/tutor/2026-10-08-socratic-tutor-status.md` (Updated Oct 10, commit `d7782c0`) | *None* | **Missing Page**: Mature subproject completed Oct 8–10; has full CLI, FSM, claims ledger, and profile v2. No website page exists. |
| **`agent/viz`**<br>(Visualization Sub-Agent) | `agent/viz/` | `38239eb`<br>(2026-09-30) | • `agent/viz/2026-09-02-visualization-agent-status.md` | `academic-hub/visualization/index.md` | **Aligned**: Accurately describes Plotly templates and local LLM fallback. |
| **`agent/problem_gen`**<br>(Practice Problem Sub-Agent) | `agent/problem_gen/` | `38239eb`<br>(2026-09-30) | • `agent/problem_gen/2026-09-05-problem-generation-status.md` | `academic-hub/problem_generation/index.md` | **Aligned**: Accurately describes practice problem generation, textbook grounding, and verification. |
| **`agent/problem_corpus`**<br>(Problem Extraction) | `agent/problem_corpus/` | `38239eb`<br>(2026-09-30) | • `agent/problem_corpus/2026-09-06-problem-corpus-extraction-status.md` | `academic-hub/problem_corpus/index.md` | **Aligned**: Accurately describes problem/solution extraction from textbooks and problem sets. |
| **`agent/study_guide`**<br>(Quiz & Study Guide Pipeline) | `agent/study_guide/` | `bbcf843`<br>(2026-10-09) | • `agent/study_guide/2026-10-05-quiz-study-guide-generation-status.md`<br>• `agent/2026-10-05-wald-guide-recovered-generation-status.md`<br>• `agent/2026-10-07-study-guide-comparison-status.md`<br>• `agent/2026-10-09-microecon-hw4-guide-status.md` | *None* | **Missing Page**: Complete 5-stage pipeline with TOML specs, source ledger, drafting, prompt caching, and revise pass. No website page exists. |
| **`agent/summary_enhance`**<br>(Summary Enhancement) | `agent/summary_enhance/` | `83996d1`<br>(2026-10-09) | • `agent/summary_enhance/2026-10-03-summary-enhancement-status.md` | *None* | **Status Outdated & Missing Page**: Status doc only covers v1; misses per-topic source sets, improve mode, worked examples, and prompt caching. No website page. |
| **`resume_manager`**<br>(Resume Tailoring) | `resume_manager/` | `a893750`<br>(2026-09-30) | • `resume_manager/2026-09-09-resume-manager-status.md`<br>• `resume_manager/2026-09-28-resume-manager-tailoring-guidance-status.md` | `resume_manager/index.md` | **Aligned**: Accurately describes YAML parser, Ollama tailoring, fact-checking, and interactive Q&A. |
| **`audio_generator`**<br>(Podcast Synthesis) | `audio_generator/` | `a893750`<br>(2026-09-30) | • `audio_generator/2026-09-09-audio-generator-status.md` | `academic-hub/audio_generator/index.md` | **Aligned**: Accurately covers Piper TTS, LaTeX density routing, and MP3 assembly. |
| **`tools/corpus_health`**<br>(Corpus Health Scanner) | `tools/corpus_health/` | `dbab9ff`<br>(2026-10-09) | • `academic_hub/2026-10-08-corpus-health-capability-inventory.md`<br>• `academic_hub/2026-10-09-corpus-health-apply-first-adapter-decision.md`<br>• `academic_hub/2026-10-09-corpus-health-implementation-retrospective.md` | *None* | **Missing Page**: Whole-corpus scanner, review server, PowerShell automation, and chunk repair adapter. No website page exists. |
| **`tools/project_steering`**<br>(Steering & Ranking) | `tools/project_steering/` | `0eea394`<br>(2026-10-10) | • `academic_hub/2026-10-10-project-steering-status.md` (Landed Oct 10, commit `8b0c7b7`) | *None* | **Missing Page**: Model-free tracker parser, deterministic scoring, review server, agent routing, and archival. No website page exists. |
| **`agent/problem_sets`**<br>(Guided Solutions & Proofs) | vault operational runs | 2026-10-06 runs | • `agent/problem_sets/2026-10-06-guided-solutions-proof-pipeline-status.md` | *None* | **Missing Page**: Formal collaborative proof architecture (`[gemini]` formal derivation + `[human]` economic intuition). No website page exists. |
| **`obsidian_git_sync`**<br>(Vault Sync & Tablet) | `.obsidian/` | `7bbb00c`<br>(2026-10-05) | • `2026-09-21-obsidian-git-sync-status.md`<br>• `2026-09-26-obsidian-git-sync-status.md` | `academic-hub/obsidian_git_sync/index.md` | **Aligned**: Accurately describes Obsidian Fit plugin API sync, gesture control CSS, and subset linking. Links directly to status docs. |
| **`academic-hub-overview`**<br>(Hub Portal Page) | *Portfolio Overview* | Monorepo root | Trackers in `docs/trackers/` | `academic-hub-overview/index.md` | **Page Outdated**: Hardcodes "Twelve subprojects" and omits all 6 new systems landed between Oct 5 and Oct 10. |

---

## 3. Subprojects Missing Website Pages (8 Components)

The following substantive systems have completed code implementations and narrative status documentation, but have no presence on the personal website:

1. **`agent/tutor` — Socratic Tutor Session Gate & Learner Profile**
   * *What it does:* CLI session gate that enforces a pedagogically strict finite state machine (FSM) for live tutoring sessions. An IDE agent handles dialogue while the CLI checks claims against prep-authored recognizers, seals/releases solution checkpoints, caps rubric ratings by logged evidence, and persists sessions and a learner profile v2 to the vault.
   * *Status documentation:* `docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md`
   * *Target website location:* `content/projects/academic-hub/socratic_tutor/index.md`

2. **`agent/study_guide` — Quiz & Study Guide Generation & Revise Pipeline**
   * *What it does:* End-to-end 5-stage pipeline for turning course materials into comprehensive, verified study guides. Resolves TOML guide specs into source plans, drafts cited content with prompt caching, integrates summary enhancement, and executes multi-stage revision (relevance scoring, duplicate clustering, correctness audit with code execution rechecks, and outline organization).
   * *Status documentation:* `docs/status/agent/study_guide/2026-10-05-quiz-study-guide-generation-status.md`, `docs/status/agent/2026-10-09-microecon-hw4-guide-status.md`
   * *Target website location:* `content/projects/academic-hub/study_guide_pipeline/index.md`

3. **`agent/summary_enhance` — Summary Enhancement Engine**
   * *What it does:* Post-processes RAG-generated summaries into standalone pedagogical study guides with per-topic source sets, improve mode, worked-example generator with verified code execution, display math formatting, and prompt-caching optimization.
   * *Status documentation:* `docs/status/agent/summary_enhance/2026-10-03-summary-enhancement-status.md`
   * *Target website location:* `content/projects/academic-hub/summary_enhancement/index.md` (or integrated into Study Guide Pipeline)

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
  * *"has no persistent memory across process runs"* -> Resolved by `tutor_diagnosis` session event logs and `agent/tutor` learner profiles.
  * *"actively works against generating a genuinely new problem set"* -> Resolved by the dedicated `agent/problem_gen` subproject.
* **Missing Features:**
  * **Question Resolver** (`question_resolver.py`, Oct 3): disambiguates underspecified questions using syllabus and course schedule context.

### 4. `academic-hub-overview/index.md`
* **Stale Roster:** Hardcodes: *"Twelve subprojects currently make up the hub across conversion, indexing, and tutoring layers..."*
* **Correction:** Expand roster to include the 6 newer systems (Socratic Tutor, Study Guide Pipeline, Summary Enhancement, Guided Solutions, Corpus Health, and Project Steering).

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
1. **No Explicit Status Doc Links (except one):** Only `academic-hub/obsidian_git_sync/index.md` explicitly links to status docs in its frontmatter `links:` block. None of the other 12 project pages link to status docs or README files.
2. **Inconsistent GitHub URL Granularity:**
   * 10 pages link directly to their specific subproject directory (e.g. `.../ai-sandbox/academic-rag-model/audio_generator`).
   * 5 pages link only to the top-level repository root (`.../ai-sandbox/academic-rag-model`), losing subproject traceability (`marker_conversion`, `notes_transcription`, `journal_article_transcription`, `journal_discovery`, `research_notes_conversion`).
3. **No Back-Links from Code/Docs:** Subproject READMEs and status docs do not link to their corresponding website pages.

### Proposed Frontmatter Schema for Automated Drift Detection
To enable automated verification scripts to detect when code or status docs advance past website pages, website project pages should adopt standard YAML frontmatter metadata:

```yaml
---
title: Notes Transcription Pipeline
date: 2026-08-27
type: academic-hub-project
subproject:
  package: pipelines/transcribe_notes
  readme: ai-sandbox/academic-rag-model/pipelines/transcribe_notes/README.md
  status_docs:
    - ai-sandbox/academic-rag-model/docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md
  primary_source_files:
    - ai-sandbox/academic-rag-model/pipelines/transcribe_notes/transcribe_notes.py
    - ai-sandbox/academic-rag-model/pipelines/transcribe_notes/agent_transcribe.py
links:
  - type: site
    icon: brands/github
    label: GitHub
    url: https://github.com/AaronScherf/ai-sandbox-master/tree/main/ai-sandbox/academic-rag-model/pipelines/transcribe_notes
---
```

### Proposed Automated Verification Workflow
With structured metadata or a shared registry (`docs/trackers/subproject_registry.json`), an automated CLI tool (e.g. `python -m tools.audit_website_currency`) can:
1. Compare `git log -n 1 --format=%cd` of `subproject.package` against the project page's `git log`.
2. Inspect whether any commits touched the subproject code after the website page's last commit date.
3. Check for any package directory under `academic-rag-model/` lacking a registered website page.
4. Output a machine-readable report or feed directly into `tools.project_steering` as reviewable to-do items.
