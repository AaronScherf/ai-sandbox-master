# Codex brief: landing test selection and tamper-resistant guard (2026-11-11)

From Claude (design), to Codex (implementation). Read these first, grep rather than read whole:
- `docs/superpowers/specs/2026-11-11-landing-test-selection-proposal.md` (the evidence and rules)
- `docs/trackers/academic_hub_to_do.md`, TODO-0095
- `tools/land_branch.py`: `selection_reason`, `run_checks`, `_is_documentation_only`, `GUARD_POLICY_PATHS`, `RETEST_OUTSIDE_PATHS`

Use a `codex/<task>` branch and worktree per `docs/WORKTREE_WORKFLOW.md`. Stage explicit paths. Tests make no API calls. Do not land; the owner lands.

**Gate:** do Part A only after the owner answers the two open questions in the proposal (post-landing full run acceptable? which outside-project paths do tests read?). Part B can start now and is independent.

## Part B (start now): TODO-0095, run `main`'s guard when landing

Problem: `land_branch` imports `guard_binaries` from the branch being landed, so a branch that weakens the guard is judged by its own edited copy.

Do:
1. Execute the guard from the main checkout: `python -m tools.guard_binaries --range main...HEAD` with `cwd` at the main checkout (`main_checkout(worktree).path`), or load `main`'s copy with `git show main:ai-sandbox/academic-rag-model/tools/guard_binaries.py`. Choose the simpler one and say why.
2. When `GUARD_POLICY_PATHS` changed (already computed as `policy_changed`), `land` refuses unless the owner's approval covers that change ID. Reuse the existing change-ID approval; do not invent a second mechanism.
3. Test: a branch edits `guard_binaries.py` to allow PDFs and stages a hub PDF; `check` and `land` must still refuse. Also test that a branch which only adds an allowlist line is judged against `main`'s allowlist (already true via `_base_allowlist`; keep it true).

## Part A (after owner answers): selection rules

Implement proposal rules 1-4 in `selection_reason`/`run_checks`:
1. New reason `outside_project_only`: every changed path is outside `ai-sandbox/academic-rag-model/` and none is in the allowlist of paths tests read. Skip tests (like `doc_only`). Seed the allowlist from the existing `RETEST_OUTSIDE_PATHS` (`.gitignore`, `ai-sandbox/.obsidian`) plus whatever `grep` over `tests/` finds reading paths above the project root.
2. In-project non-`.py` files map to the nearest package with a `tests/<pkg>` directory; otherwise run `tests/tools`.
3. `core/` changes run `tests/core` plus packages that import the changed module (start with a static `import` scan; fall back to full if unsure).
4. Always full: `--full`, any `GUARD_POLICY_PATHS` file, `conftest.py` or top-level test helpers, dependency pins, pytest config.
5. Post-landing safety net: after `land`, start a background full chunked run on `main` and append the result to the landing log as `{"event": "post_land_full", ...}`. Surface failures in `tools.landing_metrics`.

Tests:
- Fixtures from the logged cases: an outside-only `.json` change, a `.docx` move, a research-repo pin → `outside_project_only`; an edit to `tools/land_branch.py` → full.
- Replay script (read-only, not committed unless useful): feed the logged `changed_*` fields from `.git/agent-landing-log.jsonl` through the old and new rules and print the old vs new reason and the minutes saved. Report the totals in your handoff; expectation is about 256 of 336 minutes saved.

## Report back

Branch and commit, test results, the replay totals, and anything in the rules you changed from this brief and why. Do not touch the interference items in the proposal; those are not decided.
