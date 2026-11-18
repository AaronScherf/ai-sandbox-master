# Handoff to Codex: v12 plus the citation gate (v13)

From: Claude, 2026-11-18. To: Codex.
This is one work order covering `... - v12.md` (unchanged; read it first, all of it still applies) plus the citation gate below (Aaron approved adding it to the same handoff). Do v12's steps first: the gate blocks on v12's TITLE_WRONG defects. One branch, one landing. Start from current `origin/main` in a new worktree; run `tools.active_work` before starting and before asking to land. Report before landing.

## 1. Why a gate

Nothing calls the checker today: no pipeline, landing check or agent procedure. Gemini's self-reported "44 verified, 0 unverified" is how this project started, so the check must not depend on an agent choosing to run it. Every agent lands through `tools.land_branch`, so that is the enforcement point.

## 2. Gate behaviour

- **Scope:** Markdown files under `ai-sandbox/research/` that the branch adds or modifies (not deletions, not renames-only). Other paths are untouched by the gate.
- **Run:** `reference_review.gate(note_paths, client) -> GateResult` raises the notes into the ledger (so open questions reach the review page) and returns, per note, `defects`, `open_items` and `unresolved`. Online with the shared cache; tests use recorded answers only.
- **Ledger location (fix first):** `DEFAULT_STORE` resolves next to the module file, so a worktree gets its own empty ledger and would not see Aaron's decisions. Resolve the store to the main checkout's `ai-sandbox/academic-rag-model/.reference_checker_review/` through git's common dir, the same way `load_dotenv_override()` finds the main `.env`. Same for the registry cache. Test it from a worktree layout.
- **Blocks** (`check` and `land` print `STOP: citation gate: ...` with per-note counts):
  1. any defect for a scoped note: WRONG_WORK, NOT_FOUND, TITLE_WRONG, from the checker or a human decision;
  2. any open review item (pending or deferred) for a scoped note;
  3. any registry lookup that failed, so a DOI could not be judged (fail closed; the message says to retry).
- **Does not block:** CONFIRMED and AUTHOR_YEAR rows; items Aaron accepted (dismissed); URL-only rows (report their count; the URL check is separate and not built).
- **When:** `check` runs the gate after tests; `land` re-runs it immediately before the merge, since decisions can change in between. The gate result is not part of the change ID.
- **Message on a block:** name each note, its counts, and "ask Claude to sync the review page" for open items, or "fix the note" for defects. No override flag in this pass.
- `land_branch` is a guard-policy file: expect the full chunked suite.

## 3. Agent instruction

Add to `docs/AGENT_ROUTING.md` (not `GEMINI.md`: it has uncommitted changes in the main checkout, and touching it would create an overlap): any agent writing or revising a research note that cites literature runs `python -m tools.reference_review raise <note>` before handing off, fixes defects, reports the counts, and never writes a `[source-verified]` or similar tag by hand; the landing gate enforces this. Claude adds the same line to `GEMINI.md` after its pending edits are committed.

## 4. Tests (in addition to v12 section 3)

1. A branch changing a research note with a recorded WRONG_WORK, NOT_FOUND or TITLE_WRONG row: `check` stops with the citation gate message.
2. An open review item stops; after `resolve`, the same check passes.
3. A recorded lookup failure stops (fail closed).
4. A note with only CONFIRMED, AUTHOR_YEAR and URL rows passes and reports the URL count.
5. Paths outside `ai-sandbox/research/` and deleted notes are not gated.
6. The store and cache resolve to the main checkout from a worktree layout.
7. `land` re-runs the gate and stops if a defect appeared after `check`.

## 5. Acceptance (report; do not tune)

1. v12 section 4 as written.
2. Gate dry run: run the gate on the five notes from v12 section 4 as if a branch changed them, against a copy of the main ledger in the worktree. Expected from current decisions: RQ3 v5 and RQ1 v4 stop on their TITLE_WRONG defects; RQ2 v4, Summary v3 and Memo v2 pass, unless v12's title search changes a row. Report per note.
3. Confirm by test, not by hand, that a branch touching only code passes the gate untouched.

## 6. Out of scope

URL checking, the claim check, any LLM call, editing notes, `GEMINI.md`, an override flag.

## 7. Reporting back

Per step: commit hash, tests passed and skipped, evidence type, what was not run. Commits: v12's five steps, then store resolution; gate function; `land_branch` wiring; routing doc line; acceptance.
