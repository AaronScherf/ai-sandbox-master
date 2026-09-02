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
- `--pace-per-hour` (default `25`) paces every full-text download attempt,
  jittered +/-30%. This protects your own institutional EZProxy access
  from automated-abuse detection, not just publisher politeness -- don't
  raise it casually.
- `--zotero` additionally pushes fetched papers into a Zotero collection
  matching the topic folder.
- Output: PDFs land in `research/journal-articles/<topic>/`, auto-created
  from each paper's top OpenAlex concept if it doesn't already exist, each
  with a `.meta.json` sidecar (title/authors/year/DOI/concepts/relevance
  score). A `research/journal-articles/.discovery/seen.json` manifest
  tracks what's already been fetched or flagged, across runs.
- This step never calls into `indexer/` or `convert_journal_articles.py`.
  Run that separately (`--dry-run` first, as its own docs already say)
  once you're happy with what landed on disk.

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

<!-- Not yet run. Fill in after using manual_validate_ezproxy.py above:
date tested, how many of N real gated DOIs succeeded, and whether the
cookie held for the full paced session. If any failed, note whether it
was a cookie problem or a genuinely unavailable paper -- and if the
cookie itself didn't hold up, that's the signal (spec S9) to revisit
browser-automated login rather than relying on the manual hand-off. -->
