# Textbook Conversion — Walk-Away Execution Design

## Context

The sibling specs —
`docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`
(decision policies) and
`docs/superpowers/specs/2026-09-20-textbook-conversion-skill-design.md`
(Skill + orchestrator packaging) — solve *reliability*: replacing an LLM
issuing ~100 individual `gcloud`/`ssh` calls with a single tested
orchestrator script executing deterministic policy. Neither solves
*supervision*: something still has to invoke that script and remain alive
long enough to react to the handful of decisions that genuinely need a
human, and to know when the run is done.

Two things make this less than it might first appear:

- **The multi-hour "wait and react" work is entirely GCP-side.** VM
  lifecycle, log polling, and the escalation ladder never touch the local
  filesystem. Only the final artifact download does (Step 3.4a), and that
  step is already documented as safe to run any time, including mid-batch
  — it doesn't need to happen synchronously with the run at all.
- **A VM cannot reset or resize itself.** `gcloud compute instances
  reset`/`stop` must be issued by something external to the instance
  being acted on (the calling process would be killed along with it), so
  no amount of on-VM watchdog logic (already true today) can fully absorb
  this — an external supervisor of some kind is unavoidable for the OOM
  ladder's reset/resize rungs.

Given the sibling specs already reduce the OOM/duplicate/cost decisions to
deterministic thresholds (score ≥ `AUTO_SKIP_THRESHOLD`, 2nd/3rd OOM
count, a fixed batch-size cap) rather than judgment calls, the
orchestrator can execute all of them as plain code. **No LLM inference is
needed during the run itself** — the reasoning happened once, at spec-writing
time, in the two sibling specs. This spec is therefore about keeping one
detached script alive for hours, plus a much lighter, infrequent check-in
loop that only needs an LLM for the rare moments a human decision or
notification is genuinely required.

## Goals

- The orchestrator runs as a detached local background process that
  survives the driving Claude Code session/terminal closing — the machine
  needs to stay powered on, but nothing needs to be actively watched.
- A lightweight, periodic (not continuous) supervisor loop, backed by this
  environment's own self-pacing loop mechanism, whose only job is: read
  the run's durable state, decide whether a push notification is due, and
  eventually produce the final report.
- Each of the three surviving hard stops (nested-subfolder inclusion,
  unprecedented-batch-size cost cap, 3rd-OOM escalation) gets its own
  wait/no-wait/timeout-default behavior, matched to that gate's actual
  cost asymmetry — not one uniform policy.
- Artifact sync to the local `academic-hub` folder is decoupled from the
  live run entirely: a separate, idempotent, on-demand step you run
  whenever you're next at your machine.
- A durable run-state file so either the supervisor loop or a freshly
  opened Claude Code session can pick up a run's status without needing
  prior conversation context.

## Non-goals

- **Not fully cloud-hosted, laptop-off execution.** Per your stated
  requirement ("machine stays on, I don't need to watch a terminal"),
  this spec does not design separate GCP credentials for a cloud-hosted
  scheduled agent, or any mechanism that survives the local machine itself
  being off. That remains a possible future upgrade once this shape is
  validated, not something to build now.
- **Not changing any of the autonomy policies themselves** (thresholds,
  escalation rungs, duplicate confidence bands) — those are entirely the
  sibling policies spec's concern. This spec only adds the wait/notify/
  timeout behavior around the three stops that spec still leaves as real
  human decisions.
- **Not building a general-purpose job queue or workflow engine.** The
  mechanisms below (a JSON run-state file, a decision file, a self-pacing
  check-in loop) are sized for one conversion run at a time, matching how
  this pipeline is actually used (roughly monthly, one batch per session)
  — not designed for multiple concurrent runs.

## Architecture

```
Local machine (stays powered on)
---------------------------------
Orchestrator (detached background process, launched once)
  - Executes the full pipeline: preflight, duplicate check (with
    sibling spec's auto-resolution), VM lifecycle, escalation ladder,
    upload/launch/poll, cleanup, VM deletion.
  - All autonomy-policy decisions are plain code -- no LLM call.
  - Writes/updates run_state.json continuously.
  - On a stop that needs a wait (cost cap only -- see Component 2):
    blocks on its own poll loop, reading decision.json; applies its own
    built-in timeout default if nothing appears in time.
  - On a stop that doesn't need a wait (nested-subfolder default,
    3rd-OOM): applies the default/failure immediately, records it in
    run_state.json, and continues.

Supervisor loop (Claude Code, self-paced -- e.g. superpowers "loop" skill)
  - Wakes every ~20-30 min (idle-tick cadence -- this is a multi-hour
    batch, not something needing per-minute polling).
  - Reads run_state.json.
  - New pending_human_input, book_failures_needing_review, or
    auto_skipped_pending_confirmation entries since last tick? -> one
    batched push notification (never one notification per item).
  - A human reply naming a decision? -> write it to decision.json for
    the orchestrator to pick up.
  - stage == "completed"? -> produce the final report (per the skill
    spec's Component 4), push-notify completion, stop the loop.
  - Otherwise -> quiet no-op tick, schedule next wakeup.
```

Two processes because they have very different lifetime requirements: the
orchestrator must survive the Claude Code session ending, while the
supervisor loop *is* a Claude Code session (by construction) and exists
specifically to bridge "the human isn't watching" to "the human gets
pulled in when it matters."

## Component 1: Run-state and decision files

New per-run files (gitignored — transient, not a permanent artifact,
matching `docs/status/vm_sizing_raw/`'s existing convention):

`docs/status/textbook_runs/<run_id>/run_state.json`:
```json
{
  "run_id": "microecon_textbooks_20260921_103000",
  "textbook_subdir": "academic_resources/microecon/textbooks",
  "stage": "awaiting_cost_confirmation | converting | completed | failed",
  "started_at": "2026-09-21T10:30:00Z",
  "pending_human_input": null,
  "book_failures_needing_review": [],
  "auto_skipped_pending_confirmation": [],
  "resize_events": [],
  "log_tail_path": "docs/status/textbook_runs/<run_id>/orchestrator.log"
}
```

`pending_human_input` shape when set (only the cost-cap gate ever sets
this — see Component 2):
```json
{"type": "cost_cap_exceeded", "details": {"book_count": 40, "total_mb": 8200},
 "raised_at": "...", "timeout_at": "...", "notified": true}
```

`docs/status/textbook_runs/<run_id>/decision.json`: written by the
supervisor loop (or a human directly, if they're back at the machine
before the timeout) when a reply to a `pending_human_input` arrives —
`{"proceed": true}` or `{"proceed": false}`. The orchestrator's poll loop
picks this up and deletes it once consumed.

## Component 2: Per-gate wait behavior

Each of the three surviving hard stops gets the behavior matched to its
own cost asymmetry (per the sibling specs' established reasoning), not a
single uniform timeout policy:

- **Nested-subfolder inclusion:** no wait. The orchestrator defaults
  immediately to "skip this run, mention it in the final report" and the
  main batch proceeds without delay. Skipping is free to undo later (the
  files stay where they are), so pausing anything for this decision buys
  nothing.
- **Unprecedented-batch-size cost cap (sibling policies spec, Component
  2a):** the one gate where the safe direction is the *opposite* of
  "proceed" — an unusually large batch might mean a real mistake, not
  just a big-but-intentional run. The orchestrator sets
  `pending_human_input`, then blocks in its own poll loop (checking
  `decision.json` every ~60s) for up to a timeout window (proposed 4
  hours — an initial judgment call, tunable). If `decision.json` never
  appears: default to **not** creating the VM, mark the run `failed` with
  a clear reason in `run_state.json`, and end. If it does appear:
  proceed or stop per the decision.
- **3rd-OOM escalation:** no wait. This already matches how an ordinary
  book failure works today ("one book failing is logged and skipped, not
  fatal to the rest of the batch") — the orchestrator marks that one book
  failed with reason `"3rd_oom_escalation"` in
  `book_failures_needing_review`, and continues to the next book
  immediately. The only new behavior versus today's plain failure handling
  is the stronger, dedicated notification (Component 3), since this
  specific failure reason is worth a human looking at sooner than an
  ordinary corrupt-PDF failure would be.

## Component 3: Notification batching

The supervisor loop never fires one push notification per item — it
diffs `run_state.json` against what it last saw, and if anything new
appeared (a pending cost-cap decision, a new 3rd-OOM book failure, a new
auto-skipped-pending-confirmation duplicate), it sends **one** notification
summarizing everything new since the last tick. A `pending_human_input`
entry gets notified on the tick it first appears, and is not re-notified
on every subsequent tick while it's still waiting (only once more, if it
times out and the safe default gets applied, so you know that happened).

## Component 4: Local artifact sync and cleanup (both decoupled)

Downloading finished output into the local `academic-hub` folder
(existing Step 3.4a) is **not** part of the orchestrator's automatic
lifecycle in the walk-away model — it stays a separate, on-demand command
you run whenever you're next at your machine, exactly as it's already
documented today (safe to run any time, including mid-batch, since each
book uploads to GCS as soon as it finishes). The orchestrator's own
lifecycle only needs the GCS bucket, never your local filesystem, until
you choose to sync.

**This must also apply to bucket cleanup (Step 3.4b), not just
download — this was a real gap in an earlier draft of this spec.** The
skill spec's default orchestrator lifecycle includes emptying
`processed_outputs/*`/`input_documents/*` from the bucket automatically
after conversion. In the walk-away model specifically, that would delete
the only copy of a freshly-converted book before you've ever run your
on-demand local sync — a real, permanent data-loss risk, not a
theoretical one. **In walk-away mode, cleanup is deferred to the same
on-demand step as download**, not run automatically by the orchestrator:
VM deletion still happens automatically (it holds no unique data once
output is in GCS), but the bucket itself is left alone until you've
synced. The completion notification (Component 3) says so explicitly —
"output ready in GCS, not yet synced or cleaned up" — so this doesn't
depend on you remembering it days later; leaving finished output sitting
in GCS a while longer costs only object storage, not the ongoing
GPU/disk billing this pipeline already treats as the real cost to avoid.

## Component 5: Detachment mechanism (Windows)

This environment is Windows/PowerShell. A plain `&`-backgrounded process
or a Bash-tool `run_in_background` call is tied to the parent shell/tool
session and is not guaranteed to survive that session or the Claude Code
process ending. The orchestrator must be launched via
`Start-Process -WindowStyle Hidden` (or an equivalent OS-level detachment,
e.g. a Scheduled Task run-once trigger) so its process tree is independent
of whatever launched it, with stdout/stderr redirected to
`orchestrator.log` rather than inherited from a console that may not exist
by the time something is read from it.

## Error handling

- If the orchestrator process itself dies unexpectedly (not a handled
  failure — a crash, or the machine losing power), `run_state.json`
  simply stops updating. The supervisor loop's tick should treat "no
  update to `run_state.json` for longer than some staleness window" as
  its own notification-worthy event, distinct from a normal in-progress
  run — otherwise an actually-dead run looks identical to a healthy one
  that's just between log lines.
- `decision.json` race: if a human answers via a resumed Claude Code
  session *after* the orchestrator's own timeout already fired and
  applied the default, the late `decision.json` is simply ignored (the
  orchestrator no longer polls for it once its own timeout path has run)
  — the supervisor loop should say so explicitly rather than silently
  dropping the late reply.

## Testing

- `run_state.json`/`decision.json` read/write logic and the per-gate
  wait/no-wait/timeout state machine are pure logic, factorable out of
  the orchestrator and unit-testable independent of any real `gcloud`
  call — same principle as the sibling policies spec's testing approach.
- The supervisor loop's diff-and-notify logic (Component 3) is testable
  against synthetic `run_state.json` snapshots without needing a real
  orchestrator run.
- The actual detachment mechanism (Component 5) and a real multi-hour
  unattended run are real-run verification items, not something a unit
  test can safely cover — consistent with how every other GCP-touching
  piece of this pipeline has been verified.

## Documentation updates

- `convert_textbook_agent_instructions.md` / the skill's `SKILL.md`: add
  a short section on the walk-away invocation path (launch, what
  notifications to expect, how to check `run_state.json` directly if
  curious) alongside the existing synchronous/attended path — both remain
  valid; walk-away is an option, not a replacement for running the skill
  interactively for a shorter/smaller batch.

## Open items deferred to the future

- **Fully cloud-hosted, laptop-off execution** (Non-goals) — would need
  its own GCP credential setup for a cloud-hosted scheduled agent,
  independent of the local `gcloud` login this pipeline uses today. Worth
  revisiting once the local-background-process model here has been
  validated against a few real runs.
- The cost-cap timeout window (proposed 4 hours) is an initial judgment
  call, not derived from data.
- Whether the supervisor loop's ~20-30 minute cadence is the right default
  once real runs show how often something actually needs attention.
