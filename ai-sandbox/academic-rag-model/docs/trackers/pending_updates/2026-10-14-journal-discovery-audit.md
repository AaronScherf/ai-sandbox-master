# Journal discovery: coverage, classification, and reliability audit

Date: 2026-10-14. Status: assessment and brainstorm for later review; no implementation approved or performed.

## Scope and requirements

Assess breadth relative to scholarly aggregators; explain the apparent preference for lesser-known papers and the agriculture/business folder mismatch; reconcile existing pending work; recommend fixes with verification criteria. Preserve pipeline code, credentials, PDFs, manifests, index cards, tags, and owner decisions. The only saved outputs are this report and its [sample evidence appendix](2026-10-14-journal-discovery-audit-evidence.md).

Code baseline: `f985bdf9129191c094b95fa4d83136464146fb56`, outer repository `C:/Users/theaa/ai-sandbox-master`. Report branch: `codex/journal-discovery-audit`; worktree: `.worktrees/codex-journal-discovery-audit`. Live corpus reads used the original checkout. Unrelated existing changes there were preserved. The assessment does not approve changes or replace Claude's architecture review. Recommendations below are options for that review, not settled design decisions.

## Main conclusions

1. Candidate discovery is OpenAlex-only. Other providers locate full text for already-selected works. OpenAlex covers major journals, but the current capped, sequential search does not establish comprehensive retrieval or parity with Google Scholar.
2. Live known-paper checks found relevant Nature-family and World Bank Economic Review articles in OpenAlex that passed local relevance scoring but were absent from the first 100 keyword results. That demonstrates a retrieval-window problem for these samples, not missing index coverage. It does not establish absence from the full default 300-candidate window.
3. Folder routing prioritizes broad level-0 Concepts, then score, and chooses one label. This directly explains agricultural papers filed under Business. This rule is also used by the metadata audit, so running that audit cannot independently fix the semantic problem.
4. The download chain has a reproducible fallback gap: a present but unusable OA URL prevents querying subsequent OA providers. Ordinary reruns then skip `needs_manual` entries, preserving unresolved failures.
5. No evidence here proves a general bias toward small or low-quality journals. Accessibility, query vocabulary, result ordering, caps, document-type mixing, and metadata differences are distinct mechanisms. Journal prestige is neither a relevance label nor a quality verdict.

## Code and documentation map

Paths below are relative to `academic-rag-model/` unless stated otherwise.

| Area | Files and responsibilities |
| --- | --- |
| Entry point | `discovery/discover_journal_articles/discover.py`: defaults, search, seen filter, scoring, download, output persistence |
| Search and metadata | `discovery/discover_journal_articles/discovery.py`: author resolution, topic search, DOI lookup, citing works, Concept ordering |
| Selection | `discovery/discover_journal_articles/relevance.py`: cached MiniLM embeddings, threshold, title fallback, early stopping, normalized-title deduplication |
| Access | `discovery/discover_journal_articles/access.py`, `http_utils.py`: OA lookups, arXiv, institutional proxy, response validation/retries |
| Organization/state | `topic_routing.py`, `metadata_sidecar.py`, `manifest.py`, `worklist.py` in the same package |
| Citation expansion | `discovery/discover_journal_articles/snowball.py`: propose/confirm, forward citations |
| Downstream | `pipelines/convert_journal_articles/{README.md,convert_journal_articles.py}`, `tools/reconcile_needs_manual.py`, `tools/audit_metadata.py`, `core/indexer/README.md` |
| Usage | `discovery/discover_journal_articles/README.md` |
| Status | `docs/status/discover_journal_articles/2026-09-01-journal-discovery-status.md` (includes October 4 additions despite its filename) |
| Original design/plan | `docs/superpowers/specs/discover_journal_articles/2026-08-31-journal-discovery-design.md`; `docs/superpowers/plans/discover_journal_articles/2026-09-01-journal-discovery-plan.md` |
| Snowball design/plan | `docs/superpowers/{specs,plans}/discover_journal_articles/2026-09-02-journal-discovery-snowball-{design,plan}.md` |
| Adjacent audit design | `docs/superpowers/plans/2026-09-02-metadata-folder-audit-plan.md` |
| Project queue | `docs/trackers/academic_hub_to_do.md`, especially TODO-0035 through TODO-0037 |
| Existing infrastructure | `tools/corpus_health/README.md`, `tools/project_steering/README.md`: review/state/writer coordination patterns; neither is a literature search or semantic journal organizer |
| Tests | `tests/discovery/discover_journal_articles/`, plus corresponding conversion and metadata-audit tests |

The project tracker refers to discovery `pipeline.py`; the actual entry point is `discover.py`. Older design examples use the former `journal_discovery` package name. Update examples when implementing, without rewriting historical findings as current behavior.

## Audit method and limits

Used read-only public OpenAlex GET requests, current code inspection, local metadata/manifest inspection, and in-memory mocked reproductions. Loaded the already-cached `all-MiniLM-L6-v2` with offline mode; no model installation or download, Gemini calls, PDF downloads, institutional sessions, conversions, reconciliation, or index mutations.

Three representative queries were chosen from the user's corpus themes: `smallholder climate adaptation`, `climate migration`, and `digital credit`. Requests used the implementation's `filter=default.search:<query>` syntax, with `per-page=100`. Each sampled record was scored using the existing `_work_from_openalex`, `embed_text`, and `score_work` functions. Audit prompts and per-paper rows are preserved in the evidence appendix. These are new representative prompts, not reconstructed historical commands.

This is a first-100 raw-result assessment, not a complete default CLI run: no historical manifest exclusions, no download step, and no claim that these are the final `max-results` selections. Aggregate passes count records meeting 0.5 after dataset exclusion, before normalized-title deduplication. The normal CLI pages in batches of 25 and may examine up to 300 unseen candidates, accepting up to 100. Near-threshold scores are displayed rounded in the appendix.

Initial requests encountered a 504 timeout and anonymous-search 429 rate limits. Later requests succeeded. These are availability observations, not proof of coverage failure. Requests did not use the configured contact email or a private API key; anonymous load behavior therefore does not establish the exact behavior of a configured production run. The sampled responses are time-dependent. No Google Scholar result list was scraped or compared, and no systematic multi-provider recall benchmark was completed. Publisher pages independently corroborated selected paper identities; that is not a Google Scholar parity test.

### Live sample results

| Query | Raw records | Eligible after dataset exclusion | Above 0.5 | OA among eligible | OA among passing | Title-only eligible / passing | Business folders among passing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| smallholder climate adaptation | 100 | 99 | 96 | 63 | 61 | 25 / 24 | 50 |
| climate migration | 100 | 100 | 89 | 44 | 39 | 24 / 24 | 1 |
| digital credit | 100 | 88 | 75 | 65 | 56 | 26 / 24 | 60 |

Climate migration succeeded on a later retry, with its earlier 429 preserved in the appendix. The initial successful unscored probe returned 100 records, 44 marked OA, 76 with abstracts, and 69 distinct primary-source labels. That raw sample contained 50 articles, 27 book chapters, 6 books, and additional types. Source labels include repositories and book platforms, so they must not be presented as a count of journals. Climate migration's scored OA share was 44/100 before the gate and 39/89 (43.8%) after it.

Applying the implementation's ASCII normalized-title rule to passing sample records leaves 94 agriculture, 78 migration, and 65 digital-credit titles. These are sample deduplication counts, not full CLI output counts. In particular, generic identical titles can belong to genuinely different works, so duplicate suppression itself needs human validation before being treated as correct version linking.

For the agriculture scored sample, OA share barely changed: 63/99 (63.6%) before the gate versus 61/96 (63.5%) after. For digital credit it was 65/88 (73.9%) versus 56/75 (74.7%). These two samples do not support a large OA preference introduced by the similarity gate alone. Download availability remains a separate selection stage. Title-only scoring also did not universally depress acceptance: 24/25 agriculture title-only records and 24/26 digital-credit title-only records passed. Missing abstracts should be treated as uncertainty, not assumed to always lower scores.

### Known-paper checks

All six core benchmark DOIs resolved in OpenAlex and scored above 0.5 using the relevant audit prompt.

| Paper / DOI | Venue | Score / input | First-100 result observation |
| --- | --- | --- | --- |
| Risk transfer policies and climate-induced immobility among smallholder farmers — `10.1038/s41558-021-01205-4` | Nature Climate Change | 0.769231 / title | Absent from agriculture sample |
| A scoping review of adoption of climate-resilient crops by small-scale producers in low- and middle-income countries — `10.1038/s41477-020-00783-z` | Nature Plants | 0.754026 / abstract | Absent from agriculture sample |
| Carbon Farming as a Tool for Climate Resilience in Smallholder Agriculture — `10.55121/nc.v3i2.207` | New Countryside | 0.636151 / abstract | Also absent from agriculture sample |
| Climate migration myths — `10.1038/s41558-019-0633-3` | Nature Climate Change | 0.753289 / title | Present at rank 2 in initial migration probe |
| Asylum applications respond to temperature fluctuations — `10.1126/science.aao0432` | Science | 0.607246 / abstract | Absent from migration sample |
| Behavior Revealed in Mobile Phone Usage Predicts Credit Repayment — `10.1093/wber/lhz006` | The World Bank Economic Review | 0.694162 / abstract | Absent from digital-credit sample |

Passing the similarity gate does not prove a paper meets an empirical-study requirement: “Climate migration myths” illustrates why study type and a human relevance judgment matter. The smaller-venue carbon-farming article was also absent, so these misses are not evidence of a simple prestige-based ordering rule. All six benchmark records were marked OA by OpenAlex at lookup time; no actual download success was checked.

An exploratory DOI was excluded from the core benchmark after lookup identified it as the unrelated Nature paper “Sulfoxaflor exposure reduces bumblebee reproductive success” (`10.1038/s41586-018-0430-6`). It was not counted as a climate-migration retrieval failure. Separate exploratory Science lookups confirmed broad journal presence but were not a prespecified representative sample.

### Local corpus observations

The live `.discovery/seen.json` contained 97 entries: 64 `needs_manual`, 20 `fetched`, 13 `downloaded`. There were 20 `.meta.json` sidecars. These counts describe state, not a file-presence, successful-conversion, or publisher-quality audit. The state does not preserve a full historical candidate/rejection ledger, so historical bias cannot be reliably reconstructed.

The business folder contains the carbon-farming paper above, “Risk Transfer Policies Facilitate Smallholder Farmer Climate Adaptation” (`10.21203/rs.3.rs-129931/v1`), and the Zambia smallholder adaptation paper (`10.62225/2583049x.2026.6.3.6221`), with Business first in stored concepts. The fresh carbon-farming record ranked Business at 0.391096, barely above Environmental science at 0.387535; its primary Topic was “Soil Carbon and Nitrogen Dynamics.” This is direct evidence that the single broad-label rule discards useful topical information. Some older sidecars have different ordering from the current folder rule; stored labels are historical metadata, not guaranteed current classifications.

### In-memory behavior reproductions

No files or live download endpoints were used in these reproductions.

- Given a work with a present OA URL and a mocked failed download, `resolve_full_text` returned `needs_manual`; Unpaywall, Semantic Scholar, and CORE lookup call counts were all zero. This verifies the fallback gap.
- With two candidates scoring 0.51 then 0.99 and `max_results=1`, selection returned the first at 0.51. This verifies early acceptance rather than global best-score selection.
- A manifest entry already marked `needs_manual` was excluded by `skip_already_seen`. This verifies that an ordinary rerun does not retry access.
- Code inspection additionally shows `counts['examined'] = len(scored)` in discovery and snowball: the printed examined count is actually the accepted-list length, not all candidates scored. No production counter trace was run.

## Findings and proposed remedies

### A. Coverage, ordering, and quality

**Verified:** one candidate provider; sequential faculty-then-topic processing; global early-stop limits; only datasets explicitly excluded. Topic queries are not restricted to Columbia, while faculty resolution initially prefers Columbia and falls back to the first global author match. The `Work` object discards venue, work type, citations, Topic IDs, and Concept scores after parsing, limiting later explanations and ranking choices.

**Propose:** first add a genuinely read-only search/report mode that separates retrieval, relevance, access, and review. Record each query's candidates, rank, rejection reason, type, venue, metadata availability, model/version, threshold, and cap termination. Preserve all selected candidates regardless of download outcome. Count retrieved, deduplicated, examined, accepted, and fetched separately. Benchmark at least 20–30 known papers across these themes, including recent/older, OA/gated, established/specialist venues, and studies with missing abstracts.

Next compare bounded pooled ranking against current first-passing selection. Balance query budgets or interleave queries so one topic cannot exhaust the run. Consider synonyms and explicit Boolean variants, then evaluate an independent Semantic Scholar or Crossref candidate-search adapter only if it adds unique relevant works. Those services' current DOI access lookups are not search adapters. Validate current endpoint contracts, credentials, limits, costs, and licenses before choosing an integration. Do not assume a Google Scholar automation API exists.

Expose configurable article/review/preprint/book inclusion. Preserve useful working papers and regional journals rather than silently excluding them. Consider citations and journal information as transparent optional context, not a hard prestige cutoff. Compare title-only and abstract-based calibration on human judgments; do not automatically penalize title-only works. Test domain-suitable embeddings only after establishing a baseline; replacing a model without evidence can merely change the bias.

**Acceptance:** known-paper presence is measured independently at index lookup, retrieved window, relevance gate, and access stage; per-query budgets are visible; a later high-scoring candidate can beat an earlier lower-scoring one under the new ranking mode; human-reviewed precision/recall and OA/missing-abstract strata are reported. Broader coverage is unverified until that comparison succeeds.

### B. Classification and corpus organization

**Verified:** broad level-0 Concepts precede all narrower Concepts, then descending score; folder router chooses the first. All Concept names are retained in the sidecar, but scores/levels/IDs are lost. This is not the same as semantic indexer tagging. The metadata auditor repeats the first-Concept rule and synchronizes tags to cards; it does not judge whether the concepts are useful.

**Propose:** retain raw classification IDs, scores, levels, provenance and retrieval timestamp. Evaluate OpenAlex `primary_topic`/`topics` alongside existing semantic index tags. Concepts are deprecated; migration to Topics is justified as compatibility work but must not be presented as a guaranteed semantic fix. Use multiple topical labels and a stable document identity; let the user review any mapping from provider Topics to useful local groups. A semantic organization proposal should compare converted content, multiple topics, and existing corpus groups. Preserve explicit human overrides so the old auditor cannot revert them.

The first useful release can display suggested categories and evidence without moving any files. Corpus-wide clustering and physical moves are later capabilities, requiring Claude design review. Before enabling moves, require exact document/hash selection, per-target machine-readable outcomes, coordination with every destination writer and sync process, atomic state replacement, recovery from partially moved groups, and a post-run audit covering PDF, sidecar, Markdown, caches, manifest, cards, chunks, and links. A sequence of renames is not a transaction.

**Acceptance:** review a varied sample including agriculture, climate, digital finance, interdisciplinary work, missing concepts, near-tied scores, and historical sidecars. Measure incorrect suggestions and abstentions; the reported agriculture examples must receive useful suggestions without forcing all papers into agriculture. Reruns preserve accepted overrides, and changed source/classifier versions invalidate proposals explicitly.

### C. OA lookup and download reliability

**Verified:** `work.oa_url or try_unpaywall(...) or try_semantic_scholar(...) or try_core(...)` stops at the first URL, not the first successful PDF. A landing page or blocked URL can prevent trying a valid alternative. Current PDF checking accepts a Content-Type containing `application/pdf`; it does not check PDF bytes. `source_tier='open_access'` hides which provider succeeded.

**Propose:** iterate provider candidates lazily and continue after HTTP, content, or validation failure; deduplicate URLs; consider alternate OA locations within a provider under an explicit attempt/time budget. Record provider, URL, attempt status, HTTP failure class, and selected version/license where available. Validate PDF signature and parseability, with temporary output and atomic replacement. Never label a transient API failure as evidence the paper is paywalled. Keep institutional authorization and browser challenges as distinct outcomes.

**Acceptance:** fixtures cover an existing OpenAlex URL failing followed by successful Unpaywall/Semantic Scholar/CORE URLs, a landing-page response, all locations failing, duplicated URLs, invalid PDF bodies, and interrupted writes. Then validate a small authorized live sample. The current mocked reproduction proves the defect, not the effectiveness of a future fix.

### D. Retry state, duplicates, and durability

**Verified:** all manifest keys are treated as seen, including failed access and unconfirmed snowball proposals. Manifest saves use direct overwrite; discovery writes files before saving the manifest at the end. Current title deduplication is exact normalized title within the selection call, not robust cross-run version linking. Snowball confirmation cannot re-resolve a proposed non-DOI OpenAlex key through its current DOI-only branch.

**Propose:** separate bibliographic identity, discovery history, access state, and human decisions. Use normalized DOI with OpenAlex ID fallback, explicit version relationships, and file hashes. Add a scoped retry action for exact failed IDs, bounded attempts/backoff, and reason codes; never reset or delete the manifest as a retry mechanism. Distinguish deferred/rejected proposals from unseen or access-failed works. Preserve decisions against a fingerprint of the relevant content/configuration; changed inputs create a reviewable revision rather than silently overwriting or repeatedly alerting unchanged rejected items.

For durability, write PDFs and JSON via temporary files and atomic replacement, checkpoint completed work, and reconcile crash leftovers deterministically. Coordinate all discovery, snowball, reconciliation, audit, and sync writers. For duplicates, propose likely preprint/published pairs using DOI relations, normalized title and authors; require review for fuzzy merges. Add ID-based singleton re-resolution for DOI-less snowball works.

**Acceptance:** retry only selected failed IDs; reruns neither redownload successful papers nor erase declined/deferred decisions; changed evidence is visible; crash/restart fixtures avoid corrupt JSON, duplicate downloads, or lost review state; DOI-less confirmation succeeds in fixtures and a small live case. These are recommendations, not observed production failures from a crash experiment.

### E. API compatibility and operational diagnostics

**Observed:** 504 and 429 responses during this audit. Current code uses contact-email parameters but no OpenAlex API-key option; `default.search` is a deprecated alias. Metadata lookups lack explicit request timeouts even though downloads specify 30 seconds. `Retry-After` parsing assumes a numeric value and does not handle an HTTP-date form. There is no per-run wall-clock/request budget.

**Propose:** centralize current OpenAlex authentication and search parameters, use explicit connect/read timeouts, support documented retry signals, and set total request/time budgets. Report partial results and failure reasons rather than pretending an interrupted search was complete. Log usage and cap reasons without credentials. Refresh setup documentation against current provider docs. Do not assume the old email “polite pool” description establishes current service guarantees.

**Acceptance:** contract fixtures for timeouts, malformed responses, numeric/date Retry-After, 429/5xx exhaustion, credential redaction, and partial-result resumption; one bounded live query and singleton lookup under configured credentials. Do not infer API-wide reliability from a single successful request.

### F. Existing queued improvements

| Existing item | Current interpretation and recommendation | Acceptance evidence needed |
| --- | --- | --- |
| TODO-0035 browser institutional access | Still pending. First fix ordinary OA fallback and measure remaining manual workload. If still justified, design an explicitly user-authenticated browser flow; do not treat bot-detection evasion as the requirement. | Small supported-publisher sample, expired-session handling, correct PDF identity, manual fallback |
| TODO-0036 semantic tag consolidation | Directly supported by the classification findings. Corpus now has 33 manifest entries marked acquired, but usable converted/indexed count was not verified; do not equate that with the original >20-paper semantic evaluation prerequisite. | Human-reviewed taxonomy comparison and override preservation |
| TODO-0037 wrapper | Existing conversion already has indexing hooks. Avoid double indexing; resolve explicit roots and stage results, failures, costs and restart semantics. Tracker's `pipeline.py` name is stale. | One paper through each stage, a failed stage, restart without duplicate paid calls |
| Interactive manual worklist | Recorded October 4, not implemented. Follow the project's interactive Artifact convention, with decisions applied through pipeline functions; marking “downloaded” should require content reconciliation. Markdown report here is an assessment, not an operational decision interface. | Stable IDs, pending/declined/deferred decisions, reconciliation evidence, no lost decisions |
| Backward citations | Still deferred. OpenAlex singleton records expose `referenced_works`; sampled benchmark records had 88, 54, 0, 13, 41, and 30 references respectively. Evaluate that structured graph before inventing PDF/Markdown bibliography parsing. Missing references require an explicit fallback policy. | Known reference recovery, missing-reference behavior, bounded fan-out |
| Snowball scale/provenance | Better seed scoping and multi-seed provenance remain open. Balance budgets across seeds and retain all cited-seed relationships. | Reversing seed order does not starve a theme; provenance complete for sampled candidates |
| Author disambiguation | Old deferred suggestion. Prefer identifiers/ORCID and an ambiguity review over automatically rejecting cross-disciplinary work based on concept mismatch. | Homonym and genuine interdisciplinary examples |
| Charts/data loss in conversion | Recorded downstream issue. Re-check current prompts and source/output samples before treating the September diagnosis as current; this audit did not run or assess transcription. Preserve figure evidence and uncertainty; do not invent exact values from plots. | Reviewed chart/table/text samples and downstream retrieval of the represented result |
| CORE / forward snowball / metadata audit | Implemented, with historical live validation documented. Do not relist as unbuilt. | New validation only if changing affected behavior |
| Academic Commons | Dedicated integration deliberately declined in later status, superseding older “still open” brainstorming. Revisit only with measured unique coverage. | Evidence of useful records not already found through current sources |
| EZProxy User-Agent retest | README says the earlier proxy test predates the User-Agent fix. Keep effectiveness unverified until a bounded authorized retest. | Actual publisher-level outcomes, not inference from CORE success |

## Capability, cost, and destination constraints

| Capability | Discovery/scope | Side effects and cost | Output / idempotency | Verification |
| --- | --- | --- | --- | --- |
| Direct metadata audit used here | Three query samples and selected DOIs | Public GET requests; local CPU scoring; no paid model | Two Markdown artifacts; sampled data is time-sensitive | Saved per-paper ranks/scores and errors |
| Existing discover CLI | Author/topic stream; global caps | Network downloads; optional institutional/Zotero calls | PDFs, sidecars, manifest, manual list; seen keys suppress retries | Historical live runs; current targeted mocks |
| Existing snowball | Forward citations of acquired or explicit seeds | Propose writes state/folders/list; confirm downloads | Shared manifest and checkbox worklist; unchecked proposals remain seen | Code/status inspection; not executed here |
| Conversion/indexing | Explicit PDF or corpus tree | May call paid Gemini and indexer | Markdown/cache/cards under selected roots | Not run in this audit |
| Reconcile/audit | Converted papers and manifest | Writes statuses, can move files and update index | Worklist, audit flags, relocation; uses audited state | Not a read-only command; deliberately not run |
| Corpus health / project steering | File/index gaps or tracker tasks | Scan/state/review facilities; some apply actions write | Existing ledgers and local review patterns | Not literature coverage or semantic routing implementations |
| Proposed organizer | Converted content plus existing groups | Initially proposals only; later model/move costs require scope | Unsupported today; no automatic repair authorization | Requires exact selectors, writer coordination and post-audit |

Verified repository mapping: pipeline code, `research/journal-articles/`, and default `research/.index/` belong to the outer repository. `academic-hub/academic_notes/` is a separate nested repository. Journal conversion defaults to the research index, not the academic-hub index; future cross-vault organization must preserve that distinction. Outer worktrees do not isolate the live nested notes checkout. Obsidian sync and existing unadapted writers must be coordinated before any future mutation. The corpus-health lock is cooperative and does not automatically cover every discovery/audit caller. The report itself is written only under the task worktree's requested `docs/trackers/pending_updates/` directory.

No unattended scheduler, new server, vector database, or new persistent service is needed for the smallest useful release. Existing local metadata and a review artifact can support a bounded diagnostic/category-proposal pass. A later mutation feature does require durable state and writer coordination. Scheduling is outside this request; no unattended repair or no-human decision policy is being introduced.

## Suggested review order and smallest useful release

1. Review the verified OA fallback and misleading examined counter as isolated correctness fixes. Include API timeouts and explicit failure reporting if scoped separately with regression evidence.
2. Establish read-only candidate reporting and the known-paper benchmark. Evaluate fair query budgets, bounded reranking, document types, and threshold calibration before adding providers or replacing embeddings.
3. Review a Topics/semantic-tag proposal mode against the agriculture examples. Keep file moves disabled. Decide the local grouping vocabulary and override policy with Claude/user review.
4. Add explicit retry/recovery state and resolve writer coordination before any broader acquisition or organization workflow.
5. Consider multi-provider search, backward graph expansion, browser downloads, and the convenience wrapper only against demonstrated remaining gaps.

The smallest usable improvement is a correct OA fallback plus honest diagnostics and a category proposal report. It can deliver value independently of corpus-wide clustering, browser automation, or a unified pipeline. No proposed item here is approved merely because it appears in this document. Outstanding design choices are local topic vocabulary, acceptable document types, retrieval budget/recall tradeoffs, and version-merging rules; route those to Claude rather than deciding them during routine implementation.

## External evidence checked

- [OpenAlex source coverage](https://help.openalex.org/data/sources/): upstream indexes and source types. Broad coverage does not prove query recall.
- [OpenAlex search](https://help.openalex.org/api/searching/): search ordering and deprecated filter syntax.
- [OpenAlex Concepts](https://help.openalex.org/data/concepts/) and [Topics](https://help.openalex.org/data/topics/): legacy Concepts versus inferred topical assignments. Neither is an owner-approved local filing taxonomy.
- [OpenAlex authentication](https://help.openalex.org/api/authentication/): current key/rate-limit guidance; verify again when implementing.
- [Google Scholar help](https://scholar.google.com/intl/us/scholar/help.html): broad scholarly coverage and known-title coverage checks. No measured Scholar overlap is claimed here.
- [Nature risk-transfer article](https://www.nature.com/articles/s41558-021-01205-4), [Nature Plants review](https://www.nature.com/articles/s41477-020-00783-z), and [Oxford article record](https://academic.oup.com/wber/article-abstract/34/3/618/5622690): independent benchmark identity checks.

## Verification status

Completed: implementation/doc trace; local manifest and sidecar inspection; live sampled search/DOI queries; cached-model scoring; three in-memory behavioral reproductions; durable evidence appendix. No implementation tests or full suite were warranted for this Markdown-only deliverable. No new pipeline implementation, successful production rerun, exhaustive recall measurement, download verification, human labeling study, or long-term reliability observation is claimed. Architectural recommendations remain unreviewed proposals.
