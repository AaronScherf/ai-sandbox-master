# Landing check speed: review findings and handoff to Codex

**From:** Claude (review + design decisions). **To:** Codex (implementation).
**Reviewed:** `codex/landing-speed-impl` through `20a340e8` (steps 1-2 plus `982e949c`, `bf399b96`, `20a340e8`).
**Spec:** `2026-11-03-landing-check-speed-design.md` (same folder).
**Branch rule:** continue on `codex/landing-speed-impl`; unpublished, so rebase/amend is fine. Do not push or land; ask the owner.

Line numbers below refer to `ai-sandbox/academic-rag-model/tools/land_branch.py` at `20a340e8` unless stated.

## Do these first (correctness)

### A. Renames hide the deleted path (decision: fix in the git helper)
`tools/git_workflow.py:96` `changed_since_merge_base` runs `git diff --name-only base...ref` with rename detection on. Verified in a scratch repo (git 2.45): `git mv core/x.py agent/x.py` lists only `agent/x.py`, so `selection_reason` never sees the `core/` path and returns `targeted`.

- Add `--no-renames` to that command. It feeds `_run_check` (selection), `_run_land` `branch_files` (overlap and retest inputs) and `find_overlaps`. `change_id` is unaffected.
- Test first, in a real temp repo: a branch that `git mv`s a file from `core/` to `agent/` must give `selection_reason == "core_change"` and run the full suite. Also assert both paths appear in `changed_since_merge_base`.

### B. Outside-project files tests really read (decision: explicit list now, hermetic tests later)
The claim "no live tracked outside-project dependency" is false:
- `tests/agent/literature/test_lit_gap_report.py:124-125` reads the repo-root `.gitignore` (`parents[5]`) and asserts a line.
- `tests/tools/test_audit_website_sync.py:20,49` resolves `MONOREPO_ROOT = parents[1]` and asserts `missing_monorepo_targets(...) == []`; the registry (`docs/trackers/subproject_registry.json`) lists `ai-sandbox/.obsidian`.

Because `code_delta` (`:~412`) ignores outside paths, main deleting `ai-sandbox/.obsidian` or editing that `.gitignore` line lands with no retest while the suite is red.

- Add a module constant, e.g. `RETEST_OUTSIDE_PATHS = (".gitignore", "ai-sandbox/.obsidian")`, with a comment naming the two tests. A main-side change to any of these (prefix match) counts toward `code_delta`.
- On the branch side, such a path in `outside` already falls to the full suite (non-`.py`); keep it that way and add a test.
- Tests: main changes root `.gitignore` after approval -> `run_checks` is called; main changes unrelated outside JSON -> it is not (the existing test stays green).
- Do **not** make the two tests hermetic in this branch. Add a to-do to `academic_hub_to_do.md` (owner approves wording) so the list can be deleted later.

## Then (behavior and robustness)

### C. Retest reuses what was approved (decision)
`_run_land` (`:~418`) recomputes selection from current rules and passes only `approved.get("full", False)`. Instead, use the approved entry's `selection_reason`/`check_targets`: pass `reason=approved["selection_reason"]` to `run_checks` when present, and fall back to recomputing for legacy entries without it. Test: log an entry with reason `targeted`, patch `selection_reason` to return `core_change`, land after a project code change on main; the retest must use the logged reason.

### D. Weaker pass must not replace a stronger one (decision)
`approved_check` returns the newest passing entry for the change ID, so a later targeted pass supersedes an earlier `--full` pass. Prefer, among passing entries for the same branch and change ID, the strongest (`explicit_full` > full-suite reasons > targeted > `doc_only`/skipped); newest wins ties. Test with two entries.

### E. Real legacy-log test (replaces a vacuous one)
`tests/tools/test_landing_metrics.py:37` `test_legacy_log_fields_are_optional` passes on `main` too (`landings()` reads none of the new fields; `full_reason` never existed). Replace it with an old-format `check` entry (no `selection_reason`, `changed_*`, `chunk_timings`, `full`) run through both `approved_check` and `landings`/`summarize`; assert no exception and the legacy defaults.

### F. Empty diff (decision: keep the old behavior)
`selection_reason` returns `unmapped_file` when `changed` and `outside` are both empty (`:~199-201`), which now runs the full suite. Return `doc_only` (skip) instead, as before this branch. Add a test.

## Cleanup (no decision needed)
1. Log retest timings: pass `chunk_results` in the `_run_land` retest and add a `retest_chunk_timings` field to the `land` event (optional field; keep `LandResult` compatible).
2. `chunk_timings` entries keep only `name`, `returncode`, `seconds`; do not store `stdout` in the targeted-path `ChunkResult` kept for logging.
3. `changed_packages` (`:~320`) drops outside paths and top-level files; log outside paths separately (e.g. `outside_paths` count) so an outside-only change is not `[]`.
4. Revert the whitespace-only rewrap of `code_delta` in `_run_land`.
5. Spec step 1 also asked for `--durations` slowest-test reporting; implement it or record in the spec that it is deferred.

## Docs
- `docs/WORKTREE_LANDING.md`: state that targeted selection runs only the changed package's tests and does not follow imports into other packages (spec step 4 is deferred); say a rename counts as both paths; list the outside paths that force a retest.
- Rename the `multi_package` reason to something that does not imply dependency analysis (e.g. `targeted_multi`), or add a code comment; update `tests/tools/test_land_branch.py::test_selection_rules` and any log readers.

## Not changing
- Dependent-package selection stays deferred to spec step 4 (owner decision, spec section "Decisions already made").
- `core/` still runs the full suite.

## Verification expected
Focused tests while iterating (`tests/tools/test_land_branch.py`, `tests/tools/test_landing_metrics.py`, `tests/tools/test_git_workflow*.py`). Run the full chunked suite once at the end. Report new tests per item A-F. Claude will re-review only the follow-up commits.
