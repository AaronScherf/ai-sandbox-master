<!-- agent/study_guide/README.md -->
# study_guide

Reusable pipeline for building study guides from indexed course material: a **guide spec**
(TOML, in `guide_specs/<course>/`) is resolved to a **source plan**, which feeds a **draft**
(grounded, cited) and, optionally, an **enhance** pass (`agent.summary_enhance`).

    python -m agent.study_guide plan   guide_specs/econometrics/wald_lm_lr_tests.toml --root <hub> --env-file <.env>
    python -m agent.study_guide apply-review <plan> --decisions <decisions.json>
    python -m agent.study_guide draft  guide_specs/econometrics/wald_lm_lr_tests.toml --root <hub> --tag b0 --dry-run
    python -m agent.study_guide draft  <spec> --root <hub> --tag b0

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
