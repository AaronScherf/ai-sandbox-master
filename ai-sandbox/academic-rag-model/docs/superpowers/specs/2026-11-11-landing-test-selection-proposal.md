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

1. **Outside-project paths never force a run.** Paths outside `ai-sandbox/academic-rag-model/` are not importable by the suite unless a test reads them. Drop the two `outside` rules (`non_py_file`, `unmapped_file` for outside paths) from the full-suite triggers. Add a new reason `outside_project_only` that skips tests when every changed path is outside the project and none is on an allowlist of paths tests read (enumerated below from a grep of `tests/`).
2. **Data files inside the project map to their readers.** A changed `.json`/`.txt`/`.ps1` inside the project falls under the nearest package that has a test directory (`tests/<pkg>`), instead of `non_py_file`. If the file is in no package, run `tests/tools` only.
3. **`core/` changes run `tests/core` plus the packages that import the changed module**, instead of everything. Keep the full suite when `conftest.py` or a top-level helper changes.
4. **Keep the full suite for:** `--full`, changes to `tools/land_branch.py` or `tools/guard_binaries.py` and the other `GUARD_POLICY_PATHS`, a dependency pin, and pytest config.
5. **Safety net (revised 2026-11-16): no full run per landing for non-code changes.** A change no test reads cannot fail a test, so a full run after it repeats the last run on `main`. The risk is only that the allowlist (rule 1) is incomplete, and that is covered two cheaper ways:
   - **Allowlist guard test.** A test scans `tests/` for filesystem reads above the project root and fails if one is not on the allowlist. A new dependency is caught when its test is written, not after a landing.
   - **Scheduled full run.** One full chunked run of `main` nightly or weekly, independent of landings, logged as `{"event": "scheduled_full", ...}` and surfaced in `tools.landing_metrics`. It catches drift from any cause.
   - Code landings that ran targeted tests (`targeted`, `targeted_multi`, `core_change`) may still get a background full run afterwards. `outside_project_only` and `doc_only` landings never do.
6. **One dependency list, two uses.** The allowlist is a single constant. It replaces `RETEST_OUTSIDE_PATHS`, so the check step and the land-time re-test (`_run_land`) agree on which outside paths matter. Today `main` gaining a new `hub_config.json` would not trigger a re-test.

### Allowlist: outside-project paths tests read (grep of `tests/`, 2026-11-16)

| Path | Read by |
|---|---|
| `.gitignore` (root) | `test_lit_gap_report.py` |
| `ai-sandbox/.obsidian/` | `test_audit_website_sync.py` (per the existing comment in `land_branch.py`; not re-verified) |
| `ai-sandbox/academic-hub/hub_config.json` | `core/env/hub_vocabulary.py` default config; any test not using the `seed_hub_config` fixture |
| `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Summary - v3.md` | `test_reference_checker.py` |
| `GUARD_POLICY_PATHS` (guard files, `.githooks/pre-commit`) | already forced to a full run by rule 4 |

Not inputs: `ai-sandbox/academic-hub/.index/**`, hub Markdown, PDFs and notes. Tests use temp-dir fixtures, including the cross-course retrieval tests. `test_document_pairing.py` and `test_offering_links.py` only assert the hub directory exists. The hub Excalidraw scripts are read by two `.cjs` tests that pytest and the chunked runner do not invoke, so they stay off the list. This is a grep result, so it can miss runtime-built paths; the guard test in rule 5 is the backstop.

## Daily-workflow acceptance (the objective)

The aim is to make routine non-code work cheap. Each case below must be selected as shown, and the first is the logged case that took 912.8 s.

| Change | Expected reason | Tests run |
|---|---|---|
| One PDF transcribed: hub `.md` plus `.index/courses.json` and `.index/<course>.json` | `outside_project_only` | none |
| Hub notes, summaries, study guides, `.rag.md` | `outside_project_only` | none |
| Research-repo pin or notes not on the allowlist | `outside_project_only` | none |
| `docs/status/` or `docs/superpowers/` Markdown | `doc_only` | none |
| `hub_config.json` or the Novelty Check note | `allowlist_hit` | targeted by the reader where mappable, else full |
| `docs/trackers/subproject_registry.json` (in project, no package) | `tests/tools` only | `tests/tools` |
| Edit to `land_branch.py`, guard files, `conftest.py`, pins, pytest config | full | full |

Target: the daily cases in the first four rows take seconds, not 16 minutes. Replaying the logged history should show about 256 of 336 minutes saved.

Expected effect on the 47 logged checks: rule 1 alone removes about 256 minutes of 336 (76%), with no change for code branches.

## Interference between agents (separate from speed)

The log shows 12 of 47 checks with overlapping changes and 13 rebases. Test selection does not fix this. Candidate fixes, to evaluate separately: refuse `check` while another branch with the same changed paths is unlanded (already detected by `find_overlaps`, but only reported), and make the overlap report block rather than warn when a branch touches `.index/` or other shared generated files.

## Open questions for the owner

- ~~Is a post-landing full run on `main` an acceptable replacement for pre-landing full runs on non-code changes?~~ Resolved 2026-11-16: no per-landing full run for non-code changes at all; guard test plus scheduled run instead (rule 5). Owner objective: speed up daily non-code work.
- ~~Which outside-project paths do you consider "read by tests"?~~ First draft answered by grep, see the allowlist table. Owner to confirm.

## Verification plan (for the implementer)

- Unit tests for `selection_reason` with fixtures drawn from the 15 logged cases (an outside-only `.json` change, a `.docx` move, a research-repo pin) asserting `outside_project_only`, and one fixture where a branch edits `tools/guard_binaries.py` and still gets the full suite.
- Replay the logged `changed_*` fields through the new rules and compare the new selection with the old one.
