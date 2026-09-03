# Journal Discovery: Status Summary

Start here for "what happened and where do we stand" on the journal
discovery subproject -- `journal_discovery/`, which resolves a faculty
name or topic query into full-text PDFs under
`research/journal-articles/<topic>/`. Design reference:
`docs/superpowers/specs/2026-08-31-journal-discovery-design.md`;
implementation plan: `docs/superpowers/plans/2026-09-01-journal-discovery-plan.md`.
Merged into `main` 2026-09-01 (commit `bb94cbb`), 545 tests passing at
merge; 586 passing after a day-two round of real-usage fixes and
features (commit `8e27c24`); 616 passing as of `2f287d2` after adding
and live-validating citation snowball sampling (see that section
below). No dedicated feature branch exists anymore -- all work since the
original merge has landed directly on `main` (the snowball work used a
temporary worktree/branch, merged and deleted the same day).

## What shipped

`discovery.py` (OpenAlex author/topic resolution), `relevance.py` (local
`sentence-transformers` scoring + the threshold/ceiling volume control),
`manifest.py`/`metadata_sidecar.py` (dedup + bibliographic metadata),
`topic_routing.py` (auto-created topic folders), `access.py` (paced
Unpaywall -> arXiv -> EZProxy tiers), `zotero_sync.py` (optional), and
`discover.py` (the CLI wiring all of it together). Full detail in the
spec and plan above.

## Real-world validation: EZProxy tier, tested live 2026-09-01

The design spec's S9 flagged one open risk before relying on
`EZPROXY_SESSION_COOKIE` for real use: does a manually-obtained session
cookie survive a real paced session, or does it expire/get challenged.
Live testing found a different, more fundamental blocker *before* that
question was ever reached.

**What was tested:** the user authenticated for real through
`https://ezproxy.cul.columbia.edu/login?url=<a real DOI>` in a browser
(confirmed by a Columbia library ribbon appearing on the destination
page), for two different real, gated articles from two different
publishers (Taylor & Francis, and Elsevier/ScienceDirect). From the same
machine/network, a plain Python `requests` call through
`access.build_ezproxy_url()` -- with **no cookie at all** -- was then
made against both.

**Result 1 (Taylor & Francis):** the request reached the real publisher
domain with no Columbia CAS login redirect at all (evidence that
EZProxy/Columbia's own access check passed, likely via IP-based
recognition of the already-authenticated session's network) -- but got a
403 with a Cloudflare "Just a moment..." JS-challenge page
(`<meta name="robots" content="noindex,nofollow">`, 5.6KB body), not a
real article or PDF.

**Result 2 (Elsevier/ScienceDirect):** same pattern. The initial
`linkinghub.elsevier.com` hop returned 200 with no CAS redirect (again
suggesting IP-based access was already granted), and following its
HTML `<meta http-equiv="REFRESH">` redirect by hand landed on the real
`sciencedirect.com` article URL -- which also returned 403, this time a
large (832KB) ScienceDirect-branded page containing the literal string
`CLOUDFLARE_ERROR_1000S_BOX`, confirming it's the same category of
block, just a differently-styled Cloudflare error page.

**Conclusion:** in both real cases tested, EZProxy/Columbia authorization
itself was not the obstacle (no CAS login wall was ever hit from the
already-authenticated network) -- the block happens at the *publisher's*
own bot-detection layer (Cloudflare), which fingerprints the requesting
client itself (no real browser engine, no JS execution, no matching TLS
fingerprint) independent of whether valid institutional credentials or a
session cookie are presented. This is a different and more fundamental
limitation than session-cookie fragility: a fresh, perfectly valid
cookie would very likely hit the same wall, because the block fires
before authentication would be checked.

## Corrections made against real evidence, not assumptions

1. **The spec's S9 anticipated the wrong failure mode.** It assumed the
   main EZProxy risk was cookie expiry/challenge over a paced session --
   worth testing carefully with `--pace-per-hour`-limited volume. Real
   testing found the dominant, first-encountered failure is publisher-
   side bot protection (Cloudflare), which triggers on a single
   unauthenticated *or* authenticated scripted request alike, before
   pacing or cookie freshness are ever relevant.
2. **A deliberate scope boundary, stated plainly to the user and
   recorded here:** working around Cloudflare's bot detection
   (fingerprint spoofing, replaying its `cf_clearance` cookie, stealth
   headless-browser tooling) was explicitly ruled out as a direction to
   pursue -- that crosses from "fetching content you're entitled to"
   into actively defeating a publisher's anti-bot system, a different
   category of action than the account-safety pacing this pipeline was
   built for.

## Specific limitations, honestly assessed

- **The EZProxy tier's automated fetch is unreliable for major
  publishers, by design of the publishers, not a bug here.** Expect a
  meaningfully high `needs_manual_download` rate for gated papers behind
  Cloudflare-class protection (which appears to include at least
  Taylor & Francis and Elsevier, and plausibly most major academic
  publishers) -- the code already degrades to this correctly (spec S6),
  so no fix is needed; it's the realistic steady state for this tier,
  not a broken fallback path.
- **Open-access and arXiv tiers are unaffected.** Unpaywall and arXiv
  are real APIs built for programmatic access, not general publisher
  websites defending against scraping -- nothing in this finding changes
  their reliability.
- **A genuine, not-yet-built alternative exists and is worth naming
  precisely:** a full browser-automation tool (Playwright) driving the
  *actual* Columbia SSO login and article/PDF navigation -- a real
  browser executing real JS with a real TLS fingerprint -- is a
  meaningfully different thing from spoofing a plain HTTP client, and
  was already named as a legitimate future direction in the design
  spec's S9 ("semi-automated browser login"). It is not guaranteed to
  pass every publisher's specific Cloudflare configuration (some tiers
  specifically detect automation-framework signals like
  `navigator.webdriver`), and is a real engineering lift (new
  dependency, browser install, 2FA handling) -- not attempted in this
  pass.

## Bugs found and fixed via real usage, 2026-09-02

Both found on the very first live runs, not by inspection -- exactly
what real-corpus validation is for.

1. **Crash on a terminal HTTP error.** The first real run
   (`--topic "climate shock adaptation"`) hit a genuinely OA-flagged URL
   (`aeaweb.org`) that returned a permanent 403. `fetch_with_retries()`
   raises `FetchError` for a non-retryable status rather than returning
   a response, but `_download()`/`try_unpaywall()` in `access.py` didn't
   catch it -- the whole run died instead of falling through to the next
   tier / `needs_manual`, as designed. Fixed (commit `92d226f`, regression
   test added): both functions now treat `FetchError` the same as a
   non-PDF response.
2. **OpenAlex's author-works list includes non-paper records.** A real
   author-seeded batch (Daniel Björkegren, 20 examined) included 7
   RCT-registry entries and a replication-data record (OpenAlex
   `type="dataset"`) alongside real papers -- confirmed directly via the
   OpenAlex API for two of them ("Manipulation-Proof Machine Learning"
   trial registration, and a replication-data record). These can never
   have a fetchable PDF and were burning
   `--max-results`/`--max-examined` candidate slots for nothing. Fixed
   (commit `6e52f3f`): `iter_author_works()`/`iter_topic_works()` now
   filter out `type="dataset"` records before they ever reach relevance
   scoring.

## Real end-to-end runs, 2026-09-02

**Open-access topic search** (`--topic "climate shock adaptation"`,
`--max-results 3`): after the crash fix, ran clean -- 1 fetched, 2
correctly flagged `needs_manual`. The fetch: "Anticipatory Learning for
Climate Change Adaptation and Resilience" (Tschakert & Dietrich, 2010),
a real, valid 365KB PDF (`%PDF-1.6` header confirmed), correct
`.meta.json` sidecar, relevance score 0.51 against threshold 0.5. Its
auto-created folder (`resilience-materials-science`) is itself a live
example of an OpenAlex concept-ranking quirk: the paper's top-ranked
concept was literally "Resilience (materials science)" -- a homonym
collision, not the social/ecological sense the paper is actually about
-- more on-topic concepts ("Climate change adaptation") were ranked
lower by OpenAlex itself.

**Faculty-seeded batch, Daniel Björkegren** (two runs, `--max-results 20`
then `90`, `--pace-per-hour` raised to 120 then 300 for the batch since
OA-dominated output carries none of the EZProxy account-safety risk the
default pacing protects against): found and exhausted essentially his
entire relevant OpenAlex-indexed output -- 19 genuine (non-dataset)
candidates total, of which **3 fetched**, 16 flagged `needs_manual`
(mostly SSRN-hosted working papers, which Unpaywall doesn't index as OA
and whose own site is presumably similarly bot-protected; a couple of
AEA journal articles hitting the same Cloudflare pattern already
documented above; World Bank policy papers with no indexed OA copy; one
Nature *News* piece merely mentioning him). The run stopped well short
of the `--max-results` cap both times -- not a partial sample, but
essentially the full reachable-and-relevant slice of his record. Two of
the "his papers" results were also flagged as likely OpenAlex
author-disambiguation errors (climate/agricultural-econometrics papers
with no topical relation to his actual digital-credit/mobile-money
research) -- a different person's work probably merged into the same
author ID, a known limitation class of automated author disambiguation,
not something this pipeline can detect on its own today.

**Takeaway confirmed by real numbers, not just the earlier EZProxy
test:** for real applied-economics authors, a meaningful fetch ceiling
around 15-20% of total output is realistic given current publisher
access patterns (SSRN, AEA, Elsevier, Taylor & Francis all presenting
some form of bot protection or non-indexed-OA gap) -- `needs_manual` at
volume is the expected steady state, not a signal something is broken.

## Needs-manual worklist, 2026-09-02

Per user request, closing the loop on "what do I do with all these
`needs_manual` entries": `record_outcome()` (commit `b92693f`) now
captures title/authors/year/DOI-link and a pre-created target folder for
`needs_manual` entries too, not just successful fetches (previously only
`.meta.json` sidecars, written solely on the fetched path, carried this
information at all). Every run regenerates
`research/journal-articles/needs_manual_downloads.md` from the *entire*
current manifest -- a click-through Markdown list, each paper's title
linking to its DOI, with the exact `research/journal-articles/<topic>/`
folder to save it into once downloaded by hand, so
`convert_journal_articles.py` picks it up automatically afterward with
no extra sorting step. A follow-up fix (commit `8757d0f`) excludes
stale dataset-type entries (recorded before the filter above existed)
from the generated worklist too, via a backfilled `work_type` tag, so
old RCT-registration noise doesn't clutter it. The existing manifest
was one-time backfilled with real OpenAlex data (title/authors/folder/
work_type) so the very first generated worklist was immediately useful,
not just future runs.

## Efficiency ideas acted on, 2026-09-02

Of the brainstormed list below, four were picked for immediate
implementation after user feedback (the other two -- CORE.ac.uk, and the
author-mis-attribution check -- stayed open ideas, not built):

1. **Dedup before relevance scoring, not after** (commit `6483594`).
   `select_relevant_works()` used to see already-seen candidates in
   OpenAlex's own list order and burn `--max-results` slots re-selecting
   them before ever reaching new candidates -- exactly why the second
   Björkegren run needed `--max-results 90` to find only 5 new ones.
   `discover.py` now filters already-seen works out of the raw
   `resolve_works()` stream before it ever reaches scoring.
2. **Tier-specific pacing** (commit `49085f8`). Pacing's real purpose --
   protecting the user's own Columbia account from automated-abuse
   detection -- never applied to OA/arXiv downloads, which hit diverse,
   unrelated hosts, not Columbia's proxy. Uniform pacing across every
   tier is why the Björkegren batch needed `--pace-per-hour` manually
   bumped to 300 just to finish in reasonable time. OA and arXiv
   downloads are now unpaced by default; only the EZProxy tier honors
   `--pace-per-hour`.
3. **Semantic Scholar as a second OA-discovery tier** (commit `6a582ac`).
   A real, free, keyless API -- same shape and risk profile as Unpaywall
   -- tried after `work.oa_url`/Unpaywall and before arXiv/EZProxy, to
   catch a green-OA copy Unpaywall's own crawl hasn't indexed.
4. **Exact-normalized-title duplicate detection** (commit `8372d9e`), per
   direct user report of repeats in the generated worklist. Real
   duplicates confirmed this session: "Causal Inference from Hypothetical
   Evaluations" under two SSRN revision DOIs; a World Bank and an SSRN
   copy of the same mobile-phone-credit paper. `select_relevant_works()`
   now tracks normalized (lowercased, punctuation-stripped) titles
   already selected and skips an exact match -- deliberately exact-match
   only, not fuzzy, to avoid any risk of merging genuinely different
   papers with similar titles (a real limitation: it does *not* catch a
   true near-duplicate like "...Predicts Credit Repayment" vs
   "...Predicts Loan Repayment", which differ by one word).

**A real mistake made and caught during the one-time manifest cleanup
that accompanied idea 4:** the cleanup script grouped existing
`needs_manual` entries by normalized title and kept the alphabetically-
first DOI per group -- for one group this kept an RCT-registration
record (`10.1257/rct.4649-1.1`, `type="dataset"`, already excluded from
the worklist) and silently dropped the actual real, fetchable preprint
(`10.26085/c36k5w`, `type="article"`, "Manipulation-Proof Machine
Learning") that happened to share its title. Caught by checking the
regenerated worklist against the prior one before considering the
cleanup done, not by any automated check -- restored by re-fetching the
dropped DOI's real metadata from OpenAlex and re-inserting it. **How to
apply:** an alphabetical or arbitrary tiebreak between duplicate
candidates is not safe when one of them might be a non-paper record --
prefer whichever candidate has the more informative `work_type` (or
simply isn't `"dataset"`) when one exists.

## Folder-naming fix and manual-download workflow, 2026-09-02

Per direct user report ("grasp", "competition-biology" as folder names
looked wrong): confirmed via the OpenAlex API that `topic_routing.py`'s
folder name came from `Work.concepts[0]`, which was sorted purely by
score -- and the top-scored concept is often a narrow, homonym-prone
level-2/3 concept (e.g. "GRASP" the metaheuristic algorithm for a paper
merely using the word "grasp"; "Competition (biology)" for a paper about
market competition) even when a sensible, broad level-0 field
("Sociology", "Business") is also present in the same list, just scored
lower. Fixed (commit `82e9883`): concept sorting now prefers any
level-0 concept over score ranking among narrower ones, falling back to
plain score ranking only when no level-0 concept exists at all.

**Applied retroactively, not just to future runs:** every existing
manifest entry was re-routed under the fixed logic via a one-time
script (re-querying OpenAlex per DOI), and the 4 real auto-fetched
files plus all 12 of the user's own manually-downloaded PDFs (already
sitting in the *old*, worse folder names) were physically moved into
their corrected folders (`business`, `computer-science`,
`environmental-science`, `sociology`, `geography`, `physics`), with old
now-empty folders removed. One residual known limitation: when a
paper's *only* level-0 concept is very weakly scored (e.g. "Nostalgic
Demand" -> "physics" at score 0.17, OpenAlex's classifier simply didn't
find good concepts for it), the result can still look odd -- not
regressed from before, just not fully solved either.

**A real cost bug found and fixed while auditing the corpus for
conversion (commit `3c86c47`):** the user's own Zotero library is
synced into this same directory tree, putting its own attachment copies
under `research/journal-articles/zotero/storage/<hash>/` -- structurally
indistinguishable from a topic folder to `convert_journal_articles.py`'s
recursive discovery, and in at least two cases (`Li et al. 2025`,
`Alatorre et al. 2025`) duplicating a PDF already converted elsewhere in
the tree. Left alone, conversion would have paid to re-process content
already on hand. `local/` held a similar stray duplicate. Both excluded
from discovery by directory name, at any depth.

**Checkbox tracking added to the worklist** (commit `ef25073`), per user
request: each entry is now `- [ ] [Title](link)`, and regenerating the
file (every `discover` run) preserves existing checkmarks by reading the
current file before rewriting -- a user's own manual progress-tracking
survives, distinct from the automatic removal the reconciler (below)
does once a download is actually confirmed by content.

**`reconcile_needs_manual.py` added** (commit `8e27c24`) -- the
explicit, human-run bridge between `journal_discovery`'s manifest and
`journal_articles`' converted output, since neither subproject calls the
other. A manually-downloaded PDF's filename is arbitrary (never matches
anything the pipeline would have generated), so matching is
content-based: a DOI substring match against the converted `.md` first,
a normalized-title substring match as fallback for papers that don't
print their DOI in the visible text. A confirmed match moves the
manifest entry to `status="downloaded"` (recording which `.md` matched)
and drops out of the regenerated worklist automatically. The script also
prints a folder/content review -- folder name next to a real content
preview for every converted paper -- so folder-appropriateness can be
checked against what a paper actually says, not just its OpenAlex
concept tags.

**Conversion + reconciliation completed, 2026-09-02.** 21 papers
converted, 760 pages total. Model usage split exactly along the
existing routing tiers, not chosen independently: every
`gemini_batched` (whole-document batching, used when >10% of a
document's pages extract as defective) document used
**gemini-3.1-flash-lite** (12 files, 503 pages, 66.2%); every
`gemini_accumulating` (clean per-page transcription) document used
**gemini-3.6-flash** (9 files, 257 pages, 33.8%). One transient
runaway-repetition-loop output was auto-retried successfully, no
manual intervention needed.

`reconcile_needs_manual.py`'s first real run: of the 15 outstanding
`needs_manual` papers, **12 confirmed downloaded and converted**
(title-matched against real content), dropped from the worklist
automatically. 3 genuinely remain (`needs_manual_downloads.md` now
correctly shows only these): "Nostalgic Demand" (never downloaded at
all), plus two with real, interesting content-based explanations rather
than a missing download:

- **"AI is transforming the economy — understanding its impact requires
  both data and imagination"** (the Nature *News* piece) has a real PDF
  and real converted content, but its actual printed subtitle
  ("...and studying it will require fresh approaches") doesn't match
  OpenAlex's stored title for that DOI -- a metadata-drift case the
  reconciler's exact-title matching correctly declined to force-match.
- **"Scoping for Competition in Network Industries..."** (`ssrn.3049364`)
  has a downloaded PDF, but its actual content is "Competition in
  Network Industries: Evidence from the Rwandan Mobile Phone Network"
  (`ssrn.3527028`) -- confirmed by near-identical file size (4,431,238 vs.
  4,431,243 bytes). Two different SSRN listing IDs, almost certainly the
  same underlying paper (a preliminary "scoping" SSRN posting vs. a later
  revision) -- the user likely got redirected to the same PDF from both
  links. Real evidence that discovery-time exact-title dedup (S9's known
  limitation) can't catch every duplicate: these two had genuinely
  different registered titles, so nothing before download could have
  flagged them as the same paper.

One correction made and worth recording honestly: mid-session, a check
of `Björkegren`'s name across converted files appeared to show literal
U+FFFD replacement characters (real corruption) -- retracted after
checking the actual codepoint directly (`0xF6`, correctly "ö"). What
looked like corruption was this session's own terminal failing to
*display* the character, not a bug in the conversion pipeline. Recorded
as a reminder to verify a suspected data-corruption claim against the
actual bytes/codepoints before reporting it, not against how a terminal
renders it.

## Open issue: charts/plots lose their underlying data on conversion

Checked directly against real converted output, 2026-09-02. Confirmed
first that `transcribe_notes.py`'s actual prompts (`build_transcription_prompt`,
`build_batch_transcription_prompt`) contain **no instruction at all**
about how to handle non-text visual elements -- "transcribe into clean
markdown... preserve reading order" is the whole instruction. What
happens with figures is Gemini's own emergent choice, not a designed,
guaranteed-consistent pipeline feature:

- **Data tables convert cleanly and losslessly** -- real numeric values,
  full row/column structure, e.g. a real converted table
  (`ssrn-3049364.md`): `| Switching Cost | $s$ | $36.09 | Hypothetical
  switching exercises |`.
- **Charts/plots get a bracketed caption-style description only** -- axis
  labels, variable names, sometimes tick-value ranges -- e.g.
  `[Graph 1: Call Price ($p^F/p^{base}$) vs Interconnection Rate ($0.15,
  0.10, 0.05, 0.00$)]`. The underlying curve/data points are **not**
  extracted. If a paper's key result lives only in a scatter plot or
  time series with no companion table, that result is effectively lost
  to the text representation the RAG/indexer layers will ever see.
- **Logos and decorative images** get a generic placeholder (`[Image of
  EconStor header and license information]`) noting presence only, which
  is fine -- there's no real content there to lose.

**Assessed as acceptable for now, not urgent** -- most quantitative
results in these papers also appear in a table or in-text statistic, so
the loss is real but partial, not sweeping. Left open rather than fixed:
a real fix would mean either a different (more expensive) transcription
prompt specifically instructing structured data extraction from charts,
or a separate image-description pass -- both real engineering lifts, not
attempted here.

## Citation snowball sampling: implemented and live-tested, 2026-09-02

Spec: `docs/superpowers/specs/2026-09-02-journal-discovery-snowball-design.md`;
plan: `docs/superpowers/plans/2026-09-02-journal-discovery-snowball-plan.md`.
Built as a new `journal_discovery/snowball.py` module with a two-phase
`propose`/`confirm` CLI, on an isolated worktree/branch, merged to `main`
(commits `8fd1835` through `047379d`, 616 tests passing at merge). Never
auto-fetches: `propose` seeds from every `fetched`/`downloaded` paper in
the corpus (or `--seed-doi`, repeatable), follows OpenAlex's forward
"cited by" graph, scores candidates through the same relevance gate as
`discover.py`, and writes a checkbox worklist
(`snowball_candidates.md`); `confirm` fetches only what's checked,
through the identical access chain as any other route. Website project
page updated to describe the new route.

**Two real bugs found on the very first live `propose` run, both fixed
same-day:**

1. **Crash on `None` relevance scores** (commit `662a28c`).
   `select_relevant_works()` can legitimately return a `ScoredWork` with
   `score=None` (a candidate with no abstract, kept as a filler); the
   snowball worklist writer tried to `:.2f`-format it unconditionally
   and crashed. Fixed with a null guard, regression test added.
2. **The no-abstract-fallback design itself was the deeper problem**
   (commit `2f287d2`). The first real `propose` run (prompt: development
   economics / mobile money / market competition, seeded from the 16
   already-fetched corpus papers) returned 50 candidates -- but 43 of
   them traced to one heavily-cited, completely off-topic seed paper
   (an urban-climate-resilience article) and carried `score=None`,
   because the old `select_relevant_works()` design let any
   no-abstract candidate fill leftover `--max-results` slots
   *regardless of relevance*, purely because nothing else was
   available to score. Root-caused two of these `None`-score
   candidates directly against the live OpenAlex API: both were
   closed-access Elsevier articles (*Economic Systems*,
   *Technology in Society*) with no `abstract_inverted_index` in
   OpenAlex's own record at all -- a publisher-side metadata gap
   (Elsevier not sharing abstracts through Crossref/OpenAlex for
   non-OA content), not a parsing bug here. Fixed by having
   `score_work()` fall back to the work's title when no abstract
   exists, returning a real (if weaker) similarity score instead of
   `None`; `select_relevant_works()` was simplified to run every
   candidate through the *same* threshold check, abstract- or
   title-scored, with the old "unscored candidates bypass the
   threshold" bucket removed entirely. A new `ScoredWork.scored_from`
   field ("abstract" or "title") flags the weaker signal, surfaced in
   the worklist as "(scored from title only, no abstract)". Net effect
   on the live data: of the 50 original candidates, only 2 were
   genuinely on-topic (relevance-scored 0.50 and 0.63); the other 46
   noise entries were purged from the manifest by hand as a one-time
   cleanup (the new scoring logic wouldn't have proposed them).

**Confirm run, real papers:** the two genuinely-relevant candidates
("Mobile Money, Interoperability, and Financial Inclusion", and
"Digital and Data Infrastructure...") were checked and run through
`confirm`. Both landed in `needs_manual` -- not open access, and (unlike
this doc's earlier Cloudflare finding) this time the user confirmed
directly that Columbia's own ScienceDirect access did not cover either
article at all when attempting the manual download. **Distinct failure
mode worth naming precisely:** the earlier EZProxy finding was a
publisher-side bot-detection block despite valid institutional access;
this is a genuine subscription-coverage gap -- Columbia simply doesn't
license these specific journals/articles. Both are real, different
reasons a paper can end up permanently `needs_manual`, and neither is
fixable by this pipeline.

**Housekeeping caught during the follow-up convert/reconcile pass:**
two of the user's manual downloads (`ssrn-3049364 (1).pdf`,
`d41586-025-04053-w (1).pdf`) were confirmed byte-identical re-downloads
of papers already converted -- deleted before conversion to avoid
wasted Gemini spend. The one genuinely new download ("Nostalgic Demand",
Björkegren) converted and reconciled cleanly, closing out one of this
doc's own previously-open `needs_manual` entries -- though it landed in
the `physics` folder, a live instance of the weak-level-0-concept-score
limitation already documented above ("Folder-naming fix" section), not
a new issue.

**Assessed as a feasible stopping point for this round.** The
propose/confirm loop, relevance scoring, and worklist mechanics are all
validated against real data, not just unit tests. What remains in
`needs_manual_downloads.md` is entirely pre-existing/expected: the two
ScienceDirect subscription gaps above, plus the already-documented
Nature-title-mismatch and SSRN-duplicate-listing cases (see "Conversion
+ reconciliation completed" above).

## Metadata/folder audit: implemented and live-tested, 2026-09-02

Spec: `docs/superpowers/specs/2026-09-02-metadata-folder-audit-design.md`;
plan: `docs/superpowers/plans/2026-09-02-metadata-folder-audit-plan.md`.
Built as `audit_metadata.py` (folder placement and tag-frontmatter sync
auto-correct when there's a mechanically well-defined right answer;
title/author mismatches flag into `metadata_audit_flags.md` for human
review), chained automatically onto `reconcile_needs_manual.py`'s own
run rather than a separate command. 714 tests passing at merge.

**Two real bugs found on the very first live run against the actual
corpus, both fixed same-day:**

1. **Neither `audit_metadata.py` nor `reconcile_needs_manual.py` ever
   loaded `.env`.** Both checked `os.environ.get("OPENALEX_CONTACT_EMAIL")`
   directly without calling `common.gemini_utils.load_dotenv_override()`
   first, unlike `discover.py`/`snowball.py`'s own established
   convention -- so a real run always hit the "not set" branch even with
   a real `.env` in place. Unit tests never caught this because they
   patch `os.environ` directly rather than exercising real `.env`
   loading. Fixed by adding the missing `load_dotenv_override()` call to
   both scripts' `main()`s.
2. **The DOI check (`check_doi()`) was designed on a false assumption
   and removed entirely.** It flagged a paper whenever its own stored
   DOI didn't appear as literal text in its converted body -- but the
   very first real run flagged 14 of 17 audited papers (82%) this way.
   Root-caused by reading one flagged paper's actual converted text
   directly: its own DOI genuinely never appears anywhere in its body --
   only *other* papers' DOIs, in its own reference list, do. Real
   academic papers routinely don't self-print their own DOI in visible
   text at all (it's typically publisher-stamped metadata, not prose).
   This was already known and documented elsewhere in this very
   codebase -- `reconcile_needs_manual.py`'s own `is_confirmed_downloaded()`
   docstring explicitly calls out "papers that don't print their DOI in
   the visible text" as the reason it falls back to title-matching --
   but wasn't applied when `check_doi()` was designed. Since `check_title()`
   already provides a reliable, corroborated identity signal on its own,
   `check_doi()` added no real value and pure noise; removed rather than
   patched, since no minor tweak fixes an unreliable-by-design signal.
   **How to apply:** before trusting "does X appear as literal text in a
   real converted paper" as a signal, check it against a few real
   converted files first -- title and author names tend to appear near a
   paper's own header reliably; bibliographic identifiers like DOIs
   often don't, except in citations *of other papers*.

After both fixes, a clean re-run against the real corpus: 17 papers
audited (1 skipped -- a fetched-but-not-yet-converted PDF, correctly
left for a later run), 0 folder corrections needed (the folder-naming
fix from earlier this session already holds), 0 tag syncs needed
(frontmatter already in sync with the index), 0 flags -- a genuinely
clean corpus, not an audit that found nothing because it's broken.

## What's next

Not currently planned as active work -- recorded here as the honest
answer if gated-paper coverage becomes a real bottleneck later:

1. **Semi-automated Playwright-driven login and download**, if the
   `needs_manual_download` volume from real usage turns out to matter
   enough to justify the engineering cost. Not spec'd.
2. **CORE.ac.uk as a third OA-discovery tier** and **Columbia's Academic
   Commons repository check** -- both still open ideas from the
   brainstorm below, not picked for this round.
3. **A combined convenience wrapper** chaining discovery -> conversion ->
   reconciliation in one command (approach C from the original
   brainstorming session) -- the three exist as separate, focused
   scripts today by design; a thin wrapper is a cheap follow-on if
   running them separately proves tedious in practice.
4. ~~Citation/bibliography-based snowball sampling.~~ **Implemented and
   live-tested, 2026-09-02 -- see "Citation snowball sampling" section
   below.** Built as forward-only (papers citing the corpus via
   OpenAlex's own citation graph), not backward bibliography-parsing, per
   the reasoning originally flagged here.
5. The tags and folder organization follow the OpenAlex conventions but haven't been tested against the indexer system for the academic hub, which pulls out tags semantically based on the content of the entire knowledge graph. It would be worth testing the standard convention tags used by OpenAlex against the academic hub system once the corpus of research journals is larger, then consolidating the two systems so they can cross reference each other better.
6. ~~A metadata/folder audit process against full text, flagged
   2026-09-02, not scoped.~~ **Implemented and live-tested, 2026-09-02 --
   see "Metadata/folder audit" section above.**
7. Otherwise, no change: the existing OA -> Semantic Scholar -> arXiv ->
   EZProxy-with-manual-fallback pipeline is the correct, working design
   as shipped.

## Original brainstorm, 2026-09-02 (superseded by "acted on" above)

The six ideas as originally brainstormed, before user feedback picked
four for immediate implementation. Kept verbatim for the record; see
"Efficiency ideas acted on" above for what actually shipped and how.

1. ~~Move the dedup check before relevance scoring, not after.~~
   **Implemented, commit `6483594`.**
2. ~~Pace only the EZProxy tier, not OA/arXiv.~~
   **Implemented, commit `49085f8`.**
3. ~~Add CORE.ac.uk and/or Semantic Scholar as additional free
   OA-discovery tiers, before EZProxy.~~ **Semantic Scholar implemented,
   commit `6a582ac`. CORE.ac.uk remains open** -- requires a free API-key
   registration step the user would need to do, unlike Semantic Scholar's
   keyless access, which is why it wasn't picked up in this round.
4. **Check Columbia's own institutional repository (Academic Commons) as
   an additional tier for Columbia-affiliated authors. Still open.**
   Likely to have green-OA copies of exactly the kind of faculty output
   this pipeline targets; a targeted, probably-high-value win specific to
   this user's actual use case, not yet scoped.
5. ~~Detect near-duplicate candidates and prefer the most fetchable
   venue.~~ **Implemented (exact-title match only, not fuzzy), commit
   `8372d9e`.** Fuzzy matching (to also catch a true near-duplicate like
   "...Predicts Credit Repayment" vs "...Predicts Loan Repayment", which
   differ by one word) remains a real, not-yet-built refinement.
6. **A lightweight author-profile sanity check against OpenAlex
   mis-attribution. Still open, explicitly the weakest idea of the six**
   (per direct user feedback declining it for this round). Two of
   Björkegren's "papers" this session looked like a different person's
   work merged into the same OpenAlex author ID (topically unrelated to
   his real research area) -- comparing a candidate's concepts against
   the author's own dominant concept profile and flagging outliers is a
   rougher, more speculative payoff than the others above.
