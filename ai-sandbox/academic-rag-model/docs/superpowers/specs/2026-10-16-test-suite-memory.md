# Test Suite Memory / OOM Fix Design

**Status:** Decided 2026-10-16 (chunk granularity, jsonschema fix scope, and CLAUDE.md doc update all confirmed). Implementation tracked in the plan of the same date.
**Date:** 2026-10-16
**Scope:** `academic-rag-model`'s pytest suite (`tests/`) and its landing-gate caller, `tools/land_branch.py`.
**Source:** Live debugging session 2026-10-16 (see conversation; not yet written to a status doc).

## 1. Problem

A plain `python -m pytest tests/ -q` run (no xdist, no extra tooling) on this machine
drove system available memory from ~2.2 GB down past the point where Claude Code's own
background-task OOM guard killed a monitoring process watching it. The run had reached
98% of its ~2,230 tests when killed. The user reports this fails outright (true OOM,
not just a guard trip) occasionally during normal work.

`tools/land_branch.py:run_checks()` runs exactly this invocation — one `pytest tests/ -q`
subprocess — as the full-suite landing gate (`full=True` path, `tools/land_branch.py:170-181`).
That is the place this bites hardest, since landing is the one case that can't just run a
changed-package subset (`docs/trackers/academic_hub_to_do.md` decision 7).

## 2. Root cause investigation

**Confirmed:**
- `pytest-xdist` is not installed. The suite runs as one long-lived Python process, serially.
  Parallelism is not the cause.
- The host has very little free memory to begin with (~2.2 GB available before the run even
  starts) and the available-memory figure fell gradually and continuously through the run — not
  a single spike at one file. This points to cumulative retention across the one process's
  lifetime (fixtures, imports, GC lag) compounding an already-tight host, not one pathological test.
- `tests/` mirrors the full package tree: `agent/`, `audio_generator/`, `core/`, `discovery/`,
  `pipelines/`, `resume_manager/`, `tools/` — 100+ files, ~2,230 collected items.
- Separately: the venv has drifted from `requirements.txt` — `jsonschema` is missing, which
  aborts collection of `tests/tools/test_audit_website_sync.py`,
  `tests/tools/test_audit_website_sync_git.py`, and `tests/tools/test_website_sync_scan.py`
  with `ModuleNotFoundError`. Unrelated to the OOM; tracked separately in section 6.

**Ruled out (checked, not assumed):**
- `transformers`, `faster-whisper`, `onnxruntime` (direct), `piper`, `kokoro_onnx` are **all
  already lazily imported inside function bodies**, not at module top level (e.g.
  `audio_generator/engine.py:36,45`, `pipelines/generate_video_notes/transcribe.py:31`,
  `pipelines/postprocess_notes/local_model_scoring.py:34,45`, with an explicit comment at
  `transcribe.py:4` confirming this was deliberate). Every test that touches these modules
  patches the exact lazy-import call site (e.g.
  `@patch("audio_generator.engine._synthesize_piper_wav")`,
  `@patch("faster_whisper.WhisperModel")`), so the real heavy library is never imported during
  the test run today. **This is good existing practice — the local-model packages are not
  currently a test-time memory cost.**
- `local_model_scoring.py` (the one module that does local-LLM-style scoring —
  `score_causal_zscore`, `score_masked_candidates`, used by the paused causal-z-score feature
  in `postprocess_notes.py`) has **zero test coverage** anywhere in `tests/` today. There is
  nothing currently being "pruned" there because nothing currently runs it.
- `scikit-learn` (`AgglomerativeClustering`, imported eagerly at the top of
  `pipelines/generate_video_notes/grouping.py`) **does** load at collection time for any test
  file that imports `grouping.py` (`tests/pipelines/generate_video_notes/test_grouping.py` and
  anything importing the package `__init__`). This is a real, currently-active feature (video
  grouping), not an abandoned local-LLM experiment, so it is in scope for "keep testing it,"
  not for pruning.

**Net assessment:** the memory pressure is not concentrated in a prunable set of local-LLM
tests — those are already cheap. It is the combination of (a) a host with little headroom and
(b) one long-lived process running ~2,230 tests' worth of fixtures without ever releasing memory
back to the OS until the whole run ends.

## 3. Decided approach

Two independent pieces, both small:

1. **Chunk the full-suite run into subprocesses, one per top-level `tests/` package
   directory**, so memory is actually freed (process exits) between chunks instead of
   accumulating for the whole run. This is the direct fix for the reproduced OOM and is the
   piece that's pressing.
2. **Add a `local_llm` pytest marker, excluded by default**, as forward-looking
   infrastructure: the user does not want the local-model code path deleted (it may be
   revisited on a better machine), but does not want it exercised on every default run once it
   *does* get test coverage again. Today this marker has zero tests to apply it to — it's a
   convention + default-exclusion wired up now so the next person adding a real
   `score_causal_zscore`/`score_masked_candidates` test (which would load real `transformers`
   models) does it correctly from the start, without being told.

Chunk boundaries: the seven top-level dirs under `tests/` — `agent`, `audio_generator`, `core`,
`discovery`, `pipelines`, `resume_manager`, `tools`. Coarse enough that subprocess-startup
overhead (Python interpreter boot, ~100-200ms each) stays negligible against the ~107s+ total
runtime; fine enough that memory is actually released seven times over the run instead of zero.

## 4. Chunked runner

New file: `tools/run_tests_chunked.py`.

- Discovers chunks by listing immediate subdirectories of `tests/` (skips `__pycache__` and
  anything not a directory). This means new top-level test packages are picked up
  automatically — no hardcoded list to maintain.
- Runs `python -m pytest <chunk> -q -m "not local_llm"` as a **separate subprocess per chunk**
  (same pattern `run_checks` already uses: `subprocess.run([sys.executable, "-m", "pytest", ...], capture_output=True, text=True)`), in sequence, not in parallel — parallel would multiply
  peak memory instead of capping it, which is the opposite of the goal.
- Aggregates: collects each chunk's returncode, stdout tail (on failure), and wall time.
  Returns non-zero overall if any chunk failed. Prints a per-chunk summary line and, for any
  failed chunk, the same `proc.stdout[-4000:]` tail `run_checks` already prints today.
- A `--full-suite-marker` passthrough flag (default off) runs **with** `local_llm` included,
  for the rare case of validating the local-model path on a machine with more headroom. Maps
  to passing `-m local_llm` (instead of `-m "not local_llm"`) as an additional pass, not a
  replacement — so both "everything except local_llm" and "only local_llm" results are visible
  rather than one silently replacing the other.
- Callable directly (`python tools/run_tests_chunked.py`) for a human running the full suite by
  hand, and importable for `tools/land_branch.py` to call instead of its current single
  `pytest tests/ -q` subprocess when `full=True`.

## 5. `land_branch.py` integration

`run_checks()` (`tools/land_branch.py:167-186`) changes only in the `full=True` branch:
instead of
```python
targets = ["tests/"] if full else select_test_targets(changed, project_root)
...
proc = subprocess.run([sys.executable, "-m", "pytest", *targets, "-q"], ...)
```
the `full=True` case calls the chunked runner and adapts its aggregate result back into the
existing `(status, targets, seconds)` return shape the caller (`_run_check`,
`tools/land_branch.py:201-...`) already expects, so nothing downstream (the user-facing landing
summary) needs to change. The `full=False` changed-package-subset path is untouched — it's
already scoped small enough not to be the problem.

## 6. Out of scope for this spec (separate follow-ups)

- **`jsonschema` venv drift.** Already in `requirements.txt` but missing from `.venv`, breaking
  collection of 3 `tools/` test files. Real bug, unrelated to memory, but **decided: fix in this
  same branch** (`pip install -r requirements.txt` sync) — the chunked runner's `tools/` chunk
  would otherwise still fail collection regardless of the memory fix, so leaving it broken makes
  this change impossible to verify end-to-end.
- **`pytest-xdist` adoption** (existing to-do item, `docs/trackers/academic_hub_to_do.md:170`,
  never measured). Given the root cause here is memory, not CPU, parallel workers would make
  things *worse* (each worker re-imports and holds its own copy of everything) unless paired
  with a small, fixed worker count well below "auto." This spec's chunking already gets the
  memory win without that risk. The to-do item's text should be amended to note this before
  anyone acts on it.
- **Pruning or deleting the local-LLM code path itself.** Explicitly not wanted by the user —
  may be revisited on better hardware. Section 3.2's marker is the chosen middle ground
  (keep the code and the option to test it, stop paying for it by default).

## 7. Decisions from review

1. Chunk granularity: top-level `tests/<dir>` (7 chunks), as proposed in section 3 — no
   objection raised, going with the default.
2. `tools/run_tests_chunked.py` becomes the documented way to run the whole suite locally, not
   just an internal `land_branch.py` helper: update the `CLAUDE.md` "Tests:" line to mention it
   as the full-suite option, alongside the existing single-file/`-k` guidance for iteration.
3. `jsonschema` drift: fix in this same branch (section 6, updated).
