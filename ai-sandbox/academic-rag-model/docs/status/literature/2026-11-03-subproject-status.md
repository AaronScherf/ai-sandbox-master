# Literature taxonomy: subproject status (2026-11-03)

Branch `claude/literature-reextract-v4`. Scope: `agent/literature`. Aggregates only: no paper text or quotes appear here.

This is the one-page picture. Detail lives in the documents linked under "Where the detail is".

## Where we are in the plan

The plan is the [discovery roadmap](../../superpowers/specs/literature_taxonomy/2026-10-31-literature-discovery-roadmap.md): get the taxonomy
good enough, then design and build an opt-in loop that finds external works when a gap run finds the corpus thin.

| Roadmap phase | State |
|---|---|
| Phase 0: housekeeping (gap rules and minors, `status` and coverage count fixes) | Landed on main, per the handoff. TODO-0091 (reference data separated from the vocabulary directory) not re-checked in this session. |
| Phase 1: quality gate on the taxonomy as it is | **Precision criterion met** on a sound method (A+B 0.88 weighted, 0.90 unweighted [0.84, 0.94]; see the [Phase 1 doc](2026-11-02-phase1-quality-gate.md)). Still open: the two proposals on eligible papers, and the taxonomy questions below. Recall unmeasured. |
| Phase 2: design the discovery loop (brainstorm, then spec) | Not started. Blocked on Phase 1 only for confidence in the extraction it will multiply. |
| Phase 3: build | Not started. |
| Phase 4: worktree cleanup (TODO-0092) | Tool landed and tracker item closed; one more `--apply` run is due once the merged worktrees pass 24 hours. |

## What has shipped (on main unless noted)

- Extraction with two independent passes, a checker, and confidence tiers A, B and C (stage 2); synthesis (stage 3); the query database; gap
  analysis with an opt-in OpenAlex recall probe (stage 5, slices 1 and 2); grain refinement.
- Card limit raised from 240,000 to 300,000 characters, which brought three large papers into the corpus.
- The review-paper rule (`extract-v4`): a country must be the paper's own sample or setting, and a review lists only data it analysed.
- On this branch, not yet landed: the review-rule results in the Phase 1 status doc, and this document.

## State of the data (database of 2026-11-03)

- 82 papers with a record; 15 excluded as off-topic; 67 in analyses. Five duplicate-title copies are never extracted.
- Facts: tier A 411, tier B 130, tier C 77. The database loads A and B: 541 facts.
- The eight papers that held wrong facts were re-extracted under `extract-v4` (2026-11-03). Both passes were redone, and verification was redone for the five whose passes disagreed.
- Open vocabulary proposals: 2 (one on a re-extracted paper, one on `7f88458c5df631df`, which was not re-extracted). The Phase 1 doc counted 0 open on
  eligible papers on 2026-11-02, so I do not know yet why these appeared; check before reviewing them.

## What has worked well

- **Two passes plus a checker.** Tier A (both passes agree) is 411 of 618 facts, and tier C reliably flags the weak ones: in the Phase 1 sample tier C
  was 40% supported against 83% to 90% for A and B.
- **Trials with restore.** Running a rule change on ten papers, then restoring the records, let the review rule be measured before it touched the
  database: all 14 wrong countries removed, none of the correct ones lost (trial 2).
- **The review rule worked where it was aimed.** On the eight re-extracted papers, countries drawn from example lists were removed (all ten from
  one review), and four of the five known wrong data sources went. Two papers still list several countries (3 and 7); I did not check whether those
  are the paper's own sample.
- **Byte-identity check on Gemini runs.** A trial that only looks like a re-extraction is caught by comparing against the backed-up records.
- **Division of labour.** Gemini operates pipeline runs on subscription; Claude designs and reviews; the owner makes judgments. No paid API calls so far.

## Challenges and what we learned

1. **Quote-only judging cannot score paper-level labels.** The Phase 1 audit and the 2026-11-03 sample both asked whether one quote supports a label.
   Sector, population, intervention and data-source labels describe the whole paper, so neither Gemini nor the owner could tell from a fragment.
   Result: 85 supported, 28 not supported, 37 unsure of 150 (strict 0.56). **That figure measures the method, not the labels. Do not cite it.**
   Replaced by a paper-level pass (full text plus labels, no quotes or tiers), then an owner audit of the contested labels with evidence pages: A+B 0.88
   weighted. Lesson: judge a paper-level label against the paper, and keep human audits to the contested few.
2. **Verification goes stale after re-extraction.** `verify` matches verdicts on facet, label and pass, and skips a paper whose transcript hash is
   unchanged. Re-extracted records therefore kept the old verifiers' verdicts; a new tier B fact could inherit one. Handled by hand with
   `verify --redo` on the five affected papers. It needs a code fix before the next re-extraction (see Next steps).
3. **Outcome facts fall under `extract-v4`:** 29 to 22 across the 16 re-extracted records, and 37 to 27 in the earlier trial. Probably the rule or a
   more conservative run; unconfirmed. Recall is unmeasured, so a drop cannot yet be called a loss.
4. **Rule trade-offs.** One correct data source (programme documents) was lost on the priority cash-transfer review in both trials. One Nepal portal
   fact survived both passes as tier A and was removed by hand from the record (the only manual edit; the pre-edit records are backed up).
5. **Tier A is not more precise than tier B**, even at paper level (0.87 against 0.93, within noise). Two-pass agreement does not buy precision in this
   sample; it may mainly select facts that are easy to find. Do not treat "tier A" as "more correct" in the discovery loop without more evidence.
6. **Same design, two labels.** In one paper a single design was labelled differently by the two passes, leaving a tier B fact beside a tier A
   fact for the same thing. A vocabulary-grain question, not an extraction error.
7. **Recall is unmeasured** (the owner chose to skip it for now). A "no evidence in corpus" gap verdict can still mean a missed fact.

## Questions for the taxonomy (from the owner's audit, 2026-11-03)

Checked against the vocabularies in `agent/literature/vocab_data/` and `research/resources/3ie/vocab/`. Each needs an owner decision.

1. **Individuals against households.** No individual-level term exists. Population has `households`, `general_population`, `women`, `children` and
   so on; data sources have `household_survey` and `panel_survey`. A survey of camp residents and a study of phone subscribers were labelled
   `household_survey` and `households`; the owner judged the distinction minor in practice. Options: add `population.individuals` and an
   individual-survey source, or widen the household terms' definitions to cover individuals. Not decided.
2. **What counts as "Resilience".** The owner accepted adaptation-adoption and farm-return outcomes as resilience, while Gemini rejected them as
   mere motivation. The term is vague; its definition decides the call. Needs a written inclusion rule.
3. **Non-empirical papers.** `narrative_review` and `systematic_review` exist, but there is no term for a commentary or conceptual piece. Two
   papers were labelled `qualitative`: one is probably a narrative review (a term-choice error), the other a commentary (a vocabulary gap).
4. **Over-specific adoption terms.** The outcome vocabulary lists many "adoption of recommended X practices" terms (planting, seed selection,
   fertiliser, harvesting, and an umbrella index). A planting-and-seed paper was labelled harvesting: a wrong pick where the right terms exist.
   Candidate remedy: a stronger prompt instruction to choose the closest sibling, or a prompt example.
5. **Plain wrong picks** the owner upheld (pastoralists, communities, agrobiodiversity, a conflict sector label, administrative records, food
   subsidies on a handset-subsidy paper): extraction errors, not vocabulary questions.

## Open decisions

- The four taxonomy questions above (1 to 4).
- The two open vocabulary proposals; the grain question in item 6.
- When to measure recall (the roadmap says before the discovery loop scales up).
- Adjudication for real disagreements between passes: deferred.

## Next steps, in order

1. Done: paper-level precision pass, owner audit of the contested labels, Phase 1 doc updated.
2. Owner decisions on the taxonomy questions above; then a prompt or vocabulary change and a re-extraction trial, if any.
3. Find out why two proposals are open on eligible papers (Phase 1 said none), then review them.
4. Make re-extraction invalidate stale verification (spec for Codex: clear or re-key a record's verification when its transcript or facts change, with
   a test). Not started.
5. Phase 2: brainstorm the discovery loop with the owner, then write the spec. Held-out probe split and classification card are the first decisions.
6. Worktree cleanup: dry run, then `--apply` once the merged worktrees are over 24 hours old.
7. Landing: owner runs `land_branch check --full`; nothing on this branch is landed.

## Where the detail is

- Spec and plan (design):
  [pipeline design](../../superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md),
  [grain refinement](../../superpowers/specs/literature_taxonomy/2026-10-25-grain-refinement-design.md),
  [synthesis](../../superpowers/specs/literature_taxonomy/2026-10-21-stage3-synthesis-design.md),
  [gap analysis](../../superpowers/specs/literature_taxonomy/2026-10-29-literature-gap-analysis-design.md),
  [recall probe](../../superpowers/specs/literature_taxonomy/2026-10-31-literature-gap-recall-probe-design.md),
  [roadmap](../../superpowers/specs/literature_taxonomy/2026-10-31-literature-discovery-roadmap.md).
- Plans:
  [grain refinement](../../superpowers/plans/2026-10-25-literature-grain-refinement.md),
  [gap analysis slice 1](../../superpowers/plans/literature_taxonomy/2026-10-29-literature-gap-analysis-slice1.md),
  [recall probe](../../superpowers/plans/literature_taxonomy/2026-10-31-literature-gap-recall-probe.md). Phase 2 and 3 plans do not exist yet.
- Status history: [stage 2 extraction](2026-10-16-stage2-extraction.md), [stage 3 synthesis](2026-10-22-stage3-synthesis.md),
  [stage 5 gap analysis](2026-10-29-stage5-gap-analysis-slice1.md), [Phase 1 quality gate](2026-11-02-phase1-quality-gate.md).
