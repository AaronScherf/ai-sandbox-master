# Journal Discovery: Citation Snowball Sampling — Design Spec

Date: 2026-09-02
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

`journal_discovery` has two ways to find candidate papers today: a
faculty name or a topic query, both resolved via OpenAlex (spec
`2026-08-31-journal-discovery-design.md`). Neither grows the corpus from
what's *already in it* -- a well-established literature-review technique
(snowball sampling: find new work by following citations from papers you
already have) that this pipeline doesn't do at all. Flagged as an open
idea in `docs/2026-09-01-journal-discovery-status.md` point 4.

This spec designs a third route: **`journal_discovery/snowball.py`**,
seeded from every paper already fetched into the corpus, using
OpenAlex's own forward-citation graph ("papers that cite this one") --
deliberately not backward references (a seed paper's own bibliography),
which would need parsing plain-text citations out of Gemini-transcribed
markdown with no structured citation format to rely on. Forward
citations need no parsing at all; OpenAlex already has that graph
structured.

The user was explicit about the interaction shape: **not** a fully
automated pull. The pipeline proposes candidates (seeded from the
corpus's own citation network, narrowed by the same relevance-scoring
gate the other two routes already use), and a human picks which of
those proposals are actually worth fetching before anything is
downloaded.

**Goals**
- Seed forward-citation lookups from every `fetched`/`downloaded`
  manifest entry by default (the whole real corpus), with `--seed-doi`
  (repeatable) to scope to specific papers later if the corpus grows
  large enough that "everything" stops being the right default.
- Score every citing candidate through the *existing*
  `select_relevant_works()` (a `--relevance-prompt` you write, the same
  threshold/ceiling volume control the other two routes already use) --
  this is the automatic "narrow by topic" step, before any human ever
  sees the list.
- Present what survives scoring as a checkbox worklist
  (`snowball_candidates.md`), never auto-fetched. A separate `confirm`
  step reads which boxes are checked and only then runs full-text
  resolution for those specific papers -- the human-selection step.
- Once confirmed, a paper flows through the *exact same* access chain,
  folder routing, and manifest/worklist machinery every other route
  already uses. Nothing downstream needs to know a paper arrived via
  citation graph rather than author/topic search.
- Never re-propose something already seen (fetched, needs_manual,
  downloaded, or already proposed in an earlier run) -- a re-run of
  `propose` should only ever surface genuinely new candidates.

**Non-goals**
- No backward-reference parsing (a paper's own bibliography) --
  deferred; noted in `docs/2026-09-01-journal-discovery-status.md` as a
  harder, unparsed-format problem, out of scope for this pass.
- No new access tier, no new folder-routing logic, no new
  `.meta.json`/dedup mechanism -- this route feeds the *existing*
  pipeline a new stream of candidates; it doesn't change what happens
  once a candidate is confirmed.
- No automatic "reject" action for an unchecked proposal -- leaving a
  box unchecked indefinitely is the reject; there's no separate action
  needed, matching how an unchecked `needs_manual_downloads.md` entry
  already behaves.

## 2. Architecture

A new module, `journal_discovery/snowball.py`, living *inside* the
existing package -- unlike `reconcile_needs_manual.py` (a top-level
script bridging `journal_discovery` and `journal_articles`), everything
snowball needs already lives inside `journal_discovery` itself
(`discovery.py`'s OpenAlex access, `relevance.py`'s scoring,
`access.py`'s fetch chain, `manifest.py`, `worklist.py`). Two
subcommands, sharing the manifest as their sole hand-off point:

```powershell
python -m journal_discovery.snowball propose --relevance-prompt "climate-forced displacement and adaptation policy"
python -m journal_discovery.snowball confirm
```

## 3. New and changed components

- **`discovery.py` gains two functions:**
  - `resolve_work_by_doi(doi: str, mailto: str) -> Work | None` -- a
    plain DOI lookup against `{_OPENALEX_BASE}/works/https://doi.org/{doi}`,
    parsed via the existing `_work_from_openalex()`. Generically useful,
    not snowball-specific; needed here because most manifest entries are
    keyed by bare DOI, not OpenAlex ID, and citation lookup needs a
    seed's OpenAlex ID.
  - `iter_citing_works(openalex_id: str, mailto: str, batch_size: int)`
    -- pages `{_OPENALEX_BASE}/works` with `filter=cites:{openalex_id}`,
    identical shape and paging logic to `iter_author_works`/
    `iter_topic_works`, including the same `type="dataset"` exclusion
    (spec `2026-08-31`'s fix applies unchanged, since a citing "work" can
    itself be a dataset/RCT-registration record).

- **`manifest.py`:** `_skip_already_seen()` (currently private to
  `discover.py`) is promoted to a public function here, since
  `snowball.py` needs the identical "don't resurface anything already
  fetched/needs_manual/downloaded/**proposed**" filter.
  `discover.py`'s own usage is updated to import it from here instead of
  defining it locally -- one implementation, two callers. No new
  manifest fields: `record_outcome()`'s existing generic `metadata` dict
  parameter already covers everything a proposed entry needs to carry
  (see S5).

- **`worklist.py`:** the checkbox-writer generalizes to a single
  parameterized function, `_write_checkbox_worklist(manifest, articles_dir,
  filename, heading_lines, status_filter)`, so `write_needs_manual_worklist`
  and a new `write_snowball_candidates_worklist` both call into it
  instead of duplicating the checkbox-preservation logic
  (`_read_checked_links`, already generic, is reused as-is).
  `write_snowball_candidates_worklist(manifest, articles_dir) -> Path`
  writes `snowball_candidates.md`, filtering `status == "proposed"`.
  The shared writer renders `relevance_score`/`cites_seed` lines
  underneath an entry only when those keys are present in its manifest
  metadata -- true for every snowball-sourced entry, never true for a
  `needs_manual` one -- so the two worklists share one implementation
  without one file showing blank fields the other doesn't have.

- **`snowball.py`:**
  - `iter_seed_openalex_ids(manifest, mailto, seed_dois=None)` -- yields
    the OpenAlex ID for every `fetched`/`downloaded` manifest entry
    (or just `seed_dois` if given), resolving a bare-DOI key via
    `resolve_work_by_doi()` first. Skips (with a warning, doesn't crash)
    any seed whose lookup fails.
  - `iter_snowball_candidates(manifest, mailto, batch_size, seed_dois=None)`
    -- chains `iter_citing_works()` for every seed into one generator,
    filtering through the promoted `skip_already_seen()` as candidates
    stream past, exactly mirroring `discover.py`'s own
    `resolve_works()` -> `_skip_already_seen()` -> `select_relevant_works()`
    pipeline shape.
  - `propose(args) -> dict` -- orchestrates: load manifest, build the
    candidate stream above, score it through the *unmodified*
    `select_relevant_works()` (S1's automatic topic-narrowing step),
    record every passing candidate as `status="proposed"` with metadata
    (S5), save the manifest, write `snowball_candidates.md`. Returns
    counts for CLI reporting, same shape as `discover.run()`.
  - `confirm(args) -> dict` -- orchestrates: load manifest, find every
    `status == "proposed"` entry whose link appears *checked* in the
    current `snowball_candidates.md` (reusing `_read_checked_links()`),
    re-resolve each to a fresh `Work` (via `resolve_work_by_doi()` or an
    OpenAlex-ID lookup, since a manifest entry only stores metadata, not
    a full `Work` object), and run the *unmodified* `resolve_full_text()`
    for each -- landing as `fetched` (PDF + sidecar + topic folder, same
    as today) or `needs_manual` (folder + metadata, same as today).
    Regenerates both `snowball_candidates.md` (confirmed entries drop
    out) and `needs_manual_downloads.md` (any confirmed-but-unfetchable
    entry appears there, same as any other route's `needs_manual`
    outcome) at the end.

## 4. Data flow

**`propose`:**
1. Load the manifest. Collect seed OpenAlex IDs from every
   `fetched`/`downloaded` entry (or `--seed-doi` values if given),
   resolving bare-DOI keys via `resolve_work_by_doi()`.
2. Chain `iter_citing_works()` across every seed into one stream, in
   seed order (mirrors `resolve_works()`'s own faculty-then-topic
   chaining convention).
3. Filter the stream through `skip_already_seen()` -- anything already
   `fetched`, `needs_manual`, `downloaded`, or `proposed` never reaches
   scoring at all.
4. Score the survivors through `select_relevant_works()` unchanged --
   `--relevance-prompt`/`--relevance-threshold` narrow by topic,
   `--max-results`/`--max-examined` bound volume, exact-title dedup
   applies automatically (all for free, since this is the same function
   the other two routes call).
5. For each work that passes: `record_outcome(manifest, key, "proposed",
   folder=<computed via route_to_folder, same as today>, metadata={title,
   authors, year, doi_url, relevance_score, cites_seed})`.
6. Save the manifest; write `snowball_candidates.md`.

**`confirm`:**
1. Load the manifest and `snowball_candidates.md`'s current checked
   links.
2. For every `status == "proposed"` manifest entry whose link is
   checked: re-resolve a fresh `Work`, run `resolve_full_text()` (paced
   per S3/S6 of the original spec, same as any other route), write the
   PDF + sidecar on success (`status="fetched"`) or record
   `needs_manual` metadata on failure -- byte-for-byte the same logic
   `discover.run()`'s own fetch loop already runs, not a reimplementation.
3. Save the manifest; regenerate `snowball_candidates.md` (confirmed
   entries excluded now) and `needs_manual_downloads.md` (any
   confirmed-but-unfetchable entry now appears there).

## 5. State model and dedup

A new manifest status, `"proposed"`, sits between "never seen" and
`"fetched"`/`"needs_manual"`:

```json
{
  "10.1234/citing-paper": {
    "status": "proposed",
    "fetched_at": "2026-09-02T12:00:00+00:00",
    "folder": "business",
    "title": "A Paper Citing Something Already in the Corpus",
    "authors": ["..."],
    "year": 2025,
    "doi_url": "https://doi.org/10.1234/citing-paper",
    "relevance_score": 0.62,
    "cites_seed": "10.1257/pandp.20181032"
  }
}
```

`skip_already_seen()` treats `"proposed"` as seen, the same as any other
status -- this is deliberate and has two consequences worth stating
explicitly for an implementer: a proposed-but-unconfirmed paper is
invisible to *every* discovery route (faculty, topic, and a later
`propose` run alike) until confirmed, and `confirm` itself never calls
`skip_already_seen()` at all -- it looks up `status == "proposed"`
entries directly, by design, since its entire job is to act on entries
that route already correctly filtered everyone else away from.

**Known simplification:** if a citing work appears under more than one
seed (it cites two different papers already in the corpus), only the
first-encountered seed is recorded in `cites_seed` -- the candidate
itself is still deduped correctly (never proposed twice), just without
tracking every seed it actually cites. Acceptable for a first version;
revisit only if that context turns out to matter in practice.

**Reject is implicit.** There is no separate "declined" state. An
unchecked box in `snowball_candidates.md` stays unchecked and un-fetched
indefinitely; because its manifest status is already `"proposed"`, no
future `propose` run re-lists it. The user is free to check it later if
they change their mind -- checkbox state is read fresh from the file at
`confirm` time, not cached anywhere else.

## 6. Error handling

- A seed whose DOI-to-OpenAlex-ID lookup fails (e.g. a transient
  network error, or a DOI OpenAlex no longer recognizes) is skipped with
  a printed warning, not a crash -- mirrors `resolve_works()`'s existing
  handling of an unresolvable `--faculty` name.
- `iter_citing_works()` reuses `fetch_with_retries()`/`FetchError`
  handling exactly as `iter_author_works()`/`iter_topic_works()` already
  do -- no new error-handling surface.
- `confirm` re-resolving a checked candidate whose DOI has since become
  unreachable (rare, but possible between `propose` and `confirm`) is
  treated as any other access failure: `resolve_full_text()` naturally
  returns `needs_manual` rather than raising.

## 7. Testing

Mirrors the existing flat `tests/` convention throughout:

- `discovery.py`: new tests for `resolve_work_by_doi()` and
  `iter_citing_works()`, same mocked-`fetch_with_retries` shape as the
  existing author/topic tests, including a dataset-type-exclusion case.
- `manifest.py`: tests for the promoted `skip_already_seen()`, plus
  confirming `discover.py`'s own tests still pass unchanged against the
  promoted (not duplicated) implementation.
- `worklist.py`: tests for the generalized checkbox-writer producing
  correct output for *both* the needs-manual and snowball status
  filters, and that checkbox-preservation still works per-file
  independently (checking a box in one file never affects the other).
- `snowball.py`: unit tests for `propose()` (candidate scored and
  recorded as `proposed`, already-seen candidates never re-proposed,
  relevance threshold/ceiling honored -- all via mocking
  `select_relevant_works`/`iter_snowball_candidates` the same way
  `test_discover.py` mocks `resolve_works`/`select_relevant_works`
  today) and `confirm()` (checked proposed entries fetched via a mocked
  `resolve_full_text`, unchecked ones left untouched, a confirmed-but-
  unfetchable entry ends up in `needs_manual_downloads.md`).

## 8. Follow-on discussion (open, not decided by this spec)

- **Backward citation parsing** remains the harder, deferred half of
  the original idea -- extracting a paper's own reference list from its
  Gemini-transcribed markdown has no structured format to rely on.
  Worth a future spike once forward-citation snowballing has real usage
  to learn from.
- **Seed scoping as the corpus grows.** `--seed-doi` exists from day one,
  but the *default* (every fetched/downloaded paper) will eventually
  need a better default than "everything" once the corpus is large
  enough that citation fan-out becomes unwieldy even with
  `--max-examined` bounding it -- not a problem at today's corpus size
  (~20 papers), worth revisiting once it grows.
- **Multi-seed provenance** (S5's known simplification) -- tracking
  every seed a candidate cites, not just the first, if that context
  turns out to matter for review decisions in practice.
