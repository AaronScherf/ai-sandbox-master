# Subproject Website Alignment & Automated Verification: Implementation Plan

**Status:** Amended proposal; blocked on design decisions D1–D3. No implementation started.

**Date:** 2026-10-10; amendment resumed 2026-10-11.

**Spec:** [Canonical design/contracts](2026-10-10-subproject-website-sync-design.md)

**Review:** [Codex architectural review](../2026-10-10-subproject-website-sync-codex-review.md)

**Editorial baseline:** [Audit tracker](../../trackers/subproject_website_status_tracker.md)

## 1. Release Boundaries and Current Evidence

M1 delivers a registry, strict schema and read-only local CLI with tests. It reports coverage, metadata integrity and heuristic history gaps without editing website files or certifying prose accuracy. It also traces specs, implementation plans, status backlinks and test references; it does not execute those tests or require architecture docs to follow every code commit. M2 installs metadata/visible links in a dedicated website worktree. M3 reconciles content/status records with source evidence and separate repository commits.

The proposed inventory is 24 components plus two overviews: 16 existing component pages, two existing overview pages, six original missing pages, one newly proposed concept-graph page, and internal core/env infrastructure. D1 must settle publication/overview policies before registry authoring. These are the recorded review-baseline counts, not a claim that later checkouts cannot change.

| Stage | Implemented | Fixture-tested | Live evidence | Remaining gate |
| --- | --- | --- | --- | --- |
| Review amendments | Spec/plan/tracker corrections drafted | Documentation checks only | Roots, inventory, timestamp sample in review | D1–D3 unresolved |
| M1 schema/registry | No | No | Paths inspected; manifest absent | G0 then G1 |
| M1 scanner | No | No | No checker run; review sample found false positives | G2 |
| M2 metadata/links | No | No | Website inspected read-only; no changed-site build | G3 |
| M3 content | No | No | Editorial baseline subject to revalidation | Batch review/publication |

Update this table after each milestone with commits, commands, results, limitations and remaining work. Design approval, passing fixtures, live observations and longitudinal behavior are distinct evidence.

## 2. Ownership and Repository Map

Follow the outer [worktree procedure](../../../../../docs/WORKTREE_WORKFLOW.md) and [routing convention](../../../../../docs/AGENT_ROUTING.md). Use a fresh owned agent/task branch according to assignment; do not reuse a published review branch. Resolve D1–D3 with Claude/the design author before coding.

| Stage | Write scope | Read scope / constraints |
| --- | --- | --- |
| M1 | Outer academic-rag-model: registry/schema, checker/tests, README and explicit dependency change | Explicit website root read-only; no vault scan, sync or API-client initialization |
| M2 | Website worktree: allowlisted project pages and isolated build outputs | Committed M1 registry read-only; no outer writes |
| M3 website | Website worktree per content batch | Code/status read-only; preserve draft/publication rules |
| M3 status/mappings | Separate outer worktree and commit | Status records and changed registry mappings; never in website commits |

Website root is `C:/Users/theaa/ai-sandbox-master/ai-sandbox/personal-website/AaronScherf.github.io`, independently versioned. Outer worktrees do not create it. Read its `CLAUDE.md`/`docs/AGENT_ROUTING.md`, verify root/branch/status and an ignore rule before nesting a worktree. Keep one writer per checkout and coordinate build outputs. Do not run workspace_generator or modify live Obsidian/vault data to initialize work.

## 3. Requirement-to-Task and Review Traceability

| Requirement / review finding | Tasks | Acceptance evidence |
| --- | --- | --- |
| REQ-1 / R1 inventory | T0–T1 | All inventory rows accounted for; original six missing and existing pages traced |
| REQ-2 / R3 metadata/schema | T1,T3,T5 | Actual strict schema, positive/negative fixtures, identical bidirectional projection |
| REQ-3 / R4–R5 offline/read-only | T2–T4 | Denied-network run including child Git; no lazy fetch/remote schema; unchanged bytes/status |
| REQ-4 / R4 boundaries | T2,T4,T5 | Independent repos/branches/worktrees, explicit roots/SHAs and write allowlists |
| REQ-5 / R2 semantic limits | T3–T4,T6 | Heuristic labels, per-doc evidence, metadata-only-commit regression, independent editorial backlog |
| REQ-6 / R5 reports/exits | T3–T4 | Deterministic JSON, format parity, finding/exit combinations and error precedence |
| REQ-7 / R3–R5 edges | T1–T4 | Rename/archive, dirty/untracked/staged, cwd/path, missing history/input-change fixtures |
| REQ-8 / R6 Hugo/links | T5 | Five corrected URLs, source/status links, safe patch, production build/rendered inspection |
| REQ-9 / R2,R5 evidence | T4 | Real Git fixtures, varied live sample/discrepancies, cold/warm timings |
| REQ-10 / proportionality | T0–T6 | No server/state/scheduler/repair/publication; deferred scope explicit |
| REQ-11 / owner lifecycle extension | T1,T3,T4,T6a | Explicit revision/spec/plan/test mapping, normalized status/plan backlinks, supersession handling and no age-based architecture warnings |
| R7 narrative accuracy | T6 | Scoped persistence claims, operational Guided Solutions, evidence-backed concept graph |

The [design capability table](2026-10-10-subproject-website-sync-design.md#6-capability-cost-and-verification) owns discovery, costs, output and idempotency. This plan adds ordering/evidence rather than a competing schema or CLI.

## 4. Ordered Tasks and Gates

### T0 — Resolve architecture (G0, before coding)

Owner: Claude/the design author. Review D1 publication/overview policies, D2 schema/frontmatter (including lifecycle records and backlinks) and D3 runtime/dependencies. Record explicit decisions in the spec and update the plan if choices change. Account for R1–R7 through amendments or explicit deferrals/rationale. Requesting amendments or landing a review does not approve design decisions.

**G0:** D1–D3 resolved and canonical contract consistent. No silent coding defaults for blockers. The original Blocked verdict remains historical; new sign-off must identify the amended revision.

### T1 — Manifest/schema and validation (M1, G1)

Create `docs/trackers/subproject_registry.json`, adjacent `subproject_registry.schema.json`, and schema/loader fixtures in `tests/tools/test_audit_website_sync.py`. Add the reviewed local validator dependency to `requirements.txt` if D3 selects it; provision only an implementation-worktree environment. The eventual code/schema/dependency branch requires the full landing suite.

Populate the approved inventory with separate RAG/tutor-diagnosis IDs. Resolve all status paths, including indexer feature docs and scattered study-guide histories. Classify current/historical from content. Use explained null READMEs/empty code paths where permitted; never invent Guided Solutions code or infrastructure status. Retain required target page paths before creation, so existence changes are detectable without null-to-path edits.

Author actual Draft 2020-12 schema/local-only loader. Cover duplicate JSON keys, unknown keys/versions/enums, conditional nullability, invalid paths, duplicate status/page ownership, Windows case collisions, symlink escapes, invalid overview members and conflicting exclusions. Separate invalid configuration from missing-target findings: planned nonexistent website pages remain schema-valid.

Inventory lifecycle records separately from page coverage. Search `docs/superpowers/specs/`, `docs/superpowers/plans/`, `docs/brainstorms/`, package status records and `tests/`; classify by content, not directory or dates. For each component, enumerate specs, implementation plans and explicit test paths, map each status record to applicable lifecycle IDs, and identify legacy backlink gaps. Include multi-feature/multi-plan cases and deliberately absent operational tests without inventing provenance. Unknown mappings remain LIFECYCLE_UNMAPPED findings. Preserve superseded records and historical status associations. Shared status files use the union of required references across components.

**G1:** Reviewed manifest covers approved inventory; executable schema exists; valid/invalid fixtures pass; disk paths/types checked. Explain status roles, lifecycle relationships/absence reasons, membership and exclusions. Schema fixtures cover lifecycle ID uniqueness, dangling/cyclic supersession, missing spec/plan/test files and differing current/historical records. Complete G1 before implementing scanner logic against the contract.

### T2 — Roots and local Git evidence (M1)

Create `tools/audit_website_sync.py` using design section 5. Restrict imports to local parsing/validation and Python/Git; no pipelines, indexers, models or dotenv. Implement explicit website root, anchored/explicit monorepo/registry, wrapper invocation, root identity checks and independently pinned HEADs. Support worktree `.git` files, standalone clones and distinct branch names.

Use literal Git argument arrays, sanitized repository/index/object/config environment, disabled optional locks/lazy fetch and bounded timeouts. Cache unique paths per invocation. Check history completeness and relevant tracked/dirty/untracked state; detect observed relevant path/HEAD changes. No staged-only/arbitrary-ref mode.

Acceptance: independent real-repo/worktree fixtures cannot bleed indexes/refs/environment; wrong roots/missing objects fail incomplete. Wrapper works from outer/package/website/unrelated cwd. Spaces/Windows paths stay literal. Verify supported Git controls, not merely their appearance in code.

### T3 — Discovery, metadata and reports (M1)

Implement bounded package discovery/exclusions without requiring READMEs. Scan registered targets plus claiming website pages, preserving unrelated portfolio projects. Safe YAML rejects duplicate keys. Validate the exact params.subproject projection, required local source/status links, unknown IDs and duplicate owners; retain multiple findings per component.

Implement per-current-doc/code-to-page history warnings with strict greater-than tolerance, never semantic ALIGNED. Dirty/untracked freshness is unknown; operational/overview records use applicable checks. Text/JSON/Markdown share one sorted model and 0/1/2 policy. Stdout only; no generated files, tracker edits or sync.

Add lifecycle-reference checking: resolve the documented Lifecycle references sections in plans/status docs, compare normalized local links to canonical registry records, and expose missing specs, implementation plans, tests, backlinks and unmapped/review-needed lifecycle associations. Do not follow arbitrary external URLs, infer coverage from prose, or invoke linked tests/commands. Historic backlinks stay tied to their described revision; current status using only superseded records is a review finding. Spec/plan/test timestamps are excluded from age-based warnings.

Acceptance: every design finding category covered, formats agree, runtime JSON remains parseable and exit 2 takes precedence. Metadata-only commits may change warnings but cannot complete editorial tasks. Historical/newer status edits cannot certify all docs as fresh.

### T4 — Fixtures, live sampling and documentation (M1, G2)

Use independent temporary real Git repositories with deterministic dates and different branch names; mocks supplement them. Cover linked worktrees, shallow/missing history, missing objects, empty Git output/timeouts; 3599/3600/3601-second boundaries, skew/nonmonotonic dates, metadata-only commits, historical-status edits, package-less records, multi-status records, deleted/renamed/archived entries and unknown pages.

Cover dirty/staged/untracked inputs, partial staging (workspace reporting, not index certification), deletion with old history, concurrent changes, unrelated dirtiness, traversal/symlink escape, arbitrary cwd and inherited Git overrides. Deny network for checker and subprocesses: socket mocks alone do not prove Git offline. Test no lazy fetch for partial-clone missing objects. Compare pre/post bytes and tracked/untracked status with bytecode/Git optional locks disabled.

Lifecycle fixtures must cover old-but-current specs with newer code, routine plan checkbox/test edits, explicit architectural supersession, several plans per spec, several lifecycle IDs per status, shared status files, missing/wrong backlinks, cross-directory plans, documented lack of tests, unknown inventory, path escapes and renamed/removed historical files. Assert that reading test references never executes them and that file existence never becomes a passing-test claim. Check metadata projection parity for status lifecycle_ids and all new finding/exit combinations.

Run `python -B -m pytest tests/tools/test_audit_website_sync.py -q` and the required full landing gate. Document module/wrapper invocation in README. Record Git/Python/dependency versions, cold/warm timings, process counts and inventory size; no unmeasured sub-500 ms promise.

Live sampling records explicit roots, HEADs and initial dirtiness. Inspect source indexer, textbook/postprocess (known timestamp/editorial mismatch), video notes, a missing page, study-guide multi-status, Guided Solutions, tutor diagnosis and Obsidian. Compare files/Git and retain discrepancies. Relevant live dirtiness can correctly cause exit 2: record it, then use clean owned fixtures/worktrees for reproducible acceptance, without cleaning another checkout.

Create the checker's own implementation status record under `docs/status/tools/website_sync/` when implementation exists. Link this spec, this plan and the actual new test module; record tested SHA, command, date, outcome and evidence, and distinguish fixtures from live samples. No such implementation status/test result is fabricated during this documentation task. Inventory the newly implemented checker itself explicitly at that stage, separately from the 26-record historical proposal baseline.

**G2:** G1 plus fixtures, full-suite landing check, varied live report with false-positive/unknown explanations, denied-network/no-write evidence and latency measurements. Report lifecycle coverage separately: valid known links and an enumerated legacy-backfill backlog are required; zero legacy gaps is a T6a gate, not a reason to delay the useful M1 scanner. User reviews the concrete M1 registry/report before M2 edits. Passing M1 does not repair content or prove prose accuracy.

### T5 — Website metadata and visible links (M2, G3)

After G2, create a website-owned worktree using the committed M1 mapping. Under D1's proposal the allowlist is **16 existing component pages plus two overviews** in design section 3. Do not create proposed missing pages in M2.

Insert canonical metadata under params, preserving unrelated fields/body/publication state. Add visible source/status links and approved overview members. Preserve existing Obsidian and intentional overview root links. Repeat insertion must produce no duplicates; avoid whole-file YAML rewriting. Review the exact metadata/link patch.

Five replacements relative to `https://github.com/AaronScherf/ai-sandbox-master/tree/main/ai-sandbox/academic-rag-model/`:

| Website component | Correct source suffix |
| --- | --- |
| marker_conversion | pipelines/convert_textbook |
| notes_transcription | pipelines/transcribe_notes |
| journal_article_transcription | pipelines/convert_journal_articles |
| journal_discovery | discovery/discover_journal_articles |
| research_notes_conversion | pipelines/convert_essays |

Run the M1 checker against the exact website worktree via its wrapper. During edits metadata can pass while dirty-page history causes exit 2; inspect metadata without claiming full acceptance. Commit the patch locally and rerun on a clean committed pair for final evidence. Missing pages/history warnings may still cause strict exit 1. G3 requires zero metadata mismatches/orphaned claims for owned targets, not an empty content backlog.

Provision pinned Hugo Extended/modules/JS dependencies separately. Run `pnpm run build` (Hugo plus Pagefind); inspect generated changes and representative component, multi-status, configuration and overview pages. Check visible links and absence of unintended metadata rendering. Preserve drafts; no publication/push as part of build checks.

**G3:** Website-only patch, YAML/metadata/local-link checks, production build, rendered samples and unresolved findings recorded. Contract/registry changes require separate outer commits. Website landing/publication needs its own approval.

### T6a - Backfill lifecycle links (monorepo portion of M3)

Write only in an owned monorepo worktree. Use M1's explicit component/status/plan target list to add normalized Lifecycle references sections and repair mappings after inspecting source material. Preserve narrative status history and old run evidence. Plans link to applicable specs/tests; statuses link to applicable specs, plans and tests. Do not rewrite specs to appear newer, mark a plan completed, or manufacture a passing result. Operational components can record genuine absence of automated tests. Partial batches report remaining gaps by stable ID; each batch gets a reviewed diff and post-edit scanner audit.

Acceptance: all approved targets have matching local backlinks or reviewed explicit absence reasons; unknown inventory remains a finding until resolved. Current architecture may predate many code/test commits without a staleness warning. Historical associations survive supersession. Commit registry/status/plan changes only in the monorepo; coordinate changed website status lifecycle_ids separately after the prerequisite commit. M2 remains website-only. No automatic repair is enabled by this manual backfill task.

### T6 — Content/status reconciliation (M3 backlog)

Review pages independently at approved targets. Prioritize Socratic Tutor, Study Guide, Corpus Health and Project Steering; then Summary Enhancement and Guided Solutions. Proposed Concept Graph is a seventh current-main addition under D1, not an original eighth finding. Its status files have historical not-merged/not-run claims: verify landed code independently and never infer live-corpus success from fixtures.

Refresh Source Indexer, Notes Transcription, RAG Analysis and Academic Hub overview. For RAG, distinguish persisted diagnosis/gap events and summaries from full conversation restoration: REPL history starts anew; tutor profiles belong to another component. Describe actual problem-generation routing/question resolution. Guided Solutions is operational work, not a standalone executable. Derive overview prose from approved membership and shipped behavior, not a hardcoded count.

Update summary-enhancement status in a separate outer worktree. A new status file requires registry references/roles updated there and a dependent website metadata patch in its own repository. Record both commits and expected intermediate mismatch. Predeclared page creation alone needs no registry edit. New pages remain drafts until publication is requested.

Acceptance: source-backed distinctions among design/fixtures/live evidence, editorial review, mapping checks, build/preview and separate publication authorization. No automatic steering ingestion/content pipeline is assumed.

## 5. Deferred Capabilities and Landing

Deferred: staged-index checks, arbitrary-ref mode, shared component pages, semantic-approval markers, scheduler/steering ingestion, persistent decisions, metadata repair and publication. None is required for M1's useful local report. Future repair/unattended work must meet design section 7 safeguards.

For each milestone stage explicit paths, check the owned repository, commit and follow landing rules. Markdown-only amendments use the doc-only check; eventual M1 code/schema/dependencies require `tools.land_branch check --full`. Approval names an exact SHA. Website main pushes deploy and require publication authorization. Preserve unrelated work and report overlaps/main's status snapshot before landing.

## Lifecycle references

### Specs

- [Website-sync design and lifecycle contract](2026-10-10-subproject-website-sync-design.md)

### Tests

The checker and its planned `tests/tools/test_audit_website_sync.py` do not exist at this planning stage. T1/T4 create and verify them; T4 then records actual results in the implementation status. Documentation link/example checks performed on this proposal are not checker fixture or live-run evidence.

Next action: design-author review of D1–D3 against this amended revision. Landing these documents preserves a proposal; it does not authorize M1 implementation or certify its tests.
