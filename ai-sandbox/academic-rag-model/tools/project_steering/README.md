# Project steering and to-do review

`python -m tools.project_steering scan` reads one explicit to-do tracker and
refreshes a provisional local work view. It makes no model or network calls and
does not edit the tracker. Run it from `academic-rag-model/`:

```powershell
python -m tools.project_steering scan --tracker C:\path\to\docs\trackers\academic_hub_to_do.md --state-dir C:\path\to\local\project-steering
```

Both paths must be absolute. Put the state directory outside tracked source and
the nested `academic_notes/` repository. The command writes versioned JSON and
Markdown reports under `runs/`, then atomically replaces `latest.json` to point
at the complete pair. If a write fails, the previous pointer still names the
last complete pair. `--format json` prints the same findings as machine-readable
stdout; the default prints the generated Markdown view.

The scan recognizes eligible task bullets under `##` headings, including dated
bullets in subsections and undated textbook tasks (`added: "unknown"`). It retains
line-numbered diagnostics. Prose that is not a task bullet (such as the
Textbook Conversion example notes) is ignored. Exit `0` means complete coverage; exit `2` means unresolved
classification or an operational error. A partial report is published with
`coverage_complete=false`; source-change and operational errors publish nothing.

The one-time ID migration is separate from `scan`. In an assigned outer-repository
worktree, run `preview-ids --tracker <absolute-path>` and inspect its diff and
`source_sha256`. Then run `apply-ids --tracker <same-path> --source-sha256 <hash>`.
An intervening tracker edit rejects the apply; recover with a fresh preview.
The marker is an invisible Markdown comment at each task bullet start. The
scheduled scan never invokes this command or edits the tracker.

Owner decisions live in a versioned, locked `decisions.json` under `--state-dir`.
Use `review --tracker <absolute-path> --state-dir <absolute-path>` to start the
short-lived loopback page and follow the printed URL. Set impact and urgency
from 0–3, choose an effort band, and optionally confirm dependencies, defer,
decline, or mark done. Scores and shortlist explanations update after each save.
The page never executes work items. The generated view stays provisional until
the owner supplies these inputs. An `URGENT` word and pause/defer wording remain
unreviewed suggestions, not automatic priority or status decisions.

The daily scheduler is still a later milestone in the
[plan](../../docs/superpowers/plans/academic_hub/2026-10-09-project-steering.md).

## Agent routing suggestions

The tracker does not assign an agent by itself. A separate, one-time Claude
classification can be imported as **unapproved suggestions** with
`import-routing --tracker <absolute-path> --state-dir <absolute-path>
--draft <absolute-json-path>`. The JSON must identify the current tracker hash,
stable task IDs and fingerprints, and valid agent/complexity/difficulty/context
values. The import is locked, atomic, and rejects a stale or invalid batch.
It never approves a route or changes the tracker. `scan` makes no model call;
new tasks default to Needs Human Review until someone supplies a route.

Open `review` to see proposed and approved agent batches. Select proposed tasks
and use **Approve selected proposed routes and tags**, or override the agent and
tags on an individual task. Only approved routes with approved complexity,
difficulty, and context tags enter actual agent batches. Proposals whose task
text changed since import are marked stale and cannot be batch-approved.
Approved batches also have per-task checkboxes and **Select all returnable** for
tasks with a current valid proposal. **Return selected approved routes to
proposed** clears only their approved agent and routing tags, so they reappear
in the proposed batch for the originally suggested agent. Scores, priority,
status, and time gates are preserved. Fallback Needs Human Review items and
owner routes without a current proposal have no return checkbox.
The routing policy is [AGENT_ROUTING.md](../../../../docs/AGENT_ROUTING.md).

`not_before` is a separate owner-controlled date gate. It keeps a task visible
but out of today's shortlist and agent batches until that date; it does not
change the task's score. This suits a task such as a trial review that cannot
begin until its scheduled runs finish.

## Potential priority estimates

`import-scores --tracker <absolute-path> --state-dir <absolute-path> --draft
<absolute-json-path>` loads a source-hash- and task-fingerprint-checked score
draft into local **suggested** fields. It does not change the approved impact,
urgency, or effort fields, or add dependency edges. A failed batch changes no
state bytes. Each row carries `id`, `fingerprint`, `impact` (0–3), `urgency`
(0–3), `effort` (a listed band or `unknown`), `confidence`, and `rationale`.
The draft envelope carries `source_sha256`, `batch`, and `rows`.

The review page shows suggested scores beside each task's editable inputs.
Use **Fill fields from potential score** to adjust and save one item, or select
suggestions in the priority section and use **Approve selected score estimates**.
Approval fills only still-unknown score fields, preserving values already
entered by the owner. A changed task is skipped as stale. Unknown effort stays
in Needs Estimate even when its impact and urgency are approved. The proposed
agent batches are separate: their checkboxes approve routing tags, never scores.
Each proposed agent batch has a select-all checkbox for faster routing review.
It also has a **Select with approved scores only** checkbox. This selects
routes whose score proposal was approved by the owner, excluding unapproved
suggestions even if they contain numeric values. Routing and score approvals
remain separate actions.
The potential-priority section groups pending suggestions by proposed agent,
including Claude, Gemini, Codex, and Needs Human Review. Each group has its own
select-all and high-, medium-, and low-confidence controls; confidence is
advisory and never changes the ranking formula. A one-time Codex draft for the
previously unestimated non-Codex tasks was imported on 2026-10-10 as
**unapproved** suggestions, with task-specific rationales and confidence.

The **Full scored order** uses a scrollable table with task index, a three-word
title preview, pipeline/section, added date, score, tags, and editable impact,
urgency, and effort. Save scores updates the owner decision and reorders the
ranking. Click a task's title preview to expand its full title, source link,
dependencies, status, route, and other existing controls.
Click a column heading to sort the scored table in either direction. **Filter**
opens text, agent, and minimum-score controls; **Clear filters** restores the
full table. These controls change the displayed view only, not stored scores
or the default ranking order.
In **Next three** and **Needs Estimate**, each task starts with its title and
metadata visible. **Show details** reveals its source link, explanation, and
editing controls; **Hide details** collapses them again without changing state.
