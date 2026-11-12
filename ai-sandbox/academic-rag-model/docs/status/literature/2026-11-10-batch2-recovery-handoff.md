# Batch 2 recovery: approved design and Codex handoff (2026-11-10)

Owner approved this design on 2026-11-10. Claude designed it; Codex implements the code in a dedicated `codex/<task>` worktree; subscription Gemini fills cards. Context: [batch 2 rejected and restored](2026-11-06-term-selection-trials.md#batch-2-rejected-and-restored-2026-11-10) and [the design request](2026-11-10-batch2-design-handoff.md). Based on `codex/literature-rollout` at `b425dfbc`.

## Out of bounds (do not do)

- Do not change the 3ie vocabulary, `CHOOSING_RULE`, or `FIT_TEST_EXAMPLES` in `stage.py` (shared with the extract card). All edits go in `refine_grain.py`.
- Do not accept, reject, or resolve proposals (P0172 `FinTech coverage` stays open).
- Do not resubmit `rollout-refine-v3-b2-20261110` (applied historical artifact) or submit `rollout-verify-after-b1-20261108` (stale REDDI checker card).
- Do not re-run batch 1 or the REDDI correction; those records are accepted.
- No paid API calls. Warn the owner before anything estimated over $1.
- Do not run `tiers`, `verify` or `db build` on trial records until the owner says so.

## Diagnosis (why batch 2 failed)

1. `scope_roots` (`refine_grain.py:51`) anchors the listing on the roots of the paper's own current facts, else its sector. A paper with an agriculture-only fact never sees other branches. `proposed: true` was allowed, but the card never said it was the expected move for out-of-scope subjects.
2. `INSTRUCTIONS` never defines what counts as a fact. "The paper itself does, studies or measures" is written as a gate for choosing a *child*; Gemini applied it as a gate for *listing anything*, then used "Write [] for a facet the paper does not give" to empty facets of simulations and reviews.

## Approved decisions

1. **Out-of-scope subjects: propose, do not widen.** The listing stays scoped. The card tells Gemini to write `proposed: true` for an intervention/outcome the paper reports outside the offered branch. No `scope_roots` change now; revisit only if trials show unmanageable proposal volume.
2. **A fact is anything the paper itself reports** (evaluates, models, simulates, reviews, designs, measures). Fit test governs only *which term*, not *whether to list*. `[]` is correct only when the paper names no such object of its own analysis; background, motivation and citations do not count.

   | Paper type | Intervention | Outcome |
   |---|---|---|
   | Empirical evaluation | programme evaluated | outcomes estimated |
   | Simulation / model | each policy the model runs or compares | outcomes it produces or compares |
   | Systematic / narrative review | programmes the review examines as its subject | outcomes it synthesises |
   | Conceptual / commentary | `[]` unless it analyses a named policy | `[]` unless it names outcomes it argues about |
   | Observational | exposures framed as policy/programme, else `[]` | measured dependent variables |

   `study_design` stays separate (commentary and conceptual use `narrative_review`). Settled owner decisions stand: individuals fall under households; adopting adaptation measures is not resilience.
3. **New version `refine-v4`**, fresh cards. The prompt text is the card; reusing `refine-v3` would let `make_tasks` skip v3-stamped papers and blur provenance of the rejected b2 results.

## Codex implementation

All in `agent/literature/refine_grain.py` (+ tests under `tests/agent/literature/`).

1. `PROMPT_VERSION = "refine-v4"`.
2. In `INSTRUCTIONS`, replace the line `- Be complete: list every distinct intervention and outcome the study itself reports, not only the main one.` with:

   ```
   - What to list: list every distinct intervention and outcome the paper itself reports. That includes ones it evaluates, models or simulates, reviews as a subject of the review, designs, or measures; it does not need to estimate a causal effect. The fit test above decides which term to use, never whether to list a fact. Do not list items that appear only as background, motivation, or in citations.
   - If the paper reports an intervention or outcome that is outside the branch offered below, do not leave it out and do not force a listed term: write it with `proposed: true`.
   ```

3. Replace the last line `- Write [] for a facet the paper does not give.` with `- Write [] for a facet only when the paper reports nothing of that kind as part of its own analysis.`
4. Check `refinement_state.py` and `status`: papers stamped `refine-v3` (batch 1, REDDI) must not become "stale" or be re-staged merely because `PROMPT_VERSION` moved to v4. Choose the smallest mechanism (e.g. treat v3 and v4 as both current, with the v3 set named explicitly) and test it. If this is non-trivial, report back instead of widening scope.
5. Confirm a way to stage a chosen list of papers (e.g. `--papers` / file-id filter on the stage command). Add the smallest one if absent.
6. Tests: card contains the new fact rule and proposal sentence; the shared `CHOOSING_RULE` text is byte-identical to before; `make_tasks` stages v1-stamped papers under v4 and skips v4-stamped ones; selection filter works; status counts v3 as current. Run `python -m pytest tests/agent/literature/`.
7. Stage the trial run (below) as pending cards only. Do not submit.

## Trial (before any 70-card run): 8 papers, 16 cards, subscription Gemini

Run name suggestion: `rollout-refine-v4-trial-20261110`.

| Slot | Paper |
|---|---|
| Out-of-scope empirical | `0bc75ee4d419ba1e` (Rwanda mobile-network subsidy) |
| Model | `0d683d8c58e1fd52` (index insurance, remittances, cash transfers) |
| Review | `b52cb3c54136c4df` (cash-plus programmes, livelihoods) |
| Nonempty control | one `refine-v1` paper whose current facts Codex has already checked against the text |
| Empty/conceptual control | one commentary or conceptual paper |
| 3 more | drawn from the 24 papers with no facts in either pass; pick different types (observational, simulation, review) |

Codex selects the unnamed five by the type-spread rule and records the choices and reasons in the run notes.

Submit order: Rwanda, model, review, controls, then the rest. A Gemini limit mid-run: stop, keep the same run, resume later. Do not regenerate cards. Validate before applying any partial submission.

**Pass criteria** (judge against the paper text and the official 3ie definition, never against old `refine-v1` facts):

1. The three known false negatives are now nonempty, each with a quote showing the paper itself reports the item.
2. Codex reads the sources for the three extra papers and finds no clear omission (at most one minor).
3. The conceptual control stays `[]`, or lists only items the paper genuinely analyses. The nonempty control keeps its labels or changes with a defensible reason.
4. No child term without a quote of the paper doing what its definition says. The Rwanda paper yields at least one non-duplicate `proposed` fact.
5. Smoke alarm only: counts across the 8 papers should not fall below pre-rollout without an explained cause.

Report per paper: facts, quotes checked, false negatives, any proposals created. Codex does the quote/page check; the owner makes the pass/fail call.

**Gate.** Pass: ask the owner before the remaining 27 papers (54 cards), in sub-batches of ~10 papers, auditing 3 papers per sub-batch. Fail: report the pattern to Claude; do not run more cards. Owner decides whether trial records that pass stay applied (so those papers are not repeated).

## Stale artifacts and rebuild

Stale: `rollout-refine-v3-b2-20261110` manifest and its 70 cards (old wording); `rollout-verify-after-b1-20261108` (stale REDDI card). Current live state: batch 1 + REDDI correction accepted; the 35 `refine-v1` papers restored to pre-rollout records (backups under `research/.agent_work/term-selection-trials/data/`).

After the full rollout succeeds (not after the trial alone), in order: regenerate verification cards, submit checker results, `tiers`, `db build`, then re-check leaf concentration against the 10% bar. Update this status area with final numbers.

## Owner items still open

- Whether passing trial records stay applied.
- P0172 and any proposals the trial creates.
