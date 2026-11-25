# Claude handoff: TODO-0100, make tests hermetic against `hub_config.json` (2026-11-25)

From Claude (this session), to a fresh Claude session. Decide the approach before coding. Use a `claude/<task>` worktree per `docs/WORKTREE_WORKFLOW.md`. Landing runs the full suite for this change (it adds a top-level test helper), and the owner approves the change ID.

## Why this matters

Hub changes are the owner's daily work. `ai-sandbox/academic-hub/hub_config.json` changes whenever the owner confirms a folder, and it is on `OUTSIDE_TEST_INPUTS` (`tools/land_branch.py`), so any branch that edits it triggers a broad test run at check and land. Making the tests independent of the live file removes that cost for a common change. Tracker entry: `docs/trackers/academic_hub_to_do.md`, TODO-0100 (added 2026-11-18); read it with `grep "TODO-0100 -->"`, not the whole file.

## What is known

- `core/env/hub_vocabulary.py` (`default_config_path`) loads the live file unless `ACADEMIC_HUB_CONFIG` is set. The env var and `default_config_path` are referenced from 5 Python files (grep count, not an audit of every reader; the tracker says about 32 modules use the vocabulary).
- The only freeze today is the opt-in fixture `seed_hub_config` in `tests/core/conftest.py`, pointing at `tests/core/env/seed_hub_config.json` (the config as of `fff259ee^`, before the first owner answers). Four test files use it.
- There is no root `tests/conftest.py`. Adding one counts as a top-level test helper change (`helper_change`), so the change itself needs a full run.
- `tests/core/env/test_hub_vocabulary.py:66` loads the shipped file; this is the one test that should keep reading it.
- Hidden dependencies exist: tests that rely on owner-confirmed folders in the live file (example in the tracker: `tests/core/indexer/test_nested_layer_scenarios.py`). They fail the first time the seed is applied everywhere.
- `tests/tools/test_outside_test_inputs.py` fails when a test reads an outside path not listed in `OUTSIDE_TEST_INPUTS`, so the list and the tests must change together.

## Question to verify first

The tracker says a `hub_config.json` change selects `allowlist_hit`, the full suite. The 2026-11-11 proposal (`docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md`, the row for `hub_config.json`) says "targeted by the reader where mappable, else full", and the 2026-11-22 handoff says the change selects about 165 test files. Check what `selection_reason` actually returns today for a branch that only edits `hub_config.json` (a throwaway branch and `check`, no landing). The size of the saving, and how urgent this is, depends on the answer.

## Approach in the tracker (not yet validated)

1. A root `tests/conftest.py` autouse fixture sets `ACADEMIC_HUB_CONFIG` to the seed for every test.
2. Keep one dedicated test that validates the shipped `hub_config.json`.
3. Run the suite once; for each failure, pin what that test needs in its own fixture.
4. Drop `hub_config.json` from `OUTSIDE_TEST_INPUTS` and update `tests/tools/test_outside_test_inputs.py` and `docs/WORKTREE_LANDING.md`.

## Decisions for you

- **Scope vs payoff.** If the check selects only about 165 files rather than everything, is the full hermetic rewrite worth it, or is a narrower mapping (the reader modules to their tests) enough? Estimate fixture edits from a trial run before committing to either.
- **Seed or per-test config.** One global seed is simple but hides which tests need owner-confirmed folders. A small per-test builder makes each dependency visible. Pick one.
- **The shipped-file test.** It still reads the live file, and `hub_config.json` still needs a path that triggers it. Decide whether the dedicated test makes `hub_config.json` map to that one test (selection by reader), which would let it leave `OUTSIDE_TEST_INPUTS` cleanly.
- **Same pattern as TODO-0093.** `.gitignore`, `ai-sandbox/.obsidian` and the Novelty Check note remain on `OUTSIDE_TEST_INPUTS`. Decide whether to handle them in the same pass or leave them.

## Constraints

- Do not change `impact_selection` semantics without a test for the case first.
- A `selection_reason`, `OUTSIDE_TEST_INPUTS` or `tools/land_branch.py` edit is guard-adjacent; read the 2026-11-18 follow-ups spec and `docs/WORKTREE_LANDING.md` first.
- No API calls in tests. Run the suite with `python tools/run_tests_chunked.py`, never `pytest tests/` directly (OOM history).
- Do not mark the TODO done without evidence: a `check` on a `hub_config.json`-only branch that skips or targets only the dedicated test.

## Report back

Your answer to the verification question, the chosen approach with its trade-offs, an estimate of fixture edits, and whether to go ahead. If you implement, the branch, commit, test results, and the before and after `check` time for a `hub_config.json`-only change.
