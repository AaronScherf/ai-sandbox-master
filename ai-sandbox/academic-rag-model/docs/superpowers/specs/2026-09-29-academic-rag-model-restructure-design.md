# academic-rag-model directory restructure — design

## Problem

`academic-rag-model/` grew ~15 subprojects as flat, same-level directories
with no role grouping, several ambiguous names (`essays/`, `notes/`,
`postprocessing/` don't signal they're conversion processes), duplicate
per-package docs (`README.md` inside the package + a separate
`*_instructions.md` at repo root), loose root-level scripts that belong to
no single package, a flat `tests/` directory not mirrored by package, and a
`docs/` tree split by doc-type with all ~15 subprojects' files mixed
together inside each type folder. The goal is a standard, role-based layout
that a new coder or agent can navigate without a guided tour, and naming
that describes what each package *does*.

Scope is limited to `academic-rag-model/`. `academic-hub/` (the content
vault) and `personal-website/` are untouched.

## Goals

- Group packages by role (conversion pipeline, discovery, tutoring agent,
  shared core, standalone app) instead of one flat sibling list.
- Verb-first names for process packages so the folder name states the
  action it performs.
- One `README.md` per package (merge today's split README +
  root-level `*_instructions.md`).
- `docs/` keeps its current doc-type-first split (status/specs/plans/
  brainstorms) — required so the brainstorming/writing-plans skills'
  default output paths (`docs/superpowers/{specs,plans}/`) keep working —
  but each type folder gains a per-package subfolder.
- `tests/` mirrors the new package tree.
- Root is left holding only true cross-cutting files: build/env config,
  `tools/` bridge scripts, and the top-level docs.
- Remove debris (`preview.txt`) and archive superseded code
  (`old_attempts/`) out of the active tree.

## Non-goals

- No behavior changes to any pipeline, agent, or script — this is a pure
  file move + import/reference rewrite.
- No change to `academic-hub/` or `research/` (the content vaults these
  pipelines populate) or to any other subproject's CLAUDE.md.
- No decomposition of any package's internals (e.g. splitting
  `transcribe_notes.py` further) — out of scope for this pass.

## Target structure

```
academic-rag-model/
├── pipelines/
│   ├── convert_textbook/
│   ├── transcribe_notes/
│   ├── convert_essays/
│   ├── convert_journal_articles/
│   ├── generate_video_notes/
│   └── postprocess_notes/
├── discovery/
│   └── discover_journal_articles/
├── agent/
│   ├── rag/
│   ├── viz/
│   ├── problem_gen/
│   └── problem_corpus/
├── core/
│   ├── env/
│   └── indexer/
├── resume_manager/
├── audio_generator/
├── tools/
│   ├── audit_metadata.py
│   └── reconcile_needs_manual.py
├── tests/
│   ├── pipelines/<package>/...
│   ├── discovery/<package>/...
│   ├── agent/<package>/...
│   ├── core/<package>/...
│   ├── resume_manager/...
│   └── audio_generator/...
├── docs/
│   ├── status/<package>/YYYY-MM-DD-*.md
│   ├── superpowers/
│   │   ├── specs/<package>/YYYY-MM-DD-*.md
│   │   └── plans/<package>/YYYY-MM-DD-*.md
│   ├── brainstorms/<package-or-unnested-if-cross-cutting>/*.md
│   └── trackers/  (unchanged — inherently cross-cutting)
├── archive/
│   └── old_attempts/
├── Dockerfile
├── requirements.txt
├── conftest.py
├── .python-version
├── README.md
└── CLAUDE.md
```

## Package rename mapping

| Current path | New path |
|---|---|
| `textbook/` | `pipelines/convert_textbook/` |
| `notes/` | `pipelines/transcribe_notes/` |
| `essays/` | `pipelines/convert_essays/` |
| `journal_articles/` | `pipelines/convert_journal_articles/` |
| `video_notes/` | `pipelines/generate_video_notes/` |
| `postprocessing/` | `pipelines/postprocess_notes/` |
| `journal_discovery/` | `discovery/discover_journal_articles/` |
| `rag/` | `agent/rag/` |
| `viz/` | `agent/viz/` |
| `problem_gen/` | `agent/problem_gen/` |
| `problem_corpus/` | `agent/problem_corpus/` |
| `common/` | `core/env/` |
| `indexer/` | `core/indexer/` |
| `resume_manager/` | `resume_manager/` (unchanged, moves nowhere) |
| `audio_generator/` | `audio_generator/` (unchanged, moves nowhere) |
| `old_attempts/` | `archive/old_attempts/` |

`resume_manager/` and `audio_generator/` stay top-level, unrenamed: neither
is part of the academic-conversion pipeline or the tutoring agent, so they
don't belong under any of the new category folders, and their current
names already describe their function.

## Loose root files

| Current | New |
|---|---|
| `audit_metadata.py` | `tools/audit_metadata.py` |
| `reconcile_needs_manual.py` | `tools/reconcile_needs_manual.py` |
| `marker_setup.sh` | `pipelines/convert_textbook/marker_setup.sh` |
| `start_conversion.sh` | `pipelines/convert_textbook/start_conversion.sh` |
| `convert_textbook_instructions.md` | merged into `pipelines/convert_textbook/README.md` |
| `convert_textbook_agent_instructions.md` | `pipelines/convert_textbook/AGENT_INSTRUCTIONS.md` (kept separate — genuinely different audience, not duplicate content) |
| `notes_instructions.md` | merged into `pipelines/transcribe_notes/README.md` |
| `essays_instructions.md` | merged into `pipelines/convert_essays/README.md` |
| `journal_articles_instructions.md` | merged into `pipelines/convert_journal_articles/README.md` |
| `journal_discovery_instructions.md` | merged into `discovery/discover_journal_articles/README.md` |
| `resume_manager_instructions.md` | merged into `resume_manager/README.md` |
| `preview.txt` | deleted (untracked from git; stray single-run debug dump, not referenced by any package or doc) |

`tools/` holds `audit_metadata.py` and `reconcile_needs_manual.py`
specifically because neither belongs to one package: `reconcile_needs_manual.py`
bridges `discovery/discover_journal_articles/`'s manifest and
`pipelines/convert_journal_articles/`'s output, and chains into
`audit_metadata.py` as its last step. A future cross-package bridge script
goes here too, rather than back at repo root.

`Dockerfile` stays at repo root — it packages `core/env/`, `core/indexer/`,
and `pipelines/convert_textbook/` together for the GCP VM build context;
moving it into any one package would misrepresent what it builds. Its
`COPY` lines get updated to the new paths.

## Docs reorganization

Each of `docs/status/`, `docs/superpowers/specs/`, and
`docs/superpowers/plans/` gains one subfolder per package, named after the
package's new directory name (e.g. `transcribe_notes`, not `notes/notes-transcription`).
A status/spec/plan file moves into the subfolder matching the package its
content is about, keeping its existing date-prefixed filename unchanged —
only its directory changes. Files that genuinely span multiple packages
(e.g. `docs/trackers/academic_hub_to_do.md`, cross-cutting brainstorms like
`Academic Hub Progress Reflections.md`) stay unnested at the doc-type
folder's root rather than being forced into one package's subfolder.

`docs/trackers/` is left structurally as-is (it's inherently cross-cutting
by nature, not per-package).

This preserves the brainstorming/writing-plans skills' default write paths
(`docs/superpowers/specs/`, `docs/superpowers/plans/`) — a new spec or plan
still lands at the type-folder root by default; sorting it into the right
package subfolder is a manual follow-up, same as today's manual filing.

## Tests reorganization

`tests/` currently is one flat directory of ~90 files, explicitly
documented as not mirroring package structure. It moves to mirror the tree
above, including the two standalone apps that don't change location
themselves: `tests/pipelines/transcribe_notes/test_transcribe_notes.py`,
`tests/agent/rag/test_rag_agent.py`, `tests/core/indexer/test_index_search.py`,
`tests/resume_manager/test_convert_resume.py`,
`tests/audio_generator/test_cleaner.py`, etc. Each test file's existing
name is kept (only its directory changes) unless it needs renaming to
track a renamed source module.

`conftest.py` and pytest discovery config need to keep working with the new
nested `tests/` tree — this is a config check during implementation, not a
design change.

## Migration mechanics — call out for the implementation plan

This is a mechanical rename-and-move, not a design risk, but the blast
radius is real and should shape how the plan sequences work:

- **122 files** currently have direct `from X import ...` / `import X`
  statements referencing the current package names (grep count across
  `*.py`, excluding docs/READMEs). Every one needs its import path
  rewritten to match the new package location.
- `Dockerfile`'s `COPY` lines reference `common/`, `indexer/`, `textbook/`
  by current path.
- `marker_setup.sh` / `start_conversion.sh` are scp'd to a GCP VM and
  reference `convert_textbook_instructions.md` by name in comments.
- `core/env/academic_hub_paths.py` (renamed from `common/academic_hub_paths.py`)
  and any other path-construction code should be checked for assumptions
  about the current layout.
- Every relative doc/README cross-link (`../notes_instructions.md`-style)
  needs updating, including this repo's own `README.md`, both `CLAUDE.md`
  files (root and `academic-rag-model/`), and `docs/AGENT_ROUTING.md` if it
  names these packages by their old paths.

Recommended sequencing for the implementation plan: move and rewire one
category at a time (`core/` first, since `pipelines/`, `discovery/`, and
`agent/` all depend on it; then `pipelines/`, `discovery/`, `agent/`, then
the doc/test reorganization last), running `python -m pytest tests/` after
each category to catch import breakage before moving to the next, rather
than one single giant diff.

## Success criteria

- `python -m pytest tests/` passes from a clean checkout after the move.
- No file under `academic-rag-model/` still imports a package by its old
  name.
- No relative link in any `README.md`, `CLAUDE.md`, or `docs/` file points
  at a pre-move path.
- `old_attempts/` and `preview.txt` no longer appear at repo root.
- Every package directory has exactly one `README.md`, no orphaned
  `*_instructions.md` at repo root.
