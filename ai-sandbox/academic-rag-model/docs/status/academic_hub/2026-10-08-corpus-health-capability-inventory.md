# Corpus Health Capability Inventory

**Date:** 2026-10-08
**Scope:** Initial read-only scanner; this inventory records verified interfaces and deliberate apply gates.

| Operation | Discovery and scope | Cost / side effects | Scanner treatment |
|---|---|---|---|
| Notes PDF transcription | `route_notes_transcribe` has pure `pdf_output_path()` and supports `--dry-run`; per-file `transcribe_notes --file` exists. | Transcription can call Gemini; writes into `processed_outputs/` and indexes output. | Use the path helper and filesystem existence only. No dry-run or model call during scan. |
| Excalidraw transcription | Router exposes `excalidraw_output_path()`; one scene plus a sibling `.svg` or `.png` is the input. | Vision/expansion can call Gemini; writes raw/RAG Markdown and indexing artifacts. | Use expected `.rag.md` path only. Report missing export as an input issue. No apply in initial milestone. |
| Notes postprocessing | `postprocess_notes` supports explicit roots, `--file`, and `--dry-run`. | May call Gemini and edits Markdown/change log. | Not used as a scanner primitive. |
| Textbook conversion | `convert_textbook` follows the documented GCP/VM multi-PDF process; `describe_images --dry-run --book` is narrower. | Cloud/VM conversion and Gemini image description; outputs span `academic_resources/` and the notes vault. | Detect expected resource Markdown and tablet `.rag.md`; no v1 adapter. |
| Essay conversion | `convert_essays --file` and `--dry-run`; configurable input/output roots. | Local DOCX conversion; optional index hook may call Gemini. Defaults to research content. | Outside default hub categories; configurable policy only. |
| Journal article conversion | `convert_journal_articles --file` and `--dry-run`. | Reuses cost-routed transcription and indexing; defaults to research content. | Outside default hub categories; inventory only. |
| Index rebuild | `index_search rebuild` has course/force/prune options, no read-only mode. | Can create/update cards and aggregates, use Gemini, and mutate Markdown/index files. | Never called by scanner. |
| Index retag/chunk | `retag --dry-run`; `chunk --course/--file --dry-run`. | Real runs can call models/embeddings and write index/frontmatter. | Never used for discovery; scanner uses the new read-only audit API. |
| Index card/chunk readers | `index_card.list_courses/load_shard` and `chunk_index.load_chunks` are public read helpers. | Local reads only; malformed data can raise. | Reused behind `core.indexer.audit.audit_markdown_index`; errors mark the result incomplete. |
| Git status | `tools.git_workflow.current_branch`, `dirty_files`, and `git_common_dir`; `active_work` provides cross-worktree reporting. | Local Git metadata reads only; no fetch or network. | Report branch, dirty paths, and locally available upstream divergence. No cleanup. |

## Root and output policy

The `academic-hub/` directory is inside the outer monorepo. Its
`academic_notes/` child is a nested Git checkout in the live workspace and may
be absent from an outer worktree. Configuration therefore names the hub and
notes roots independently. A missing notes root is reported unavailable.

For note sources under `academic_resources/`, the output path mirrors the
source-relative directory under the configured notes root and then enters
`processed_outputs/`. Sources already in the notes checkout use their sibling
`processed_outputs/`. Textbook PDFs are excluded from note-transcription
findings and checked against the textbook conversion layout instead.

Markdown frontmatter/index checks are opt-in through explicit config policies.
The extension alone is not a category rule. The read-only index API matches
cards using their public `path` field and compares `content_hash` only for
files up to its configured size limit (8 MiB by default); larger files are
reported unverified. `compute_file_id()` is PDF-specific and is not used as a
generic fingerprint for Markdown or Excalidraw.

## Apply gates

- No API, cloud, or pipeline dry-run is part of `scan`.
- No repair adapter is enabled in the scanner MVP.
- Any later write into `academic_notes/` requires an independently reviewed
  sync-quiescence boundary; an orchestrator-only lock is insufficient.
- Any later write to the outer corpus/index requires all participating direct
  writers to adopt the same lock contract.
- The project steering / `what_to_do_today` workflow remains separate.
