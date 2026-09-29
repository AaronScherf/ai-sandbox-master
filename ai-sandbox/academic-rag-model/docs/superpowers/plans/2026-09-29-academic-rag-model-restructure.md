# academic-rag-model Directory Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `academic-rag-model/` from ~15 flat, ambiguously-named sibling packages into a role-based tree (`pipelines/`, `discovery/`, `agent/`, `core/`, standalone apps), with matching `tests/` and `docs/` reorganization, and zero behavior change.

**Architecture:** Pure mechanical move-and-rewrite. A small reusable helper script does the actual import-statement rewriting (regex-anchored to import lines only, so it can't touch comments/strings/prose); each package gets one task that moves its directory, moves+renames its tests, rewrites every absolute import of it repo-wide, and runs its own tests before committing. Docs and root reference cleanup happen after all code moves land, since they don't affect test correctness.

**Tech Stack:** Python 3.13, pytest, git (worktree already created), bash/sed (Git Bash on Windows).

**Spec:** [`docs/superpowers/specs/2026-09-29-academic-rag-model-restructure-design.md`](../specs/2026-09-29-academic-rag-model-restructure-design.md)

## Global Constraints

- Run all Python as modules (`python -m pkg.module ...`), never as bare file paths — existing project convention, unaffected by the move.
- Every package keeps its `__init__.py`; `git mv` preserves it automatically.
- Pure move/rename only — no logic edits to any `.py` file's actual code beyond import-path lines.
- `core/env/` and `core/indexer/` (was `common/`, `indexer/`) are depended on by nearly everything (45 and 29 importing files respectively) — do these first so every later task's repo-wide rewrite pass runs against an already-consistent base.
- `resume_manager/` and `audio_generator/` keep their current top-level path and dotted import name; only their tests and docs move.
- Stage explicit paths only; never `git add -A` / `git add .` (repo policy — `docs/WORKTREE_WORKFLOW.md`).
- Never commit secrets or copyrighted source material.
- Every commit in this plan happens on branch `claude/academic-rag-model-restructure`, in worktree `.worktrees/claude-academic-rag-model-restructure` — already checked out; do not `cd` out of it.

## Review Focus

- A multi-name import line (`import notes, essays`) or a mid-file `import X as Y` the helper script's line-start anchor doesn't catch, leaving a broken import that only surfaces when that specific code path actually runs — mitigated by a full `pytest tests/` run in the final task, not just each task's own package tests.
- A shell script or runbook doc that references the old directory layout by literal path (not a Python import) — `gcloud compute scp` source arguments, `python3 -u -m textbook.X` invocation examples inside the GCP runbook — silently stale since pytest never exercises them. Task 5 handles this explicitly for the textbook pipeline's VM deployment docs.
- A relative markdown link (`../notes_instructions.md`) left dangling after a file merge/move — not caught by tests, but directly visible to the "new coder should be able to navigate this" goal the whole reorg is for. Verified per-task and again in the final task.
- `academic-rag-model/CLAUDE.md`'s documented "`docs/status/<date>-<subproject>-status.md`, latest date wins" convention needs to still resolve correctly once those files sit in per-package subfolders instead of one flat directory — handled explicitly in Task 19's doc and Task 20's CLAUDE.md update.
- A test file with a hardcoded path string (fixture path built from `Path(__file__).parent`, or a docstring telling a human to run `pytest tests/test_old_name.py`) that goes stale once the file physically moves — checked via grep in Task 20 across all moved test files.

---

## Task 1: Import-rename helper script

**Files:**
- Create: `scripts/_rename_pkg_imports.sh`
- Test: manual smoke test in this task's own steps (temp fixture files, deleted after)

**Interfaces:**
- Produces: `scripts/_rename_pkg_imports.sh OLD_PKG NEW_DOTTED_PATH` — rewrites every `*.py` file under the current directory whose import statement starts with `from OLD_PKG` or `import OLD_PKG` (anchored at line-start after whitespace, so comments/strings/prose containing the same word are untouched) to use `NEW_DOTTED_PATH` instead. Prints the count of files changed. Every later task in this plan invokes it with real `OLD_PKG`/`NEW_DOTTED_PATH` values.
- Consumes: nothing (first task).

- [ ] **Step 1: Write the script**

```bash
mkdir -p scripts
cat > scripts/_rename_pkg_imports.sh <<'SCRIPT'
#!/usr/bin/env bash
# scripts/_rename_pkg_imports.sh OLD_PKG NEW_DOTTED_PATH
# Rewrites `from OLD_PKG...` / `import OLD_PKG...` import statements,
# repo-wide under the current directory, to NEW_DOTTED_PATH. Only lines
# that are themselves import statements (anchored at line start, after
# optional whitespace) are touched -- this can't clobber comments,
# strings, or prose that happens to contain the same word.
set -euo pipefail
OLD="$1"
NEW="$2"
FILES=$(grep -rlE "^[[:space:]]*(from|import)[[:space:]]+${OLD}(\.|[[:space:]])" --include="*.py" . || true)
if [ -z "$FILES" ]; then
  echo "No files reference ${OLD}"
  exit 0
fi
for f in $FILES; do
  sed -i -E \
    -e "s/^([[:space:]]*from[[:space:]]+)${OLD}(\.|[[:space:]])/\1${NEW}\2/" \
    -e "s/^([[:space:]]*import[[:space:]]+)${OLD}(\.|[[:space:]]|\$)/\1${NEW}\2/" \
    "$f"
done
COUNT=$(echo "$FILES" | wc -l)
echo "Rewrote ${COUNT} file(s): ${OLD} -> ${NEW}"
SCRIPT
chmod +x scripts/_rename_pkg_imports.sh
```

- [ ] **Step 2: Smoke-test it against fixture files**

```bash
mkdir -p /tmp/rename_smoke_test
cat > /tmp/rename_smoke_test/a.py <<'EOF'
from oldpkg.sub import thing
import oldpkg
import oldpkg.other as o
# a comment mentioning oldpkg should not change
x = "oldpkg appears in a string too, should not change"
EOF
cd /tmp/rename_smoke_test
/c/Users/theaa/ai-sandbox-master/.worktrees/claude-academic-rag-model-restructure/ai-sandbox/academic-rag-model/scripts/_rename_pkg_imports.sh oldpkg newpkg.moved
cat a.py
cd - 
```

Expected output of `cat a.py`:
```
from newpkg.moved.sub import thing
import newpkg.moved
import newpkg.moved.other as o
# a comment mentioning oldpkg should not change
x = "oldpkg appears in a string too, should not change"
```

- [ ] **Step 3: Verify and clean up the fixture**

```bash
rm -rf /tmp/rename_smoke_test
```

Confirm Step 2's actual output matched the expected output exactly (import lines rewritten, comment/string untouched) before proceeding — this is the correctness guarantee every later task relies on.

- [ ] **Step 4: Commit**

```bash
git add scripts/_rename_pkg_imports.sh
git commit -m "chore: add repo-wide import-rename helper for the directory restructure"
```

---

## Task 2: Remove debris, archive superseded code

**Files:**
- Delete: `preview.txt`
- Move: `old_attempts/` → `archive/old_attempts/`

**Interfaces:**
- Produces: nothing other packages depend on.
- Consumes: nothing.

- [ ] **Step 1: Delete preview.txt**

```bash
git rm preview.txt
```

- [ ] **Step 2: Archive old_attempts/**

```bash
mkdir -p archive
git mv old_attempts archive/old_attempts
```

- [ ] **Step 3: Verify nothing referenced either path**

```bash
grep -rl "preview\.txt\|old_attempts" --include="*.py" --include="*.md" --include="*.sh" . | grep -v "^./archive/"
```

Expected: no output (or only matches inside `archive/old_attempts/`'s own files, e.g. `old_Dockerfile.md` mentioning itself — those are fine, they're archived).

- [ ] **Step 4: Commit**

```bash
git add -A -- preview.txt archive/
git commit -m "chore: delete debug debris, archive superseded old_attempts/"
```

---

## Task 3: Move `common/` → `core/env/`

**Files:**
- Move: `common/*.py` → `core/env/*.py` (4 modules: `academic_hub_paths.py`, `frontmatter.py`, `gemini_utils.py`, `ollama_utils.py`)
- Move+rename tests: `tests/test_academic_hub_paths.py`, `tests/test_frontmatter.py`, `tests/test_gemini_utils.py`, `tests/test_ollama_utils.py` → `tests/core/env/`
- Modify: every file in the repo with `from common...` / `import common...` (45 files found via search)

**Interfaces:**
- Produces: `core.env.academic_hub_paths`, `core.env.frontmatter`, `core.env.gemini_utils`, `core.env.ollama_utils` — the canonical import path every other package now uses for shared env/util helpers.
- Consumes: nothing (no other package's rename this depends on).

- [ ] **Step 1: Move the package directory**

```bash
mkdir -p core
git mv common core/env
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/core/env
git mv tests/test_academic_hub_paths.py tests/core/env/test_academic_hub_paths.py
git mv tests/test_frontmatter.py tests/core/env/test_frontmatter.py
git mv tests/test_gemini_utils.py tests/core/env/test_gemini_utils.py
git mv tests/test_ollama_utils.py tests/core/env/test_ollama_utils.py
```

- [ ] **Step 3: Rewrite every import of `common` repo-wide**

```bash
scripts/_rename_pkg_imports.sh common core.env
```

Expected: `Rewrote 45 file(s): common -> core.env` (or close to it — file count may drift slightly from earlier tasks' commits; any nonzero count touching the files above is correct).

- [ ] **Step 4: Verify no old-style references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+common(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/core/env/ -v
```

Expected: all pass, same as before the move (this is a pure rename — any failure means a rewrite bug, not a real regression).

- [ ] **Step 6: Commit**

```bash
git add -A -- core/env tests/core/env $(grep -rlE "core\.env" --include="*.py" . | grep -v "^./core/env/\|^./tests/core/env/")
git commit -m "refactor: move common/ to core/env/"
```

---

## Task 4: Move `indexer/` → `core/indexer/`

**Files:**
- Move: `indexer/*.py` → `core/indexer/*.py` (5 modules: `chunk_index.py`, `duplicate_check.py`, `index_card.py`, `index_search.py`, `retag.py`)
- Move+rename tests: `tests/test_chunk_index.py`, `tests/test_duplicate_check.py`, `tests/test_index_card.py`, `tests/test_index_search.py`, `tests/test_retag.py` → `tests/core/indexer/`
- Modify: every file with `from indexer...` / `import indexer...` (29 files found via search)

**Interfaces:**
- Produces: `core.indexer.chunk_index`, `core.indexer.duplicate_check`, `core.indexer.index_card`, `core.indexer.index_search`, `core.indexer.retag`.
- Consumes: `core.env.*` (Task 3) — `indexer/`'s own modules import `common`, already rewritten to `core.env` by Task 3's repo-wide pass since it ran before this task.

- [ ] **Step 1: Move the package directory**

```bash
git mv indexer core/indexer
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/core/indexer
git mv tests/test_chunk_index.py tests/core/indexer/test_chunk_index.py
git mv tests/test_duplicate_check.py tests/core/indexer/test_duplicate_check.py
git mv tests/test_index_card.py tests/core/indexer/test_index_card.py
git mv tests/test_index_search.py tests/core/indexer/test_index_search.py
git mv tests/test_retag.py tests/core/indexer/test_retag.py
```

- [ ] **Step 3: Rewrite every import of `indexer` repo-wide**

```bash
scripts/_rename_pkg_imports.sh indexer core.indexer
```

Expected: `Rewrote 29 file(s): indexer -> core.indexer`.

- [ ] **Step 4: Verify no old-style references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+indexer(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/core/indexer/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- core/indexer tests/core/indexer $(grep -rlE "core\.indexer" --include="*.py" . | grep -v "^./core/indexer/\|^./tests/core/indexer/")
git commit -m "refactor: move indexer/ to core/indexer/"
```

---

## Task 5: Move `textbook/` → `pipelines/convert_textbook/`

This is the largest task: besides the code move, it also relocates the VM deployment scripts and merges two instruction docs, both of which hardcode the old directory layout in `gcloud compute scp` commands and `python -m textbook.X` invocation examples.

**Files:**
- Move: `textbook/*.py` → `pipelines/convert_textbook/*.py` (8 modules: `bib_info.py`, `chapter_index.py`, `convert_textbook.py`, `describe_images.py`, `page_markers.py`, `split_chapters.py`, `toc_identify.py`, `toc_repair.py`, plus `vm_sizing_log.py`)
- Move+rename tests: `tests/test_bib_info.py`, `tests/test_chapter_index.py`, `tests/test_convert_textbook.py`, `tests/test_describe_images.py`, `tests/test_page_markers.py`, `tests/test_split_chapters.py`, `tests/test_toc_identify.py`, `tests/test_toc_repair.py`, `tests/test_vm_sizing_log.py` → `tests/pipelines/convert_textbook/`
- Move: `marker_setup.sh`, `start_conversion.sh` → `pipelines/convert_textbook/`
- Merge: `convert_textbook_instructions.md` into `pipelines/convert_textbook/README.md`
- Move: `convert_textbook_agent_instructions.md` → `pipelines/convert_textbook/AGENT_INSTRUCTIONS.md` (kept as a separate file — genuinely different audience, not a duplicate)
- Modify: every file with `from textbook...` / `import textbook...` (15 files found via search)

**Interfaces:**
- Produces: `pipelines.convert_textbook.convert_textbook`, `.describe_images`, `.split_chapters`, `.toc_identify`, `.toc_repair`, `.chapter_index`, `.bib_info`, `.page_markers`, `.vm_sizing_log`.
- Consumes: `core.env.*` (Task 3), `core.indexer.*` (Task 4) — already rewritten.

- [ ] **Step 1: Move the package directory and its scripts**

```bash
mkdir -p pipelines
git mv textbook pipelines/convert_textbook
git mv marker_setup.sh pipelines/convert_textbook/marker_setup.sh
git mv start_conversion.sh pipelines/convert_textbook/start_conversion.sh
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/pipelines/convert_textbook
git mv tests/test_bib_info.py tests/pipelines/convert_textbook/test_bib_info.py
git mv tests/test_chapter_index.py tests/pipelines/convert_textbook/test_chapter_index.py
git mv tests/test_convert_textbook.py tests/pipelines/convert_textbook/test_convert_textbook.py
git mv tests/test_describe_images.py tests/pipelines/convert_textbook/test_describe_images.py
git mv tests/test_page_markers.py tests/pipelines/convert_textbook/test_page_markers.py
git mv tests/test_split_chapters.py tests/pipelines/convert_textbook/test_split_chapters.py
git mv tests/test_toc_identify.py tests/pipelines/convert_textbook/test_toc_identify.py
git mv tests/test_toc_repair.py tests/pipelines/convert_textbook/test_toc_repair.py
git mv tests/test_vm_sizing_log.py tests/pipelines/convert_textbook/test_vm_sizing_log.py
```

- [ ] **Step 3: Rewrite every import of `textbook` repo-wide**

```bash
scripts/_rename_pkg_imports.sh textbook pipelines.convert_textbook
```

Expected: `Rewrote 15 file(s): textbook -> pipelines.convert_textbook`.

- [ ] **Step 4: Merge the human instructions doc into the package README**

Read `pipelines/convert_textbook/README.md` (was `textbook/README.md`) and `convert_textbook_instructions.md` in full. Append the instructions content to the README under a `## Full usage guide` heading (the README's existing content becomes a `## Overview` section above it, if it doesn't already have clear headings — preserve all content from both, don't summarize). Then:

```bash
git rm convert_textbook_instructions.md
```

- [ ] **Step 5: Move the agent instructions doc as-is**

```bash
git mv convert_textbook_agent_instructions.md pipelines/convert_textbook/AGENT_INSTRUCTIONS.md
```

- [ ] **Step 6: Fix the module-path references inside the merged README and the agent instructions**

These two files reference `textbook.<module>` by name in `python -m` command examples throughout (19 occurrences in the former human-instructions content, 5 in the agent instructions). Rewrite only genuine module-path references, not prose:

```bash
sed -i -E "s/\btextbook\.(convert_textbook|describe_images|split_chapters|toc_identify|toc_repair|chapter_index|bib_info|page_markers|vm_sizing_log)\b/pipelines.convert_textbook.\1/g" pipelines/convert_textbook/README.md pipelines/convert_textbook/AGENT_INSTRUCTIONS.md
```

- [ ] **Step 7: Fix the two `gcloud compute scp` lines that ship source to the VM**

The remote directory layout must mirror the new local one: `core/` (holding `env/` and `indexer/`) plus `pipelines/convert_textbook/` nested under `pipelines/`. Since `scp --recurse SRC DEST` places `SRC`'s basename directly under `DEST`, shipping `pipelines/convert_textbook` needs its parent `pipelines/` created remotely first.

In `pipelines/convert_textbook/README.md`, find:
```
gcloud compute scp --recurse common indexer textbook $VM_INSTANCE_NAME:~/academic-rag-model/ --zone=$GCP_ZONE --tunnel-through-iap
```
Replace with:
```
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="mkdir -p ~/academic-rag-model/pipelines"
gcloud compute scp --recurse core $VM_INSTANCE_NAME:~/academic-rag-model/ --zone=$GCP_ZONE --tunnel-through-iap
gcloud compute scp --recurse pipelines/convert_textbook $VM_INSTANCE_NAME:~/academic-rag-model/pipelines/ --zone=$GCP_ZONE --tunnel-through-iap
```

In `pipelines/convert_textbook/AGENT_INSTRUCTIONS.md`, find:
```
gcloud compute scp --recurse common indexer textbook "$VM_INSTANCE_NAME":"$REMOTE_HOME/academic-rag-model/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
```
Replace with:
```
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="mkdir -p $REMOTE_HOME/academic-rag-model/pipelines" --quiet
gcloud compute scp --recurse core "$VM_INSTANCE_NAME":"$REMOTE_HOME/academic-rag-model/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
gcloud compute scp --recurse pipelines/convert_textbook "$VM_INSTANCE_NAME":"$REMOTE_HOME/academic-rag-model/pipelines/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
```

- [ ] **Step 8: Fix `start_conversion.sh`'s comment referencing the now-merged instructions file**

```bash
grep -n "convert_textbook_instructions" pipelines/convert_textbook/start_conversion.sh
```

That comment (originally: `-- see Step 3.3 in convert_textbook_instructions.md`) points at a filename that no longer exists — its content is now inside `pipelines/convert_textbook/README.md`'s `## Full usage guide` section. Edit the comment to read `-- see Step 3.3 in README.md's Full usage guide section` instead.

- [ ] **Step 9: Confirm the Dockerfile needs no change**

```bash
grep -n "^COPY\|^ADD" Dockerfile
```

Expected: no output — this repo's `Dockerfile` only installs the `gcloud` CLI into a local orchestration image; it does not `COPY` `common/`, `indexer/`, or `textbook/` (verified during planning — the spec's claim that its `COPY` lines need updating was checked against the actual file and doesn't hold). No action needed here; this step just confirms that's still true before moving on.

- [ ] **Step 10: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+textbook(\.|[[:space:]])" --include="*.py" .
grep -n "common indexer textbook\|textbook\.\(convert_textbook\|describe_images\|split_chapters\|toc_identify\|toc_repair\|chapter_index\|bib_info\|page_markers\|vm_sizing_log\)" pipelines/convert_textbook/README.md pipelines/convert_textbook/AGENT_INSTRUCTIONS.md
grep -n "convert_textbook_instructions" pipelines/convert_textbook/start_conversion.sh
```

Expected: no output from any of the three.

- [ ] **Step 11: Run the moved tests**

```bash
python -m pytest tests/pipelines/convert_textbook/ -v
```

Expected: all pass.

- [ ] **Step 12: Commit**

```bash
git add -A -- pipelines/convert_textbook tests/pipelines/convert_textbook $(grep -rlE "pipelines\.convert_textbook" --include="*.py" . | grep -v "^./pipelines/convert_textbook/\|^./tests/pipelines/convert_textbook/")
git commit -m "refactor: move textbook/ to pipelines/convert_textbook/, merge instructions, fix VM deploy paths"
```

---

## Task 6: Move `notes/` → `pipelines/transcribe_notes/`

**Files:**
- Move: `notes/*.py` → `pipelines/transcribe_notes/*.py` (5 modules: `excalidraw_chunking.py`, `migrate_sources_to_resources.py`, `route_notes_transcribe.py`, `transcribe_excalidraw.py`, `transcribe_notes.py`)
- Move+rename tests: `tests/test_excalidraw_chunking.py`, `tests/test_migrate_sources_to_resources.py`, `tests/test_route_notes_transcribe.py`, `tests/test_transcribe_excalidraw.py`, `tests/test_transcribe_notes.py` → `tests/pipelines/transcribe_notes/`
- Merge: `notes_instructions.md` into `pipelines/transcribe_notes/README.md`
- Modify: every file with `from notes...` / `import notes...` (12 files found via search — includes `journal_articles/convert_journal_articles.py` and `postprocessing/postprocess_findings.py` / `postprocess_notes.py`, both still at their pre-move paths at this point in the plan; the rewrite still finds and fixes them there)

**Interfaces:**
- Produces: `pipelines.transcribe_notes.transcribe_notes`, `.route_notes_transcribe`, `.transcribe_excalidraw`, `.excalidraw_chunking`, `.migrate_sources_to_resources`.
- Consumes: `core.env.*`, `core.indexer.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv notes pipelines/transcribe_notes
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/pipelines/transcribe_notes
git mv tests/test_excalidraw_chunking.py tests/pipelines/transcribe_notes/test_excalidraw_chunking.py
git mv tests/test_migrate_sources_to_resources.py tests/pipelines/transcribe_notes/test_migrate_sources_to_resources.py
git mv tests/test_route_notes_transcribe.py tests/pipelines/transcribe_notes/test_route_notes_transcribe.py
git mv tests/test_transcribe_excalidraw.py tests/pipelines/transcribe_notes/test_transcribe_excalidraw.py
git mv tests/test_transcribe_notes.py tests/pipelines/transcribe_notes/test_transcribe_notes.py
```

- [ ] **Step 3: Rewrite every import of `notes` repo-wide**

```bash
scripts/_rename_pkg_imports.sh notes pipelines.transcribe_notes
```

Expected: `Rewrote 12 file(s): notes -> pipelines.transcribe_notes`.

- [ ] **Step 4: Merge the instructions doc into the package README**

Read `pipelines/transcribe_notes/README.md` (was `notes/README.md`) and `notes_instructions.md` in full. Append the instructions content under a `## Full usage guide` heading, preserving all content. Then:

```bash
git rm notes_instructions.md
```

- [ ] **Step 5: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+notes(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 6: Run the moved tests**

```bash
python -m pytest tests/pipelines/transcribe_notes/ -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add -A -- pipelines/transcribe_notes tests/pipelines/transcribe_notes $(grep -rlE "pipelines\.transcribe_notes" --include="*.py" . | grep -v "^./pipelines/transcribe_notes/\|^./tests/pipelines/transcribe_notes/")
git commit -m "refactor: move notes/ to pipelines/transcribe_notes/, merge instructions"
```

---

## Task 7: Move `essays/` → `pipelines/convert_essays/`

**Files:**
- Move: `essays/convert_essays.py` → `pipelines/convert_essays/convert_essays.py`
- Move+rename test: `tests/test_convert_essays.py` → `tests/pipelines/convert_essays/test_convert_essays.py`
- Merge: `essays_instructions.md` into `pipelines/convert_essays/README.md`
- Modify: `tests/test_convert_essays.py` (the only file with a direct import, per search)

**Interfaces:**
- Produces: `pipelines.convert_essays.convert_essays`.
- Consumes: `core.env.*`, `core.indexer.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv essays pipelines/convert_essays
```

- [ ] **Step 2: Move and rename its test**

```bash
mkdir -p tests/pipelines/convert_essays
git mv tests/test_convert_essays.py tests/pipelines/convert_essays/test_convert_essays.py
```

- [ ] **Step 3: Rewrite every import of `essays` repo-wide**

```bash
scripts/_rename_pkg_imports.sh essays pipelines.convert_essays
```

Expected: `Rewrote 1 file(s): essays -> pipelines.convert_essays`.

- [ ] **Step 4: Merge the instructions doc into the package README**

Read `pipelines/convert_essays/README.md` (was `essays/README.md`) and `essays_instructions.md` in full. Append under `## Full usage guide`. Then:

```bash
git rm essays_instructions.md
```

- [ ] **Step 5: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+essays(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 6: Run the moved test**

```bash
python -m pytest tests/pipelines/convert_essays/ -v
```

Expected: passes.

- [ ] **Step 7: Commit**

```bash
git add -A -- pipelines/convert_essays tests/pipelines/convert_essays
git commit -m "refactor: move essays/ to pipelines/convert_essays/, merge instructions"
```

---

## Task 8: Move `journal_articles/` → `pipelines/convert_journal_articles/`

**Files:**
- Move: `journal_articles/convert_journal_articles.py` → `pipelines/convert_journal_articles/convert_journal_articles.py`
- Move+rename test: `tests/test_convert_journal_articles.py` → `tests/pipelines/convert_journal_articles/test_convert_journal_articles.py`
- Merge: `journal_articles_instructions.md` into `pipelines/convert_journal_articles/README.md`
- Modify: `tests/test_convert_journal_articles.py` (the only file with a direct import, per search)

**Interfaces:**
- Produces: `pipelines.convert_journal_articles.convert_journal_articles`.
- Consumes: `pipelines.transcribe_notes.*` (Task 6 — this package reuses `transcribe_notes`'s pipeline unchanged), `core.env.*`, `core.indexer.*`.

- [ ] **Step 1: Move the package directory**

```bash
git mv journal_articles pipelines/convert_journal_articles
```

- [ ] **Step 2: Move and rename its test**

```bash
mkdir -p tests/pipelines/convert_journal_articles
git mv tests/test_convert_journal_articles.py tests/pipelines/convert_journal_articles/test_convert_journal_articles.py
```

- [ ] **Step 3: Rewrite every import of `journal_articles` repo-wide**

```bash
scripts/_rename_pkg_imports.sh journal_articles pipelines.convert_journal_articles
```

Expected: `Rewrote 1 file(s): journal_articles -> pipelines.convert_journal_articles`.

- [ ] **Step 4: Merge the instructions doc into the package README**

Read `pipelines/convert_journal_articles/README.md` (was `journal_articles/README.md`) and `journal_articles_instructions.md` in full. Append under `## Full usage guide`. Then:

```bash
git rm journal_articles_instructions.md
```

- [ ] **Step 5: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+journal_articles(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 6: Run the moved test**

```bash
python -m pytest tests/pipelines/convert_journal_articles/ -v
```

Expected: passes.

- [ ] **Step 7: Commit**

```bash
git add -A -- pipelines/convert_journal_articles tests/pipelines/convert_journal_articles
git commit -m "refactor: move journal_articles/ to pipelines/convert_journal_articles/, merge instructions"
```

---

## Task 9: Move `video_notes/` → `pipelines/generate_video_notes/`

**Files:**
- Move: `video_notes/*.py` → `pipelines/generate_video_notes/*.py` (8 modules: `audio_download.py`, `grouping.py`, `note_indexing.py`, `pipeline.py`, `pipeline_state.py`, `synthesize.py`, `transcribe.py`, `youtube_metadata.py`)
- Move+rename tests: `tests/test_audio_download.py`, `tests/test_grouping.py`, `tests/test_note_indexing.py`, `tests/test_pipeline.py`, `tests/test_pipeline_state.py`, `tests/test_synthesize.py`, `tests/test_transcribe.py`, `tests/test_youtube_metadata.py`, `tests/test_video_notes_package.py` → `tests/pipelines/generate_video_notes/`
- Modify: every file with `from video_notes...` / `import video_notes...` (10 files found via search)

**Interfaces:**
- Produces: `pipelines.generate_video_notes.pipeline`, `.grouping`, `.note_indexing`, `.pipeline_state`, `.synthesize`, `.transcribe`, `.audio_download`, `.youtube_metadata`.
- Consumes: `core.env.*`, `core.indexer.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv video_notes pipelines/generate_video_notes
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/pipelines/generate_video_notes
git mv tests/test_audio_download.py tests/pipelines/generate_video_notes/test_audio_download.py
git mv tests/test_grouping.py tests/pipelines/generate_video_notes/test_grouping.py
git mv tests/test_note_indexing.py tests/pipelines/generate_video_notes/test_note_indexing.py
git mv tests/test_pipeline.py tests/pipelines/generate_video_notes/test_pipeline.py
git mv tests/test_pipeline_state.py tests/pipelines/generate_video_notes/test_pipeline_state.py
git mv tests/test_synthesize.py tests/pipelines/generate_video_notes/test_synthesize.py
git mv tests/test_transcribe.py tests/pipelines/generate_video_notes/test_transcribe.py
git mv tests/test_youtube_metadata.py tests/pipelines/generate_video_notes/test_youtube_metadata.py
git mv tests/test_video_notes_package.py tests/pipelines/generate_video_notes/test_video_notes_package.py
```

- [ ] **Step 3: Rewrite every import of `video_notes` repo-wide**

```bash
scripts/_rename_pkg_imports.sh video_notes pipelines.generate_video_notes
```

Expected: `Rewrote 10 file(s): video_notes -> pipelines.generate_video_notes`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+video_notes(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/pipelines/generate_video_notes/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- pipelines/generate_video_notes tests/pipelines/generate_video_notes $(grep -rlE "pipelines\.generate_video_notes" --include="*.py" . | grep -v "^./pipelines/generate_video_notes/\|^./tests/pipelines/generate_video_notes/")
git commit -m "refactor: move video_notes/ to pipelines/generate_video_notes/"
```

---

## Task 10: Move `postprocessing/` → `pipelines/postprocess_notes/`

**Files:**
- Move: `postprocessing/*.py` → `pipelines/postprocess_notes/*.py` (4 modules: `local_model_scoring.py`, `postprocess_discovery.py`, `postprocess_findings.py`, `postprocess_notes.py`)
- Move+rename tests: `tests/test_postprocess_discovery.py`, `tests/test_postprocess_findings.py`, `tests/test_postprocess_notes.py` → `tests/pipelines/postprocess_notes/`
- Modify: every file with `from postprocessing...` / `import postprocessing...` (4 files found via search)

**Interfaces:**
- Produces: `pipelines.postprocess_notes.postprocess_notes`, `.postprocess_findings`, `.postprocess_discovery`, `.local_model_scoring`.
- Consumes: `pipelines.transcribe_notes.*` (Task 6), `core.env.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv postprocessing pipelines/postprocess_notes
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/pipelines/postprocess_notes
git mv tests/test_postprocess_discovery.py tests/pipelines/postprocess_notes/test_postprocess_discovery.py
git mv tests/test_postprocess_findings.py tests/pipelines/postprocess_notes/test_postprocess_findings.py
git mv tests/test_postprocess_notes.py tests/pipelines/postprocess_notes/test_postprocess_notes.py
```

- [ ] **Step 3: Rewrite every import of `postprocessing` repo-wide**

```bash
scripts/_rename_pkg_imports.sh postprocessing pipelines.postprocess_notes
```

Expected: `Rewrote 4 file(s): postprocessing -> pipelines.postprocess_notes`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+postprocessing(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/pipelines/postprocess_notes/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- pipelines/postprocess_notes tests/pipelines/postprocess_notes $(grep -rlE "pipelines\.postprocess_notes" --include="*.py" . | grep -v "^./pipelines/postprocess_notes/\|^./tests/pipelines/postprocess_notes/")
git commit -m "refactor: move postprocessing/ to pipelines/postprocess_notes/"
```

---

## Task 11: Move `journal_discovery/` → `discovery/discover_journal_articles/`

**Files:**
- Move: `journal_discovery/*.py` → `discovery/discover_journal_articles/*.py` (10 modules: `access.py`, `discover.py`, `discovery.py`, `http_utils.py` — wait, `http_utils.py` had no direct-import hit but lives in the package directory so moves with it — `manifest.py`, `manual_validate_ezproxy.py`, `metadata_sidecar.py`, `relevance.py`, `snowball.py`, `text_match.py`, `topic_routing.py`, `worklist.py`, `zotero_sync.py`)
- Move+rename tests: `tests/test_access.py`, `tests/test_discover.py`, `tests/test_discovery.py`, `tests/test_http_utils.py`, `tests/test_manifest.py`, `tests/test_metadata_sidecar.py`, `tests/test_relevance.py`, `tests/test_snowball.py`, `tests/test_text_match.py`, `tests/test_topic_routing.py`, `tests/test_worklist.py`, `tests/test_zotero_sync.py` → `tests/discovery/discover_journal_articles/`
- Merge: `journal_discovery_instructions.md` into `discovery/discover_journal_articles/README.md` (create the README if the package has none yet — check first)
- Modify: every file with `from journal_discovery...` / `import journal_discovery...` (26 files found via search — includes `audit_metadata.py` and `reconcile_needs_manual.py`, both still at repo root at this point; Task 16 moves them into `tools/` afterward, and this rewrite already updated their import lines in place)

**Interfaces:**
- Produces: `discovery.discover_journal_articles.discover`, `.discovery`, `.access`, `.manifest`, `.relevance`, `.snowball`, `.text_match`, `.topic_routing`, `.worklist`, `.zotero_sync`, `.metadata_sidecar`, `.manual_validate_ezproxy`, `.http_utils`.
- Consumes: `core.env.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
mkdir -p discovery
git mv journal_discovery discovery/discover_journal_articles
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/discovery/discover_journal_articles
git mv tests/test_access.py tests/discovery/discover_journal_articles/test_access.py
git mv tests/test_discover.py tests/discovery/discover_journal_articles/test_discover.py
git mv tests/test_discovery.py tests/discovery/discover_journal_articles/test_discovery.py
git mv tests/test_http_utils.py tests/discovery/discover_journal_articles/test_http_utils.py
git mv tests/test_manifest.py tests/discovery/discover_journal_articles/test_manifest.py
git mv tests/test_metadata_sidecar.py tests/discovery/discover_journal_articles/test_metadata_sidecar.py
git mv tests/test_relevance.py tests/discovery/discover_journal_articles/test_relevance.py
git mv tests/test_snowball.py tests/discovery/discover_journal_articles/test_snowball.py
git mv tests/test_text_match.py tests/discovery/discover_journal_articles/test_text_match.py
git mv tests/test_topic_routing.py tests/discovery/discover_journal_articles/test_topic_routing.py
git mv tests/test_worklist.py tests/discovery/discover_journal_articles/test_worklist.py
git mv tests/test_zotero_sync.py tests/discovery/discover_journal_articles/test_zotero_sync.py
```

- [ ] **Step 3: Rewrite every import of `journal_discovery` repo-wide**

```bash
scripts/_rename_pkg_imports.sh journal_discovery discovery.discover_journal_articles
```

Expected: `Rewrote 26 file(s): journal_discovery -> discovery.discover_journal_articles`.

- [ ] **Step 4: Merge the instructions doc into the package README**

Check whether `discovery/discover_journal_articles/README.md` already exists (the original `journal_discovery/` directory listing had no README.md — verify with `ls discovery/discover_journal_articles/`). If it doesn't exist, create it from `journal_discovery_instructions.md`'s content directly (add a one-paragraph orientation header above the existing instructions content, matching the style of other package READMEs). If it does exist, append the instructions content under `## Full usage guide` as in prior tasks. Then:

```bash
git rm journal_discovery_instructions.md
```

- [ ] **Step 5: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+journal_discovery(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 6: Run the moved tests**

```bash
python -m pytest tests/discovery/discover_journal_articles/ -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add -A -- discovery/discover_journal_articles tests/discovery/discover_journal_articles $(grep -rlE "discovery\.discover_journal_articles" --include="*.py" . | grep -v "^./discovery/discover_journal_articles/\|^./tests/discovery/discover_journal_articles/")
git commit -m "refactor: move journal_discovery/ to discovery/discover_journal_articles/, merge instructions"
```

---

## Task 12: Move `rag/` → `agent/rag/`

**Files:**
- Move: `rag/*.py` → `agent/rag/*.py` (5 modules: `problem_set_parser.py`, `rag_agent.py`, `report_builder.py`, `session_log.py`, `tutor_diagnosis.py`)
- Move+rename tests: `tests/test_problem_set_parser.py`, `tests/test_rag_agent.py`, `tests/test_report_builder.py`, `tests/test_session_log.py`, `tests/test_tutor_diagnosis.py` → `tests/agent/rag/`
- Modify: every file with `from rag...` / `import rag...` (9 files found via search)

**Interfaces:**
- Produces: `agent.rag.rag_agent`, `.tutor_diagnosis`, `.report_builder`, `.session_log`, `.problem_set_parser`.
- Consumes: `core.env.*`, `core.indexer.*` (already rewritten). `agent.viz.*` and `agent.problem_gen.*` are wired in as opt-in imports inside `rag_agent.py` — those get fixed in Tasks 13–14, since this task's rewrite only touches lines starting with `rag`, not `viz`/`problem_gen`.

- [ ] **Step 1: Move the package directory**

```bash
mkdir -p agent
git mv rag agent/rag
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/agent/rag
git mv tests/test_problem_set_parser.py tests/agent/rag/test_problem_set_parser.py
git mv tests/test_rag_agent.py tests/agent/rag/test_rag_agent.py
git mv tests/test_report_builder.py tests/agent/rag/test_report_builder.py
git mv tests/test_session_log.py tests/agent/rag/test_session_log.py
git mv tests/test_tutor_diagnosis.py tests/agent/rag/test_tutor_diagnosis.py
```

- [ ] **Step 3: Rewrite every import of `rag` repo-wide**

```bash
scripts/_rename_pkg_imports.sh rag agent.rag
```

Expected: `Rewrote 9 file(s): rag -> agent.rag`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+rag(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/agent/rag/ -v
```

Expected: `test_rag_agent.py` and `test_viz`-related assertions inside it may still reference `viz`/`problem_gen` by their old dotted names until Tasks 13–14 run — if any test in this file fails specifically on a `viz.` or `problem_gen.` import error (not a `rag.`-related one), that's expected at this point in the sequence; confirm the failure message names `viz` or `problem_gen`, not `rag`, before proceeding. All other tests must pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- agent/rag tests/agent/rag $(grep -rlE "agent\.rag" --include="*.py" . | grep -v "^./agent/rag/\|^./tests/agent/rag/")
git commit -m "refactor: move rag/ to agent/rag/"
```

---

## Task 13: Move `viz/` → `agent/viz/`

**Files:**
- Move: `viz/*.py`, `viz/templates/*.py` → `agent/viz/*.py`, `agent/viz/templates/*.py` (`example_store.py`, `llm_fallback.py`, `viz_agent.py`, plus `templates/__init__.py`, `templates/convergence.py`, `templates/distributions.py`, `templates/gradient_descent.py`, `templates/spectral_decomposition.py`)
- Move+rename tests: `tests/test_example_store.py`, `tests/test_llm_fallback.py`, `tests/test_viz_agent.py`, `tests/test_viz_templates.py` → `tests/agent/viz/`
- Modify: every file with `from viz...` / `import viz...` (12 files found via search — includes `rag/rag_agent.py`, already at `agent/rag/rag_agent.py` after Task 12)

**Interfaces:**
- Produces: `agent.viz.viz_agent`, `.llm_fallback`, `.example_store`, `.templates.*`.
- Consumes: `core.env.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv viz agent/viz
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/agent/viz
git mv tests/test_example_store.py tests/agent/viz/test_example_store.py
git mv tests/test_llm_fallback.py tests/agent/viz/test_llm_fallback.py
git mv tests/test_viz_agent.py tests/agent/viz/test_viz_agent.py
git mv tests/test_viz_templates.py tests/agent/viz/test_viz_templates.py
```

- [ ] **Step 3: Rewrite every import of `viz` repo-wide**

```bash
scripts/_rename_pkg_imports.sh viz agent.viz
```

Expected: `Rewrote 12 file(s): viz -> agent.viz`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+viz(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests, plus rag's tests again now that viz is fixed**

```bash
python -m pytest tests/agent/viz/ tests/agent/rag/ -v
```

Expected: all pass (this also confirms Task 12's deferred `viz`-import failure, if any, is now resolved).

- [ ] **Step 6: Commit**

```bash
git add -A -- agent/viz tests/agent/viz $(grep -rlE "agent\.viz" --include="*.py" . | grep -v "^./agent/viz/\|^./tests/agent/viz/")
git commit -m "refactor: move viz/ to agent/viz/"
```

---

## Task 14: Move `problem_gen/` → `agent/problem_gen/`

**Files:**
- Move: `problem_gen/*.py` → `agent/problem_gen/*.py` (2 modules: `generator.py`, `llm_gen.py`)
- Move+rename tests: `tests/test_generator.py`, `tests/test_llm_gen.py` → `tests/agent/problem_gen/`
- Modify: every file with `from problem_gen...` / `import problem_gen...` (4 files found via search — includes `agent/rag/rag_agent.py`)

**Interfaces:**
- Produces: `agent.problem_gen.generator`, `.llm_gen`.
- Consumes: `core.env.*`, `core.indexer.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv problem_gen agent/problem_gen
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/agent/problem_gen
git mv tests/test_generator.py tests/agent/problem_gen/test_generator.py
git mv tests/test_llm_gen.py tests/agent/problem_gen/test_llm_gen.py
```

- [ ] **Step 3: Rewrite every import of `problem_gen` repo-wide**

```bash
scripts/_rename_pkg_imports.sh problem_gen agent.problem_gen
```

Expected: `Rewrote 4 file(s): problem_gen -> agent.problem_gen`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+problem_gen(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests, plus rag's tests again**

```bash
python -m pytest tests/agent/problem_gen/ tests/agent/rag/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- agent/problem_gen tests/agent/problem_gen $(grep -rlE "agent\.problem_gen" --include="*.py" . | grep -v "^./agent/problem_gen/\|^./tests/agent/problem_gen/")
git commit -m "refactor: move problem_gen/ to agent/problem_gen/"
```

---

## Task 15: Move `problem_corpus/` → `agent/problem_corpus/`

**Files:**
- Move: `problem_corpus/*.py` → `agent/problem_corpus/*.py` (3 modules: `boundaries.py`, `extractor.py`, `llm_extract.py`, `store.py`)
- Move+rename tests: `tests/test_boundaries.py`, `tests/test_extractor.py`, `tests/test_llm_extract.py`, `tests/test_store.py` → `tests/agent/problem_corpus/`
- Modify: every file with `from problem_corpus...` / `import problem_corpus...` (5 files found via search)

**Interfaces:**
- Produces: `agent.problem_corpus.extractor`, `.llm_extract`, `.boundaries`, `.store`.
- Consumes: `core.env.*`, `core.indexer.*` (already rewritten).

- [ ] **Step 1: Move the package directory**

```bash
git mv problem_corpus agent/problem_corpus
```

- [ ] **Step 2: Move and rename its tests**

```bash
mkdir -p tests/agent/problem_corpus
git mv tests/test_boundaries.py tests/agent/problem_corpus/test_boundaries.py
git mv tests/test_extractor.py tests/agent/problem_corpus/test_extractor.py
git mv tests/test_llm_extract.py tests/agent/problem_corpus/test_llm_extract.py
git mv tests/test_store.py tests/agent/problem_corpus/test_store.py
```

- [ ] **Step 3: Rewrite every import of `problem_corpus` repo-wide**

```bash
scripts/_rename_pkg_imports.sh problem_corpus agent.problem_corpus
```

Expected: `Rewrote 5 file(s): problem_corpus -> agent.problem_corpus`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+problem_corpus(\.|[[:space:]])" --include="*.py" .
```

Expected: no output.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/agent/problem_corpus/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- agent/problem_corpus tests/agent/problem_corpus $(grep -rlE "agent\.problem_corpus" --include="*.py" . | grep -v "^./agent/problem_corpus/\|^./tests/agent/problem_corpus/")
git commit -m "refactor: move problem_corpus/ to agent/problem_corpus/"
```

---

## Task 16: Move cross-package bridge scripts into `tools/`

**Files:**
- Move: `audit_metadata.py`, `reconcile_needs_manual.py` → `tools/`
- Move+rename tests: `tests/test_audit_metadata.py`, `tests/test_reconcile_needs_manual.py` → `tests/tools/`
- Modify: `reconcile_needs_manual.py` imports `audit_metadata` directly (check and fix), plus any doc that references either script by its old root-level path

**Interfaces:**
- Produces: `tools.audit_metadata`, `tools.reconcile_needs_manual`.
- Consumes: `discovery.discover_journal_articles.*` (Task 11), `pipelines.convert_journal_articles.*` (Task 8) — both already rewritten by the time this task runs.

- [ ] **Step 1: Check how `reconcile_needs_manual.py` invokes `audit_metadata.py`**

```bash
grep -n "audit_metadata" reconcile_needs_manual.py
```

If it's a subprocess/CLI call (e.g. `python -m audit_metadata ...` or a direct `subprocess.run([...])`), note the exact invocation string to update in Step 3. If it's a Python import (`from audit_metadata import ...`), it will be caught by Step 3's rewrite automatically since `audit_metadata` is one of the two packages moving in this same task — but a bare-module invocation string (module path inside a subprocess call, not a top-of-line import) needs a manual fix since the helper script only rewrites import statements.

- [ ] **Step 2: Move the scripts and their tests**

```bash
mkdir -p tools
git mv audit_metadata.py tools/audit_metadata.py
git mv reconcile_needs_manual.py tools/reconcile_needs_manual.py
mkdir -p tests/tools
git mv tests/test_audit_metadata.py tests/tools/test_audit_metadata.py
git mv tests/test_reconcile_needs_manual.py tests/tools/test_reconcile_needs_manual.py
```

- [ ] **Step 3: Rewrite every import of `audit_metadata` and `reconcile_needs_manual` repo-wide**

```bash
scripts/_rename_pkg_imports.sh audit_metadata tools.audit_metadata
scripts/_rename_pkg_imports.sh reconcile_needs_manual tools.reconcile_needs_manual
```

If Step 1 found a subprocess-style invocation (e.g. `"python", "-m", "audit_metadata"`), fix that string manually now to `"tools.audit_metadata"`.

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -rlE "^[[:space:]]*(from|import)[[:space:]]+(audit_metadata|reconcile_needs_manual)(\.|[[:space:]])" --include="*.py" .
grep -rn "python -m audit_metadata\|python -m reconcile_needs_manual" --include="*.py" --include="*.md" .
```

Expected: first command no output; second command either no output or only matches already updated to `tools.audit_metadata` / `tools.reconcile_needs_manual`.

- [ ] **Step 5: Run the moved tests**

```bash
python -m pytest tests/tools/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add -A -- tools tests/tools $(grep -rlE "tools\.(audit_metadata|reconcile_needs_manual)" --include="*.py" . | grep -v "^./tools/\|^./tests/tools/")
git commit -m "refactor: move audit_metadata.py and reconcile_needs_manual.py into tools/"
```

---

## Task 17: `resume_manager/` test relocation and instructions merge (no code move)

`resume_manager/` keeps its top-level path and dotted import name — nothing under it needs an import rewrite. Only its tests move to mirror the new tree, and its root-level instructions file merges into its README.

**Files:**
- Move+rename tests: `tests/test_apply_from_prompt.py`, `tests/test_convert_resume.py`, `tests/test_markdown_sync.py`, `tests/test_merge_resumes.py`, `tests/test_resume_extract.py`, `tests/test_resume_fact_diff.py`, `tests/test_resume_llm_yaml.py`, `tests/test_resume_manager_package.py`, `tests/test_resume_normalize.py`, `tests/test_resume_render.py`, `tests/test_resume_schema.py`, `tests/test_resume_tailor.py`, `tests/test_resume_validate.py`, `tests/test_sync_master_md.py`, `tests/test_sync_tailored_md.py`, `tests/test_tailor_resume_cli.py` → `tests/resume_manager/`
- Merge: `resume_manager_instructions.md` into `resume_manager/README.md`

**Interfaces:**
- Produces: nothing new — `resume_manager.*` dotted paths are unchanged.
- Consumes: nothing.

- [ ] **Step 1: Move and rename the tests**

```bash
mkdir -p tests/resume_manager
git mv tests/test_apply_from_prompt.py tests/resume_manager/test_apply_from_prompt.py
git mv tests/test_convert_resume.py tests/resume_manager/test_convert_resume.py
git mv tests/test_markdown_sync.py tests/resume_manager/test_markdown_sync.py
git mv tests/test_merge_resumes.py tests/resume_manager/test_merge_resumes.py
git mv tests/test_resume_extract.py tests/resume_manager/test_resume_extract.py
git mv tests/test_resume_fact_diff.py tests/resume_manager/test_resume_fact_diff.py
git mv tests/test_resume_llm_yaml.py tests/resume_manager/test_resume_llm_yaml.py
git mv tests/test_resume_manager_package.py tests/resume_manager/test_resume_manager_package.py
git mv tests/test_resume_normalize.py tests/resume_manager/test_resume_normalize.py
git mv tests/test_resume_render.py tests/resume_manager/test_resume_render.py
git mv tests/test_resume_schema.py tests/resume_manager/test_resume_schema.py
git mv tests/test_resume_tailor.py tests/resume_manager/test_resume_tailor.py
git mv tests/test_resume_validate.py tests/resume_manager/test_resume_validate.py
git mv tests/test_sync_master_md.py tests/resume_manager/test_sync_master_md.py
git mv tests/test_sync_tailored_md.py tests/resume_manager/test_sync_tailored_md.py
git mv tests/test_tailor_resume_cli.py tests/resume_manager/test_tailor_resume_cli.py
```

- [ ] **Step 2: Merge the instructions doc into the package README**

Read `resume_manager/README.md` and `resume_manager_instructions.md` in full. Append the instructions content under `## Full usage guide`, preserving all content. Then:

```bash
git rm resume_manager_instructions.md
```

- [ ] **Step 3: Run the moved tests**

```bash
python -m pytest tests/resume_manager/ -v
```

Expected: all pass unchanged (no import paths changed, only file locations — `conftest.py` puts the repo root on `sys.path` regardless of where the test file itself lives).

- [ ] **Step 4: Commit**

```bash
git add -A -- tests/resume_manager resume_manager/README.md
git commit -m "chore: relocate resume_manager tests to tests/resume_manager/, merge instructions"
```

---

## Task 18: `audio_generator/` test relocation (no code move)

**Files:**
- Move+rename tests: `tests/test_audio_generator_discovery.py`, `tests/test_audio_generator_narrate.py`, `tests/test_audio_generator_pipeline.py`, `tests/test_cleaner.py`, `tests/test_engine.py`, `tests/test_sections.py`, `tests/test_state.py` → `tests/audio_generator/`

**Interfaces:**
- Produces: nothing new — `audio_generator.*` dotted paths are unchanged.
- Consumes: nothing.

- [ ] **Step 1: Move and rename the tests**

```bash
mkdir -p tests/audio_generator
git mv tests/test_audio_generator_discovery.py tests/audio_generator/test_audio_generator_discovery.py
git mv tests/test_audio_generator_narrate.py tests/audio_generator/test_audio_generator_narrate.py
git mv tests/test_audio_generator_pipeline.py tests/audio_generator/test_audio_generator_pipeline.py
git mv tests/test_cleaner.py tests/audio_generator/test_cleaner.py
git mv tests/test_engine.py tests/audio_generator/test_engine.py
git mv tests/test_sections.py tests/audio_generator/test_sections.py
git mv tests/test_state.py tests/audio_generator/test_state.py
```

- [ ] **Step 2: Run the moved tests**

```bash
python -m pytest tests/audio_generator/ -v
```

Expected: all pass unchanged.

- [ ] **Step 3: Commit**

```bash
git add -A -- tests/audio_generator
git commit -m "chore: relocate audio_generator tests to tests/audio_generator/"
```

---

## Task 19: Reorganize `docs/` into per-package subfolders

Every code move is done by this point. This task subfolders `docs/status/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`, and `docs/brainstorms/` by the package each file is about, using the new package names. Files that genuinely span multiple packages stay unnested at the doc-type folder's root. `docs/trackers/` stays as-is (inherently cross-cutting).

**Files:** all files under `docs/status/`, `docs/superpowers/specs/`, `docs/superpowers/plans/`, `docs/brainstorms/` — moved via `git mv`, none edited.

**Interfaces:** none — pure doc reorganization, no code depends on these paths.

- [ ] **Step 1: Create the per-package subfolders and move `docs/status/`**

```bash
cd docs/status
mkdir -p convert_textbook transcribe_notes convert_essays convert_journal_articles discover_journal_articles postprocess_notes generate_video_notes indexer agent/rag agent/viz agent/problem_gen agent/problem_corpus resume_manager audio_generator
git mv 2026-08-22-chapter-aware-chunking-status.md convert_textbook/
git mv 2026-08-23-image-description-status.md convert_textbook/
git mv 2026-09-10-textbook-conversion-status.md convert_textbook/
git mv 2026-08-24-notes-transcription-status.md transcribe_notes/
git mv 2026-08-27-notes-postprocessing-status.md postprocess_notes/
git mv 2026-08-29-source-indexer-status.md indexer/
git mv 2026-08-30-rag-agent-status.md agent/rag/
git mv 2026-09-27-tutor-diagnosis-status.md agent/rag/
git mv 2026-09-01-journal-article-transcription-status.md convert_journal_articles/
git mv 2026-09-01-journal-discovery-status.md discover_journal_articles/
git mv 2026-09-01-research-notes-conversion-status.md convert_essays/
git mv 2026-09-02-visualization-agent-status.md agent/viz/
git mv 2026-09-05-problem-generation-status.md agent/problem_gen/
git mv 2026-09-06-problem-corpus-extraction-status.md agent/problem_corpus/
git mv 2026-09-06-video-lecture-notes-status.md generate_video_notes/
git mv 2026-09-09-audio-generator-status.md audio_generator/
git mv 2026-09-09-resume-manager-status.md resume_manager/
cd ../..
```

Left unnested at `docs/status/` root (cross-cutting, not tied to one package): `2026-09-21-obsidian-git-sync-status.md`, `2026-09-26-obsidian-git-sync-status.md`, `2026-09-23-agent-routing-status.md`, `2026-09-27-agent-routing-status.md`.

- [ ] **Step 2: Move `docs/superpowers/specs/`**

```bash
cd docs/superpowers/specs
mkdir -p convert_textbook transcribe_notes convert_journal_articles discover_journal_articles postprocess_notes generate_video_notes indexer agent/rag agent/viz agent/problem_gen agent/problem_corpus resume_manager audio_generator tools
git mv 2026-08-19-textbook-chunking-and-page-tracking-design.md convert_textbook/
git mv 2026-09-20-textbook-conversion-skill-design.md convert_textbook/
git mv 2026-09-20-textbook-conversion-walkaway-execution-design.md convert_textbook/
git mv 2026-09-20-vm-ram-sizing-logging-design.md convert_textbook/
git mv 2026-09-09-excalidraw-notes-transcription-design.md transcribe_notes/
git mv 2026-08-26-notes-postprocessing-design.md postprocess_notes/
git mv 2026-08-27-source-indexer-design.md indexer/
git mv 2026-08-29-passage-embeddings-design.md indexer/
git mv 2026-09-17-cross-course-duplicate-textbook-detection-design.md indexer/
git mv 2026-08-30-rag-agent-design.md agent/rag/
git mv 2026-09-27-tutor-diagnosis-design.md agent/rag/
git mv 2026-08-31-journal-discovery-design.md discover_journal_articles/
git mv 2026-09-02-journal-discovery-snowball-design.md discover_journal_articles/
git mv 2026-09-02-visualization-agent-design.md agent/viz/
git mv 2026-09-03-viz-example-store-design.md agent/viz/
git mv 2026-09-03-viz-ollama-retry-hardening-design.md agent/viz/
git mv 2026-09-03-problem-generation-design.md agent/problem_gen/
git mv 2026-09-06-problem-corpus-extraction-design.md agent/problem_corpus/
git mv 2026-09-06-video-lecture-notes-design.md generate_video_notes/
git mv 2026-09-06-audio-generator-design.md audio_generator/
git mv 2026-09-09-resume-manager-design.md resume_manager/
git mv 2026-09-02-metadata-folder-audit-design.md tools/
cd ../../..
```

Left unnested at `docs/superpowers/specs/` root (cross-cutting): `2026-09-05-combined-report-design.md`, `2026-09-20-pipeline-autonomy-policies-design.md`, `2026-09-21-source-asset-relocation-brainstorm-addendum.md`, `2026-09-21-source-asset-relocation-design.md`, `2026-09-29-academic-rag-model-restructure-design.md` (this reorg's own spec — about the whole tree, not one package).

- [ ] **Step 3: Move `docs/superpowers/plans/`**

```bash
cd docs/superpowers/plans
mkdir -p convert_textbook transcribe_notes discover_journal_articles agent/rag agent/viz agent/problem_gen agent/problem_corpus generate_video_notes resume_manager indexer
git mv 2026-08-20-chapter-aware-chunking.md convert_textbook/
git mv 2026-08-20-vm-validation-checklist.md convert_textbook/
git mv 2026-09-20-oom-cost-escalation-ladder.md convert_textbook/
git mv 2026-09-20-rebuild-safety-fix.md convert_textbook/
git mv 2026-09-20-vm-ram-sizing-logging.md convert_textbook/
git mv 2026-09-21-source-asset-relocation.md convert_textbook/
git mv 2026-09-09-excalidraw-notes-transcription.md transcribe_notes/
git mv 2026-08-26-notes-postprocessing.md transcribe_notes/
git mv 2026-08-28-source-indexer-core.md indexer/
git mv 2026-08-28-source-indexer-retag.md indexer/
git mv 2026-08-29-passage-embeddings.md indexer/
git mv 2026-09-17-cross-course-duplicate-textbook-detection.md indexer/
git mv 2026-09-20-duplicate-auto-resolution.md indexer/
git mv 2026-08-30-rag-agent.md agent/rag/
git mv 2026-09-27-tutor-diagnosis-plan.md agent/rag/
git mv 2026-09-01-journal-discovery-plan.md discover_journal_articles/
git mv 2026-09-02-journal-discovery-snowball-plan.md discover_journal_articles/
git mv 2026-09-02-visualization-agent.md agent/viz/
git mv 2026-09-03-viz-example-store.md agent/viz/
git mv 2026-09-03-viz-ollama-retry-hardening.md agent/viz/
git mv 2026-09-03-problem-generation-plan.md agent/problem_gen/
git mv 2026-09-06-problem-corpus-extraction.md agent/problem_corpus/
git mv 2026-09-06-video-lecture-notes.md generate_video_notes/
git mv 2026-09-06-audio-generator.md audio_generator 2>/dev/null || mkdir -p audio_generator && git mv 2026-09-06-audio-generator.md audio_generator/
git mv 2026-09-09-resume-manager-plan.md resume_manager/
git mv 2026-09-26-resume-manager-page-fit-plan.md resume_manager/
git mv 2026-09-27-apply-from-prompt-plan.md resume_manager/
cd ../../..
```

Left unnested at `docs/superpowers/plans/` root (cross-cutting): `2026-09-02-metadata-folder-audit-plan.md` (tools/ bridge — create a `tools/` subfolder for it like specs did, or leave unnested; leave unnested here since there's exactly one file), `2026-09-05-combined-report.md`.

- [ ] **Step 4: Move `docs/brainstorms/`**

```bash
cd docs/brainstorms
mkdir -p audio_generator resume_manager agent/rag
git mv audio_generator_brainstorm.md audio_generator/
git mv resume_manager_brainstorm.md resume_manager/
git mv 2026-09-06-research-rag-design.md agent/rag/
cd ../..
```

Left unnested at `docs/brainstorms/` root (cross-cutting, span the whole hub not one package): `Academic Hub Progress Reflections.md`, `Improving Teaching and AI Enabled Pedagogy.md`.

- [ ] **Step 5: Verify every file moved (none silently left behind)**

```bash
find docs/status docs/superpowers/specs docs/superpowers/plans docs/brainstorms -maxdepth 1 -name "*.md"
```

Compare this output against the "left unnested" lists in Steps 1–4 above — anything else listed here means a file was missed and needs to move into its matching package subfolder.

- [ ] **Step 6: Commit**

```bash
git add -A -- docs/status docs/superpowers/specs docs/superpowers/plans docs/brainstorms
git commit -m "docs: subfolder status/specs/plans/brainstorms by package"
```

---

## Task 20: Root reference cleanup, helper script removal, full verification

**Files:**
- Modify: `README.md`, `CLAUDE.md` (both in `academic-rag-model/`)
- Delete: `scripts/_rename_pkg_imports.sh` (migration is done, no longer needed)

**Interfaces:** none — final integration task.

- [ ] **Step 1: Rewrite `README.md`'s repository-layout section**

Read the current `README.md` in full. Update the "Repository layout" bullet list (and every `[`link`](path)` inside it) to reference the new paths: `core/env/`, `core/indexer/`, `pipelines/convert_textbook/`, `pipelines/transcribe_notes/`, `pipelines/convert_essays/`, `pipelines/convert_journal_articles/`, `discovery/discover_journal_articles/`, `pipelines/postprocess_notes/`, `agent/rag/`, `agent/viz/`, `agent/problem_gen/`, `agent/problem_corpus/`, `pipelines/generate_video_notes/`, `resume_manager/` (unchanged), `tools/` (new — mention the two bridge scripts), `tests/` (note it now mirrors the package tree), `docs/` (note it's subfoldered by package within each doc-type folder), `archive/old_attempts/` (was `old_attempts/`). Also fix every `python -m <old>.` example command in the file (e.g. `python -m notes.transcribe_notes` → `python -m pipelines.transcribe_notes.transcribe_notes`, `python -m indexer.index_search` → `python -m core.indexer.index_search`).

- [ ] **Step 2: Rewrite `CLAUDE.md`**

Read the current `CLAUDE.md` in full. Update:
- The `python -m notes.transcribe_notes ...` / `python -m indexer.index_search ...` example commands to their new dotted paths.
- "`tests/` is flat, not mirrored by package" → describe the new mirrored structure instead.
- "`common/` and `indexer/` are shared by everything" → `core/env/` and `core/indexer/`.
- "Ignore `old_attempts/`" → `archive/old_attempts/`.
- "Design history lives in `docs/status/<date>-<subproject>-status.md` ... and `docs/superpowers/{specs,plans}/`" → note these are now subfoldered by package name (e.g. `docs/status/<package>/<date>-*.md`), still latest-date-wins within a package's subfolder.

- [ ] **Step 3: Remove the migration helper script**

```bash
git rm scripts/_rename_pkg_imports.sh
rmdir scripts 2>/dev/null || true
```

- [ ] **Step 4: Grep for any remaining old-name import anywhere in the repo**

```bash
for pkg in textbook notes essays journal_articles journal_discovery postprocessing video_notes common indexer rag viz problem_gen problem_corpus audit_metadata reconcile_needs_manual; do
  echo "=== $pkg ==="
  grep -rlE "^[[:space:]]*(from|import)[[:space:]]+${pkg}(\.|[[:space:]])" --include="*.py" .
done
```

Expected: every `=== pkg ===` section has no output beneath it.

- [ ] **Step 5: Grep test files for hardcoded old-path strings**

```bash
grep -rln "tests/test_\|Path(__file__)" tests/ | xargs grep -l "old_attempts\|/notes/\|/essays/\|/journal_articles/\|/journal_discovery/\|/postprocessing/\|/video_notes/\|/common/\|/indexer/\|/textbook/" 2>/dev/null
```

Expected: no output. Any hit is a hardcoded path string (not a Python import, so the helper script wouldn't have caught it) that needs a manual fix in that file before proceeding.

- [ ] **Step 6: Grep docs/READMEs for dangling relative links to moved files or directories**

```bash
grep -rn "notes_instructions\.md\|essays_instructions\.md\|journal_articles_instructions\.md\|journal_discovery_instructions\.md\|resume_manager_instructions\.md\|convert_textbook_instructions\.md\|convert_textbook_agent_instructions\.md" --include="*.md" .
grep -rnE "\]\(\.?\.?/?(textbook|notes|essays|journal_articles|journal_discovery|postprocessing|video_notes|common|indexer|rag|viz|problem_gen|problem_corpus|old_attempts)/" --include="*.md" .
```

Expected: no output from either. The first catches the six merged instruction filenames; the second catches any markdown relative link (in any package's own README, not just the root one — e.g. `convert_journal_articles/README.md` linking to `../notes/` when it should now say `../transcribe_notes/`) still pointing at an old directory name. Fix every hit by hand: read the linking file, confirm the intended target under its new path, and update the link text and path together.

- [ ] **Step 7: Run the full test suite**

```bash
python -m pytest tests/ -v
```

Expected: every test passes. This is the final proof the entire move is behavior-neutral.

- [ ] **Step 8: Confirm the spec's success criteria**

```bash
ls old_attempts 2>/dev/null; ls preview.txt 2>/dev/null
find . -maxdepth 1 -name "*_instructions.md"
find . -maxdepth 1 -maxdepth 1 -type d ! -name ".*" ! -name "__pycache__"
```

Expected: first two commands report "No such file or directory" (both gone from the root); third command has no output (no orphaned `*_instructions.md` at root); fourth command's directory listing matches the spec's target tree (`pipelines/`, `discovery/`, `agent/`, `core/`, `resume_manager/`, `audio_generator/`, `tools/`, `tests/`, `docs/`, `archive/`).

- [ ] **Step 9: Commit**

```bash
git add -A -- README.md CLAUDE.md
git commit -m "docs: update README/CLAUDE.md for the new directory structure, remove migration helper"
```
