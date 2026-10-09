# Study guide pipeline: first comparison runs (B0, B1, B2, E1) and the v4 benchmark

Status as of 2026-10-07. Pipeline: `agent/study_guide` (spec, plan, draft, enhance) on branch
`claude/study-guide-spec`, built from
`docs/superpowers/plans/2026-10-05-study-guide-pipeline.md`. Design:
`docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`. Baseline provenance:
`docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md`.

All generated guides stay in the private notes vault (`academic_notes/econometrics/summaries/`).
This document records metrics and structure only; it quotes no source or guide text.

## Verdict

1. **E1 (improve mode on `gemini-3.8-flash`, worked examples on) is the quality floor.** The
   guide's owner reviewed it and judged it the minimum acceptable output. Thoroughness (long
   derivations, formulae, worked examples) matters for PhD-level study, and a thorough guide can
   be shortened later by a summarizer, but a short one cannot be re-expanded. This reverses the
   first read in the same session, which preferred B2 for being shorter and easier to study from.
2. **B0, B1 and B2 (draft stage only) are too short and too conceptual.** They also carry a
   "Retrieved sources" list under every section, which breaks up the content, and the section
   links are not clickable in Obsidian, so the lists have no use for studying.
3. **Every run organises the guide by textbook section instead of by topic** (see "Why the
   guides are split by textbook"). This is the main structural defect to fix next.
4. **The owner's own v4 guide (hand-edited after a Gemini web-app session) contains sections E1
   lacks:** formula dictionary, step-by-step recipes, worked exam problems and a cheat sheet.
   The pipeline should be able to generate these.
5. **Score threshold:** keep more candidates; the threshold should be loosened (see
   "Retrieval").

## What was run

| Run | Command | Model | Sources | Output |
|---|---|---|---|---|
| B0 | `draft` baseline spec | `gemini-3.1-flash-lite` | 24 passages from section rules (plan: 21 distinct chunks) | `wald_lm_lr_tests.b0.md` |
| B1 | `draft` new-material spec | `gemini-3.1-flash-lite` | 106 passages (pinned class files + 33 kept of 48 discovered) | `wald_lm_lr_new_material.b1.md` |
| B2 | `draft` new-material spec, `--model` | `gemini-3.8-flash` | same 106 | `wald_lm_lr_new_material.b2.md` |
| E1 | `enhance --mode improve --worked-example --output` on the original guide | `gemini-3.8-flash` | 68 chunks (the plan's passages plus the original guide's own 16) | `wald_lm_lr_tests.enhanced.e1.md` |

B1 isolates the new material (same model as B0). B2 isolates the model (same sources as B1). E1
is option 2 from the original request: improve the existing guide using the new information.
The original guide was read, never modified.

| Run | Words (answer text) | Citations | Notes |
|---|---|---|---|
| Original (2026-10-03) | about 3,550 | n/a | 16 chunks, 6 topics plus a comparison |
| B0 | 3,000 | 119 | 7 calls, about 25 s |
| B1 | 3,333 | 218 | 7 calls |
| B2 | 6,525 | 329 | 7 calls |
| E1 | 23,095 | 57 distinct sources in `source_map` (37 textbook, 15 class notes, 5 carried over from the original guide) | 12 calls; 6 topics, 34 subsections, 6 worked examples, 71 to 102 display equations per topic |

Word counts for B0 to B2 exclude the "Retrieved sources" lists. E1 has no such lists in the body;
its sources are in the frontmatter `source_map`.

## Review criteria and findings

Reviewer: the owner, with an independent skim by the author of the pipeline (headings, one
section per run, the Hansen 9.11 check, one worked example, the E1 source map). Neither was a
full read; the owner plans a fuller review.

What held across all runs:
- Each run states plainly that Hansen section 9.11 contains no likelihood ratio test.
- No administrative asides or class-note transcription errors were found in the parts read.
- The one E1 worked example checked by hand is arithmetically correct (cross-product matrices
  and X'y match the stated data); the model used code execution for it.
- B2 flagged OCR errors in the textbook conversion as gaps instead of repeating them.

What the owner found, beyond the metrics:
- **E1 handles the Hansen 9.11 mismatch well.** The requested topic (the likelihood ratio test)
  is what matters, not whether that textbook section covers it. E1 explains what 9.11 actually
  covers, says where the correct content is, and still builds the full topic section from the
  right material. B1 and B2 mostly report the mismatch.
- **LaTeX is good throughout**, with long derivations in E1.
- **B2 quotes more than it synthesises** and gives too few formulae in most sections.

Gaps in E1 itself:
- **No comparison section.** The spec's comparison ("Comparing and choosing among the three
  tests") is a draft-stage item; `enhance` only receives the six topics, so E1 has none.
- **No static source-discrepancy note** at the top (enhance does not carry static notes); the
  Hansen check section covers the same point inside the topic.
- **Heavy repetition.** Six textbook-scoped topics cover three tests twice, 3,200 to 4,700 words
  each.
- **Missing sections the owner needs for studying:** see the v4 comparison.

## Why the guides are split by textbook

Not an accident of the prompts; the pipeline imposed it.

- The baseline spec reproduces the 2026-10-03 recipe, whose topics were named by textbook
  section ("Cameron & Trivedi Section 7.2: Wald test", "Hansen Section 9.17: score test", ...).
  The new-material spec copied that topic list so that B1 would isolate the new material.
- `enhance` writes exactly the topics it is given. When the earlier v2 guide let the model plan
  its own topics, it produced three topic-first sections (Wald, likelihood ratio, Lagrange
  multiplier).
- Per-topic source scoping (built in Task 6) gives each topic only the labels its plan entries
  carry, so a Cameron-scoped topic and a Hansen-scoped topic see largely different passages and
  cannot be merged, even though the topic prompt tells the model to merge sources into one
  explanation and to say where they differ.

Fix: make topics the primary unit. Each topic's source rules should pull from every relevant
book and from the class material; differences between sources are discussed inside the topic.

## E1 compared with the owner's v4 guide

v4 (`wald_hypothesis_testing_quiz_prep.v4.final.md`): about 13,400 words, nine parts, targeted at
a quiz and midterm. Made with a few rounds in the Gemini web app, then edited by hand while
studying. Its frontmatter lists lecture notes, professor lecture notes, TA notes, recitation 5,
question-resolver sidecars, Hansen chapters 7 to 9 and Cameron and Trivedi chapter 7.

| Feature | v4 | E1 |
|---|---|---|
| Organisation | By test (Wald, LM, LR) after a shared framework part, then comparison | By textbook-scoped topic, six sections |
| Framework and geometry (likelihood curve, three distances, asymptotic equivalence) | Part 1 | Not present as a section |
| Linear and non-linear Wald, delta method, covariance estimators, t and F links | Part 2 | Spread over four sections |
| LM and LR with worked numerical examples | Parts 3 and 4 | Per-section worked examples |
| Finite-sample inequality W >= LR >= LM, over- and under-rejection | Part 5 | Not present as a section |
| Step-by-step recipes by test type ("given in the problem", steps) | Part 6 (5 recipes) | None |
| Worked exam problems (8, including a Mincer wage walkthrough and an invariance paradox) | Part 7 | None |
| Formula dictionary with term-by-term breakdowns | Part 8 | None |
| Cheat sheet: comparison table, variance expansion rules, Jacobian dictionary, critical values, exam traps | Part 9 | None |
| Figures | One image and one interactive plot embedded | None |
| Per-claim source mapping | None (a topic-to-source list only) | `source_map` per chunk with `used_in` |
| Length | 13.4k words | 23.1k words |

Reading: E1 is stronger on depth, derivations, grounding and traceability. v4 is stronger on
structure for studying and on exam-oriented sections. A guide meeting the owner's bar needs E1's
depth inside v4's structure.

Pipeline implications:
- **Guide profile (new spec concept):** an ordered list of section types that wrap the topics:
  `framework`, `topic` (existing), `comparison`, `recipes`, `worked_problems`, `formula_reference`,
  `cheatsheet`. Generated sections beyond topics should be built from the finished topic text
  (the formula dictionary and recipes are distillations), not from fresh retrieval.
- **Exam-oriented sections need exam material.** v4 used problem sets and midterm-style
  questions; the plan pinned only slides and two recitations. The TA note
  `08-hypothesis-testing-trinity.md` and the professor lecture notes are in the vault and should
  be pinned (check that they are chunked and indexed first).
- **Carry static notes and the comparison through `enhance`.**
- **Grounding of added sections:** recipes and cheat-sheet content derived from topic text can
  stay "grounded" by citing the same sources; invented exam problems must be marked external.
- v4's frontmatter says "Grounded" without a way to check it. Keep `source_map`, and have the new
  section types record which topics and chunks they were built from.

## Retrieval and score threshold

- **B0 overlap with the original guide:** 10 of the original 16 chunks were re-selected (plan: 21
  chunks, 6 original-only, 11 plan-only). The index has changed since 2026-10-03; the recipe is
  recovered closely, not exactly.
- **Review of 48 discovered candidates:** 33 kept, 15 dropped. Scores run 0.730 to 0.789.
  Kept: mean 0.762; dropped: mean 0.749. At score 0.77 and above, 12 of 12 were kept; below
  0.77, 21 of 36 were kept. Textbook split: Cameron 15 of 22 kept, Hansen 10 of 15,
  Hayashi 8 of 11, so an extra textbook outside the course's two main books was useful.
- **Conclusion:** the threshold of 0.72 filters almost nothing and the score weakly separates
  kept from dropped. The owner's preference is to include and link more, as long as passages are
  on topic, since the cost of a marginal passage is low for the model. Next runs: lower
  `min_score` (try 0.70), raise the discover `max`, and keep the review step as an on-topic
  filter instead of a score filter. Allowing a discovered passage to inform several topics is
  fine.

## Visualizations (input for the `agent/viz` component)

Two hand-made artifacts accompany v4, both in `summaries/assets/`:

1. **A static schematic from an image generator** (`testing_trinity_geometry.jpg`): one
   log-likelihood curve with the three tests drawn as three geometric features (horizontal
   distance for Wald, vertical drop for LR, tangent slope for LM), labelled with the formulas.
   It states the idea at a glance, is cleanly labelled, and has no interaction.
2. **An animated Plotly figure** (`testing_trinity_div.html`, a div-only version; and
   `testing_trinity_asymptotics.html`, a full page): the same curve with seven traces (curve,
   LR drop, Wald distance, LM tangent, estimates), a play button and a 50-step slider over sample
   size (10 to 2,000) showing the three statistics converging under the null. About 800 KB each,
   mostly the base64 arrays for the frames, with Plotly.js loaded from a CDN. v4 embeds the div
   version through a Dataview JS block that reads the file from the vault and re-creates the
   script tags.

What this suggests for `agent/viz`:
- The pipeline currently generates standalone Plotly pages from templates or an LLM fallback.
  The useful pattern here is a **pairing**: a static schematic for the concept, plus a
  parameterised animation that shows the property (here: convergence as n grows) the text
  asserts.
- **Output form for the vault:** a div-only fragment, written under `assets/`, plus the
  Dataview JS snippet (or an equivalent inline embed) generated alongside it. A full-page HTML
  requires opening it outside the note.
- **Plotly.js from a CDN** means the figure does not render offline; consider a locally stored
  copy, or accept the dependency and note it.
- A template for "testing trinity geometry" is a good first template to add; the animation's
  parameters (n, the null value, the curvature) are what a template would expose.
- The hypothesis_testing.html (9 MB) and hypothesis_testing2.html (15 MB) files in `summaries/`
  are full HTML exports of the guide; their size is a warning about embedding frame data for
  many figures.

## Pipeline notes from the run

- **Plan, review and apply flow worked end to end.** A review Artifact (48 decisions in its
  `db` collection) was published, decisions were read with `ArtifactData`, validated against
  the plan keys, and applied with `apply-review`.
- **Review pass fixes (committed):** an empty topic after review now fails instead of making a
  paid call; a plan built from a different version of the spec is refused; a section rule that
  matches nothing fails; improve mode keeps the original guide's own sources citable by every
  topic; `course` and `--tag` are validated; draft failures midway save the finished sections;
  dry-runs check the output path; reused sources keep their `doc_type` and `offering`;
  `enhance` takes `--output`.
- **Vault transiently lost files during a merge.** While another agent merged branches in the
  vault repo, `econometrics/guide_plans/` and `summaries/previous/` briefly disappeared, and the
  first E1 attempt failed before any paid call. The files returned. Runs against the vault
  should tolerate that: re-check and retry before concluding anything is lost.
- **Deferred minors** (not fixed): odd heading formats such as `Appendix A.1` for label
  matching; review-ledger edits after a decision and refreshing the review file; stricter
  file-name matching; the baseline-fidelity note (topic titles use ':' where the original used
  dashes, and `max_output_tokens` is now set).
- Costs and timing were not measured beyond B0 (about 25 s). Add token counts to the run output
  before the next comparison.

## Next steps (proposed, in order)

1. Topic-first spec for the Wald, LM and LR guide: framework, Wald, LM, LR, comparison and
   finite-sample inequality as topics; section rules from every book plus pinned class notes,
   lecture notes and TA notes; a looser `min_score`.
   Written 2026-10-07 as `guide_specs/econometrics/wald_lm_lr_topic_first.toml` (8 topics, min_score
   0.70, no `exclude_guide`); loads and its 16 pinned files exist, but it has not been planned or run.
   Indexing check: every v4 source is chunked (TA notes 07/08, professor notes 092126/092826/093026,
   both 2026 lecture-note `.rag` files and their question sidecars, the 2024 midterm key). Doc-type
   quirks seen: professor notes 092126 and `slides*` are typed `ta_notes`, and a TA note and the
   syllabus are typed `textbook`, so a `textbook` discover filter can return them.
   Planned input: tutoring-session transcripts from the tutoring agent (design spec section of that
   name); the spec header records how to wire them in once they are indexed.
2. Guide profile with the extra section types (recipes, worked problems, formula reference,
   cheat sheet), generated from the finished topic text, with `enhance` carrying notes and the
   comparison.
3. Re-run E1-style improve with the new spec, compare against v4 and E1 on the owner's checklist
   (formula coverage, recipes usable on an exam, derivations, no duplicated topics).
4. Add a testing-trinity template and a static-plus-animated pairing to `agent/viz`; decide the
   embed form for Obsidian.
5. The owner reviews B2, E1 and v4 in full and adds findings to this document.

## Decision: extend and revise are separate stages (2026-10-08)

`enhance` stays the **extend** stage (deepen thin sections, add topics); a new **revise** stage refines
a large guide against relevance (weighted by exams and problem sets), deduplication, correctness and
organization, and produces a reviewed edit list rather than a regenerated guide. Design:
[guide revise pipeline](../../superpowers/specs/agent/2026-10-08-guide-revise-pipeline-design.md), which
also lists the four small `enhance` changes extend needs. `enhance --baseline per-topic` (commit
`4730cc0`) cut the per-call prompt for the topic-first draft from about 739,000 to about 144,000
characters (first topic); the whole run is estimated at roughly 320k prompt tokens instead of 3.4M.

## Deferred changes (come back to these)

Found while planning the topic-first spec (plan measured 2026-10-08):

- **Character budget per topic** in place of the per-rule `max` counts. `draft` passes every accepted
  passage with no total cap; chunks are at most about 3,000 characters (mean 1,700), and topics ranged
  from 70k to 147k characters. Proposed: pinned passages fill the budget first in score order, then
  discover passages; the same budget would replace hand-tuned `max` values.
- **`min_chars` floor** to drop heading-only fragments (49 of 443 planned entries were under 600
  characters). Until then the review Artifact flags passages under 400 characters.
- **`[[derived]]` sections** (recipes, worked problems, formula reference) built from the finished
  topic text instead of raw sources, with formulas copied verbatim and a mechanical check that every
  display equation appears in a source topic. Worked problems should still add the problem material
  itself (problem sets, exam keys, lecture question sidecars, textbook exercises); `problem_label` is
  set on only 3 chunks, so problems cannot be selected by label.
- **Duplicate passages:** 443 planned entries were only 204 unique chunks. Consider sharing a passage
  across topics once, or deduplicating inside the prompt.
- Review Artifact v2 shows passage text, length, duplicates and short fragments, and lets the owner drop
  pinned passages (`apply_decisions` now accepts `drop` on a pinned passage).

## Findings from the topic-first drafts a1 to a3 (2026-10-08)

- **Prompt choice drove quality.** a1 (`tutor_v1`, flash-lite) was an annotated bibliography: short, a citation after every sentence, no examples. a2 (`guide_v1`, flash-lite) ignored the 1,800-word floor (500 to 1,000 words per section). a3 (`guide_v1`, `gemini-3.8-flash`, constructed examples allowed) produced 2,700 to 5,400 words per section, about 39,000 words in all, with 7 full worked problems (statement, step-by-step solution, conclusion, typical trap) and constructed numerical examples labelled for later checking. The owner judged a3 much better, with the worked-problems and formula sections good.
- **Token usage (a3, 9 calls):** 294,187 prompt, 118,836 output, 6,831 thinking tokens. The draft client now records usage in the frontmatter (`usage`).
- **Defects found in a3:** the citation stripper left empty `()`, stray `;;` and bracketed fragments (fixed afterwards: bracketed groups, empty parentheses, a sidecar with the cited text in `guide_plans/`); one section emitted a stray H1 that swallowed the following sections in an outline view (fixed: stray H1/H2 are demoted and a repeated title dropped); the comparison section repeats the earlier sections and includes an irrelevant "software packages" part.
- **Relevance drift.** Retrieval grabs everything near the topic from the textbooks, so sections drift into material the course does not use (software packages, model selection by AIC/BIC, Hausman tests). The owner's proposed direction: define the relevant scope before retrieval, either in an interactive session with the user or from the syllabus, past exams, lecture and recitation notes, then use that scope to rank and filter textbook passages and to constrain what each section may cover. Not designed yet; it needs its own spec.
- **Comparison section** should not re-derive the three tests; give it a prompt that only compares what the topic sections established, or drop it in favour of the "how the three tests relate" topic.

## Artifacts (local vault, not committed)

- Plans and review items: `academic_notes/econometrics/guide_plans/` (baseline and new-material).
- Guides: `summaries/wald_lm_lr_tests.b0.md`, `wald_lm_lr_new_material.b1.md`,
  `wald_lm_lr_new_material.b2.md`, `wald_lm_lr_tests.enhanced.e1.md`.
- Benchmark and figures: `summaries/wald_hypothesis_testing_quiz_prep.v4.final.md`,
  `summaries/assets/testing_trinity_*`.
- Specs (committed): `guide_specs/econometrics/wald_lm_lr_tests.toml` and
  `wald_lm_lr_tests_new_material.toml`.

## Revise first run on the a3 draft (2026-10-08)

Spec `wald_lm_lr_topic_first.toml` now has a `[revise]` table: seven evidence rules (2024 midterm key and 2023 exam 1 at weight 3; pset 2 solutions, pset 2 and the 2026-09-30 and 2026-10-05 lecture-question sidecars at 2; syllabus at 1.5), `relevance_low = 0.68`, `relevance_high = 0.80`, `judge_fraction = 0.15` and a `scope` sentence (software guides and AIC/BIC out of scope). Report: `guide_plans/wald_lm_lr_topic_first.a3.full.revise.json` (guide `summaries/wald_lm_lr_topic_first.a3.md`, 310 blocks, 39,472 words).

- **Relevance scores are compressed.** With the default 0.30 / 0.60 thresholds nothing was flagged: every scored block fell between 0.66 and 0.87 because the whole guide is on the exam topic. Absolute thresholds from the plan were not usable; 0.68 / 0.80 were chosen from the distribution (4 blocks under 0.68, about 16 above 0.80). The AIC/BIC block ranked lowest; the software-package blocks did not, which is why the LLM judge was added (bottom 15% of scored blocks plus unscored blocks of 15 or more words, 12 per call).
- **Result:** 30 proposed edits: relevance 7 (4 by score, 3 by the judge, including the software and MATLAB blocks and the source-reference note), dedup 10 (all links), correctness 9 (1 fix, 8 advisory notes, among them contradictions of the textbook formulas and three arithmetic mismatches: 7.82 vs 7.81, W = 23 vs 25.0, F = 12.5 vs 11.5), organization 4 (demote a second H1, one move, two retitles of bold constructed-example headings).
- **Cost:** the successful pass used 66 calls, 634,649 prompt tokens (40,991 cached by implicit caching), 34,935 output and 357,420 thinking tokens, about $1.9 at 3.8 Flash list prices. Thinking tokens were 10 times the output tokens and about 8 times the plan's $0.25 estimate, which counted only input. Two earlier attempts (one aborted by a parser error, one killed by low system memory) added cost whose usage was not recorded. The dedup stage was re-run alone after fixing the parser (11 calls, about 26k tokens) and merged into the report by hand.
- **Fixes made along the way:** a malformed model response is now skipped with a warning; a canonical block listed with action `keep` is accepted; embedding calls back off on rate limits; each finished stage and audited section is saved to `<guide>.<tag>.revise.partial.json` so a crashed run resumes (`--no-resume` to start over).
- **Open:** the correctness findings (especially the "contradicted" notes and the three arithmetic mismatches) need the owner's check against the sources before any are accepted; the review Artifact and `apply-revise` (plan Task 10, step 5) have not been run.

### Review and apply (2026-10-08)

The owner reviewed the 30 edits in an interactive Artifact: 27 accepted and 3 rejected (rel-001, rel-003 and rel-004: three low-relevance blocks the owner judged worth keeping). rel-007 (MATLAB block) was accepted together with rel-006 (the whole software-packages section); apply refuses two edits on one block, so rel-007 was recorded as superseded. `apply-revise` wrote `summaries/wald_lm_lr_topic_first.a3.revised.full.md` with 18 text edits (the other 8 accepted items are advisory notes): 39,472 to 37,663 words (-4.6%), 310 to 304 blocks, heading problems from 2 to 0, 10 cross-reference links (none dangling), and the comparison section moved to follow "How the three tests relate".

- **Section-level deletes and moves.** Review exposed that a heading block holds only its own lines, so deleting or moving a heading left its subsections behind. A delete now removes the section beneath the heading and a move carries it; moves combine with edits inside the moved section.
- **What the block-level pass does not reach.** Inline sentences inside kept blocks (for example "in MATLAB, c is computed as chi2inv(...)", two Stata remarks and one AIC/BIC sentence) remain. A sentence-level fix stage, or a stronger scope instruction to the draft, would be needed.
- **Left by the draft, not by revise.** The model wrote its own title H1 under each topic's H2; demoting it produced a second Wald H2 with all 5,144 words beneath it. It was removed by hand (recorded in the changelog). The draft stage's heading normalizer should drop a model title that repeats the topic title; revise's organization stage did not propose it.
- **Not done.** Comparison with the owner's v4 guide; the correctness notes were acknowledged, not corrected (only one produced a text fix).

### Cost controls (2026-10-08)

The first full pass cost about $1.90 because thinking tokens (357k) were ten times the output tokens. Four fixes shipped: per-stage token usage in the report and the console; `light_thinking = "low"` (`thinking_level`, the only control 3.8 Flash offers; thinking cannot be switched off) for every stage but the correctness audit; `max_cost` / `--max-cost` with a dry-run estimate, a refusal when the estimate is over the cap, and a stop between units (exit 3, work kept) when real spend passes it; and a content-keyed audit cache so a rerun audits only changed sections. Not yet measured on a real run: the per-stage split, and whether `low` thinking keeps the judge, dedup and inline decisions as good. The estimate is rough until one run records per-stage usage. Editing the spec (for example adding `max_cost`) changes its hash, so the plan would have to be rebuilt; the cap can be passed as `--max-cost` instead.
