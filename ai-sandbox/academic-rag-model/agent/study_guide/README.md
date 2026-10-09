<!-- agent/study_guide/README.md -->
# study_guide

Reusable pipeline for building study guides from indexed course material: a **guide spec**
(TOML, in `guide_specs/<course>/`) is resolved to a **source plan**, which feeds a **draft**
(grounded, cited) and, optionally, an **enhance** pass (`agent.summary_enhance`).

    python -m agent.study_guide plan   guide_specs/econometrics/wald_lm_lr_tests.toml --root <hub> --env-file <.env>
    python -m agent.study_guide apply-review <plan> --decisions <decisions.json>
    python -m agent.study_guide draft  guide_specs/econometrics/wald_lm_lr_tests.toml --root <hub> --tag b0 --dry-run
    python -m agent.study_guide draft  <spec> --root <hub> --tag b0
    python -m agent.study_guide enhance <spec> --draft <guide.md> [--mode improve] [--worked-example] [--tag T]

- **Spec:** topics, instructions, per-topic source rules (`section` = pinned textbook sections,
  `file` = pinned class notes/slides, `discover` = bounded search that can exclude an existing
  guide's chunks), per-stage models, prompt id (`tutor_v1` reproduces the 2026-10-03 recipe).
- **Plan:** `<hub>/academic_notes/<course>/guide_plans/<id>.plan.json` (ledger, no passage text)
  and `<id>.review.json` (items for the review Artifact). Pinned passages are accepted;
  discovered ones are `pending` until reviewed (`--accept-unreviewed` overrides, explicitly).
- **Draft:** `<hub>/academic_notes/<course>/summaries/<id>[.<tag>].md`, a `derived_summary`
  whose `indexer_source_refs` lists every passage used.
- Never overwrites without `--force`, never runs git, outputs stay inside `academic_notes/`.
- Design: `docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`.
  Provenance of the baseline: `docs/status/agent/2026-10-05-wald-guide-recovered-generation-status.md`.
- Tests: `python -m pytest tests/agent/study_guide -q` (no network).

## revise (refine a large guide)

```
python -m agent.study_guide revise       <spec> --guide G [--plan P] [--stages relevance,dedup,correctness,organization] [--tag T] [--dry-run] [--force] [--env-file F]
python -m agent.study_guide apply-revise <spec> --guide G --decisions D.json [--tag T] [--force]
```

- `revise` reads a draft or enhanced guide, proposes typed edits (delete, shrink, merge, link, fix, move, retitle, note) and
  writes `academic_notes/<course>/guide_plans/<guide>[.<tag>].revise.json` plus `...revise.review.json` (items for the review
  Artifact). It never changes the guide. `--dry-run` prints block and call counts and makes no calls.
- Stages: `relevance` (embeddings against weighted evidence; deletes below `relevance_low`, protects blocks above
  `relevance_high`), `dedup` (one call per duplicate cluster), `correctness` (one call per section against its own plan
  passages, plus a code-execution recheck of worked and constructed examples), `organization` (mechanical heading fixes and
  one outline-only call). A stage must be listed in the spec's `[revise] criteria`.
- A `revise` run saves each finished stage (and each audited section) to `<guide>[.<tag>].revise.partial.json` next to the
  report. If the run dies (rate limit, crash, low memory), running the same command again reuses that work and only redoes
  the rest; the file is keyed on the guide and spec hashes, so a changed input starts over. `--no-resume` discards it.
- `apply-revise` is deterministic and calls no model: it applies the accepted edits (decisions file maps edit id to
  `accept` or `reject`; undecided counts as rejected), checks the post-conditions (guide not longer, no new page citations,
  no new heading problems, untouched blocks unchanged) and writes `<guide>.revised[.<tag>].md` and a changelog. It refuses a
  guide that changed since the report, and never overwrites without `--force`.
- Spec: an optional `[revise]` table (`model`, `criteria`, `relevance_low`, `relevance_high`, `dedup_similarity`,
  `min_block_words`, and `[[revise.evidence]]` rules with a `weight`; same rule keys as `[[topic.source]]`).
- Design: `docs/superpowers/specs/agent/2026-10-08-guide-revise-pipeline-design.md`.
