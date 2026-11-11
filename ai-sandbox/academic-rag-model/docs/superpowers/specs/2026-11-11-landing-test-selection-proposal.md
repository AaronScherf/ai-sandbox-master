# Landing test selection: stop running the full suite for changes no test can see

**Status:** proposal for owner review (2026-11-11). Nothing implemented. Implementation would go to Codex per `docs/AGENT_ROUTING.md`.
**Code:** `tools/land_branch.py` (`selection_reason`, `run_checks`, `_is_documentation_only`).

## Problem

Landing a branch runs the full chunked suite (about 16 minutes) for most non-Markdown changes. The cause is the order of rules in `selection_reason`: any changed file outside `ai-sandbox/academic-rag-model/` that is not `.py` or `.md` returns `non_py_file`, and `non_py_file` means "run everything".

## Evidence

Source: `.git/agent-landing-log.jsonl`, `check` events that carry `selection_reason` (logged since 2026-11-03): 47 checks on 34 branches.

| selection_reason | checks | total minutes | median seconds |
|---|---|---|---|
| non_py_file | 17 | 282 | 993 |
| core_change | 2 | 28 | 850 |
| targeted | 2 | 13 | 388 |
| explicit_full | 1 | 13 | 758 |
| doc_only | 25 | 0 | 0 |
| **total** | 47 | **336** | |

- `non_py_file` is 84% of all test time.
- In **15 of those 17** checks, no changed file was in a package that has tests (`changed_packages` was empty or only `docs`). The changes were research-repo pins, `.gitignore` edits, `.json` pins, reorg moves of `.docx`/`.html`/`.md`, and transcription notes. No pytest test can read them. Those 15 cost **256 of the 282 minutes**.
- The remaining 2 `non_py_file` checks changed real code (`claude/hub-folder-sync`: `pipelines`, `tests`, `tools`; `codex/excalidraw-slide-specs`: `tests` plus a `.cjs` file). A full run is defensible there, though `hub-folder-sync` would have been fine with targeted tests.
- Rebased onto a moved main in 13 of 47 checks, and `overlaps` was non-empty in 12 of 47 (26%). That is the interference signal, and it is separate from test time.

## What TODO-0095 does and does not do

TODO-0095 (run `main`'s copy of the guard) is a tamper-resistance fix. It adds no tests and removes none, so it does not affect landing time. It should proceed independently.

## Proposal

Change the selection rules so that a test is run only when the change could affect it.

1. **Outside-project paths never force a run.** Paths outside `ai-sandbox/academic-rag-model/` are not importable by the suite unless a test reads them. Drop the two `outside` rules (`non_py_file`, `unmapped_file` for outside paths) from the full-suite triggers. Add a new reason `outside_project_only` that skips tests when every changed path is outside the project and none is on an allowlist of paths tests read (`ai-sandbox/academic-hub/hub_config.json`, `.githooks/`, `.gitignore`-level files used by guard tests; to be enumerated by grepping tests for non-project reads).
2. **Data files inside the project map to their readers.** A changed `.json`/`.txt`/`.ps1` inside the project falls under the nearest package that has a test directory (`tests/<pkg>`), instead of `non_py_file`. If the file is in no package, run `tests/tools` only.
3. **`core/` changes run `tests/core` plus the packages that import the changed module**, instead of everything. Keep the full suite when `conftest.py` or a top-level helper changes.
4. **Keep the full suite for:** `--full`, changes to `tools/land_branch.py` or `tools/guard_binaries.py` and the other `GUARD_POLICY_PATHS`, a dependency pin, and pytest config.
5. **Safety net:** run the full suite on `main` in the background after each landing (or nightly), and write failures to the landing log. Selective checks trade pre-landing certainty for speed, so a post-landing full run catches what selection missed.

Expected effect on the 47 logged checks: rule 1 alone removes about 256 minutes of 336 (76%), with no change for code branches.

## Interference between agents (separate from speed)

The log shows 12 of 47 checks with overlapping changes and 13 rebases. Test selection does not fix this. Candidate fixes, to evaluate separately: refuse `check` while another branch with the same changed paths is unlanded (already detected by `find_overlaps`, but only reported), and make the overlap report block rather than warn when a branch touches `.index/` or other shared generated files.

## Open questions for the owner

- Is a post-landing full run on `main` an acceptable replacement for pre-landing full runs on non-code changes?
- Which outside-project paths do you consider "read by tests"? The first draft of that allowlist should come from `grep` over `tests/` for paths above the project root.

## Verification plan (for the implementer)

- Unit tests for `selection_reason` with fixtures drawn from the 15 logged cases (an outside-only `.json` change, a `.docx` move, a research-repo pin) asserting `outside_project_only`, and one fixture where a branch edits `tools/guard_binaries.py` and still gets the full suite.
- Replay the logged `changed_*` fields through the new rules and compare the new selection with the old one.
