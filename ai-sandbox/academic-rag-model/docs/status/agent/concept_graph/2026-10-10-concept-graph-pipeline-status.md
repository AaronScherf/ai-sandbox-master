# Concept graph drafting pipeline: status (2026-10-10)

Implements Plan B: `docs/superpowers/plans/2026-10-10-concept-graph-pipeline.md`, from the spec
`docs/superpowers/specs/agent/2026-10-09-concept-graph-design.md`. Branch `claude/concept-graph-pipeline`
(branched from `claude/concept-graph-core`), not merged. Nothing has been run against the real corpus or written
into the public graph repo.

## What was built (`agent/concept_graph/`)

- `sources.py`: `Passage` and `classify_passage` (maps a retrieved file path to a `(source, ref)` citation key).
- `ipguard.py`: the own-words tripwire (8 or more consecutive shared words with an offered passage is rejected).
- `tasks.py`, `work.py`: task cards, reading back the agent's YAML result, and the private work directory with a
  manifest (offered citations and passage text live there, never on the card, so a card cannot be trusted).
- `stages/seed.py`, `fill.py`, `link.py`, `critic.py`, `common.py`: each stage's `make_tasks`, `validate_result`,
  `apply_result`. The critic is blind: it sees the claim and fresh passages, not the drafter's explanation.
- `retrieval.py`: `IndexRetriever` over the repo's passage search (only network call: the query embedding).
- `drivers.py`: `collect`, `submit` (idempotent, one bad card never stops the rest), and `api_run` behind a cost gate.
- `cli.py`: `collect`, `submit`, `status`, `bootstrap`, `api`. `store.py`: `add_sections/nodes/edges/vocab`.

## Verification

- `python -m pytest tests/agent/concept_graph -q`: 195 passed.
- Rest of the repo's suite (main checkout's full venv, `--ignore=tests/agent/concept_graph`): 2972 passed, 34 subtests passed.
- The IndexRetriever's live path (real index and key) is **not** exercised; its mapping is tested with a stand-in
  module. The Gemini completion function is not exercised (paid); the API driver is tested with a fake.
- No stage has been run on the real corpus.

## Decisions

- A proposed edge that duplicates an existing one is bounced (not silently skipped), so the agent sees the mistake.
- Seed refuses to run on a graph that already has taught sections unless `--redo`, and never edits existing items.
- Without `--redo`, `link` only visits filled nodes that have no edges yet; re-link a node with `--redo --node ID`.
- The work directory is refused if it is inside the graph repo (cards hold source text).

## What's next

1. Owner-gated first real run, in order: `seed` (review the skeleton), `fill`, `link`, `critic`; each by an agent or,
   with `--approve-cost`, by the API. Do it after the remaining prior-year documents are transcribed.
2. Then `offering_links` on the prior-year material, to mark duplicated context.
3. Later: Artifact review adapter, Obsidian export.

## Final review and fix pass

A fresh reviewer read the whole branch. Findings and what was done (each fix has a test that failed first):

- **Fixed, serious:** a crafted `--run-id` (`../graph/evil`, an absolute path) wrote task cards, which carry retrieved
  source text, inside the graph repo, defeating the work-directory guard. Run ids are now limited to letters, digits,
  dots, hyphens and underscores, and the final run folder is checked against the graph repo too.
- **Fixed:** `api` crashed the whole run on a non-text or unparseable model reply; it now bounces that card and goes on.
- **Fixed:** if applying a validated card fails midway (a disk error), the bounce message now says part of the card
  may already be in the graph and to check the data files before resubmitting (the store stays non-transactional).
- **Accepted limits:** the IP guard is a tripwire. It compares against each passage separately and ignores
  everything but letters and digits, so invisible-character tricks or stitching short fragments from two passages are
  not caught; the owner review before anything is `verified` is the backstop. Its cost grows with passage length and
  was not measured on a full 150-card submit.
- **Deferred minor:** `cli.main` catches bare `ValueError`/`RuntimeError`, so an unrelated programming error prints as
  `error: ...` without a traceback.

## First real seed run on microecon (2026-10-10) and what it taught us

`seed` was run for real with Antigravity (Gemini, subscription) filling the cards; `submit` was run by Claude Code.
Three passes, each exposing a flaw in the stage that was then fixed with tests:

1. **Pass 1** (chapter titles, syllabus, slide titles only): 8 sections, 49 nodes, but it missed the foundations the
   owner cared about (preorder, partial and total order, Szpilrajn, Sen's alpha and beta, GARP). Cause: the card
   never showed the model those concepts, and nothing required them. Also found: the syllabus text carried the
   instructor's and TA's names and emails; slide sets were listed alphabetically although labelled "in course order";
   two lecture dates were missed because unprocessed notes were ignored.
2. **Redesign:** evidence now includes the labelled statements in slides and lecture notes ("Axiom β ...",
   "Theorem" plus its statement) and the section headings of in-scope textbook chapters; a per-course
   `config/seed.yaml` (scope, `must_include` with aliases, `textbook_chapters`, `min_nodes_per_section`); a kind
   glossary, a format example and a self-check on the card; validation that bounces missing required concepts and
   duplicate names. One real bug found on the way: the printed `submit` command had its options in an order that does
   not parse.
3. **Pass 2** (redesigned card): the model returned almost exactly the required list (30 nodes) and left two
   sections empty. Lesson: **a required list becomes the target unless a floor is enforced.** Fix: the card calls the
   list a floor, and `submit` bounces any section below `min_nodes_per_section`.
4. **Pass 3** (additive, floor 6): 59 nodes in 8 sections; all 31 required concepts present; 0 validation errors.

Known weaknesses of the result (to review by hand or with another additive pass): no section for choice over time
although the syllabus mentions it; no nodes yet for framing, status-quo bias or menu dependence; four sections sit
exactly at the floor of 6; the Szpilrajn theorem landed in the revealed-preference section, not with orders.

To reuse for another course: `scaffold`, fill `config/seed.yaml`, `collect seed --course <name>`, give the card to the
drafting agent, `submit`; use `collect seed --redo` for additive passes. The corpus classifier names only three
textbooks (rubinstein, mwg, ok); other books are scoped in `seed.yaml` by their folder name.
