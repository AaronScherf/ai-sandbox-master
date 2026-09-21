# Textbook Conversion Claude Skill — Design

## Context

The textbook conversion pipeline currently has two hand-driven entry
points: `convert_textbook_instructions.md` (human-interactive, Docker +
PowerShell) and `convert_textbook_agent_instructions.md` (agent-facing,
commands run directly on the host, 6 mandatory stop-and-ask gates). The
agent-facing doc is already skill-shaped — explicit preflight checks,
single-command-per-call discipline, a condensed debugging playbook — but
it's still a document a fresh agent reads and manually executes command by
command, one `gcloud`/`ssh` call at a time, over what can be a multi-hour
run.

The goal explored in this brainstorm: a single prompt — "convert
everything in this folder" — that runs the whole pipeline end to end, with
intervention limited to genuine architectural decisions. This spec covers
how that gets packaged and driven; the decision policies that make
minimal intervention *safe* (duplicate auto-resolution, the OOM/cost
escalation ladder) are a separate, sibling spec:
`docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`.
This spec assumes that one's policies exist and focuses on orchestration.

## Goals

- A Claude Skill, invokable as a single prompt pointing at a textbook
  subdirectory, that runs the full pipeline (preflight → duplicate check →
  VM lifecycle → conversion → download → image description → cleanup)
  without the user needing to re-explain the procedure or its gotchas
  each time.
- Move the pipeline's *mechanical* GCP/shell sequencing — the actual
  source of most real bugs found in this pipeline's history (wrong
  working directory, a heredoc silently running on the wrong host, apt
  package holds, SSH-not-ready-yet retries) — off the "LLM issues each
  command individually, in order, correctly, every time" model, since
  that model is both where the historical bugs came from and the part
  least suited to LLM judgment.
- By default, the only mandatory stop is nested-subfolder inclusion (a
  genuine 3-way choice — see Component 3). Every other decision point uses
  the sibling spec's autonomy policies.
- A clear final report: what converted, what was auto-skipped as a likely
  duplicate (pending confirmation), any OOM/resize events and their
  self-check outcome, and actual vs. estimated cost.

## Non-goals

- **Not designing true walk-away execution** — surviving a Claude Code
  session restart, or running with no live session/terminal at all. This
  spec covers a skill driven within a single, possibly long, interactive
  session; the walk-away model (a detached orchestrator process plus a
  lightweight, periodic supervisor loop) is designed separately in
  `docs/superpowers/specs/2026-09-20-textbook-conversion-walkaway-execution-design.md`,
  which builds on this spec's orchestrator rather than replacing it.
- **Not re-deciding the autonomy policies themselves** (duplicate/OOM/cost
  thresholds and escalation) — those live entirely in the sibling spec.
  This spec only decides how they get invoked and reported.
- **Not deprecating either existing instructions doc.** Both remain valid,
  documented fallback paths: the human doc for a fully manual/interactive
  run, the agent-instructions doc as the reference a human or the skill
  itself falls back to when the orchestrator hits something it doesn't
  handle.

## Architecture: Skill + hardened orchestrator script

Two pieces, not one:

1. **`SKILL.md`** (new, at `.claude/skills/convert-textbook/SKILL.md` —
   the standard Claude Code project-skill location; no skill directory
   exists yet in this repo, so this establishes the convention rather than
   following an existing one) — the entry point. Describes the invocation (point it at a textbook
   subdirectory), what it does at a high level, references the
   orchestrator script and the sibling autonomy-policies spec by path, and
   defines the final-report format and the nested-subfolder question. This
   is what a Claude Code session actually loads when the skill is invoked
   — it is deliberately thin, delegating the mechanical work rather than
   re-describing every `gcloud` call inline the way
   `convert_textbook_agent_instructions.md` does today.

2. **Orchestrator script** (new — a Python or bash script, e.g.
   `textbook/run_conversion_pipeline.py`; the implementation plan should
   decide the language based on how much of it is pure logic worth unit
   testing vs. shell sequencing) — encodes the mechanical steps currently
   spread across `convert_textbook_agent_instructions.md` Steps −1 through
   5 as one script the skill invokes and monitors, rather than a sequence
   of individual tool calls an LLM issues one at a time:
   - Preflight verification (Step −1)
   - Duplicate check invocation, using the sibling spec's
     `--review-pending` check and two-tier auto-resolution
   - VM lifecycle: create, scope-fix, provision, and — per the sibling
     spec's escalation ladder — the reset/resize sequence on repeated OOM
   - Upload (pre-sorted ascending by size per the sibling spec), launch,
     detached-session log-polling loop
   - Download, RAM-sizing log correlation, bucket cleanup, VM deletion
     (automatic, per the docs' existing default recommendation — Option
     B — rather than asking, consistent with "these should be reasoned
     through")
   - Emits the structured data the final report (Component 4) is built
     from

   The skill's own job during a run shrinks to: interpret the target
   folder, check for pending duplicate confirmations from a prior run
   (Component 2), ask the one remaining nested-subfolder question if
   relevant (Component 3), invoke/monitor the orchestrator, and produce
   the final report (Component 4) — not individually issuing each
   `gcloud`/`ssh` command for the mechanical parts anymore.

## Component 2: Pending-confirmation check at invocation start

On every invocation, before touching anything new: run
`indexer.duplicate_check --review-pending`. If non-empty, surface it to
the user in chat immediately (informational — does not block the new run
from proceeding), so pending duplicate confirmations from a prior
unattended run don't go unnoticed indefinitely.

## Component 3: Nested-subfolder handling

Exactly as scoped in the brainstorm — this is the one decision point that
stays a genuine ask, not a default:

> A nested subfolder under the target directory (e.g. a `Bonus/` folder
> of supplementary readings) was found. Should it be: (a) folded into
> this run, (b) automatically run as a second batch once this one
> completes, or (c) skipped entirely?

This matches the existing agent-instructions doc's underlying reasoning
(never mix a nested subfolder's PDFs into the same spot-VM session as the
main batch) — the only change is presenting it as an explicit 3-way choice
rather than a binary "include or defer."

## Component 4: Final report

Produced at the end of a run (and available on-demand mid-run if asked),
combining structured output from the orchestrator:

- Books converted, with output location.
- Books auto-skipped as a likely duplicate, pending confirmation (from the
  sibling spec's Component 1c), with a reminder of how to review
  (`--review-pending` / `--confirm-pending` / `--reject-pending`).
- Any OOM/resize events during the run, which rung of the escalation
  ladder fired, and the self-check outcome.
- Actual VM wall-clock time and approximate cost vs. the pre-run estimate.
- Any hard stops that did occur (nested-subfolder question, a 3rd-OOM
  escalation, an "unprecedented batch size" cost escalation) and how they
  were resolved.

## Testing

- The orchestrator script gets the same treatment this pipeline's existing
  shell/Python components already get: syntax-check + a stubbed
  `gcloud`/`free`/`date` smoke test for the sequencing (matching
  `start_conversion.sh`'s existing smoke-test pattern), and unit tests for
  any pure logic factored out of it (e.g., the batch-ordering sort is a
  pure function regardless of which language the orchestrator ends up in,
  and should be tested as one).
- `SKILL.md` itself is validated the way skills in this environment
  normally are — triggering correctly and behaving consistently — using
  whatever skill-eval tooling is available at implementation time, rather
  than a bespoke test harness invented for this pipeline.
- No unit test can safely exercise the real multi-hour, real-GPU-VM path
  end to end — that remains a real-run verification item, exactly as it
  has been for every other piece of this pipeline so far.

## Documentation updates

- New `SKILL.md`.
- `convert_textbook_agent_instructions.md`: retained as reference
  material / manual fallback, with a note pointing to the skill as the
  preferred entry point for a routine run — not deleted, since a human
  (or the orchestrator itself, on an unhandled failure) still needs a
  documented manual path.
- `convert_textbook_instructions.md`: unchanged — remains the fully manual
  human-interactive path.

## Open items deferred to the future

- Exact orchestrator implementation language and file location — an
  implementation-plan decision, not a design one.
- Whether/how the final report should also be persisted somewhere durable
  (not just chat output) for a run that happens unattended — designed in
  the walk-away execution spec (Component 1's `run_state.json`), not
  here.
