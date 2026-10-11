# Subproject Website Alignment: Codex Architectural & Plan Review

Date: 2026-10-10. Reviewer: Codex, explicitly assigned by the owner.

## 1. Executive Verdict: Blocked

**Block implementation pending amendments; retain the registry plus read-only checker approach.** The proposed M1 is a useful, proportionate first release, but its acceptance contract is currently impossible: timestamps cannot reproduce the audit's semantic judgments, the inventory is inconsistent, and the plan's frontmatter comparison rejects the spec's own example. These are contract defects to resolve before coding, not reasons to introduce a larger platform.

Reviewed inputs: [design](specs/2026-10-10-subproject-website-sync-design.md), [plan](specs/2026-10-10-subproject-website-sync-plan.md), and [audit tracker](../trackers/subproject_website_status_tracker.md), originating at `777f507`. Review worktree: `C:/Users/theaa/ai-sandbox-master/.worktrees/codex-website-sync-review`, branch `codex/website-sync-review`, base `44046eb`. The design and plan have no changes between those revisions. Website inspected read-only at `ebc836ad2dccfc357d57d4504a00bc4dd75a07bb`; its status was clean. Current-main additions are distinguished below from original-audit omissions.

Required outcome: complete, explicit coverage; canonical metadata; offline diagnostics; independent repository roots; reproducible reports; safe website-only M2 edits. Semantic content accuracy remains a human review responsibility. This document recommends amendments without changing the spec, approving owner decisions, implementing the checker, or editing website content. Unresolved architectural choices below should return to Claude/the design author.

## 2. Strengths & Validated Invariants

### Repository and scope evidence

`git rev-parse --show-toplevel` confirms two independent repositories. The website's root is `C:/Users/theaa/ai-sandbox-master/ai-sandbox/personal-website/AaronScherf.github.io`; `git ls-files ai-sandbox/personal-website` in the outer checkout lists no website files. The new outer worktree does not contain that checkout. A website worktree must be created by website Git, not inferred from an outer worktree's sibling layout.

| Destination | Owner / permitted stage | Evidence and isolation |
| --- | --- | --- |
| Outer registry, schema, checker, tests, documentation | Monorepo task worktree, M1 | Ordinary outer-repository files; no website writes required |
| Website project bundles | Dedicated website worktree, M2 and website portion of M3 | Independent history/index/HEAD; pass this exact root to the checker |
| Summary-enhancement status update and registry additions for new pages | Monorepo worktree, M3 | Cannot be included in a website commit |
| Guided-solutions vault outputs | Outside this implementation's write scope | Operational status describes vault runs, not a Python package; do not scan/copy the private corpus merely to register it |
| Hugo public/resources/cache outputs | Owned website worktree or isolated build destinations | Production build can write generated files and download modules; distinct from offline M1 checking |

Read guidance: outer `AGENTS.md`, `docs/WORKTREE_WORKFLOW.md`, `docs/AGENT_ROUTING.md`, `docs/BUG_HANDOFF.md`; package `CLAUDE.md` and `README.md`; website `CLAUDE.md`, `README.md`, and `docs/AGENT_ROUTING.md`. The explicit assignment permits this Codex review despite default routing. Website pushes to main deploy through `.github/workflows/deploy.yml`; review/build success is not publication permission. An outer worktree also does not coordinate Obsidian or another website writer: read explicit roots, detect changing inputs, and keep writes owned.

Adjacent work checked: `tools/audit_metadata.py`, `tools/corpus_health/README.md`, `tools/project_steering/README.md`, the corpus-health and project-steering specs/plans in `docs/superpowers/{specs,plans}/academic_hub/`, their status records in `docs/status/academic_hub/`, and `docs/trackers/academic_hub_to_do.md`. Existing steering accepts a tracker and maintains reviewed decisions; no website-finding ingestion interface is established here. Reusing its review server or importing pipeline modules is unnecessary for M1.

### Capability and proportionality assessment

| Capability | Discovery / scope | Side effects / cost | Output / idempotency | Acceptance evidence |
| --- | --- | --- | --- | --- |
| Registry validation | Explicit component inventory, local schema | Local reads; no model needed | Stable validation diagnostics | Valid and invalid schema fixtures plus semantic path checks |
| Coverage discovery | Tracked candidate packages plus explicit operational/component entries | Local filesystem/Git only | Deterministic candidates; explicit exclusions | Reconciled inventory below, including package-less cases |
| History diagnostics | Explicit monorepo and website revisions | Local Git; prohibit lazy network fetch | Suspected freshness gaps, not factual content verdicts | Independent Git fixtures and sampled live histories |
| Bidirectional metadata audit | Registered pages plus pages claiming a registry identity | Local YAML reads | All mismatches per target, repeatable | Exact contract tests and M2 live check |
| M2 metadata edits | Explicit website path allowlist | Website writes/build costs only | Reviewed patch; reapplying produces no duplicate blocks | YAML validation, diff, production build, rendered sample |
| Steering/scheduled integration | Not implemented by this proposal | Would add state/writes and review obligations | Deferred | Separate design and supported ingestion contract required |

M1 can stand alone with registry validation, coverage checks, metadata diagnostics, and clearly labeled history warnings. It needs no server, database, scheduler, locks, model, repair command, or persistent decision ledger. Report-only findings do not collect human decisions, so the interactive-Artifact rule does not require a new UI. If later collecting accept/defer/decline decisions, use the established interactive review convention rather than hand-edited report files.

The zero-token/no-network architecture is feasible, but not yet enforced or demonstrated. Local YAML/schema dependencies do not themselves require network calls; installation/build provisioning must be distinguished from checker execution.

## 3. Identified Risks & Edge Cases

### R1 — Blocking: the inventory and baseline counts are not authoritative

The audit matrix has **23 rows: 22 component rows and one overview**. It contains **six**, not eight, missing-page rows; its missing-page section likewise enumerates six. The website contains **16 relevant existing component pages** (12 academic-hub, three research, one resume), plus **two overview pages**. M2's count of 13 excludes real targets.

Plan Task 1 lists 21 entries by omitting tutor diagnosis and Obsidian sync from the audit matrix and adding `core/env`. Neither overview has a defined Task 1 entry. Current main additionally contains `agent/concept_graph`, absent at `777f507`; the current README and concept-graph status/plan files confirm this is new baseline scope, not evidence for an unnamed original eighth missing page.

| Audited identity | Website relative to `content/projects/` | Plan Task 1 disposition |
| --- | --- | --- |
| core/indexer | academic-hub/source_indexer/index.md | Listed |
| pipelines/transcribe_notes | academic-hub/notes_transcription/index.md | Listed |
| pipelines/convert_textbook | academic-hub/marker_conversion/index.md | Listed |
| pipelines/postprocess_notes | academic-hub/postprocess_notes/index.md | Listed |
| pipelines/generate_video_notes | academic-hub/video_notes/index.md | Listed |
| pipelines/convert_essays | ai-research-assistant/research_notes_conversion/index.md | Listed |
| pipelines/convert_journal_articles | ai-research-assistant/journal_article_transcription/index.md | Listed |
| discovery/discover_journal_articles | ai-research-assistant/journal_discovery/index.md | Listed |
| agent/rag — Q&A | academic-hub/rag_analysis/index.md | Listed |
| agent/rag — tutor diagnosis | academic-hub/tutor_diagnosis/index.md | **Omitted distinct component** |
| agent/tutor | Missing | Listed |
| agent/viz | academic-hub/visualization/index.md | Listed |
| agent/problem_gen | academic-hub/problem_generation/index.md | Listed |
| agent/problem_corpus | academic-hub/problem_corpus/index.md | Listed |
| agent/study_guide | Missing | Listed |
| agent/summary_enhance | Missing | Listed |
| resume_manager | resume_manager/index.md | Listed |
| audio_generator | academic-hub/audio_generator/index.md | Listed |
| tools/corpus_health | Missing | Listed |
| tools/project_steering | Missing | Listed |
| agent/problem_sets — operational identity | Missing | Listed but package does not exist |
| obsidian_git_sync | academic-hub/obsidian_git_sync/index.md | **Omitted** |
| academic-hub overview | academic-hub-overview/index.md | Promised, not enumerated |
| research overview | ai-research-assistant-overview/index.md | Promised, not enumerated in audit matrix or Task 1 |

The union of this matrix, Task 1's `core/env`, and current-main `agent/concept_graph` is **24 component candidates plus two overviews**. Account for each explicitly; this is not a recommendation that every infrastructure component needs its own public page. Record exclusions/aggregation and rationale instead of forcing a desired count. Do not freeze the overview at 18 before deciding its membership.

Discovery by `__init__.py` AND `README.md` is insufficient. Live checks show both `core/env` and `pipelines/postprocess_notes` have an initializer but no README, while `agent/problem_sets` has no code directory. Tutor diagnosis is a file within another package; Obsidian is configuration outside the Python root. Exclude archive, environments, caches, fixtures, internal subpackages, and unrelated website projects explicitly.

### R2 — Blocking: timestamps cannot reproduce semantic alignment

Read-only sample using exactly `git -C <root> log -1 --format=%ct -- <path>` at the recorded revisions:

| Component | Code epoch | Page epoch | Difference (seconds) | Proposed rule / audit label |
| --- | ---: | ---: | ---: | --- |
| convert_textbook | 1791519076 | 1791255114 | 263962 | OUTDATED / Aligned |
| postprocess_notes | 1791519076 | 1791255378 | 263698 | OUTDATED / Aligned |
| core/indexer | 1791561674 | 1791255114 | 306560 | OUTDATED / Page Outdated |
| generate_video_notes | 1790751474 | 1791053388 | -301914 | No timestamp warning / Aligned |

This reproduces two false positives **relative to the audit's labels**; it does not independently certify those pages' entire prose. Therefore Task 2's exact-audit reproduction and capability table's zero-false-positive/negative requirement cannot hold. Filesystem checks and Git dates do not inspect the meaning of prose.

The 3600-second tolerance is an arbitrary warning threshold, not proof of concurrent commits. It suppresses real changes within an hour, flags non-substantive changes beyond an hour, and cannot resolve cross-machine clock skew, rebases, cherry-picks, backdated commits, or directory moves. Test the exact equality boundary. `git log -1` is traversal-selected latest history, not necessarily the maximum timestamp under nonmonotonic clocks.

**M2 would itself hide M3 work:** committing frontmatter/links makes `t_page` newer while leaving outdated prose untouched. Likewise editing one unrelated operational status record makes `max(t_status)` appear fresh while other linked records remain obsolete. The checker never compares status-doc advancement against page history, so it also misses status-only discoveries with unchanged code. Missing history is not timestamp zero; it is unknown/incomplete. Call results heuristic warnings and retain the editorial backlog independently.

### R3 — Blocking: no single implementable metadata/schema contract

Design section 4.2 uses `package: pipelines/transcribe_notes`, `monorepo_rel_path`, and `primary_status_doc`. Plan Task 3 instead uses `status_docs`; Task 2 compares package to `entry.code_path`, which includes `ai-sandbox/academic-rag-model/`. The example fails that comparison. Design section 5 references `registry.package`, a field its entry does not define.

The schema file is a future deliverable, not an existing strict schema that can be signed off. Required `code_path`/README cannot represent operational runs, missing READMEs, or overview aggregation. `status_docs` as an explicit list is a sound start for study-guide/indexer records, but a single `status_dir` cannot describe scattered run histories, and a singular frontmatter primary doc is not equivalent to that list. `website_page: null` conflates missing, intentionally internal, deferred, and aggregated projects. If it stays null when M3 creates a page, the checker will report it missing forever without a separate monorepo mapping update.

Keys tied to package paths are unstable under rename and cannot naturally represent two components in `agent/rag`. One scalar page also cannot express the tracker's suggestion to fold summary enhancement into the study-guide page without defining shared-page metadata semantics.

### R4 — High: cross-repository invocation and offline guarantees need mechanics

`git -C` is correct in principle, but no implementation exists to validate. A missing nested website directory in an outer worktree must not silently resolve to the outer repository. Verify each actual Git toplevel and distinct repository identity; recognize worktree `.git` files. Do not assume branch `main` exists in the website checkout. Resolve each selected ref independently and include both SHAs in reports.

The spec says code on `main`; commands without a revision query HEAD. Existence/frontmatter reads use disk. This mixes snapshots unless explicitly defined. Default to a documented workspace check of each checkout's HEAD plus disk, with dirty/untracked inputs labeled; provide a separately specified committed mode if needed. Do not silently compare main history to another branch's files.

`python -m tools.audit_website_sync` resolves from the package root, not automatically from monorepo root or arbitrary cwd. Root resolution inside the tool cannot fix import failure before the tool starts. Document a launcher/cwd wrapper or tested import setup. The same applies when checking from a website worktree.

Git hooks can inherit `GIT_DIR`, `GIT_WORK_TREE`, and index/object environment overrides. Sanitize repository-selection variables for child Git calls so `-C` cannot query the wrong checkout. Partial clones can fetch missing objects lazily: disable lazy fetch and return incomplete if local objects are unavailable. Git documents these controls in its [command/environment reference](https://git-scm.com/docs/git). Use argument lists, literal pathspecs and `--`, subprocess timeouts, local-only schema resolution, and no pipeline/client imports. Never fetch/pull to repair a check.

### R5 — High: dependency, performance and automation promises conflict

Python's standard library supplies neither a YAML parser nor a JSON Schema validator. `requirements.txt` already includes PyYAML and ruamel.yaml; it does not declare jsonschema. Amend the stdlib-only claim, choose a local safe YAML parser and schema validation dependency/strategy, and test malformed/duplicate keys. Do not hand-parse arbitrary YAML to preserve an unnecessary dependency claim.

Eight sequential local Git history queries took **1.574 seconds** in one Windows sample, before schema/YAML parsing. This is not a benchmark of the unimplemented tool, but it refutes assuming the per-path loop will meet 500 ms. The planned 21-entry loop needs at least 63 history queries and more for multiple status docs. Deduplicate/cache per invocation, consider batched histories, and measure cold/warm runs; either demonstrate the target or amend it. No persistent service/cache is required just to ship M1.

Exit behavior only defines strict missing/outdated failures, leaving schema failures, orphaned pages, metadata errors, and incomplete scans ambiguous. The design names `ORPHANED_PAGE`; the plan's global enums/tests omit it. A loop over registry entries cannot discover pages that refer to removed entries. Multiple findings must coexist for one identity.

Pre-commit verification of disk/HEAD is not staged-snapshot verification: a page staged correctly but edited incorrectly afterward (or vice versa) produces misleading results. Defer staged-index gating or specify it and test partial staging. CI also needs both local checkouts and sufficient history; a shallow checkout or absent website must not report aligned.

### R6 — High: website compatibility and links need correction

The checkout uses **HugoBlox Academic CV**, verified by `CLAUDE.md`, `go.mod`, and `config/_default/module.yaml`; it is not Blowfish. Hugo accepts nested frontmatter maps and documents custom fields under `params`; prefer an agreed `params.subproject` contract, or explicitly test retained top-level `subproject` compatibility on the pinned build. See [Hugo frontmatter](https://gohugo.io/content-management/front-matter/) and [Page.Params](https://gohugo.io/methods/page/params/). This is format feasibility, not evidence that an edited site builds or renders correctly. No local layout reference to `subproject` was found; module templates are not vendored, so a rendered sample remains necessary. Metadata alone does not create visible source/status links.

Four of Task 3's five replacement directories are correct. **Journal discovery must use `.../discovery/discover_journal_articles`, not `.../pipelines/discover_journal_articles`.** Keep legitimate overview root links and Obsidian's existing `blob/main/.../docs/status/...` links. Directory URLs use `tree`; file/status URLs use `blob`. Verify paths locally without network requests in the checker. Visible status links promised in design section 1 need explicit Task 3 work, not just metadata insertion.

### R7 — Medium: M3 narrative corrections also need evidence

Do not replace RAG's limitations with a blanket "session memory solved." `agent/rag/README.md` describes caller-owned history; `rag_agent.py` initializes REPL `history = []` while separately reading diagnosis events/gap tags and summaries. Persistence of those records and tutor profiles does not establish full conversation restoration. Describe the actual scoped persistence and the separate problem-generation route. Guided Solutions is documented operational work, not verified standalone executable code. New pages must distinguish fixtures, live runs, and planned functionality.

## 4. Concrete Amendments to Spec & Plan

### Before M1 implementation

1. **Replace the inventory contract** in design section 6 and plan Tasks 1/4 with the reconciled table and explicit inclusion/exclusion/aggregation policy. Date/pin its baseline. Account for all original rows, both overviews, `core/env`, and the newer concept graph. Correct six/eight and 13/16 inconsistencies rather than inventing missing targets.
2. **Publish one field contract and actual strict schema.** Recommend immutable IDs as identity; package labels separate from repo-relative paths; a kind for code, operational, configuration and overview; optional code/README when justified; explicit status-doc lists; lifecycle active/archived; website policy required/internal/aggregated with reason and target. For the smallest release, keep one component per page and explicit overview membership, or settle shared-page representation before claiming it works. Do not use a broad parent directory as fake Guided Solutions code.
3. **Fix validation rules:** versioned schema dialect; required fields and enums; reject extra keys, duplicate JSON keys, duplicate IDs and accidental page collisions; nonempty unique path lists where required; conditional nullability; reject absolute/drive/UNC paths, traversal, wildcard/pathspec magic, and resolved symlink escapes. Use forward-slash paths relative to the correct repo root. Add runtime semantic validation for existence, expected file/directory type, identity uniqueness and cross-references, which schema alone cannot prove. Distinguish a well-formed registry with missing targets from an invalid registry.
4. **Make bidirectional comparisons exact:** match immutable ID, package label, monorepo code path, README and status-doc set against the same named canonical fields. Declare whether status order is meaningful; compare as a set if not. Scan all claiming pages, detect unknown IDs/duplicates and missing frontmatter on registered pages, but do not label unrelated portfolio projects orphaned. Replace Task 2's package-versus-code-path comparison.
5. **Replace semantic claims with evidence-qualified diagnostics.** Timestamp warnings mean "review freshness," never proven outdated or aligned prose. Preserve content backlog after M2 metadata commits. Report each status doc's evidence and distinguish canonical status from historical run records; add status-to-page history diagnostics if included in the freshness contract. If semantic approval must be machine-recognized, design an explicit reviewed-source revision/fingerprint separately; timestamps cannot supply that approval. Keep 3600 only as a documented configurable heuristic with boundary tests.
6. **Define invocation and snapshot semantics:** add explicit monorepo root support alongside website root, script-anchored default registry, cwd-relative handling of user path arguments, independent ref resolution, and reported roots/SHAs. Fail incomplete for unavailable/wrong roots or history. Specify workspace mode now; defer staged mode unless it is truly required for M1. Document working module commands from each promised launch location.
7. **Define the report/exit contract:** recommend `0` for a complete non-strict report (or clean strict report), `1` for complete strict reports with actionable findings of any category, and `2` for invocation/configuration/parse/Git/history failures or incomplete coverage, irrespective of strictness. Error precedence is 2. Include report schema version, coverage-complete flag, both revisions, threshold, per-ID findings/evidence/dirty state, stable ordering, and summary counts. JSON stdout must contain only JSON; diagnostics go to stderr. Unify `--format text|json|markdown` versus `--json`, and remove undeclared `--check/--report` promises or define aliases.
8. **Keep execution read-only and offline:** no metadata sync, tracker writes, dotenv/model initialization, remote schema references, implicit Git downloads, or output files by default. An explicit output option must define its destination and atomic replacement; external redirection is caller-owned. Compare pre/post tracked and untracked status against the initial snapshot, not an assumption that both repos started clean. Avoid Python bytecode writes when testing literal no-filesystem-writes behavior.
9. **Replace acceptance tests with achievable evidence:** use independent temporary Git repos/worktrees with different branch names and deterministic dates, not mocks alone. Test malformed schemas/YAML, all finding categories, concurrent findings, missing/null targets, package-less records, multi-status paths, removed/renamed/archived packages, untracked files, dirty/staged states, missing/shallow histories, timestamp boundary/skew, spaces/Windows paths, cwd changes, inherited Git variables, and network-disabled execution. Compare a varied live sample to underlying records and retain false-positive explanations. Treat measured latency as evidence, not an assertion.

Renames preserve immutable ID and update explicit paths; archived entries become intentional lifecycle changes, not silently excluded missing paths. A deleted required target remains a finding even if `git log` returns historical commits. Untracked files may satisfy a workspace presence check but must have unknown freshness and cannot certify committed alignment. Dirty trees are reportable input state; detect relevant files or HEAD changing during a scan and report incomplete rather than mixing observations. Do not modify another writer's index or working tree.

No scheduler belongs in M1. If scheduling/steering is later added, specify the actual entry point, checkout paths, environment, measured scan cost, retry limits, atomic report storage, and unattended failure handling. Use stable `(component_id, finding_kind, target)` identities plus input fingerprints; new evidence invalidates prior resolutions, unchanged declined findings stay declined, and deferred items retain their gate. No human available means report pending, never auto-approve or repair. This is a future integration prerequisite, not an excuse to add a ledger/server now.

### Before M2 execution

1. Freeze the agreed frontmatter contract and explicit **16-component-page** target list (plus separately specified overview handling) in M1. Pass the dedicated website worktree root to the checker. M2 edits only website files; any newly needed registry/schema change must land independently in the monorepo first.
2. Correct journal discovery's URL; validate all five target paths locally and preserve intentional overview/status links. Add visible source/status links where promised. Preserve existing page type, body, publication state and unrelated metadata; reject duplicate YAML keys. Do not globally rewrite YAML to inject one block.
3. Follow the website's own routing/worktree rules, confirm its local ignore rule before nesting a worktree, and coordinate its sole writer/build outputs. M3 status updates and new-page registry mappings need separate monorepo commits; website publication requires its own authorization.
4. Require safe YAML parsing, full field-level consistency, and the repository's production build (`pnpm run build`, including Pagefind), plus representative rendered-page checks. Provision pinned Hugo Extended/modules/JS dependencies separately; do not count this potentially networked build as the offline checker. Assert expected missing/content findings remain, rather than expecting all drift to disappear after metadata edits.
5. Keep automated repair/synchronization out of scope. Any later `--sync-frontmatter` needs exact selectors, per-target machine-readable outcomes, all-writer coordination, atomic output and a post-run audit before enabling it.

## 5. Acceptance Criteria Sign-Off

These are gates, not assertions that implementation tests have passed.

| Requirement / stage | Required acceptance evidence | Sign-off |
| --- | --- | --- |
| Review isolation | Dedicated requested branch/worktree; only review document changed | Verified for this review |
| Two-repository boundary | Actual roots and website SHA inspected; no website edits | Verified for this review |
| M1 standalone value | Read-only inventory/metadata/history diagnostics, no new service | Architecturally sound with amendments |
| Complete coverage | Reconciled identities and explicit exclusions; all audited rows traced | **Pending before coding** |
| Schema/frontmatter contract | One schema, field mapping, nullability, lifecycle and overview policy | **Pending before coding** |
| Freshness semantics | Remove exact semantic-audit equivalence; preserve M3 backlog through M2 | **Pending before coding** |
| Offline and cwd contracts | Dependency decision, roots/snapshot/launch behavior and network prohibition | **Pending before coding** |
| Automation behavior | Explicit finding taxonomy, exit 0/1/2 policy, incomplete/dirty/staged behavior | **Pending before coding** |
| M1 implementation acceptance | Real Git fixtures, schema tests, no-network/no-mutation checks, measured latency | Not implemented/tested |
| M1 live acceptance | Varied sampled findings checked against files; false positives documented | Review sample exposes mismatch; future checker run pending |
| M2 safety and correctness | Website-only diff, field agreement, corrected links, build and rendered preview | Not executed |
| M3 factual claims | Editorial source review; separate repo commits and publication gates | Deferred |

**Recommended next action:** have Claude/the design author amend the spec and plan for R1–R6, then re-review those contracts before M1 coding. The necessary first release remains one registry, one schema and one local CLI with tests. The reviewed design is feasible after amendment; no fixture suite, implemented scanner live run, Hugo build, deployment, or longitudinal behavior is claimed by this review.

## Addendum - Lifecycle Scope Extension (2026-10-11)

At the owner's request, the [design](specs/2026-10-10-subproject-website-sync-design.md) and [plan](specs/2026-10-10-subproject-website-sync-plan.md) now propose explicit lifecycle records for specs, implementation plans and test paths, plus status-document backlinks to the applicable records. The [tracker](../trackers/subproject_website_status_tracker.md#8-lifecycle-traceability-extension-2026-10-11) records this additional scope. This addendum preserves the original review's findings/verdict; it does not retroactively assert implementation or architecture approval.

Additional acceptance checks: separate specs from plans even when stored together; support multiple plans/status records per design; preserve historical revision links and explicit supersession; validate local test references without executing them or claiming they passed; distinguish unexplored inventory from intentional absence; and never infer architectural obsolescence from newer code/status/test timestamps. Specs can remain valid through routine code changes. Plan checkbox edits do not create new architectural revisions.

M1 must report lifecycle-reference integrity and a concrete legacy-backfill backlog. Plan T6a owns manual monorepo backlink migration independently of website-only M2. D2 must review the expanded schema/backlink convention before implementation. The scanner's own future status must link its actual spec/plan/tests with revision-specific run evidence. These are proposed acceptance criteria, not test results or a completed migration.
