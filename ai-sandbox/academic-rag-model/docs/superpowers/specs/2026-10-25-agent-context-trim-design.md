# Agent context trim: to-do tracker, worktree procedure, memory index

Status (2026-10-25): approved and implemented. 1b in 3c11103; 1a in b17c53b
(7 items archived; TODO-0016 and 0018 kept as partly open; colliding TODO-0070
renumbered to TODO-0090); 1c-1f in fb6572c; 2A (split) in the commit that adds
this line; 3 applied to Claude's local memory.

Goal: cut the text every agent session (Claude, Codex, Gemini) reads by default,
without losing information or changing what any rule requires. Sizes are bytes;
tokens are roughly bytes / 4.

## 1. To-do tracker (`docs/trackers/academic_hub_to_do.md`, 90 KB, ~22k tokens)

Every "add this as a pending to-do" request touches this file, and an agent that
reads it whole pays ~22k tokens. Measured on main @ ab95b16:

| Content | Size | Notes |
|---|---|---|
| 86 `TODO-####` items | 71 KB | median item ~600 B; largest 2.9 KB (TODO-0030) |
| 9 items already marked DONE in place | 11.4 KB | TODO-0010, 0014, 0016, 0017, 0018, 0076, 0077, 0078, 0079 |
| `## Git Workflow Between Agents` brainstorm prose (`###` subsections) | ~12 KB | problem narrative, snippets, guardrails; only 3 IDs (0028, 0029, 0073) |
| Pasted textbook text at end of file (`#### 2.24`, `#### 3.8`) | ~4.7 KB | root CLAUDE.md works around it ("never append at the end") |

The completed-items protocol already exists (`academic_hub_completed.md`, 6.6 KB):
move the whole bullet under a `## YYYY-MM-DD` heading after checking the actual
outcome. The 9 DONE items were marked in place instead (e.g. commits 664b0c2,
b128163, f4347c0 each changed one line), so the protocol is not being followed.

### Proposed changes

1a. **Archive the 9 DONE items** to `academic_hub_completed.md` per its own rules,
    verifying each outcome first (the protocol forbids inferring completion from a
    commit). Saves ~11 KB.

1b. **Fix ID reuse before archiving anything.** `tools/project_steering/identity.py:33`
    computes `next_id` as the max `TODO-####` in the active tracker only. Once the
    highest-numbered item is archived, the next new item reuses its ID, which
    collides with the completed file and with any doc or commit that cites it.
    Fix: take the max over both tracker files (or keep a `<!-- next-id: N -->`
    high-water comment). Small Codex task with a test in
    `tests/tools/project_steering/`.

1c. **Move the Git Workflow brainstorm prose** into its own doc
    (`docs/superpowers/specs/2026-10-04-agent-git-workflow-brainstorm-notes.md`),
    leaving the three TODO bullets and a one-line link. Note: the 2026-10-06
    agent-git-workflow design spec may already supersede parts of it; the mover
    should check and say so in the link line. Saves ~11 KB.

1d. **Move the pasted textbook text out** to the file the related Textbook
    Conversion item needs (or delete it if no item cites it), then drop the
    "file ends in pasted example text" caveat from root `CLAUDE.md`. Saves ~4.7 KB
    and one rule. Copyright check: confirm this text is allowed in a public repo at
    all (root `.gitignore` excludes copyrighted source material).

1e. **Tell agents not to read the whole tracker.** Change the pending-to-do rule in
    root `CLAUDE.md` (and the equivalents in `AGENTS.md` / `GEMINI.md` if they
    carry it) to: "grep `^## ` for the headings, read only the target section,
    append there." This holds the per-add cost at ~2-5 KB no matter how long the
    file gets.

1f. *(Optional)* **Cap new items at ~800 B.** Longer evidence goes in a status
    doc and gets linked. Existing long items stay as they are.

Result: about 90 KB → 63 KB for a full read, and ~3 KB for a typical to-do add
once 1e is in place.

## 2. Worktree procedure (`docs/WORKTREE_WORKFLOW.md`, 11 KB, ~2.7k tokens per writing session)

Root `CLAUDE.md`, `AGENTS.md` and `GEMINI.md` all say to follow it before any
write, and its own "Check before writing" section says to read it explicitly.
Most sessions need only about 25% of it: create a worktree, the pre-write checks,
staging rules and forbidden operations. Landing (§Integrate, ~4 KB), child-repo
and data isolation (§Isolate, ~2 KB) and retirement (§Retire, ~1.5 KB) apply only
some of the time.

`BUG_HANDOFF.md` (7.5 KB) and `AGENT_ROUTING.md` (6.5 KB) are linked
conditionally (bug intake, routing questions) and summarized inline, so they are
not a fixed cost. Leave them alone.

### Options

2A. **Split (recommended).** Keep `WORKTREE_WORKFLOW.md` as a ~3 KB core (the
    concepts, create, check before writing, forbidden ops). Move §Integrate to
    `WORKTREE_LANDING.md` and §Isolate plus §Retire to
    `WORKTREE_DATA_AND_RETIRE.md`. The core ends with "read X when landing, Y when
    touching child repos/shared data/retiring". Agents tend to read a linked file
    to the end, so a separate file stops the read more reliably than a
    "you can stop here" line.

2B. **Quick path on top.** Add a ~1 KB summary at the top and keep the file whole.
    Less churn, but agents told to "read this procedure" will probably still read
    all of it.

Either way, no rule changes wording or meaning: this is a move, not a rewrite.
Saves ~2 KB per writing session (2B) or ~8 KB (2A). Per the routing convention,
Gemini (docs review) or Codex (docs maintenance) can carry it out after you choose.
Every agent's instruction file links here, so all three need the same updated link.

## 3. Claude memory index (`MEMORY.md`, 4.5 KB, loaded every Claude session)

Small but always paid. These entries are closed and could each be deleted, or
folded into a single "historical" line:

- marker-conversion branch topology (marked SUPERSEDED 2026-08-30)
- Duplicate-check rebuild limitation (FULLY RESOLVED 2026-09-22)
- Pipeline autonomy policies (no open follow-ups)
- Source indexer subproject (shipped 2026-08-28, says "merged to marker-conversion", a branch that no longer exists)

Also: "Agent git workflow metrics" had a revisit date of ~2026-10-21, which has
passed. Either do the revisit or push the date back.

Saves ~0.8 KB per Claude session. Claude can do this alone (memory is
Claude-local) once you approve.

## Already done in the same session (for context)

- Retired 35 merged worktrees and deleted 38 merged branches; `.worktrees/` went from 28 GB to 18 GB.
- Excluded `.worktrees/` from the JetBrains index (local `.idea/`, not committed).
- Saved the unfiled landing-duration bug report to the main checkout's
  `.agent-reports/bugs/20261011-224922-landing-test-duration/` (tracked as TODO-0073).

## Decisions needed

1. Approve 1a-1e (and 1f?). 1b must land before 1a.
2. 2A (split) or 2B (quick path)?
3. Approve the memory pruning in §3, and say whether the git-metrics revisit is still wanted.
