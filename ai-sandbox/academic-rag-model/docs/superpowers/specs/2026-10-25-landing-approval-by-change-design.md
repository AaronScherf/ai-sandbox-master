# Landing approval by change, not by commit SHA

**Status:** proposal, awaiting owner review (2026-10-25). Amends decision 1 of
`2026-10-06-agent-git-workflow-design.md`. Nothing below is built.
**Scope:** `tools/land_branch.py`, its tests, and `docs/WORKTREE_LANDING.md`.

## 1. Problem

Approval covers one commit SHA. Any rebase changes the SHA, so when `main` moves
between the agent's check and the owner's "yes", the agent has to ask again,
even if the change itself is the same.

Evidence from `.git/agent-landing-log.jsonl` (113 landings, 2026-10-07 to 10-25):

| Window | Landed branches (matched) | Needed re-approval | Extra approval rounds |
|---|---|---|---|
| All | 88 | 25 | up to 49 (about 214 min of repeat checks) |
| Last 7 days | 27 | 7 | — |

"Extra rounds" counts distinct passing SHAs per branch. A few of those come from
fixes, not from `main` moving, so treat it as an upper bound.

In the 24 hours to 2026-10-25 evening, `main` got 27 commits, a median of 3.7
minutes apart. 11 of them were docs or `todo:` commits that went direct to
`main`. A full-suite check takes about 10 minutes, so a code branch almost always
finds `main` has moved by the time the owner answers. On 2026-10-25 a docs-only
branch needed three approvals for one unchanged change.

The second cause of re-asks is the snapshot rule: landing stops if the main
checkout's `git status --short` differs at all. Unrelated untracked files from
another session (e.g. stray `test_*.svg` files) blocked a landing that touched
neither.

## 2. Goal

Ask the owner once per *change*. Ask again only when what would land is actually
different, or when a check that protects `main` fails. Keep: nothing reaches
`main` without the owner's yes, and agents never force anything.

## 3. Decisions proposed

1. **Approval names a change ID, not a SHA.** The change ID is a whitespace-sensitive
   fingerprint of the branch's diff against its merge-base with `main`:
   SHA-256 of `git diff --no-color --no-ext-diff --binary -U0 --src-prefix=a/ --dst-prefix=b/ <merge-base> HEAD`,
   with the `index ...` and `@@ ...` lines removed (they change when unrelated
   lines move). A clean rebase leaves it unchanged; any edit to the change itself
   changes it.
   *Why not `git patch-id --stable`:* it ignores whitespace, which matters in
   Python and Markdown.
2. **One `land` command does the landing.** On the owner's yes the agent runs
   `land --change-id <id>`. In one process, it:
   1. refuses unless the main checkout is on `main`;
   2. rebases the branch onto `main` (a conflict stops the command);
   3. recomputes the change ID and stops if it differs from the approved one;
   4. stops if the files `main` changed since the approved check intersect the
      branch's files, even when the rebase was clean (a nearby edit can change
      meaning without a conflict);
   5. re-runs tests only if needed (decision 3);
   6. recomputes overlaps (decision 4);
   7. runs `git merge --ff-only` in the main checkout, then
      `git push origin main`;
   8. logs the outcome as `landed`, so a separate `record` call is no longer
      needed.

   If the fast-forward fails because `main` moved during steps 2-6, it goes back
   to step 2, at most **3 attempts** in total. After that it stops with
   "main kept moving".
3. **Re-test only when `main`'s new commits could affect the result.** Let *delta*
   be the files changed between the `main` commit the approved check ran
   against and the current `main`.
   - The branch is Markdown-only: no tests (same as today).
   - Delta is Markdown-only: reuse the approved check's result.
   - Otherwise: re-run the same targets the approved check ran (`tests/` in chunks
     if it was `--full`). A failure stops the command.
4. **The snapshot rule becomes an overlap rule.** At landing time, stop only if a
   *tracked* file that the branch changes is modified in the main checkout, or
   changed on another open worktree's branch (the existing `find_overlaps`).
   Untracked files and unrelated modified files no longer block a landing.
   `git merge --ff-only` already refuses to overwrite a dirty file it would touch.
   The approval message no longer needs a `git status --short` snapshot.
5. **`check` prints and logs what approval needs.** It adds `Change ID:` and
   `Base:` (the `main` SHA it checked against) to its summary and its `check` log
   entry, and changes its last line to "Ask the user to approve change <id>".
   `land` takes the base, the `--full` flag and the test targets from the newest
   passing `check` entry with that branch and change ID, so the agent passes
   only `--change-id`.
6. **Approval scope.** One yes covers one change ID on one branch, for the session
   that asked. It does not carry over to other branches or sessions. Every STOP
   from `land` means: report the reason and ask again.

## 4. Agent flow after the change

1. `land_branch check [--full]` in the worktree: rebase, test, report.
2. Ask once: branch, change ID, changed paths, check result, overlaps, known
   risks. Question: "May I land change `<id>` on `main`?"
3. On yes: `land_branch land --change-id <id>`. It either prints `LANDED <sha>`,
   or `STOP: <reason>` (conflict, change differs, main touched the same files,
   tests failed, overlap, main kept moving, push rejected). On a STOP, report it
   and ask again.
4. On no: `land_branch record --sha <sha> --outcome declined` (kept for declines).

## 5. Logging and metrics

`land` appends one `land` entry per run: `branch`, `change_id`, `attempts`,
`retested` (bool), `result` (`landed` or the STOP reason), `sha`. A re-ask is
counted as a STOP followed by a later `land` for the same branch.

Revisit 14 days after shipping and compare against the baseline in section 1:
the share of landed branches needing more than one approval (now 7 of 27 per
week), and time from first check to landing. This replaces the overdue
2026-10-21 revisit of the original workflow metrics; section 1 records the
results of that revisit.

## 6. Implementation notes

- New functions in `tools/land_branch.py`: `change_id(worktree, base)`,
  `land(worktree, change_id)`, and a log lookup for the approved check. Reuse
  `rebase_onto_main`, `find_overlaps`, `run_checks` and `main_checkout`.
- `git merge --ff-only` and the push run with `cwd` set to the main checkout
  (`main_checkout(worktree).path`). Never `--force`, never a bare `git push`.
- Tests in `tests/tools/test_land_branch.py` using the existing `git_fixture`
  repos, at minimum:
  - change ID is stable across a clean rebase over an unrelated commit;
  - change ID differs for a whitespace-only edit;
  - `land` lands when `main` gained a docs-only commit, without re-running tests;
  - `land` re-runs tests when `main` gained a `.py` commit, and stops on failure;
  - `land` stops when `main` touched a file the branch changed, even with a clean rebase;
  - `land` stops when the change ID differs;
  - untracked files in the main checkout do not block it, but a dirty tracked
    file the branch changes does;
  - the retry loop gives up after 3 attempts (simulate `main` moving between
    rebase and merge).
- Update `docs/WORKTREE_LANDING.md` steps 2-4 and the approval paragraph
  ("Approval covers one commit SHA ...") to match section 4.
- Routing: design stays with Claude. The implementation is mechanical script and
  test work that Codex or Claude can do test-first in a worktree.

## 7. Alternatives considered

- **"After one yes, land the branch whenever there are no conflicts."** Rejected
  as the default: it would also cover later commits the owner never saw. The
  change-ID rule gives the same relief for the common case (`main` moved under an
  unchanged change) without that gap.
- **`git patch-id --stable` as the fingerprint.** Rejected: it ignores whitespace.
- **Keep the SHA rule and just land faster.** A faster ask doesn't help: the
  owner's reply time, not the tooling, is most of the gap.

## 8. Unchanged

Only the owner approves landings on `main`. Local commits to a task branch stay
pre-authorized. No force-push, no `reset --hard`, no forced worktree removal or
branch deletion. Rebase only exclusively owned, unpublished branches (the
existing `preflight` published-branch guard stays). Pushing `main` still
publishes any other sessions' commits already on local `main`; that side effect
is not changed here.

## 9. Open questions for the owner

1. Is a retry cap of 3 right, or should `land` keep retrying for as long as only
   Markdown commits arrive?
2. Should "`main` touched the same files" stop the landing for Markdown files
   too, or only for code? This proposal stops for both.
