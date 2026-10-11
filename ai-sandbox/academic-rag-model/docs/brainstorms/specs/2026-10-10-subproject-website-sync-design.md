# Subproject Website Alignment & Automated Verification: Design Spec

**Status:** Draft for design review  
**Date:** 2026-10-10  
**Authors:** Aaron Scherf & Gemini Agent  
**Source Request:** Implement both a central registry of subproject connections and website frontmatter cross-links, plus a lightweight automated checker to identify missing or outdated docs/pages, followed by an implementation plan.

---

## 1. Requirements and Constraints

1. **Dual-Layer Connection Architecture:**
   * **Central Registry:** Maintain a single canonical, machine-readable registry file in the monorepo (`docs/trackers/subproject_registry.json`) mapping every package in `academic-rag-model` to its code directory, README, status documents, and website project page.
   * **In-Page Frontmatter Links:** Standardize YAML frontmatter on website project pages (`content/projects/.../index.md`) with explicit `subproject:` metadata and verified GitHub repository/status doc links.
   * **Bidirectional Integrity:** The automated checker must verify that the central registry and the website page frontmatter agree, flagging any discrepancy.

2. **Model-Free, Zero-Cost Verification:**
   * The checker must execute locally without API calls, LLM tokens, cloud network access, or paid quotas.
   * Drift checks must rely solely on local file existence and Git commit timestamps (`git log -1 --format=%ct`).
   * Execution time must be sub-second (target < 500 ms) so it can run on demand, in pre-commit hooks, or within CI workflows.

3. **Multi-Repository Boundaries:**
   * **Monorepo Checkout:** `ai-sandbox-master` containing Python packages, tests, tools, status docs, and trackers.
   * **Personal Website Repository:** `ai-sandbox/personal-website/AaronScherf.github.io` is a distinct, independently versioned Git checkout.
   * The tool must query Git history across both repository roots using `git -C <repo_root>` without assuming shared Git objects, index states, or branch names.

4. **Idempotency and Non-Destructive Behavior:**
   * The verification checker must be strictly read-only by default (`--check` / `--report`), producing structured findings without altering files.
   * Any future metadata synchronization (`--sync-frontmatter`) must be explicitly targeted, previewed, and committed via dedicated Git worktrees.

5. **Precise Drift Classification:**
   * `ALIGNED`: Code, status docs, and website project page are all present and synchronized within acceptable commit windows.
   * `MISSING_WEBSITE_PAGE`: A substantive subproject exists in the codebase but has no corresponding website project page.
   * `WEBSITE_PAGE_OUTDATED`: Subproject code on `main` has commits newer than the website page's latest Git commit.
   * `STATUS_DOC_OUTDATED`: Subproject code has commits newer than the latest corresponding status doc in `docs/status/<package>/`.
   * `ORPHANED_PAGE`: A website page references a subproject package or doc path that no longer exists in the monorepo.
   * `METADATA_MISMATCH`: Discrepancy between central registry metadata and website page frontmatter.

---

## 2. Verified Repository Facts & Adjacent Work

* **Monorepo Layout:**
  * Packages are grouped by role: `core/`, `pipelines/`, `discovery/`, `agent/`, `resume_manager/`, `audio_generator/`, and `tools/`.
  * Status documents live under `ai-sandbox/academic-rag-model/docs/status/<package>/`.
  * Trackers live in `ai-sandbox/academic-rag-model/docs/trackers/` (`academic_hub_to_do.md`, `academic_hub_completed.md`, `subproject_website_status_tracker.md`).
* **Personal Website Layout:**
  * Hugo static site rooted at `ai-sandbox/personal-website/AaronScherf.github.io/`.
  * Project pages reside in `content/projects/<category>/<slug>/index.md`.
  * Project frontmatter currently includes `title`, `date`, `type`, `tags`, `image`, and `links` (containing generic GitHub links, but no structured subproject mapping).
* **Adjacent Tools & Prior Art:**
  * `tools/corpus_health/` demonstrates model-free discovery and deterministic state management.
  * `tools/project_steering/` demonstrates markdown parsing, multi-factor scoring, and local review serving.
  * `tools/audit_metadata.py` demonstrates programmatic metadata inspection across vault items.

---

## 3. Scope and Capability Inventory

| Capability | Discovery and Scope | Side Effects / Cost | Output and Idempotency | Verification |
| :--- | :--- | :--- | :--- | :--- |
| **Central Registry (`subproject_registry.json`)** | All Python packages and tools in `academic-rag-model` | None (static JSON file) | Canonical ground truth mapping; fully idempotent | Schema validation against `subproject_registry.schema.json` |
| **Website Frontmatter Standard** | All markdown project pages in `content/projects/` | None until edited | Machine-readable `subproject:` block in Hugo YAML | YAML parser validation |
| **Read-Only Automated Checker (`tools/audit_website_sync.py`)** | Both Git repos, local disk paths, Git logs | Local read only; 0 API calls, 0 cost | Machine-readable JSON report + formatted markdown summary | Unit tests on mock repo histories and live run comparison |
| **Steering Queue Integration (Optional)** | Ingests drift findings into `academic_hub_to_do.md` | Non-destructive review items | Structured to-do entries for missing/outdated pages | Parser compatibility with `tools.project_steering` |

---

## 4. Data Model & Specifications

### 4.1 Central Registry Schema (`subproject_registry.json`)

The central manifest will be placed at `ai-sandbox/academic-rag-model/docs/trackers/subproject_registry.json`.

```json
{
  "$schema": "./subproject_registry.schema.json",
  "version": "1.0.0",
  "last_updated": "2026-10-10",
  "subprojects": {
    "pipelines/transcribe_notes": {
      "id": "transcribe_notes",
      "name": "Notes Transcription Pipeline",
      "category": "academic-hub",
      "role": "pipeline",
      "code_path": "ai-sandbox/academic-rag-model/pipelines/transcribe_notes",
      "readme_path": "ai-sandbox/academic-rag-model/pipelines/transcribe_notes/README.md",
      "status_dir": "ai-sandbox/academic-rag-model/docs/status/transcribe_notes",
      "status_docs": [
        "ai-sandbox/academic-rag-model/docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md"
      ],
      "specs": [
        "ai-sandbox/academic-rag-model/docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md"
      ],
      "website_page": "content/projects/academic-hub/notes_transcription/index.md",
      "github_url": "https://github.com/AaronScherf/ai-sandbox-master/tree/main/ai-sandbox/academic-rag-model/pipelines/transcribe_notes"
    },
    "agent/tutor": {
      "id": "socratic_tutor",
      "name": "Socratic Tutor Session Gate",
      "category": "academic-hub",
      "role": "agent",
      "code_path": "ai-sandbox/academic-rag-model/agent/tutor",
      "readme_path": "ai-sandbox/academic-rag-model/agent/tutor/README.md",
      "status_dir": "ai-sandbox/academic-rag-model/docs/status/agent/tutor",
      "status_docs": [
        "ai-sandbox/academic-rag-model/docs/status/agent/tutor/2026-10-08-socratic-tutor-status.md"
      ],
      "specs": [
        "ai-sandbox/academic-rag-model/docs/superpowers/specs/2026-10-08-socratic-tutor-v1-1-design.md"
      ],
      "website_page": null,
      "github_url": "https://github.com/AaronScherf/ai-sandbox-master/tree/main/ai-sandbox/academic-rag-model/agent/tutor"
    }
  }
}
```

### 4.2 Website Frontmatter Specification

Each `content/projects/<category>/<slug>/index.md` will include a structured `subproject:` block:

```yaml
---
title: Notes Transcription Pipeline
date: 2026-08-27
type: academic-hub-project
subproject:
  id: transcribe_notes
  package: pipelines/transcribe_notes
  monorepo_rel_path: ai-sandbox/academic-rag-model/pipelines/transcribe_notes
  readme: ai-sandbox/academic-rag-model/pipelines/transcribe_notes/README.md
  primary_status_doc: ai-sandbox/academic-rag-model/docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md
links:
  - type: site
    icon: brands/github
    label: GitHub
    url: https://github.com/AaronScherf/ai-sandbox-master/tree/main/ai-sandbox/academic-rag-model/pipelines/transcribe_notes
---
```

---

## 5. Automated Checker Architecture (`tools/audit_website_sync.py`)

### 5.1 CLI Interface
```powershell
python -m tools.audit_website_sync [--registry PATH] [--website-root PATH] [--json] [--strict]
```

### 5.2 Verification Pipeline
1. **Load Registry:** Ingest `subproject_registry.json`. Validate schema and ensure every entry defines required paths.
2. **Subproject Code Discovery:** Verify whether any directory under `ai-sandbox/academic-rag-model/` containing an `__init__.py` and `README.md` is absent from the registry (detecting untracked subprojects).
3. **Existence Check:** Verify that configured `code_path`, `readme_path`, and `status_docs` exist in the monorepo, and `website_page` exists in the website checkout (if non-null).
4. **Git Timestamp Analysis:**
   * Query `t_code = git log -1 --format=%ct -- <code_path>` in the monorepo.
   * Query `t_status = max(git log -1 --format=%ct -- <doc>)` for all linked status docs.
   * Query `t_website = git log -1 --format=%ct -- <website_page>` in the website repository.
5. **Drift Evaluation:**
   * If `website_page is None` -> Classify as `MISSING_WEBSITE_PAGE`.
   * If `t_code > t_website + TOLERANCE_SECONDS` (e.g., 3600s) -> Classify as `WEBSITE_PAGE_OUTDATED`.
   * If `t_code > t_status + TOLERANCE_SECONDS` -> Classify as `STATUS_DOC_OUTDATED`.
   * If `website_page` has frontmatter `subproject.package != registry.package` -> Classify as `METADATA_MISMATCH`.
6. **Report Generation:** Output formatted summary tables, status badges, and actionable next steps.

---

## 6. Phased Implementation Plan Outline

* **Phase 1: Registry Foundation & Scanner Tooling (Monorepo only)**
  * Create `ai-sandbox/academic-rag-model/docs/trackers/subproject_registry.json` covering all 21 subprojects.
  * Implement `ai-sandbox/academic-rag-model/tools/audit_website_sync.py` with full CLI and test coverage.
  * Verify that running the tool reproduces the findings of the 2026-10-10 audit.
* **Phase 2: Website Frontmatter Alignment (Website repo only)**
  * Update existing 13 website project pages in a dedicated `AaronScherf.github.io` worktree to include the `subproject:` frontmatter block and correct granular GitHub URLs.
  * Run `audit_website_sync.py` to confirm zero metadata mismatches.
* **Phase 3: Content Reconciliation (Website & Status Docs)**
  * Draft missing website project pages for the 8 identified components (prioritizing Socratic Tutor, Study Guide Pipeline, and Corpus Health).
  * Update outdated pages (`source_indexer`, `notes_transcription`, `rag_analysis`, and `academic-hub-overview`).
  * Draft the v2 update for `agent/summary_enhance` status documentation.
