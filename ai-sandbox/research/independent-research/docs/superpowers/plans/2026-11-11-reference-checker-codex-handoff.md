You are a Codex session. Task: build a small, tested reference-checking tool for this monorepo, and report where it should plug into the literature pipelines. Follow docs/WORKTREE_WORKFLOW.md: own branch and worktree (for example `codex/reference-checker`), explicit-path staging only, never `git add -A`. Do not commit or push without reporting to Aaron.

Why
Gemini wrote four literature-check notes for Aaron's PhD agenda and tagged every reference [VERIFIED]. Claude resolved the 38 `doi.org` links in them against Crossref: only 13 resolved to the cited paper, 13 resolved to a different paper, and 12 did not resolve (a few for benign reasons). Two citations also had wrong authors, journal and finding. The errors look like identifiers recalled from memory rather than copied from a source page. If the literature taxonomy or evidence-map pipelines take metadata from model output, the same silent error can enter them. A mechanical checker catches this class of error cheaply. Use the Gemini notes as a regression set but do not edit them.

Read first
- notes/00_overview-and-strategy/03_novelty-check/Novelty Check - Claude Spot Check - v1.md (under ai-sandbox/research/independent-research/ in the `codex-nexus-presentation-strategy-v3` worktree; ask Aaron for the path if it has moved)
- The Gemini notes, read-only, in the `gemini-nexus-novelty-check` worktree: `Novelty Check - RQ1/RQ2/RQ3/Summary - v1.md` under the same folder
- docs/AGENT_ROUTING.md and the existing code conventions (package layout, test runner, dependency tool) of whichever subproject you choose

Step 1: survey (read-only), then report before building
1. Search the repo for existing citation or DOI handling: `crossref`, `doi`, `datacite`, `openalex`, `unpaywall`, `bibtex`, `zotero`, `citation` in the academic-rag-model pipelines (literature, taxonomy, evidence-map, source indexer) and in the notes tooling. List what exists and what is missing.
2. Identify where reference metadata enters those pipelines and whether any of it comes from an LLM rather than from a registry or from the source file itself.
3. Propose a home for the tool (for example a module beside `tools.landing_metrics` if that package fits, or a new `tools` module), with reasons. Stop and report this survey and proposal to Aaron before writing code, unless the choice is obvious.

Step 2: build the checker (after Aaron approves the location)
Inputs: a markdown, text or JSON file, or a list of references.
Extraction: DOI links and bare DOIs (handle DOIs containing parentheses, such as old Wiley SICI identifiers, and strip trailing punctuation); arXiv identifiers; ordinary URLs; and, where a reference has no identifier, the citation text (authors, year, title) as a candidate for a title search. Associate each identifier with the citation text next to it.
Resolution:
- Find the registration agency for a DOI (doi.org's registration-agency lookup) and then query the right registry: Crossref for most journals and books, DataCite for arXiv and many data and institutional DOIs.
- For references without a DOI, run a bibliographic title search against Crossref and report the top candidates with scores. Candidates are suggestions, never matches.
Comparison, against the citation text:
- Normalized title similarity, first-author family name, year (allow a one-year gap for online-first versus issue year), journal, and volume and pages where present.
Classification per reference:
- MATCH
- PARTIAL (small title or year difference, same first author and venue)
- MISMATCH (resolves to a different work)
- UNRESOLVED (not found in any registry checked; say which)
- NO_IDENTIFIER (with title-search candidates)
Output: a table (markdown and JSON) with one row per reference: citation text, identifier, registry answer, classification, reason. Never print a "verified" label that the checker has not earned.
Politeness and privacy: cache responses on disk (ignored by git), rate-limit requests, retry with backoff, and use a generic user agent with no personal email, name or project detail. Do not send anything beyond the identifier or bibliographic string.
Tests: unit tests with recorded fixtures so they run offline. Add an optional online smoke test, off by default. Use the Gemini notes as a regression set: expected totals for the 38 DOIs are about 13 MATCH, 13 MISMATCH, 12 not matched, but the tool should do better on the unresolved group (arXiv and other DataCite DOIs should resolve, and the parenthesized DOI should parse), so report what changes and why. Include known cases such as: Vivalt (2020) `10.1093/jeea/jvz054` (Crossref returns a Bennett and Ouazad paper), Pritchett and Sandefur `10.1257/aer.p20151034` (Crossref returns an Ambuehl, Niederle and Roth paper), and Hjort et al. `10.1257/aer.20190830` (a correct match).

Step 3: report
Report to Aaron with: the survey findings, where the tool lives, how to run it, the regression-set results, known limits (for example items with no DOI, books, grey literature, paywalled metadata), and a short recommendation on how the taxonomy and evidence-map pipelines should use it. Include a design rule for Aaron to decide on: identifiers and bibliographic metadata should come from a registry or from the source file, never from model recall, and an LLM should only extract claims with quote-anchored spans. Do not wire the tool into any pipeline without approval.

Constraints
- Do not edit the Gemini notes, the review files, the tracker or existing pipeline code in this pass.
- Do not commit secrets. No PDFs or copyrighted text in the repo.
- Keep the tool small. This is a checker, not a bibliography manager.
- Mark anything you could not verify as unverified in your report.
