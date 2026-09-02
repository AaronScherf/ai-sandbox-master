# Journal Discovery: Status Summary

Start here for "what happened and where do we stand" on the journal
discovery subproject -- `journal_discovery/`, which resolves a faculty
name or topic query into full-text PDFs under
`research/journal-articles/<topic>/`. Design reference:
`docs/superpowers/specs/2026-08-31-journal-discovery-design.md`;
implementation plan: `docs/superpowers/plans/2026-09-01-journal-discovery-plan.md`.
Merged into `main` 2026-09-01 (commit `bb94cbb`), 545 tests passing.

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

## What's next

Not currently planned as active work -- recorded here as the honest
answer if gated-paper coverage becomes a real bottleneck later:

1. **Semi-automated Playwright-driven login and download**, if the
   `needs_manual_download` volume from real usage turns out to matter
   enough to justify the engineering cost. Not spec'd.
2. Otherwise, no change: the existing OA -> arXiv -> EZProxy-with-manual-
   fallback pipeline is the correct, working design as shipped.
