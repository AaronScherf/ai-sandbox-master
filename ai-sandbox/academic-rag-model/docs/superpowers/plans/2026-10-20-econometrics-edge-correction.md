# Econometrics edge correction implementation plan

Date: 2026-10-20. Design: [edge-vocabulary decision](../specs/agent/2026-10-20-econometrics-edge-vocabulary-design.md).

The requested outcome is a graph whose visible connection claims have
accurate relation types, direction, conditions, and citations. The 41
flagged LINK claims are the first correction set; the 33 supported claims
also receive a semantic-label audit. No agent action marks content verified
or lands/publishes either repository.

| Milestone | Work and global constraints | Acceptance evidence | State |
|---|---|---|---|
| 1. Shared vocabulary | Add the five selected types to schema, LINK card, Python/JS sentences, viewer legend/form, and prerequisite traversal. Show any nonempty condition on all types except the special `is_a` differentiator. Keep existing graph behavior and review states. | Focused Python/JS tests, microecon regression tests, fixture graph validate/build. | Implemented on this branch; 370 Python and 46 viewer tests passed; five-type fixture validated with 0 errors and built locally. The full repository landing check passed twice, including after the sentence-label refinement (527.6s on the refined code). Not landed or live-observed. |
| 2. Graph migration | In a separate graph-repo worktree, inspect exact cited passages for 41 flagged edges; replace, condition, add result nodes, or omit. Track every old ID and reason; leave status `proposed`, clear stale critic verdicts, preserve unrelated reviews/changes. | 41-entry disposition audit, no stale verdicts, corrected sentence/citation check for every replacement. | Implemented on `codex/econometrics-edge-corrections`: 33 retyped, 4 conditioned, 4 omitted; 3 result nodes added. Two supplementary evidence-backed edges and a node terminology repair were also made. All corrections remain proposed. The exact mapping and evidence are in `docs/econometrics-edge-correction-audit-20261020.md` in that repo. |
| 3. Independent review and preview | Critic changed claims using fresh offered evidence; inspect originally supported 33 for same label errors; run `validate` and local `build`; inspect viewer sentences and orphan report. | Zero validation errors; bounced/weak/unsupported counts and page preview recorded separately from owner review. | Author semantic audit completed: 11 formerly supported labels retyped and 4 claims narrowed; 18 original supports retained. Live graph validates with 0 errors/4 orphan warnings and builds locally (83 nodes, 72 edges; graph version `e501a5933b60`). Separate independent CRITIC has not been rerun on corrected claims; that remains a review gate, not evidence of support. |
| 4. Owner gate | Present branch SHAs and local review files/page. Do not set `verified`, merge, or push without the appropriate owner decision and landing checks. | Explicit owner review/landing decision; graph commits remain local until then. | Blocked on owner decisions. |

No new server, persistent store, scheduler, or automatic supersession registry
is part of this release. The code and graph are separate Git repositories;
the code must be available before graph YAML uses new edge types. The
`academic-hub/.agent_work` cards are private run artifacts, not publication.
The current graph main checkout has an unrelated untracked applied-review
file; it is read-only for this task.

Update this table after each milestone to distinguish code tested on
fixtures, the live graph validated/built locally, and owner-reviewed state.
