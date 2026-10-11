# Subproject Website Alignment & Automated Verification: Implementation Plan

**Status:** Draft for review  
**Date:** 2026-10-10  
**Spec:** [2026-10-10 subproject-website-sync design](2026-10-10-subproject-website-sync-design.md)  
**Scope:** Establish a canonical central registry manifest, standardize website project page frontmatter, and implement a model-free automated CLI checker for continuous drift detection.  

---

## 1. Goal and Release Boundaries

The goal is to eliminate documentation drift between the active Python codebase in `ai-sandbox/academic-rag-model/`, its operational status documents in `docs/status/`, and the public project descriptions in `ai-sandbox/personal-website/AaronScherf.github.io/content/projects/`.

We deliver this across three sequential, independently verifiable milestones:

1. **M1 — Central Registry & Read-Only Automated Scanner (Monorepo only):**
   * Author the canonical manifest `subproject_registry.json` covering all 21 substantive subprojects/tools and 2 overview pages.
   * Author JSON Schema validation (`subproject_registry.schema.json`).
   * Implement `tools/audit_website_sync.py` with zero-cost Git timestamp comparison and drift classification.
   * Add automated test suite with synthetic Git history fixtures.
   * *Outcome:* An immediate, verifiable CLI tool reproducing the 2026-10-10 audit findings with 0 edits to website content.

2. **M2 — Website Frontmatter Alignment (Website repository worktree):**
   * Update the existing 13 website project pages in a dedicated `AaronScherf.github.io` worktree to include structured `subproject:` YAML frontmatter.
   * Upgrade the 5 pages linking to generic repo root URLs to point directly to their subproject package paths on GitHub.
   * Run the M1 checker to verify bidirectional consistency and zero metadata mismatches.

3. **M3 — Content & Documentation Reconciliation (Backlog execution):**
   * Author new project pages for the 8 missing subprojects identified in the audit (prioritizing `agent/tutor`, `agent/study_guide`, `tools/corpus_health`, and `tools/project_steering`).
   * Update the 3 existing outdated project pages (`source_indexer`, `notes_transcription`, `rag_analysis`) and the `academic-hub-overview` portal.
   * Author the v2 status doc update for `agent/summary_enhance`.

---

## 2. Verified Inputs and Repository Boundaries

* **Monorepo Checkout (`ai-sandbox-master`):**
  * Root path: `c:\Users\theaa\ai-sandbox-master`
  * Python pipeline packages: `ai-sandbox/academic-rag-model/` (`core/`, `pipelines/`, `discovery/`, `agent/`, `resume_manager/`, `audio_generator/`, `tools/`)
  * Tracker directory: `ai-sandbox/academic-rag-model/docs/trackers/`
* **Personal Website Repository (`AaronScherf.github.io`):**
  * Root path: `c:\Users\theaa\ai-sandbox-master\ai-sandbox\personal-website\AaronScherf.github.io`
  * Separate Git repository with its own branch history and commit log.
  * Project markdown files: `content/projects/<category>/<slug>/index.md`
* **Git Worktree Rules:**
  * Changes to the monorepo must be isolated in dedicated `gemini/<task>` worktrees.
  * Edits to the website repository must be executed in a dedicated worktree belonging to `AaronScherf.github.io`.
  * Writers must never cross repository boundaries within a single commit.

---

## 3. Capability & Operation Table

| Operation | Discovery & Scope | Cost & Side Effects | Output & Idempotency | Acceptance Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Validate Registry** | One file: `docs/trackers/subproject_registry.json` | Local CPU, no API calls | Schema validation pass/fail | Unit test validating every subproject path against disk |
| **Discover Monorepo Packages** | Scans `academic-rag-model/` for directories with `__init__.py` and `README.md` | Read-only directory traversal | List of active subprojects | Zero active packages omitted from the registry |
| **Query Git Timestamps** | `git -C <repo> log -1 --format=%ct` across code, status doc, and website page | Zero API calls; sub-second process execution | Epoch timestamps for drift comparison | Matches manual `git log` inspection on main |
| **Audit Website Frontmatter** | Scans all `index.md` files in `content/projects/` | Read-only YAML parsing | Structured metadata matching registry | 100% agreement on package identifiers |
| **Generate Drift Report** | Full drift comparison across all 21 subprojects | Read-only; stdout or JSON/Markdown file | Deterministic report reproducing audit matrix | Zero false positives/negatives against manual baseline |

---

## 4. Global Contracts and Traceability

| Requirement | Implementation Component | Verification Evidence |
| :--- | :--- | :--- |
| **Dual-Layer Linking** | `subproject_registry.json` + website frontmatter `subproject:` block | Verification tool validates mutual agreement between registry and page frontmatter |
| **Model-Free, Zero API Cost** | `tools/audit_website_sync.py` uses only Python standard library and `git log` | Zero network calls, zero token usage, sub-500ms execution |
| **Multi-Repo Safety** | Git queries use explicit `-C <repo_path>` | Operates cleanly whether invoked from monorepo root or package directory |
| **Non-Destructive Execution** | Checker default mode is read-only | Running `python -m tools.audit_website_sync` leaves Git status completely clean |
| **Drift Classification** | Explicit enums: `ALIGNED`, `MISSING_WEBSITE_PAGE`, `WEBSITE_PAGE_OUTDATED`, `STATUS_DOC_OUTDATED`, `METADATA_MISMATCH` | Synthetic test cases covering every drift state |

---

## 5. Detailed Task Breakdown

### Task 1 — Create Central Registry Manifest & JSON Schema (M1)

* **Files to create:**
  * `ai-sandbox/academic-rag-model/docs/trackers/subproject_registry.json`
  * `ai-sandbox/academic-rag-model/docs/trackers/subproject_registry.schema.json`
* **Implementation Details:**
  * Define all 21 substantive subprojects and tools identified in the 2026-10-10 audit:
    * `core/indexer`, `core/env`
    * `pipelines/convert_textbook`, `pipelines/transcribe_notes`, `pipelines/convert_essays`, `pipelines/convert_journal_articles`, `pipelines/postprocess_notes`, `pipelines/generate_video_notes`
    * `discovery/discover_journal_articles`
    * `agent/rag`, `agent/tutor`, `agent/viz`, `agent/problem_gen`, `agent/problem_corpus`, `agent/study_guide`, `agent/summary_enhance`, `agent/problem_sets`
    * `resume_manager`, `audio_generator`
    * `tools/corpus_health`, `tools/project_steering`
  * Each entry records: `id`, `name`, `category` (`academic-hub` / `ai-research-assistant` / `standalone`), `role` (`pipeline` / `agent` / `tool` / `core`), `code_path`, `readme_path`, `status_docs` (list of relative paths), and `website_page` (relative path in website repo, or `null`).
* **Acceptance:** Schema validation passes cleanly; every non-null path in the registry points to an existing file on disk.

---

### Task 2 — Implement Automated Verification Tool & Unit Tests (M1)

* **Files to create:**
  * `ai-sandbox/academic-rag-model/tools/audit_website_sync.py`
  * `ai-sandbox/academic-rag-model/tests/tools/test_audit_website_sync.py`
* **Implementation Details:**
  * Standard CLI:
    ```powershell
    python -m tools.audit_website_sync [--registry PATH] [--website-root PATH] [--format text|json|markdown] [--strict]
    ```
  * Execution Flow:
    1. Resolve monorepo root and website root paths automatically or from CLI arguments.
    2. Ingest and schema-validate `subproject_registry.json`.
    3. Discover package directories under `academic-rag-model/` and alert if any new package lacks a registry entry.
    4. For each registered subproject:
       - Query latest commit timestamp for `code_path` in monorepo (`t_code`).
       - Query latest commit timestamp for `status_docs` in monorepo (`t_status`).
       - If `website_page` is null, flag as `MISSING_WEBSITE_PAGE`.
       - If `website_page` exists, query its latest commit timestamp in website repo (`t_page`).
       - If `t_code > t_page + 3600`, flag as `WEBSITE_PAGE_OUTDATED`.
       - If `t_code > t_status + 3600`, flag as `STATUS_DOC_OUTDATED`.
       - Parse website page YAML frontmatter and verify `subproject.package == entry.code_path`. If divergent, flag as `METADATA_MISMATCH`.
    5. Render formatted console summary table, JSON payload, or Markdown output.
    6. Exit code 0 if fully aligned; exit code 1 if missing or outdated pages are detected under `--strict`.
  * Unit tests:
    * Mock Git runner testing all drift classifications.
    * Schema validation unit tests.
* **Acceptance:** Tests pass with `pytest tests/tools/test_audit_website_sync.py -q`. Running against live repositories reproduces the exact findings from the 2026-10-10 audit report.

---

### Task 3 — Standardize Website Frontmatter & Fix Granular Links (M2)

* **Target Repository:** `ai-sandbox/personal-website/AaronScherf.github.io`
* **Branch/Worktree:** Dedicated worktree `AaronScherf.github.io/.worktrees/gemini-frontmatter-sync` on branch `gemini/frontmatter-sync`.
* **Implementation Details:**
  * For each of the 13 existing project pages:
    * Inject the structured `subproject:` YAML block:
      ```yaml
      subproject:
        id: <slug>
        package: <relative_monorepo_package>
        readme: <relative_monorepo_readme>
        status_docs:
          - <relative_monorepo_status_doc>
      ```
    * Fix the 5 project pages that link to the generic repo root so their `links:` block points directly to the subproject package directory on GitHub:
      * `marker_conversion` -> `.../tree/main/ai-sandbox/academic-rag-model/pipelines/convert_textbook`
      * `notes_transcription` -> `.../tree/main/ai-sandbox/academic-rag-model/pipelines/transcribe_notes`
      * `journal_article_transcription` -> `.../tree/main/ai-sandbox/academic-rag-model/pipelines/convert_journal_articles`
      * `journal_discovery` -> `.../tree/main/ai-sandbox/academic-rag-model/pipelines/discover_journal_articles`
      * `research_notes_conversion` -> `.../tree/main/ai-sandbox/academic-rag-model/pipelines/convert_essays`
* **Acceptance:** Hugo build succeeds (`hugo --minify`); `python -m tools.audit_website_sync` reports `METADATA_MISMATCH: 0`.

---

### Task 4 — Content Reconciliation Backlog (M3)

* **Scope:** Author missing project pages, refresh outdated project pages, and update status records.
* **Work Packages:**
  * **Package 4.1: High-Priority Missing Pages:**
    * `content/projects/academic-hub/socratic_tutor/index.md` (`agent/tutor`)
    * `content/projects/academic-hub/study_guide_pipeline/index.md` (`agent/study_guide`)
    * `content/projects/academic-hub/corpus_health/index.md` (`tools/corpus_health`)
    * `content/projects/academic-hub/project_steering/index.md` (`tools/project_steering`)
  * **Package 4.2: Remaining Missing Pages:**
    * `content/projects/academic-hub/summary_enhancement/index.md` (`agent/summary_enhance`)
    * `content/projects/academic-hub/guided_solutions/index.md` (`agent/problem_sets`)
  * **Package 4.3: Outdated Existing Pages:**
    * Update `source_indexer/index.md` (passage embeddings completed, cross-offering linkage, chunk repair adapter).
    * Update `notes_transcription/index.md` (agent-driven transcription mode, Excalidraw, subset discovery).
    * Update `rag_analysis/index.md` (session memory solved, question resolver, problem generator separation).
    * Update `academic-hub-overview/index.md` (expand roster from 12 to 18 systems).
  * **Package 4.4: Outdated Status Docs:**
    * Author `docs/status/agent/summary_enhance/2026-10-09-summary-enhancement-v2-status.md` covering per-topic source sets, improve mode, worked examples, and prompt caching.

---

## 6. Review Gates & Landing Procedures

1. **Gate 1 (M1 Review):** User reviews `subproject_registry.json` and `tools/audit_website_sync.py` results on `gemini/website-status-tracker` before any website repository files are touched.
2. **Gate 2 (M2 Landing):** User reviews website frontmatter diffs in the dedicated website worktree before merging to `main`.
3. **Gate 3 (M3 Content Batches):** Each new project page or major revision is drafted and reviewed independently in accordance with the project's editorial guidelines.
