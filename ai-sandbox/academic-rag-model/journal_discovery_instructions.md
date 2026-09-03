# Journal Discovery Pipeline

Companion to `journal_articles_instructions.md`, one step upstream: resolves
a faculty name or topic query into full-text PDFs on disk under
`research/journal-articles/<topic>/`, ready for `convert_journal_articles.py`
to pick up exactly as it does for manually-added papers. Design spec:
`docs/superpowers/specs/2026-08-31-journal-discovery-design.md`.

## Step 1: One-time local setup

```powershell
cd academic-rag-model
pip install requests sentence-transformers pyzotero
```

Add to `ai-sandbox/.env` (copy the placeholders from `.env.example`):
- `OPENALEX_CONTACT_EMAIL` -- required. OpenAlex and Unpaywall both use
  this for their "polite pool" of higher, faster rate limits.
- `EZPROXY_SESSION_COOKIE` -- optional. Only needed for gated (non-open-
  access, non-arXiv) papers. See "EZProxy setup" below before relying on
  this for real use.
- `ZOTERO_LIBRARY_ID` / `ZOTERO_API_KEY` -- optional, only needed with `--zotero`.

## Step 2: Run it

```powershell
python -m journal_discovery.discover --faculty "Alexander de Sherbinin" `
  --relevance-prompt "climate-forced displacement and migration vulnerability"

python -m journal_discovery.discover --topic "climate-forced displacement" `
  --relevance-prompt "empirical measurement of displacement, not policy commentary" `
  --max-results 50
```

- `--faculty` / `--topic` are both repeatable and can be combined in one run.
- `--relevance-prompt` is required: describe what you're actually looking
  for, not just the author/topic name -- it's what every candidate's
  abstract is scored against (locally, via `sentence-transformers`, no
  Gemini API cost) before any full-text access is attempted.
- `--relevance-threshold` (default `0.5`), `--max-results` (default `100`),
  `--max-examined` (default `300`) control the two-layer volume cap from
  the spec's S1 -- tune the threshold empirically against a few real runs
  before trusting the default.
- `--pace-per-hour` (default `25`, jittered +/-30%) applies **only to the
  EZProxy tier** -- confirmed 2026-09-02 that OA/arXiv downloads carry
  none of the account-safety risk this exists for (they hit diverse,
  unrelated hosts, not Columbia's proxy), so they're never paced. Don't
  raise this casually; it protects your own institutional EZProxy access
  from automated-abuse detection.
- `--zotero` additionally pushes fetched papers into a Zotero collection
  matching the topic folder.
- Output: PDFs land in `research/journal-articles/<topic>/`, auto-created
  from each paper's top OpenAlex concept if it doesn't already exist, each
  with a `.meta.json` sidecar (title/authors/year/DOI/concepts/relevance
  score). A `research/journal-articles/.discovery/seen.json` manifest
  tracks what's already been fetched or flagged, across runs.
- Every run also (re)writes `research/journal-articles/needs_manual_downloads.md`
  from the *entire* current manifest, not just this run's results -- a
  click-through Markdown list of every paper auto-fetch couldn't reach
  (title linking to its DOI, and exactly which auto-created topic folder
  to save the PDF into once you download it by hand). A paper you drop
  into that folder is picked up automatically the next time
  `convert_journal_articles.py` runs -- no separate step needed.
- This step never calls into `indexer/` or `convert_journal_articles.py`.
  Run that separately (`--dry-run` first, as its own docs already say)
  once you're happy with what landed on disk.

## Step 3: Reconcile manual downloads

After you've downloaded some of `needs_manual_downloads.md`'s papers by
hand and run `convert_journal_articles.py`, run:

```powershell
python -m reconcile_needs_manual
```

A manually-downloaded PDF's filename is arbitrary -- it never matches
anything this pipeline would have generated -- so this matches by real
content instead: a DOI substring match against the converted `.md`
first, a normalized-title match as fallback. Confirmed papers are
marked `status="downloaded"` in the manifest and drop out of
`needs_manual_downloads.md` automatically, so the list always reflects
what you actually still need.

Right after reconciling, this also runs a metadata/folder audit
automatically (`audit_metadata.py`, requires `OPENALEX_CONTACT_EMAIL` --
skipped with a warning if that's not set) -- re-checking every newly
converted paper's folder placement and tag sync against fresh OpenAlex
data and the academic-hub index (both auto-corrected when there's a
well-defined right answer), and flagging title/author/DOI mismatches it
can't safely auto-fix into `metadata_audit_flags.md`. Already-audited
papers are skipped on later runs. For a full forced re-audit (e.g.
after fixing a flagged paper by hand):

```powershell
python -m audit_metadata --recheck-all
```

A paper can stay listed even with a real PDF downloaded if its content
doesn't match what was expected for that DOI (checked, not guessed) --
seen for real: an OpenAlex title that didn't match the actual PDF's
subtitle, and two different SSRN listing IDs that turned out to be the
same underlying paper. Worth a manual look rather than assuming the
reconciler missed something.

## Route 3: Citation snowball sampling

A third way to find papers, alongside `--faculty`/`--topic`: follow
citations from what's already in your corpus, via OpenAlex's own
"cited by" graph. Two steps, deliberately never auto-fetching anything:

```powershell
python -m journal_discovery.snowball propose --relevance-prompt "climate-forced displacement and adaptation policy"
```

Seeds from every paper already `fetched`/`downloaded` in your corpus
(or `--seed-doi`, repeatable, to scope it to specific papers), finds
what cites them, scores each candidate through the same relevance gate
`discover.py` uses, and writes `snowball_candidates.md` -- a checkbox
list, nothing downloaded yet. Each entry shows its relevance score and
which corpus paper it cites, so you have context for *why* it was
proposed. Check the ones you actually want, then:

```powershell
python -m journal_discovery.snowball confirm
```

Fetches full text only for checked candidates, through the same
Unpaywall -> Semantic Scholar -> arXiv -> EZProxy chain as any other
route. A confirmed candidate that can't be auto-fetched lands in
`needs_manual_downloads.md` exactly like any other route's outcome --
nothing downstream treats a snowball-sourced paper any differently once
you've confirmed it.

An unchecked candidate is never re-proposed on a later `propose` run --
leaving it unchecked *is* the reject; there's no separate action
needed. Change your mind later by checking it before your next
`confirm`.

## EZProxy setup

`EZPROXY_SESSION_COOKIE` is a manually-obtained session cookie, not
automated login. **Confirmed live:** visiting the bare
`https://ezproxy.cul.columbia.edu` does *not* prompt a login -- it just
serves a menu of proxied resources, since EZProxy only authenticates when
asked to proxy a specific target. To actually get a session cookie, visit
the same URL shape the code itself builds, for one real article you have
legitimate access to:

```
https://ezproxy.cul.columbia.edu/login?url=https://doi.org/<a-real-gated-doi>
```

That routes through Columbia's SSO (CAS/Shibboleth, with 2FA) and lands
you on the article via the proxy -- at which point the session cookie is
set for `ezproxy.cul.columbia.edu` in your browser. Copy its value from
DevTools (Application/Storage -> Cookies -> `ezproxy.cul.columbia.edu`).
It will expire; when gated-paper fetches start failing
(`needs_manual_download` climbing), re-obtain it the same way. Semi-
automated browser login is a deliberate non-goal for now (see the design
spec's S9) -- revisit only if the manual hand-off proves too brittle in
practice, per the validation below.

Before relying on this for a real discovery run, validate it manually:

```powershell
python -m journal_discovery.manual_validate_ezproxy `
  --doi <real-gated-doi-1> --doi <real-gated-doi-2> --doi <real-gated-doi-3> `
  --pace-per-hour 25
```

Pick 5-6 real DOIs you know are gated behind Columbia's subscriptions.
This takes roughly `N * (3600/25)` seconds at default pacing (~12 minutes
for 5 DOIs). Record the outcome below.

## EZProxy validation results

**Tested live 2026-09-01 -- see `docs/2026-09-01-journal-discovery-status.md`
for the full write-up.** Short version: the blocker in practice isn't
cookie freshness -- it's that major publishers (confirmed against both
Taylor & Francis and Elsevier/ScienceDirect) front their sites with
Cloudflare bot protection that blocks a scripted request's fingerprint
directly, before EZProxy/Columbia authorization is even the limiting
factor. Expect `needs_manual_download` often for gated papers; that
fallback is correct, working behavior, not a bug. OA/arXiv tiers are
unaffected. Working around Cloudflare's bot detection itself is out of
scope (see the status doc for why).
