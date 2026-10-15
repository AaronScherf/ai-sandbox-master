# Journal discovery: reliability fixes and classification proposal mode

Date: 2026-10-14. Status: approved design, pending implementation plan.

## Context

Codex's audit ([2026-10-14-journal-discovery-audit.md](../../../trackers/pending_updates/2026-10-14-journal-discovery-audit.md), evidence appendix alongside it) verified several defects against the current code and one structural problem in folder routing. This spec covers the subset of that audit's findings that are ready to implement now: bounded correctness fixes to the download/retry path, and a new classification proposal mode. It explicitly excludes the audit's coverage/recall questions (OpenAlex-only candidate discovery, query caps, possible second providers, reranking) — those require the audit's recommended 20-30 known-paper benchmark first, and are deferred to a future revision once that benchmark exists.

Code baseline: same repository, `academic-rag-model/discovery/discover_journal_articles/`. Paths below are relative to `academic-rag-model/` unless stated otherwise.

## Goals

1. Fix verified reliability bugs in the OA-download fallback chain, the "examined" counter, HTTP timeout/retry handling, and write durability.
2. Add a scoped retry mechanism so the 64 existing `needs_manual` entries can be re-attempted under the fixed fallback logic without a full rerun.
3. Replace the single-Concept folder-routing rule with a reviewed, Topics-based classification proposal mode that never moves files automatically.
4. Correct three stale items in the project to-do tracker.

## Non-goals

- Adding a second candidate-discovery provider, query reranking, or budget rebalancing (deferred; needs the benchmark).
- Automatic file moves based on classification proposals.
- Backward-citation graph expansion, browser-automation download tier, or the discovery-to-index convenience wrapper (TODO-0035/0037 stay open, reworded only).
- Cross-run version-linking / duplicate-paper merging beyond what exact normalized-title dedup already does.

## Section A — Reliability fixes

### A.1 OA-download fallback chain

**Current behavior** (`access.py:141-145`): `resolve_full_text` evaluates `work.oa_url or try_unpaywall(...) or try_semantic_scholar(...) or try_core(...)` and stops at the first truthy URL, whether or not the eventual download/validation of that URL succeeds. A present-but-broken `oa_url` (landing page, 404, non-PDF) prevents ever trying Unpaywall/Semantic Scholar/CORE.

**Fix:** restructure as an ordered list of `(provider_name, url_getter)` candidates. For each candidate in order: fetch the URL, validate it (see A.2), and only move to the next candidate on failure. Deduplicate URLs across candidates before attempting (two providers can return the same broken link). Record, per attempt: provider name, URL, HTTP status or exception class, and validation outcome. The work is marked `needs_manual` only after every candidate URL has been tried and failed — not after the first URL is simply present.

Replace `source_tier='open_access'` with the provider name that actually succeeded, so a sidecar can answer "which provider found this" instead of just "it was open access."

### A.2 PDF validation

**Current behavior:** a response is accepted as a successful PDF if `Content-Type` contains `application/pdf`. No byte-level check.

**Fix:** after a candidate URL returns 200 with a PDF-like content type, read the response body and verify it starts with the `%PDF-` magic bytes and is parseable (reuse whatever PDF library is already a dependency for a cheap page-count check — no new dependency). A response that passes the `Content-Type` check but fails this validation counts as a failed candidate and the chain proceeds to the next provider (A.1), not an immediate `needs_manual`.

### A.3 Examined counter

**Current behavior** (`discover.py:69`): `counts["examined"] = len(scored)`, where `scored` is the accepted-list, not every candidate that was scored against the relevance threshold.

**Fix:** track `examined` as a running count incremented once per candidate actually passed through `score_work`, independent of whether it was accepted. Keep `accepted` as today's `len(scored)` under its own name. Final summary prints `retrieved`, `deduplicated`, `examined`, `accepted`, and `fetched` as five distinct counts (today's printed line conflates several of these).

### A.4 HTTP timeouts and Retry-After parsing

**Current behavior:** download requests specify a 30-second timeout; metadata/search requests (OpenAlex, Unpaywall, Semantic Scholar, CORE) do not specify one. `Retry-After` header parsing assumes a numeric seconds value.

**Fix:** add an explicit connect/read timeout to every metadata/search request in `http_utils.py` (reuse the existing 30-second constant unless a provider's docs specify otherwise). Extend `Retry-After` parsing to accept either an integer-seconds value or an HTTP-date (`email.utils.parsedate_to_datetime`), falling back to a fixed default backoff if neither parses.

### A.5 Per-run request/time budget

**Current behavior:** no cap on total requests or wall-clock time for a discovery run; a run that hits sustained 429/504s can retry indefinitely or silently take far longer than expected.

**Fix:** add a per-run wall-clock budget (CLI flag, default generous e.g. 15 minutes) and a per-run request-count budget. On exhaustion, stop cleanly and print a partial-results summary (counts from A.3, plus "stopped: time/request budget exhausted") instead of a summary that reads the same as a completed run.

### A.6 Atomic writes

**Current behavior:** manifest and sidecar writes are direct overwrites; a crash mid-write can corrupt either file.

**Fix:** write to a temp file in the same directory and `os.replace()` over the target for manifest.py and metadata_sidecar.py writes. PDF writes already go through a download-then-move step in most paths — audit and align any that don't (confirm during implementation; this spec does not assume which specific call sites need it, since that's an implementation-time inspection, not a design decision).

### A.7 Scoped retry

**Current behavior:** `skip_already_seen` treats any manifest key as seen, including `needs_manual`. An ordinary rerun never retries a `needs_manual` entry, so the fixed fallback chain (A.1) only helps future discoveries unless something re-queues the existing 64.

**Fix:** add a `--retry <id> [<id> ...]` CLI action (where `<id>` is a DOI or OpenAlex ID already in the manifest as `needs_manual`) that: looks up each ID's stored `Work` data, re-runs the A.1 fallback chain against it only, and updates its manifest entry in place (to `downloaded`/`fetched` on success, or refreshed `needs_manual` with updated attempt records on repeat failure). It does not touch any other manifest entry and does not re-run discovery/scoring.

## Section B — Classification proposal mode

### B.1 Problem

`route_to_folder` (`topic_routing.py:26-31`) files a paper under `work.concepts[0]` alone: the single broadest-level OpenAlex Concept, chosen before score is considered among concepts of the same level. This is why agriculture papers end up in `Business` when "Business" is a broader Concept than the paper's actual narrow-topic match. Concepts are also deprecated by OpenAlex in favor of Topics, and existing sidecars only ever stored the flat Concept display-name list — scores, levels, and IDs are lost, so nothing today can compare alternative labels after the fact.

### B.2 Data model

Add a `topics` field to the sidecar schema: a list of `{id, display_name, score, level}` entries as returned by OpenAlex's `topics` field on a `Work` lookup (separate from the existing deprecated `concepts` field, which stays for backward compatibility with old sidecars but is no longer written for new fetches). Fetch `topics` at the same point the code currently fetches `concepts` — no additional API call beyond what already resolves a `Work`.

### B.3 Backfill

One-time script (`tools/backfill_topics.py` or similar — final name decided at implementation time) that: iterates the ~97 existing manifest entries, looks up each by DOI (falling back to OpenAlex ID) against the OpenAlex API, and writes the resulting `topics` list into that paper's sidecar without changing its folder or any other field. This is a single bounded run of public, unauthenticated GET requests (same endpoint the audit itself used) — no paid model cost, no download, no file move.

### B.4 Proposal and review

New function `propose_folder(work, current_folder)` returns a ranked list of candidate folders derived from `topics` (sanitized the same way `sanitize_topic_name` works today), each annotated with its topic's score and level, plus the paper's current folder as a status-quo option.

Surface proposals through an interactive Artifact, following the existing project convention (`core/indexer/offering_links.py` and its review artifact) rather than a hand-edited file: one row per paper, showing current folder, top-3 suggested folders with scores, and accept/keep-current/custom-folder choices. Decisions are recorded in the artifact's `db`, then applied by a dedicated `resolve_folder_proposal()` function in `topic_routing.py` — never by direct file moves from the UI layer.

This proposal pass runs over both newly discovered papers (going forward) and the backfilled existing papers (B.3) — same review surface for both.

### B.5 Applying a decision

On accept: move the paper to the chosen single folder (one physical location, not multiple/symlinked). Regardless of which folder is chosen, write *all* topics above some minor relevance floor (e.g. score > 0.2 — exact threshold decided at implementation time against real data) into the sidecar as tags, so a paper filed under its primary topic remains findable by its secondary topics through the existing tag-search path. No new folder-per-tag duplication.

### B.6 Staleness

Store a fingerprint of the `topics` data (e.g. a hash of the sorted `(id, score)` pairs) alongside each accepted decision. If a later fetch/backfill produces a different fingerprint for the same paper (OpenAlex re-ranked or added topics), the existing folder placement is left untouched, but the paper is flagged in the next proposal-mode run as "topics changed since last decision — review again," rather than silently re-proposed or silently kept stale forever.

### B.7 Explicitly not in this spec

No corpus-wide clustering, no automatic move based on a confidence threshold, no deletion of the legacy `concepts` field from old sidecars, no change to `core/indexer`'s own separate tag-mining system (B.4's suggestions are compared against the existing index visually by the reviewer, not merged programmatically).

## Testing approach

- **A.1/A.2**: fixtures covering a working first URL, a failing first URL with a working second, all URLs failing, a URL that returns 200 with `Content-Type: application/pdf` but non-PDF bytes, and duplicate URLs across providers.
- **A.3**: a run with more scored candidates than accepted ones, asserting `examined > accepted`.
- **A.4**: fixtures for a numeric `Retry-After`, an HTTP-date `Retry-After`, a malformed value, and a request that exceeds the configured timeout.
- **A.5**: a fixture run that exhausts a tiny request budget, asserting a clean partial-results summary and no exception.
- **A.6**: a crash-simulated write (kill mid-write via a mocked file handle) that leaves the previous file intact.
- **A.7**: `--retry` against a fixture manifest with a mix of `needs_manual` and other states, asserting only the named IDs changed.
- **B.2-B.6**: fixtures for proposal generation against known Concept/Topic data (including the audit's own carbon-farming and Zambia smallholder examples), the staleness fingerprint changing between two fetches, and `resolve_folder_proposal` applying an accepted decision without touching unrelated manifest/sidecar fields.
- **Live checks** (bounded, authorized): the B.3 backfill run against the real 97-entry manifest; a `--retry` call against a handful of real `needs_manual` IDs to confirm the fallback chain actually recovers at least one.

## Tracker corrections (`docs/trackers/academic_hub_to_do.md`)

- **TODO-0035**: reword away from "bot-detection evasion" framing; gate it explicitly on first measuring how much manual-download workload remains after A.1/A.2 ship.
- **TODO-0036**: fix the stale `pipeline.py` reference to `discover.py`; note that Section B's proposal mode is the groundwork this item asked for, and that the ">20 papers" test corpus size should be re-checked against actually-converted/indexed count, not just manifest `acquired` count.
- **TODO-0037**: fix the same stale `pipeline.py` reference to `discover.py`.
