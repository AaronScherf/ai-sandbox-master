You are a Codex session. Task: add a DOI-list mode to the journal discovery pipeline in `ai-sandbox/academic-rag-model/discovery/discover_journal_articles/`, with tests and a README update. Follow docs/WORKTREE_WORKFLOW.md: own branch and worktree (for example `codex/discovery-doi-list`), explicit-path staging only, never `git add -A`. Do not commit or push without reporting to Aaron. The package's CLAUDE.md (`academic-rag-model/CLAUDE.md`) applies: run Python as modules, preserve CRLF/LF per file, use the chunked test runner for the full suite.

Why
Aaron has a list of 42 DOIs (references from a literature novelty check) to fetch and then read. The pipeline today is query-driven: `--faculty` or `--topic` plus a relevance prompt, or snowballing from papers already in the corpus. Neither takes "fetch exactly these DOIs", and the relevance gate (`sentence-transformers`) would drop some of them. The building blocks already exist: `discovery.resolve_work_by_doi`, `access.resolve_full_text` (Unpaywall, Semantic Scholar, CORE, arXiv, optional EZProxy), `manifest`, `metadata_sidecar.write_sidecar`, `topic_routing`, `worklist.write_needs_manual_worklist`. `discover.retry_needs_manual` is the closest existing pattern (it resolves a DOI and fetches without scoring). The goal is a small, tested mode that reuses them.

Input
- A DOI list file: `docs/superpowers/plans/2026-11-11-novelty-check-fetch-dois.txt` in the `codex-nexus-presentation-strategy-v3` worktree under `ai-sandbox/research/independent-research/` (uncommitted; read it from there or ask Aaron to copy it). One DOI per line; text after `#` is a comment; blank lines ignored.
- Also accept repeated `--doi` on the command line.
- Parsing must handle: CRLF, a leading `doi:` or `https://doi.org/` prefix, trailing whitespace and punctuation, and DOIs that contain parentheses (the first line with one is `10.1016/s0167-6296(98)00039-3`) and colons (`10.1093/acprof:oso/9780199534081.003.0015`). Normalise case for manifest keys the way the existing code does. An arXiv DOI (`10.48550/arXiv.2408.09187`) should work if OpenAlex resolves it; if not, use the existing arXiv path.

Behaviour
1. New CLI entry (either `--doi` / `--doi-file` flags on `discover.py` or a sibling module `fetch_dois.py`; your call, state which and why). No `--relevance-prompt` required, and the relevance model must not be loaded.
2. For each DOI: skip if the manifest already has it as fetched or downloaded (report as already_seen; add a `--force-retry` for needs_manual entries only if it is simple); resolve via `resolve_work_by_doi`; call `resolve_full_text` with the same pacing, EZProxy and CORE settings as `run()`; on success write the PDF, sidecar (relevance score `None`) and manifest entry; on failure record `needs_manual` with the same metadata as `run()` so it lands on `needs_manual_downloads.md`.
3. Folder routing: add an optional `--folder NAME` that overrides the automatic topic-folder choice for this batch (default stays the existing behaviour). Aaron will use one folder for this batch, for example `novelty-check`.
4. A DOI that OpenAlex cannot resolve is reported as `not_in_openalex` in the run summary and in a small per-DOI report. Do not write a fake manifest entry for it.
5. Verify the download is the paper asked for, if an existing helper fits (look at `text_match.py` and the reconcile tool, which match by DOI substring or normalised title). If a downloaded PDF fails that check, do not accept it silently: report it as `content_mismatch` and treat it as needs_manual. If no helper fits cheaply, say so in your report and leave it as a follow-up.
6. Per-DOI report at the end: DOI, outcome (fetched, already_seen, needs_manual, not_in_openalex, content_mismatch), access tier used, and the folder. Print it and also write it next to the manifest as a Markdown table (this file lives under the git-ignored articles directory).
7. `--dry-run`: resolve each DOI in OpenAlex and report what is known about open-access availability without downloading anything. Keep it only if it is simple.

Constraints
- Default articles directory is `ai-sandbox/research/journal-articles/`. PDFs, converted Markdown and images there are git-ignored (public repo, third-party copyrighted text). Do not change the ignore rules. Do not write any PDF or paper text into a tracked location.
- Leave the existing faculty, topic and snowball behaviour unchanged. Existing tests must still pass.
- Rate limits and politeness unchanged. `OPENALEX_CONTACT_EMAIL` is already required by the pipeline for OpenAlex and Unpaywall; keep using it from the environment and never print it. Do not add other identifying information to requests or user agents.
- No network in unit tests: use mocks or recorded fixtures for OpenAlex and the access chain. Add an optional online smoke test, off by default, that fetches one open-access DOI (for example an arXiv or PLOS paper).
- Tests go under `tests/discovery/discover_journal_articles/`. Add DOI-parsing tests with the cases above.

Do not
- Run the full 42-DOI list against the network until Aaron approves. After the tests pass, you may run `--dry-run` on the list (if you built it) or a 2-DOI live run to prove the path, and report what happened.
- Run conversion (`convert_journal_articles.py`); it uses paid Gemini and needs Aaron's go-ahead.
- Edit Gemini's notes, Claude's review files, the strategy or deck, or the tracker beyond marking the relevant item.

Docs
- Add a short "Route 4: DOI list" section to `discovery/discover_journal_articles/README.md` with the command and the report format.
- If it matches, note in the tracker that this covers part of TODO-0037's discovery side (do not tick TODO-0037; the conversion wrapper is separate).

Report back to Aaron with: branch and worktree, files changed (clickable file:// links to absolute paths), how to run it, test results (including the full chunked suite or the affected packages), what you did and did not run on the network, known limits, and any parsing or content-match decisions you made that Aaron should check.
