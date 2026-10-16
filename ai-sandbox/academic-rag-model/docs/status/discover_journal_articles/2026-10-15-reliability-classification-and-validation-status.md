# Journal Discovery: Reliability Fixes, Classification Mode, and Real-Run Validation

Continuation of [2026-09-01-journal-discovery-status.md](2026-09-01-journal-discovery-status.md)
(still the record for the original build and the EZProxy/snowball work).
This entry covers the reliability-and-classification spec/plan
([spec](../../superpowers/specs/discover_journal_articles/2026-10-14-reliability-and-classification-design.md))
through its full review cycle, and a live real-run validation of the
whole discovery-to-classification pipeline against fresh topic/author
queries.

## What shipped

- **PR #17** (`claude/journal-discovery-spec`, merged to `main`): Section A
  reliability fixes (OA-download fallback chain, PDF validation, examined
  counter, HTTP timeout/`Retry-After` parsing, per-run time budget, atomic
  writes, scoped `--retry`) and Section B classification proposal mode
  (`topic_proposals.py` -- a read-only ledger proposing folder/tag
  corrections from OpenAlex Topics data, applied only on explicit
  `--resolve`/`--reject`, never automatically).
- **PR #18** (`claude/journal-discovery-minors`, merged to `main` as
  `eac6503`): all 10 Minor findings deferred from PR #17's final
  whole-branch review, each fixed with its own RED->GREEN TDD cycle --
  `Retry-After` clamping/NaN handling, PDF page-count validation (pypdf's
  silent zero-page resolution on a broken `/Kids` reference), `--reject`
  help text, proposal-ledger skip counts, a stale doc link, a `retrieved`
  counter, an `--retry`-ignores-other-flags warning, atomic PDF writes
  (`write_bytes_atomic`), the time budget checked within a paper's own
  access-tier chain (not just between papers) plus a sane default (900s),
  and `--retry`/`backfill_topics.py` resolving OpenAlex-id-only manifest
  keys directly via `GET /works/{id}` instead of skipping them as
  "no DOI". Full suite 3559 passed at merge (up from 3515 at PR #17).
- **A follow-up fix, found during real-run validation below** (merged
  directly to `main` as `d16c769`, no PR -- explicit request, bypassing
  the usual push+PR convention for this one change): `iter_topic_works`
  built `filter=default.search:<keywords>` without escaping a literal
  comma in a free-text `--topic` phrase. OpenAlex's filter syntax treats
  a bare comma as the filter separator and rejects the whole request
  with 400 ("A filter value contains an unescaped comma"). Any
  multi-word topic phrase containing a comma -- e.g. "disaster
  resilience, response, recovery" -- hit this. Fixed by wrapping the
  value in double quotes whenever it contains one. TDD'd
  (`test_quotes_a_keyword_phrase_containing_a_literal_comma`), full
  suite green (3638 passed) on the merged result before push.

## Real-run validation, 2026-10-15

Ran the full discovery-to-classification pipeline live against the real
`research/journal-articles/` vault (not a scratch directory), in three
passes:

1. **Topic-keyword run**, scratch directory first:
   `--topic "disaster resilience, response, recovery" --topic "3R
   disaster framework" --topic "disaster relief"` -- failed with the
   comma bug above on the first attempt; fixed, then succeeded: 60
   retrieved, 15 accepted (threshold 0.5), 7 fetched, 8 needs-manual.
2. **Same topic-keyword run repeated against the real vault**: identical
   outcome -- same 7 DOIs fetched, same scores, same folder routing.
   Confirms the pipeline is deterministic for a fixed query within a
   short window (OpenAlex's own ranking didn't shift), not stochastic.
3. **Author-name run**, real vault: `--faculty "Donald Rubin"` with a
   relevance prompt naming his actual research area (causal inference,
   potential outcomes, propensity scores, missing data) rather than
   relying on the name match alone: 61 retrieved, 6 accepted, 1 fetched,
   5 needs-manual.

**Relevance-scoring and topic-routing quality, inspected directly:**
all 15 accepted disaster-keyword papers were genuinely on-topic (disaster
management/resilience/recovery, post-disaster waste management,
earthquake recovery, business continuity, post-disaster social support)
with sensible folder placement (business, computer-science, geography,
psychology matched each paper's actual framing). The Rubin run's 6
accepted papers were all squarely in his domain -- the one fetched paper
was co-authored by Rubin himself ("Diagnosing missing always at random
in multivariate data"), and the 5 needs-manual entries were all
propensity-score/missing-data/Rubin-Causal-Model papers, confirming the
author-id-plus-relevance-prompt combination filters out off-topic
co-authored or citing work rather than admitting everything by an
author's OpenAlex id. No mis-classification observed in either run.

These three runs wrote real PDFs/sidecars into the shared vault and
updated its `.discovery` manifest (explicit go-ahead given beforehand,
since this permanently marks the fetched/examined papers as "seen" for
future runs).

## Tracker and doc housekeeping (same day)

- `docs/trackers/academic_hub_to_do.md`: TODO-0035 and TODO-0036 reworded
  to drop their "once X lands/ships" blocker language -- both the
  OA-fallback fix and the classification proposal mode are now merged to
  `main`, so both items are unblocked and ready to revisit on their own
  merits.
- This file supersedes the 2026-09-01 doc as the current snapshot for
  the website's project page; that doc remains the record of the
  original build and is not rewritten.

## Lifecycle references

### Specs

- [2026-08-31-journal-discovery-design](../../superpowers/specs/discover_journal_articles/2026-08-31-journal-discovery-design.md)
- [2026-09-02-journal-discovery-snowball-design](../../superpowers/specs/discover_journal_articles/2026-09-02-journal-discovery-snowball-design.md)
- [2026-10-14-reliability-and-classification-design](../../superpowers/specs/discover_journal_articles/2026-10-14-reliability-and-classification-design.md)

### Implementation plans

- [2026-09-01-journal-discovery-plan](../../superpowers/plans/discover_journal_articles/2026-09-01-journal-discovery-plan.md)
- [2026-09-02-journal-discovery-snowball-plan](../../superpowers/plans/discover_journal_articles/2026-09-02-journal-discovery-snowball-plan.md)
- [2026-10-14-reliability-and-classification-plan](../../superpowers/plans/discover_journal_articles/2026-10-14-reliability-and-classification-plan.md)

### Tests

- [test_discover](../../../tests/discovery/discover_journal_articles/test_discover.py)

## Open follow-ups

Unchanged from the tracker: TODO-0035 (browser-assisted download tier --
measure remaining manual-download workload first), TODO-0036 (OpenAlex
Topics vs. Academic Hub tag-mining consolidation, now unblocked),
TODO-0037 (unified discovery-to-index convenience CLI). No new gaps
surfaced by this validation pass beyond the comma-escaping bug, which is
already fixed above.
