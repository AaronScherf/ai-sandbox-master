# Guide revise pipeline: design

Date: 2026-10-08. Status: proposed (not yet planned or built). Package: `agent/study_guide` (new
`revise` stage), reusing `summary_enhance`'s guide loader. Related: the
[study guide pipeline design](2026-10-05-study-guide-pipeline-design.md) and the
[comparison status](../../../status/agent/2026-10-07-study-guide-comparison-status.md).

## Purpose

The pipeline has produced a large topic-first Wald/LM/LR draft (about 39,000 words) that the owner
judges good but uneven: repeated material across sections, a comparison section that restates the
earlier ones, an irrelevant software-packages section, and unverified numbers in constructed
examples. More length will not help. A **revise** stage refines an already large guide against
criteria and changes it as little as it can.

Stage order: `plan` -> `draft` -> `enhance` (the **extend** role: deepen thin sections or add
topics) -> `revise` (this document) -> published guide. Revise is a separate stage because it works
differently from extend:

| | Extend (`enhance`) | Revise |
|---|---|---|
| Goal | add depth where the guide is thin | refine a large guide against criteria |
| Input | short draft plus a wide set of passages | whole guide plus course evidence (exams, problem sets, syllabus) |
| Scope | one topic at a time | per-section audit, then a whole-document pass |
| Output | regenerated sections | a reviewed edit list, applied deterministically |

## Criteria

1. **Relevance**, weighted by course evidence: past exams and problem sets carry the most weight,
   then the syllabus and lecture/recitation notes, then textbooks alone. Material no course source
   points to (for example software packages, AIC/BIC model selection) is proposed for removal or
   shrinking. Material tied to exam or problem-set content is protected.
2. **Deduplication**: the same concept, derivation or formula restated in several sections without
   added value. Keep the most useful location; replace the others with a one-line cross-link.
3. **Correctness**: every claim, equation and number is supported by that section's source
   passages or is a labelled constructed example; recompute arithmetic; flag unsupported,
   contradicted or miscalculated items. No hallucinated content.
4. **Organization**: a sensible heading hierarchy (no H1 in the body, no skipped levels, consistent
   titles, logical order, a table of contents), checked mechanically as well as by the model.

## Non-goals

Adding new source claims or sections (that is extend); increasing length; stylistic rewriting;
re-running retrieval; changing the plan. A revise pass must never make the guide longer, and never
introduces a claim that no passage supports.

## Inputs

- The guide: a draft or an enhanced guide (`.md` with frontmatter). Enhanced output is parsed from
  its rendered markdown; the frontmatter `topic_sources` (draft) or `source_map` (enhanced) tells
  which passages back each section.
- The plan (per-topic accepted passages), used as the evidence for the correctness audit.
- **Relevance evidence**, configured in a `[revise]` table added to the guide spec (the rule schema
  is the existing `[[topic.source]]` one, so no new selection code):

```toml
[revise]
model = "gemini-3.8-flash"
criteria = ["relevance", "dedup", "correctness", "organization"]

  [[revise.evidence]]            # kind/file/discover rules exactly as in topics
  kind = "file"
  file = "class_2024/processed_outputs/2024 midterm-ans-key.md"
  weight = 3.0                   # exams and graded problems

  [[revise.evidence]]
  kind = "discover"
  doc_types = ["problem_set", "excalidraw_questions"]
  weight = 2.0

  [[revise.evidence]]
  kind = "file"
  file = "syllabus/processed_outputs/ec6411A.md"
  weight = 1.5
```

  The doc-type labels in the index are not reliable (the 2024 midterm key is typed `ta_notes`), so
  evidence is pinned by file or doc type in the spec, not inferred. Tutoring-session transcripts
  (see the pipeline design's "Planned input" section) become one more evidence source: a section
  where the student needed repeated help is protected and flagged as a candidate for fuller
  explanation by extend, not trimmed.

## Stages

Every stage reads and writes JSON next to the plan (`guide_plans/<id>.<tag>.revise.json`); paid
calls happen only in stages 3 to 5. Each stage can be run alone (`--stages`).

1. **Segment.** Split the guide into blocks with stable ids: a hash of the heading path and the first
   200 characters. Record words, display equations, citations, headings and whether the block is
   a constructed example. Pure code.
2. **Relevance score** (embeddings only, no generation). Embed each block; score it against every
   evidence chunk; `score = max(similarity x weight)`. Report per block the score and its nearest
   evidence citations. Blocks below a threshold become `remove` or `shrink` proposals; blocks above a
   protection threshold are marked protected (a delete proposal on a protected block needs explicit
   owner confirmation). Borderline blocks go to an LLM judge with the evidence in the prompt.
3. **Deduplicate.** Cluster blocks by embedding similarity and by overlap of normalized LaTeX
   (strip spacing and macro aliases). For each cluster the LLM picks the canonical block and
   proposes `merge` or `link` edits for the others, quoting the redundant text.
4. **Correctness audit.** One call per section using that section's plan passages only (the same
   per-topic scoping as `enhance --baseline per-topic`). The model lists claims, equations and numbers
   with a verdict: supported / unsupported / contradicted / arithmetic error / constructed. Arithmetic
   in worked and constructed examples is recomputed with code execution. Each non-supported verdict
   yields a `fix` or `delete` edit that cites the passage label it relies on.
5. **Organization.** One call over an outline of the guide (headings, word counts, relevance and
   duplicate flags, no body text) proposing `retitle`, `move`, `demote`/`promote` and a table of
   contents. Mechanical checks run first and are enforced after.
6. **Edit report.** All proposals merge into one list. Each edit:
   `{id, type: delete|shrink|merge|link|fix|move|retitle, targets: [block ids], rationale, evidence:
   [citations], severity, confidence, replacement: text|null, protected: bool}`.
7. **Review.** Per the project rule for human decisions, the edit list is published as an interactive
   Artifact: before and after text, rationale, evidence, accept/reject per edit, bulk actions per
   type, protected edits flagged. Decisions are read back and applied by the pipeline, not by hand.
8. **Apply** (`apply-revise`, deterministic, no model). Applies the accepted edits by block id and
   writes `<guide>.revised.md` plus a changelog. Post-conditions are checked and a failure aborts
   without writing: every accepted edit applied exactly once; blocks without an edit are byte-for-byte
   unchanged; no new citations or claims introduced; total words not increased; heading rules hold;
   display equations decrease only by accepted deletions or merges.

## Commands

```
python -m agent.study_guide revise       <spec> --guide G [--plan P] [--stages ...] [--dry-run] [--tag T]
python -m agent.study_guide apply-revise <spec> --guide G --decisions <file>
```

`--dry-run` prints the block count, the evidence chunk count, which stages would make paid calls and a
prompt-size estimate (and, once run, the recorded token usage), as the other stages do.

## Cost

Stage 2 and the clustering in stage 3 need embeddings only. Stage 4 sends each section with its own
passages: for the current guide about 1.1 million characters (roughly 320k tokens) in total, like the
per-topic `enhance` dry-run. Stage 5 sends an outline only. Total is roughly the cost of the draft
stage; there is no whole-guide-per-call stage.

## Extend: what `enhance` needs for its role (done 2026-10-08)

`enhance` already supplies per-topic source scoping, grounded versus external blocks, validation
against the topic's passages, worked examples and, now, `--baseline per-topic`. Gaps closed so that
it is the extend stage (`--only-below WORDS`, a missing section under `--baseline per-topic` written
fresh with a printed note, `--carry-before`/`--carry-after` filled in by the study_guide command from
the spec's notes and comparisons, and a `usage` field in the output frontmatter):

1. Act only on thin sections: a per-topic minimum or an "only below N words" switch, so sections that
   meet the bar pass through unchanged.
2. Allow a topic with no baseline section (a newly added topic is written fresh) under per-topic
   baseline; today that is an error.
3. Carry `[[note]]` and `[[comparison]]` sections through, as the draft does.
4. Record token usage in the output frontmatter and print it, as the draft stage now does.

## Testing

All unit tests use a fake LLM, fake embeddings and small fixture guides; no paid calls. Cases: segment
ids stable across edits to other blocks; relevance ordering with weights; protected block deletion
refused; near-duplicate clusters from reworded LaTeX; the audit's verdict parsing and the arithmetic
recheck; heading validation; apply post-conditions (a failing one aborts and writes nothing); apply
idempotence (applying twice does not change the result).

## Risks and open questions

- Thresholds for relevance and duplication need calibrating on this guide, with the owner's review of
  the first edit report.
- The correctness audit can only check against the passages the plan supplies; an error in the
  passages themselves (for example a transcription error in class notes) passes unnoticed. A second
  model for the audit is an option if the first report shows missed errors.
- Constructed examples are labelled but have no source; whether to keep them after an arithmetic check
  or leave them to the owner is a review decision, shown as such in the Artifact.
- Edit anchoring by block id breaks if the guide is edited between `revise` and `apply-revise`;
  apply refuses when the guide's hash differs from the one recorded in the report.
- "Scope before retrieval" (choosing relevant topics from the syllabus, exams and notes, or
  interactively, before pulling textbook passages) addresses relevance upstream and is a separate
  design; revise is the backstop that catches what slips through.

## Build order

1. Segment and the block table; heading validation.
2. Relevance scoring with evidence loading from the spec's `[revise]` table.
3. Edit report format, apply stage and post-condition checks (testable without any model).
4. Review Artifact.
5. Dedup clustering, then the correctness audit, then the organization stage (the paid stages last).
6. Run on the topic-first a3 guide and compare with the owner's v4 guide.

## Out of scope

Automated scoring against an answer key, multi-guide reconciliation, translating the guide, and
editing the source passages.
