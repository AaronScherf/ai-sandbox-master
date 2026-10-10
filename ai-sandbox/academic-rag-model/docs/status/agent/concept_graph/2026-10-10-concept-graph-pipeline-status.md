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
