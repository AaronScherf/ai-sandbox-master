# Journal Discovery — Design Spec

Date: 2026-08-31
Status: approved in brainstorming, not yet planned/implemented

## 1. Problem & goals

`journal_articles/convert_journal_articles.py` already converts and indexes
whatever PDFs sit under `research/journal-articles/<topic>/` — but nothing
puts PDFs there in the first place. Today that folder is populated by hand
(`economics/`, `misc/`, four real papers converted so far). A brainstormed
plan (`research/independent-research/notes/lit_review.md`) sketched an
end-to-end pipeline — discovery via OpenAlex/Semantic Scholar, full-text
resolution via Unpaywall/EZProxy/arXiv, conversion via `pymupdf4llm`, and
indexing/RAG via Chroma + LangChain + Ollama — but its last two stages
duplicate `academic-rag-model`'s existing, tested, cost-tiered conversion
and indexing pipeline (see §8). Only its first two stages — discovery and
access — fill a real gap.

This spec designs **`journal_discovery`**: a new subproject that resolves a
faculty name or topic query into full-text PDFs on disk under
`research/journal-articles/<topic>/`, ready for the existing, unmodified
`convert_journal_articles.py` to pick up.

**Goals**
- Given a faculty name (`--faculty`, repeatable) or a topic/keyword query
  (`--topic`, repeatable), resolve candidate works via the OpenAlex API and
  fetch full text for as many as possible.
- Resolve full text in tiers: Unpaywall (open access) → arXiv (preprints) →
  Columbia EZProxy (gated, using a manually-supplied session cookie).
  Anything unresolved is flagged `needs_manual_download`, never guessed at.
- Route each fetched paper into a topic subfolder derived from its OpenAlex
  concept, auto-creating a new subfolder when no existing one fits.
  A `.meta.json` sidecar per PDF (title/authors/year/DOI/concepts/source)
  carries bibliographic metadata forward without touching the conversion
  pipeline's own frontmatter schema.
- Never re-fetch or re-flag a paper already seen in a previous run,
  regardless of whether it was reached via a faculty query or a topic
  query.
- Optionally sync fetched papers into Zotero (collection matching the topic
  folder, item metadata + PDF attachment).
- Stay a pure PDF-acquisition step: it never calls into `indexer/` or
  `convert_journal_articles.py` itself. A discovery run costs network
  calls only, never Gemini API spend — conversion is a separate, explicit,
  reviewable step, same as it is today for manually-added papers.

**Non-goals**
- No re-implementation of PDF→Markdown conversion, chunking, embedding, or
  RAG — `journal_articles/`, `indexer/`, and `rag/` already do this and are
  untouched by this spec (see §8 for why).
- No automated EZProxy login (browser automation, SSO/2FA handling) — the
  session cookie is supplied manually via `.env`; automating institutional
  login is future work if the manual hand-off proves too brittle.
- No embedding-model changes, no tagging-system changes — both are real,
  related questions (see §9) but touch the shared `indexer/` core across
  the *entire* existing corpus, not just newly-discovered journal articles,
  and need their own scoped evaluation.
- No orchestration wrapper that chains discovery + conversion automatically
  (approach C from brainstorming) — worth adding later as a thin
  convenience layer once discovery alone is working.

## 2. Architecture

A new sibling package, `journal_discovery/`, alongside `journal_articles/`,
`essays/`, `notes/`, `textbook/` in `academic-rag-model/`. It depends only
on `common/` (`.env` loading; its own lightweight HTTP retry loop, not
`gemini_utils.call_with_retries`, whose backoff parsing is Gemini-specific).
It does **not** import from `indexer/` and never writes into `.index/` — its
only contract with the rest of the pipeline is the same one
`journal_articles_instructions.md` already documents: a PDF sitting in
`research/journal-articles/<topic>/` is the handoff point. Run as a module
from the `academic-rag-model/` root, matching every other subproject:

```powershell
python -m journal_discovery.discover --faculty "Alexander de Sherbinin"
python -m journal_discovery.discover --topic "climate-forced displacement"
```

## 3. Components

- **`discovery.py`** — `resolve_works()` is the shared core; `--faculty`
  resolves an OpenAlex author ID (Columbia ROR-filtered, falling back to
  unfiltered search if no ROR match), then fetches that author's top-cited/
  recent works. `--topic` runs an OpenAlex works search on the given
  keywords, optionally ROR- and date-filtered. Both flags are repeatable
  and can be combined in one run, each producing its own list of works
  merged before dedup.
- **`access.py`** — per work, tries in order: Unpaywall
  (`best_oa_location.url_for_pdf`) → arXiv (if an arXiv ID is present) →
  EZProxy (`https://ezproxy.cul.columbia.edu/login?url=...` with a session
  cookie read from `.env`, e.g. `EZPROXY_SESSION_COOKIE`). A response whose
  `Content-Type` isn't `application/pdf` (an EZProxy login wall on an
  expired cookie) is never written to disk — the work is marked
  `needs_manual_download` and the run continues.
- **`topic_routing.py`** — sanitizes a work's top OpenAlex concept into a
  folder name and auto-creates `research/journal-articles/<concept>/` if it
  doesn't already exist.
- **`zotero_sync.py`** — `pyzotero`-based: find-or-create a Zotero
  collection matching the topic folder name, push the item's bibliographic
  metadata, attach the fetched PDF. A sync failure is logged but never
  blocks or discards an already-saved PDF; it can be retried independently
  later against the dedup manifest.
- **`.meta.json` sidecar** — written next to each fetched PDF
  (`<paper>.pdf` + `<paper>.meta.json`): title, authors, year, DOI,
  OpenAlex concepts, source tier (OA/arXiv/EZProxy), page count (when
  OpenAlex provides it). This is new and deliberately separate from
  conversion's own frontmatter: `convert_journal_articles.py` reuses
  `notes/transcribe_notes.py`'s `process_pdf()` completely unchanged, and
  that function's frontmatter schema (`routing`/`model`/`tags`) is shared
  by every pipeline in this repo. The sidecar carries bibliographic data
  forward for Zotero sync and dedup without touching that shared contract.

## 4. Data flow

1. `discover --faculty ... / --topic ...` → `resolve_works()` returns a
   merged list of OpenAlex work records.
2. For each work, key on DOI (falling back to OpenAlex work ID when no DOI
   exists) and check the dedup manifest (§5) — skip immediately if already
   `fetched` or `needs_manual`.
3. `access.py` attempts full-text resolution (OA → arXiv → EZProxy → flag).
4. `topic_routing.py` determines the destination folder from the work's top
   concept, auto-creating it if new.
5. PDF saved to `research/journal-articles/<topic>/<key>.pdf`; `.meta.json`
   sidecar written alongside.
6. Dedup manifest updated with the outcome (fetched, needs_manual, or
   skipped-oversized — see §6).
7. If Zotero sync is enabled, push the item + attachment.
8. Print a run summary: counts of fetched / flagged / already-seen.
9. Separately, the user runs `convert_journal_articles.py --dry-run` first
   (as already documented), then for real, exactly as today.

## 5. Dedup

`research/journal-articles/.discovery/seen.json`, keyed by DOI (or
OpenAlex work ID absent a DOI):

```json
{
  "10.1016/j.something.2024": {
    "status": "fetched",
    "folder": "climate-displacement",
    "fetched_at": "2026-08-31T00:00:00Z"
  }
}
```

Checked before any network fetch attempt, so a paper reached by both a
faculty-seeded and a topic-seeded run is only ever fetched once, and a
paper already flagged `needs_manual_download` isn't re-flagged every run
(the run summary distinguishes new flags from previously-known ones).

## 6. Error handling

- HTTP errors from OpenAlex/Unpaywall/EZProxy: a plain retry loop honoring
  a `Retry-After` header when present, otherwise fixed backoff — not
  `common.gemini_utils.call_with_retries`, whose retry-delay parsing is
  written specifically for Gemini's `retryDelay` error text.
- Non-PDF responses are caught by `Content-Type` before any disk write.
- A missing or expired `EZPROXY_SESSION_COOKIE` degrades a gated paper to
  `needs_manual_download`, not a hard failure of the run.
- The existing 150-page oversized-document guard stays exactly where it is
  today, in `convert_journal_articles.py` — not duplicated here. Discovery
  only records page count in the sidecar (when OpenAlex provides it) for
  information; the skip decision remains conversion's alone, per its own
  documented reasoning (`journal_articles_instructions.md`).
- A Zotero sync failure never discards or blocks a PDF that's already
  safely on disk.

## 7. Testing

Mirrors the existing flat `tests/` convention (package-qualified imports
via the root `conftest.py`):

- `discovery.py` / `access.py`: mocked HTTP responses, no real network
  calls in tests.
- `topic_routing.py`: pure unit tests for sanitization and auto-create
  logic.
- Dedup manifest: pure unit tests for read/update/skip logic.
- `zotero_sync.py`: mocked `pyzotero` client.

## 8. Why stages 3–4 of `lit_review.md` are out of scope

`lit_review.md` proposed `pymupdf4llm` for conversion and
Chroma + `sentence-transformers` + LangChain + Ollama for indexing/RAG.
Checked against what already exists:

- **Conversion:** the existing "free local extraction" tier already uses
  `pymupdf`/`pypdf` locally, but with tiered fallback (hybrid repair, then
  Gemini-vision) for pages that extract badly — real data on this exact
  corpus shows 32-43% of pages per paper need that fallback
  (`journal_articles_instructions.md`). A single-shot `pymupdf4llm` call
  with no fallback would silently regress quality on exactly the pages
  already known to need help.
- **Indexing/RAG:** `indexer/` (per-file cards, corpus-wide tag mining,
  passage-level chunking, multi-root cosine search) and `rag/rag_agent.py`
  (stateless, citation-grounded Q&A) already do this, tested, and running
  against real data including journal articles already in this corpus.
  Standing up Chroma + LangChain + Ollama alongside them would fragment
  the corpus across two incompatible index/RAG stacks for no benefit.

One real idea from stage 4 *is* worth pursuing, just not here (see §9).

## 9. Follow-on discussion (open, not decided by this spec)

**Local embeddings for passage chunking (cost).** `chunk_index.py`
generates "potentially hundreds of chunk-embedding calls" per file
(`chunk_index.py:13`) via `gemini-embedding-001` — by far the highest-
volume embedding cost in the pipeline (`index_card.py` and
`index_search.py` only embed once per file or once per query). A local
`sentence-transformers` model (e.g. `BAAI/bge-small-en-v1.5`, as
`lit_review.md` proposed) is a plausible free replacement for exactly this
high-volume, per-chunk workload. Not in scope here because `index_card.py`,
`chunk_index.py`, `index_search.py`, and `retag.py` all embed into one
shared cosine-comparable vector space across the *entire* existing corpus —
swapping models means either a full re-embed or maintaining two
incompatible spaces. Needs its own quality-vs-cost evaluation first (same
practice already used for `rag_agent`'s generation-model choice: tested
side-by-side against real output before switching, per
`2026-08-30-rag-agent-design.md`).

**Tagging: `retag.py` vs. OpenAlex concepts.** These solve the same problem
in opposite ways:
- `retag.py` is corpus-aware — a holistic LLM call proposes candidates from
  what's *actually* in the hub, then empirically validates each against
  real card embeddings (`MIN_TAG_CLUSTER_SIZE=3` at `threshold=0.65`
  in `retag.py`) — but costs an LLM call plus per-candidate embedding
  calls, and only ever reflects the existing corpus; it has no way to
  unify with any external taxonomy.
- OpenAlex concepts are free (arrive with the work's metadata, no LLM or
  embedding cost), standardized across all of scholarship — but only exist
  for works OpenAlex indexes. A scanned lecture note, handwritten problem
  set, or essay will never get one, and they don't adapt to this hub's own
  vocabulary or pedagogical framing.
- A middle path worth a future spike: feed OpenAlex concepts into
  `retag.py` as free candidate tags for journal-article cards specifically
  (skipping the holistic-LLM-proposal cost for that subset) while still
  gating them through the existing empirical-validation step — so
  OpenAlex-native tags and organically-discovered tags from non-journal
  content end up unified through one validation gate rather than two
  parallel tagging systems.

**EZProxy manual cookie fragility.** The manual hand-off (§1 non-goals) is
the simplest thing that could work, but session cookies expire; if gated-
paper volume turns out to matter, semi-automated browser login (Playwright
driving Columbia SSO, captured cookies) is the natural next step — deferred
here since it was explicitly out of scope for this pass.

**Orchestration wrapper.** A thin command chaining `discover` →
`convert_journal_articles --dry-run` → (human confirms) → real conversion,
for the common case — cheap to add once `journal_discovery` alone is
proven out; not designed here (approach C from brainstorming).
