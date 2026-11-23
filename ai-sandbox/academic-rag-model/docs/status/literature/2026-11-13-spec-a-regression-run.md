# Spec A regression run: 20-paper trial batch (2026-11-13 to 11-14)

Index root: main checkout `ai-sandbox/research` (178 cards, all with transcripts and page markers; 159 research papers after excluding personal essays and research notes). Batch: the first 20 papers by `file_id`. Agent: subscription Gemini through Antigravity, one session per run. No paid API calls.

## Runs

| Stage | Cards | Applied | Bounced (final) |
|---|---|---|---|
| metadata (OpenAlex) | 11 with DOI | 11 | n/a |
| classify a (full) | 20 | 20 | 0 |
| classify b (discipline check) | 20 | 20 | 0 |
| tag intervention L1 / L2 / L3 | 19 / 9 / 9 | all | 0 |
| tag outcome L1 / L2 / L3 (v1) | 19 / 9 / 9 | all | 0 |
| tag outcome L1 (v2), L2 (v2) | 19 / 3 | all | 0 |

Quote rejections: none. Every manifest shows `attempts: 0` for every card, so no card was ever bounced in the trial. (Since 2026-11-14 a manifest also keeps `bounce_log`, the reasons of each bounce, after the card is applied.)

## Results

- **Discipline:** passes a and b agreed on 20 of 20 (same model, so a weak check). OpenAlex topics decided 7, the model 13. Review queue: 5 items (3 discipline disagreements with OpenAlex, 2 DOI/title mismatches).
- **Applicability (after v2 outcome prompt):** 9 both, 3 outcome_only, 7 not_applicable, 1 not_assessed. Before v2: 9 both, 0 outcome_only, 10 not_applicable.
- **Tags by level:** intervention 10 / 10 / 9, outcome 12 / 15 / 13 (levels 1 / 2 / 3). No level 2 outcome tag lacks a level 1 parent.

## Findings

1. **Outcome-only papers were missed under the first tagging prompt.** The agent treated "no intervention" as "nothing to tag". Fixed by telling it each kind is tagged on its own (prompt `tag-v2`, `tagging.py`); re-run gave 3 outcome_only (mental health of IDPs, legislator responsiveness at sector level, student perceptions at sector level).
2. **Open owner question:** `outcome.education` on the student-perceptions survey (`0a77c9527b24af63`). Owner thinks perceptions are not an outcome; v2 may over-tag. Not yet changed.
3. **Title check false positive (fixed 2026-11-14):** a card title that is the registry title minus its subtitle was flagged as a DOI mismatch (`1ecd67b2dcea6fb9`). `title_match` now accepts a prefix of at least 6 words ending at a word boundary. A second mismatch (`0d683d8c58e1fd52`, preprint DOI vs published version) looks real.
4. **Encoding:** the registry title shows a replacement character in one record; harmless but visible in the queue.
5. **Not-applicable review:** [2026-11-14-trial20-not-applicable-review.md](2026-11-14-trial20-not-applicable-review.md). Owner confirmed #7 should get an outcome, #4 is right as `not_applicable` under the v1 prompt, #3 uncertain.
6. **Parallel handoffs:** filling cards is parallel-safe, submit is not (shared shards, no lock). Rule added to `docs/AGENT_ROUTING.md`.

## Full run (159 research papers, 2026-11-14 to 15)

One Antigravity coordinator session dispatched subagents per batch (shared workspace, never submitting); the coordinator submitted every run serially. It was interrupted once by a Gemini quota error (429, 3h 46m reset) and resumed in a fresh session; the runbook resumed cleanly because state is on disk.

| Stage | Cards (intervention + outcome where tagged) | Applied | Bounces recovered |
|---|---|---|---|
| classify a / b | 139 / 139 | all | 4 (3 empty fields, 1 `WinError 5` on the index rename; resubmit applied it) |
| tag L1 | 132 + 132 | all | 1 (quote not found) |
| tag L2 | 72 + 72 | all | 0 |
| tag L3 | 71 + 72 | all | 0 |

The coordinator's own report said 0 bounces and 135 / 134 cards at L2 / L3; the manifests (and their `bounce_log`) are the record. All 159 profiles are complete, every shard parses, and no temp files remain.

- **Applicability:** both 71, not_applicable 56, outcome_only 14, intervention_only 10, not_assessed 6.
- **Review queue:** 33 items on 29 papers. 18 papers have both agents agreeing with each other against the final discipline label, which OpenAlex decided when its topic share was at least 0.8 (`discipline.resolve_discipline`). Open design question, in the review file section D.
- **Quota measurement (cards only, about 4 characters per token, no output tokens):** about 11.6M input tokens across the run; a tagging card has a median of 88k characters (largest 318k, 147 pages) versus 21k for a classification card. The top 10 papers are 19% of the volume, so a few long papers do not drive the cost. The driver is repetition: each paper is read once per kind per level, and intervention and outcome cards carry identical pages. About 7.8M tokens were read in the hour before the 429. Timestamps are mostly write times, so burst versus window limit is not settled.
- **Owner review file:** [2026-11-15-full-run-review.md](2026-11-15-full-run-review.md) (56 not_applicable, 6 not_assessed, the queue). The dry-run folder plan is [2026-11-15-full-run-folder-plan-dryrun.txt](2026-11-15-full-run-folder-plan-dryrun.txt); nothing has been moved.

## Owner review round (2026-11-16)

Decisions came through the Corpus Review Desk Artifact (db collection `verdicts`).

- **Discipline rule:** OpenAlex stays the authority when its topic share is at least 0.8. Disagreement is no longer a review item. Instead (`discipline.resolve_discipline`) every paper keeps a **secondary discipline** (the runner-up of the pooled evidence: primary agent, second agent and OpenAlex topic shares), a `discipline_fit` of `clear` or `mixed` (clear needs a pooled score of at least 0.6 and a lead of at least 0.3 for the primary), and `discipline_scores` (top three). When OpenAlex is not strong, the primary is the best pooled label (ties go to the primary agent). After `refresh-discipline` over all 159: 133 clear, 26 mixed; 48 papers have a secondary, since a paper with agreeing agents and no OpenAlex topics has no second label to draw on.
- **Owner overrides recorded** (`decisions.json`): discipline for 5 papers (3 to the agents' label, 2 to agent b's), bibliography accepted for 4 (`1ecd67b2dcea6fb9`, `3268b7062f1745f2`, `0d683d8c58e1fd52`, which Crossref shows is the preprint of the registry DOI, same authors) and corrected for 1 (`b15db8674b100150`). The queue is empty.
- **Titles:** 12 cards without a title got one read from the first page or the audit.
- **Not assessed:** these are papers whose report type is not taggable (`book_chapter`, `book`, `notes`). Owner ruling: book chapters are not tagged for interventions or outcomes (they seldom report evaluation results); they stay `not_assessed`.
- **Not-applicable audit (11 papers read in full by two subagents, 56 in total):** 6 correct, 5 flagged. One clear miss: a systematic review of drought climate services (`24aa1b3dca4604e8`, intervention and outcome). Four borderline: two more systematic reviews (`aa67c670d7922b61` LLMs in clinical workflow, `229232bd0bc10a73` climate risk assessments), a UNDP programme case study (`e3e79699db0aa55c`) and a proposals-coding paper (`5aee159f2da0b7d0`, interventions proposed, not evaluated). Pattern: 3 of 4 systematic reviews were skipped although a review reports the interventions it synthesises. Candidate fix: tell the tagger that a synthesis paper counts for the interventions and outcomes it synthesises (new prompt version, rerun on synthesis papers only).

## Not done

`folders apply` (needs the owner's approval of the dry-run plan, now refreshed with the overrides), the review-synthesis tagging prompt change and its rerun, the eval harness against the 3ie CSV, the blind-label Artifact, the merged intervention-plus-outcome tagging card to cut quota use, and the whole-branch final review.

## Synthesis re-tag (tag-v3, 2026-11-19)

Prompt line added: a review or synthesis counts as reporting the interventions and outcomes it synthesises. Rerun on 28 review-type papers not already tagged "both" (1 skipped: over the card limit, `e1a082e5886cca32`). Gemini ran 76 cards, 0 bounced; verified from the index.

- Moved out of `not_applicable`: `24aa1b3dca4604e8` (both), `aa67c670d7922b61` (intervention), `8e601f62d25fc509` (intervention), `840c969e0d28b33b` (intervention). `not_applicable` 56 -> 52.
- Stayed `not_applicable` (22): mostly methodology and discussion papers (GRADE, DAGs, trial sequential analysis, evidence gap maps), plus `229232bd0bc10a73` and `5aee159f2da0b7d0` from the audit.
- Others already tagged kept or changed kind: `d688c2e9cec6e735` and `670e9034b3a6ec4d` outcome_only.
- Not rerun, still untagged: `e1a082e5886cca32` (needs a split or a raised card limit).
