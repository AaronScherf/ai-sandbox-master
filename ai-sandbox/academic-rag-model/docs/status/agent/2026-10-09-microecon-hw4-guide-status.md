# Study guide pipeline: microeconomics Homework 4 guide (first non-econometrics run)

Status as of 2026-10-09. Pipeline: `agent/study_guide` on branch `claude/study-guide-spec`. Spec:
`guide_specs/microecon/micro_hw4_consumer_choice.toml`. Earlier runs and the revise design:
`docs/status/agent/2026-10-07-study-guide-comparison-status.md`.

The guide, plan and revise reports stay in the private notes vault
(`academic_notes/microecon/summaries/`, `academic_notes/microecon/guide_plans/`). This document
records process, cost and structure only; it quotes no source or guide text.

## Purpose and result

A guide for GR6211 (Mark Dean), built to catch a student with little microeconomics background up
on Homework 4 and the lectures from random utility models to consumer choice. It has 11 topics:
two primers first (budget sets and demand vocabulary, then Lagrangians and Kuhn-Tucker), then the
lecture sequence, then duality ahead of the lectures because question 3 needs it.

The final guide is the draft plus one section enhanced, plus the accepted revise edits, plus
hand repairs. It is usable. It is not reliable without a check against the assignment: the checks
below found errors the pipeline did not.

## What ran, in order, with cost

| Step | Command or action | Cost |
|---|---|---|
| Index the sources | Copied hand-converted homework `.md` files beside the PDFs' `processed_outputs` (same stem), `rebuild --course microecon`, `chunk --course microecon` in the background | none |
| Transcribe the TA solutions | `pipelines.transcribe_notes.transcribe_notes --notes-subdir academic_resources/microecon/<folder>` | not recorded |
| Plan | `plan`, then the review Artifact (120 proposed passages), then `apply-review` (all 120 kept) | none |
| Draft | `draft --max-cost 2.0`, `gemini-3.8-flash` | about $0.62 |
| Enhance | Section 6 only: `enhance --topics ... --worked-example --example-focus ...` | about $0.38 (including two rejected attempts) |
| Revise | `revise --max-cost 2.0 --skip-estimate-check`, then a review Artifact, then `apply-revise` | about $1.51 |
| Total in the guide stages | | about $2.5 |

Revise detail: 36 calls, 499k prompt, 25k output and 279k thinking tokens. The correctness audit
was $1.46 of the $1.51; relevance, dedup and organization together were about $0.05.

## Findings

1. **The draft prompt is subject-specific.** `guide_v1` asks for "the statistic, its distribution
   and the decision rule", which is econometrics wording. It produced an invented "test
   statistics and decision rules" block in the section on non-rational choice. Revise did not
   catch it. Fixed by hand; a neutral `guide_v2` prompt is on the to-do list.
2. **The relevance floor is tuned to one guide.** The 0.68 floor was carried over from the Wald
   guide. In this run 29 of 30 relevance deletes were primer blocks scoring 0.66 to 0.68, so the
   course evidence is thin for them by design. All 29 were rejected at review. On the to-do list.
3. **The correctness audit finds real errors but cannot act on them.** It found a convexity /
   concavity mix-up, a weak-versus-strict preference symbol error (fixed), a CES algebra error and
   the wealth error in the aggregation example. Edits of type `note` are only recorded; five were
   still unresolved after `apply-revise` and were fixed by hand.
4. **The audit missed two defects that a check against the assignment found.** The aggregation
   example's construction made a WARP violation impossible (both consumers had both bundles
   unaffordable in the other budget set, which forces the averages out of it too), and the
   quasi-linear convexity wording was wrong. An agent that can run code and compare against the
   assignment's own solutions would have caught both. This is the reason for the decision below.
5. **Citation stripping left debris.** About 100 section-sign fragments, 88 empty backtick pairs
   and about 40 stray semicolons survived `strip_citations` in five sections of the draft, from
   multi-citation parentheses written with semicolons. Cleaned by script; the stripper still
   needs those patterns and tests.
6. **A source typo reached the guide.** The course textbook prints a continuity counterexample
   with a strict inequality that makes the relation discontinuous. The guide copied it and then
   claimed it made no difference. Found by the assignment check, not by revise.
7. **Coverage gap.** The draft covered only one of the five utility functions' demands and none of
   the CES demand limits that question 3 asks for. The spec's topic instructions did not list them.
   Written by hand and verified numerically.

## Assignment check (done by hand; should become a pipeline step)

Each assignment question was compared against the guide and against the solutions document:
question 1 matched, question 2 matched except the typo above, question 3 had the gap and wording
errors above, and question 4 matched once the construction was fixed. The check also found a
formula error in the solutions document (a quasi-linear elasticity), confirmed numerically.

## Process notes

- Hand-converted markdown that has no source PDF cannot be indexed (hints, guided solutions,
  tutoring notes). Hand-converted copies of homework that does have a PDF are indexed by placing
  them under the PDF's stem.
- Excalidraw canvases need an exported `.svg` or `.png` beside each `.excalidraw.md` before they
  can be transcribed.
- A `kind = "file"` source rule needs the file's chunks in the index first. `plan --force`
  discards review decisions, so avoid it after a review.
- Costs: `--max-cost` on draft and revise, `--dry-run` first, and the audit cache made reruns cheap.
  The first revise estimate ($1.07) was low against the real $1.51 because thinking tokens bill as
  output.

## Decision: subscription agent as the default run mode

Cost and reliability point the same way. The audit, the stage that costs the most, is also the one
that most needs to run code and cross-check against the assignment. The owner decided the
subscription agent (Claude Code or Antigravity) should be the default for drafting and auditing,
with the current API path kept for users without a subscription. To be designed in a brainstorm;
both modes share the neutral prompt and the per-course floor. Tracker entry in
`docs/trackers/academic_hub_to_do.md`, "Study Guide Pipeline".

## Commits (unpushed, branch `claude/study-guide-spec`)

Draft `--max-cost`; link and empty-math citation stripping; enhance `--topics`; plain-text
citation instruction in the draft prompt; `--example-focus`; spec sources. Tests: 1,014 agent
tests passed at the last full run.
