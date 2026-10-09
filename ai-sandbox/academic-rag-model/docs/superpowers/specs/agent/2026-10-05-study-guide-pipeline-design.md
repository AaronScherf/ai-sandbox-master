# Study guide pipeline — design

Date: 2026-10-05 · Branch: `claude/study-guide-spec` · Path: architectural
Builds on: `2026-10-03-summary-enhancement-design.md`, `...-v2-design.md`, and the recovered
recipe in `docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md`.

## Purpose

Turn the one-off script that produced the first Wald/LR/LM study guide into a reusable,
documented pipeline, and extend it so a guide can be (1) regenerated from a richer, explicitly
chosen set of sources, and (2) improved from an existing guide plus new sources. Each guide is
described by a declarative **guide spec**; every stage records exactly which passages and
models were used.

## Requirements

- **R1 Reproducible baseline.** A spec can reproduce the 2026-10-03 recipe (same retrieval
  parameters, same prompt, same model) so a later run can be compared with it fairly.
- **R2 Explicit sources.** For each topic, sources are chosen by rules: pinned textbook
  sections, pinned files (class notes, slides, recitations), and bounded auto-discovery that
  can exclude passages an existing guide already used.
- **R3 Human review of candidates.** Discovered candidates are accepted or dropped by the user
  through an interactive review Artifact (project rule), never by hand-editing a JSON file.
- **R4 Two ways to use new material.** (a) `draft` writes a new grounded guide from a source
  plan; (b) `enhance` improves an existing guide with the plan's sources (an "improve" mode).
- **R5 Per-stage models.** The model for each stage is a spec setting; no stage inherits a
  hidden default. The first comparison runs the same sources through different models.
- **R6 Provenance.** Every output records the spec and plan hashes, models, prompt ids, and the
  exact chunk ids used, in frontmatter compatible with `summary_enhance`.
- **R7 Safety.** Outputs stay under `<corpus>/academic_notes/`; no overwrite without an
  explicit flag; no git; paid key only; tests make no network or paid calls.

## Architecture

New package `agent/study_guide/` (tests in `tests/agent/study_guide/`). `summary_enhance` is
reused unchanged in role as the last stage and gains two options (below). `rag_agent.py` and
`core/` are not modified.

```
guide spec (TOML)
      |
      v   plan            rules -> concrete chunks per topic -> <id>.plan.json (ledger)
 source plan  --review--> Artifact page (keep/drop discovered candidates) --> apply decisions
      |
      +--> draft          per-topic grounded synthesis  -> <id>.md  (derived_summary)
      |
      +--> enhance        summary_enhance (rewrite | improve) -> <id>.enhanced.md
```

Option 1 (new guide from new sources) is `plan` + `draft` (optionally `enhance` after).
Option 2 (improve the original) is `plan` + `enhance --mode improve --draft <existing guide>`.

| Module | Responsibility |
|---|---|
| `spec.py` | Dataclasses and TOML loader/validator for the guide spec; rejects unknown keys. |
| `plan.py` | Resolves source rules to chunks (via `search_passages` / `load_chunks`), writes and loads the plan ledger, produces review items, applies review decisions. |
| `prompts.py` | Frozen prompt templates: `tutor_v1` (the recovered recipe, verbatim) and `guide_v1` (study-guide oriented). |
| `draft.py` | Per-topic synthesis from planned chunks; assembles and writes the draft guide. |
| `cli.py` | `python -m agent.study_guide plan | apply-review | draft | enhance | run <spec>` |

Dependencies: `core.indexer.index_search.search_passages`, `core.indexer.chunk_index.load_chunks`,
`core.env.gemini_utils`, `agent.summary_enhance` (`llm.GeminiClient`, `enhance.run`).

## Guide spec

TOML (stdlib `tomllib`, comments allowed). Specs live in the repo under
`guide_specs/<course>/<guide_id>.toml`; they contain topics, section labels and instructions,
never source text. Generated outputs go to the vault.

```toml
[guide]
id = "wald_lm_lr_tests"
title = "Wald, Lagrange Multiplier, and Likelihood Ratio Tests"
course = "econometrics"

[models]
draft = "gemini-3.1-flash-lite"     # baseline reproduces the original run
enhance = "gemini-3.8-flash"

[draft]
prompt = "tutor_v1"                 # or "guide_v1"
label_match = "citation-substring"  # legacy matching; default for new specs is "heading-prefix"
top_k = 180
file_top_k = 80

[[note]]                            # static text inserted verbatim (e.g. a discrepancy note)
heading = "Source-reference discrepancy"
body = "The course syllabus points to Hansen ..."

[[topic]]
title = "Cameron & Trivedi Section 7.2: Wald test"
instruction = "Explain the Wald test: hypotheses, unrestricted estimation, ..."

  [[topic.source]]
  kind = "section"
  book = "Cameron_Microeconometrics"       # substring of the textbook file name
  labels = ["7.2"]
  exclude_labels = []
  query = "Wald test linear nonlinear hypotheses covariance chi-square invariance"
  max = 12

  [[topic.source]]                          # added for the new-material runs
  kind = "file"
  file = "class_2024/Class Notes/Slides/processed_outputs/slidesASYM.md"
  query = "Wald test statistic homoskedastic"
  max = 6

  [[topic.source]]
  kind = "discover"
  query = "Wald test statistic, linear and nonlinear restrictions"
  doc_types = ["textbook"]
  exclude_guide = "academic_notes/econometrics/summaries/wald_lm_lr_tests.md"
  max = 8
  min_score = 0.72

[[comparison]]                              # synthesis across topics
title = "Comparing and choosing among the three tests"
instruction = "Compare the Wald, likelihood ratio, and Lagrange multiplier/score tests ..."
from = ["Cameron & Trivedi Section 7.2: Wald test", "..."]
take = 3                                    # first N planned passages from each source topic
```

## Source plan

`plan` resolves each topic's rules to a concrete, ordered, de-duplicated chunk list and writes
`academic_notes/<course>/guide_plans/<id>.plan.json` (a ledger for the code; contains ids,
paths, citations, scores and rule provenance, no passage text).

Rule semantics:

- **section:** `search_passages(roots, query, client, course, top_k, file_top_k,
  doc_type="textbook")`; keep passages whose file name contains `book`; keep those matching a
  label; drop those matching `exclude_labels`; cap at `max` in similarity order. `label_match`
  is `"heading-prefix"` (default: a label matches a chunk if any element of its `heading_path`
  starts with the label at a dot boundary, so `7.3` matches `7.3.1` but not `7.30`) or
  `"citation-substring"` (the legacy test on the rendered citation, kept for R1).
- **file:** all chunks of the named file (by path suffix or `file_id`); if `query` is given,
  ranked by similarity to it; cap at `max`.
- **discover:** a bounded search across `doc_types` in the guide's course, excluding chunk ids
  already cited by `exclude_guide` (read from its frontmatter) and any already pinned for the
  topic, keeping scores at or above `min_score`, at most `max_per_file` per file, `max` total.
- Order within a topic: section, file, then discover. A topic with no sources is an error.
- Each plan entry stores `chunk_id`, `file_id`, `path`, `citation`, `doc_type`, `offering`
  (when the file sits under a labeled prior offering such as `class_2024`), `score`, `rule`,
  `content_hash` (from the file's card), and `status`: pinned rules are `accepted`;
  discovered candidates start `pending`.
- **Staleness:** loading a plan checks each entry's chunk still exists with the same
  `content_hash`; otherwise it fails and lists the entries (re-run `plan`).

### Human review (project rule: interactive Artifact)

Discovered candidates need a decision. `plan` prints a summary and writes the review items;
Claude publishes a review Artifact (checkbox per candidate showing book, section, page,
score; pinned items shown read-only; decisions saved in the page's `db` collection) following
the `offering_links` precedent, reads the decisions, and calls
`plan.apply_decisions(plan_path, decisions)`. `draft` and `enhance` refuse a plan that still
has `pending` entries unless `--accept-unreviewed` is given explicitly. No step asks the user
to edit the plan file.

## Draft stage

For each topic, with its accepted chunks:

- `prompt = "tutor_v1"` (baseline): the question is
  `f"{title}. {instruction} Use only these excerpts. Cite each substantive claim by its exact
  source label. State plainly where the excerpts do not support an answer."`, wrapped in the
  tutor Q&A template with excerpts as `[citation]\ntext`. The template text is frozen in
  `prompts.py` (copied from `rag_agent._ANSWER_PROMPT_TEMPLATE` at spec time); a later change
  to the tutor does not alter a baseline reproduction.
- `prompt = "guide_v1"`: a study-guide prompt (thorough, structured, inline citations, honest
  about gaps, may state where sources disagree); its text and a word-count target are fixed in
  the implementation plan.
- Model and temperature come from `[models].draft` (temperature 0.2). Calls use
  `summary_enhance.llm.GeminiClient.generate_text` with the paid key.
- `[[comparison]]` sections reuse planned chunks (first `take` per source topic, de-duplicated).
- Output `academic_notes/<course>/summaries/<id>[.<tag>].md`: frontmatter (`llm_generated`,
  `content_kind: derived_summary`, `generated_by`, models, `prompt_id`, spec and plan hashes,
  `indexer_source_refs` for every chunk used), `# title`, notes, then each topic's answer
  followed by a **Retrieved sources** list (as in the original guide).
- `--tag` names an output variant (for example `b2-pro`) so comparison runs never collide;
  an existing output is never overwritten without `--force`.

## Enhance stage (changes to `summary_enhance`)

1. **Source plan input.** `--source-plan <plan>` adds the plan's accepted chunks to the guide's
   own refs (de-duplicated by chunk id). Each topic's synthesis call gets only that topic's
   chunks (labels stay globally unique), and validation requires every cited label to belong to
   that topic's set. Without a plan, behavior is unchanged (all of the guide's chunks).
2. **`--mode improve`.** The existing guide's body is the *baseline* (kept where the passages
   support it, corrected or extended where they do not); new passages are labeled with their
   type (`textbook`, `class notes`, `slides`, `recitation`) and offering. Rules added to the
   prompt: prefer textbook statements over class notes where they conflict and say so plainly
   (a grounded block citing both); class notes may be handwritten or transcribed and can
   contain errors; do not copy class-specific asides that are not about the topic. `rewrite`
   (default) is the current behavior.
3. **`source_map`** entries gain `doc_type` and, when known, `offering`.
4. The original guide is not a citable source (it is LLM output built from the same
   textbooks); it is context only.

## Models and the first comparison

Per-stage models are spec settings. Baseline reproduction pins `gemini-3.1-flash-lite` for
`draft`. New specs default `draft` and `enhance` to `gemini-3.8-flash`; a stronger model
(`gemini-3.1-pro-preview`) is tried as a variant, not a default. The original tutor-model
comparison covered short Q&A answers only, so long-form guide synthesis is tested afresh.

First comparison for the Wald/LR/LM guide, same plan machinery, outputs tagged:

| Run | Sources | Draft model | Purpose |
|---|---|---|---|
| B0 | baseline (recovered recipe) | 3.1-flash-lite | reproduce; check retrieval overlap with the original 16 chunks |
| B1 | baseline + 3 pinned class files + discovered unused textbook passages | 3.1-flash-lite | isolate the effect of new material |
| B2 | same as B1 | 3.8-flash (and optionally 3.1-pro-preview) | isolate the effect of the model |
| E1 | original guide + same new sources, `improve` | 3.8-flash | option 2 |

Pinned class files: `slidesASYM.md`, `Recitation 5`, `Recitation 3` (the midterm answer key is
excluded). Discovery: per topic, top 8 above 0.72 from all indexed textbooks, excluding the
original guide's chunks, reviewed through the Artifact. Evaluation is manual against a
coverage checklist built from the class slides, plus factual spot-checks, length and
structure, and citation traceability; no automated judge in this phase.

## Provenance and safety

- Spec path and sha256, plan path and sha256, per-stage model ids and prompt ids are recorded in
  every output's frontmatter.
- Class materials (a prior offering's slides, recitations, notes) are sent to the Gemini API
  under the same personal-use authorization as the textbooks; outputs and plans stay in the
  private notes vault; spec files hold no source text.
- All guards from `summary_enhance` apply: output inside `academic_notes/`, never over an
  input, no overwrite without `--force`, no git, secrets never printed, `--dry-run` prints
  chunk counts, call counts and destinations without any API call.

## CLI

```
python -m agent.study_guide plan   <spec> [--out PATH]
python -m agent.study_guide apply-review <plan> --decisions <file>   # used by the review Artifact flow
python -m agent.study_guide draft  <spec> --plan <plan> [--tag T] [--force] [--dry-run] [--accept-unreviewed]
python -m agent.study_guide enhance <spec> --plan <plan> --draft <guide.md> [--mode improve] [--worked-example] [--tag T]
python -m agent.study_guide run    <spec>        # plan, then stop for review; continues with --yes
```

## Testing (no paid calls)

Fixture vault with a small chunk store and cards; the planner takes an injectable `search`
callable (default `search_passages`) so tests use canned results. Fake LLM client.

- spec: valid/invalid TOML, unknown keys, missing sources, duplicate topic titles.
- plan: each rule kind; `heading-prefix` vs `citation-substring`; `exclude_labels`; `max`; dedup
  across rules; `exclude_guide` removing a guide's chunks; `min_score`; status defaults; stale
  `content_hash` detection; apply_decisions; `pending` blocks draft/enhance.
- draft: baseline prompt equals the frozen `tutor_v1` rendering for a known input; per-topic call
  count; comparison reuse; frontmatter and `indexer_source_refs` match the chunks; tag naming;
  overwrite refusal; vault guard.
- enhance (in `summary_enhance` tests): plan chunks added and de-duplicated; per-topic subsets;
  cited label outside the topic's set rejected; `improve` prompt contents; `source_map` gains
  `doc_type`/`offering`; unchanged behavior without a plan.
- acceptance (manual, paid): run B0 and compare its chunk ids with the original guide's refs.

## Build order

1. `study_guide` package with spec, plan (including review items and decisions), prompts, draft,
   CLI, tests; commit the baseline spec as `guide_specs/econometrics/wald_lm_lr_tests.toml`.
2. `summary_enhance` extensions (plan input, `improve`, `source_map` fields).
3. Real runs B0, B1, B2, E1 and the comparison write-up.

## Risks and open questions

- Class notes include handwritten-note transcriptions that may contain errors; mitigated by the
  textbook-priority rule and labeling, not eliminated.
- A prior offering (2024) may differ from the current course; sources carry their offering label.
- Retrieval scores are model-dependent; `min_score` needs calibration against the first plan
  (0.72 is a starting guess from the probe).
- `heading-prefix` matching assumes chunks carry `heading_path`; chunks without it fall back to
  the citation string.
- Open: whether specs should live in the repo (proposed) or the vault; the `guide_v1` prompt
  text and word target; whether to add an automated judge later.

## Planned input: tutoring-session transcripts

The owner is building a guided tutoring agent for the RAG. It will save transcripts of its dialogue
with the student while they work practice problems drawn from the same indexed content. Study
guides should treat these transcripts as a first-class source because they (a) elaborate the
example problems step by step, and (b) show where the student needed extra help (confusions,
mistaken steps, repeated hints), which tells a guide where to add explanation or emphasis.

Design consequences, none implemented yet:

- Transcripts are indexed like any other vault file and get their own `doc_type` (proposed:
  `tutoring_transcript`), so the existing `file` and `discover` rules can select them with no
  change to the spec schema.
- Worked-problem and recipe topics should pin or discover the transcripts for their problems; any
  topic the transcripts show to be weak can add a `discover` rule over that doc type.
- A later guide-profile feature could add an explicit "areas needing extra help" section built from
  transcript struggle points; until then they enter through the topic prompts.
- Privacy: transcripts hold student-specific dialogue. They stay in the vault and are never copied
  into specs, plans or committed docs; the plan ledger records citations only, as it does for
  other sources.
- Open: how the tutor marks struggle points (a field in the transcript, or inferred by the guide
  prompt), and whether transcripts need review before use, since the student's own mistaken
  statements must not be treated as source facts. Resolve this with the tutor design.

## Out of scope

Automated quality scoring, multi-course specs, scheduling, a GUI beyond the review Artifact,
changing `rag_agent.py`, re-chunking or re-indexing sources, and converting existing guides to
the new frontmatter.
