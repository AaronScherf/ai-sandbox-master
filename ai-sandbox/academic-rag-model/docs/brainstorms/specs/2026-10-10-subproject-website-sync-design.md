# Subproject Website Alignment & Automated Verification: Design Spec

**Status:** Amended proposal; decisions D1–D3 pending; implementation not started.

**Date:** 2026-10-10; amendment completed 2026-10-11

**Original authors:** Aaron Scherf & Gemini Agent; review amendments by Codex at the owner's request.

**References:** [Codex review](../2026-10-10-subproject-website-sync-codex-review.md), [implementation plan](2026-10-10-subproject-website-sync-plan.md), [audit tracker](../../trackers/subproject_website_status_tracker.md).

This revision replaces contradictory contracts in the initial draft. Factual corrections are incorporated; recommended architecture choices are explicit proposals for Claude/the design author, not recorded owner approvals. The original review remains a historical assessment of the previous draft.

## 1. Requirements and Smallest Usable Release

| ID | Requirement / constraint |
| --- | --- |
| REQ-1 | Account for all audited components, both overviews and current-main additions using stable identity and explicit website policy. Discovery suggests omissions; it does not decide publication scope. |
| REQ-2 | One canonical registry and strict local schema; validate the same frontmatter projection in both directions. |
| REQ-3 | Checker execution is read-only, local, model-free and network-free: zero API tokens, model inference, Git downloads or remote schema resolution. |
| REQ-4 | Independent repository roots, histories, indexes and HEADs. M1 writes only monorepo files; M2 writes only an owned website worktree. |
| REQ-5 | Separate structural integrity, history warnings and editorial accuracy. Timestamps cannot certify semantic alignment or close content tasks. |
| REQ-6 | Deterministic text/JSON/Markdown reports, per-target evidence, explicit coverage completeness and exit codes. |
| REQ-7 | Define cwd, dirty/untracked inputs, absent history, renames, archival and changes during a scan. |
| REQ-8 | Validate YAML, source/status links, the actual HugoBlox production build and representative rendered pages. |
| REQ-9 | Real independent Git fixtures, a varied live sample, discrepancy records and measured performance. |
| REQ-10 | No scheduling, steering ingestion, staged-index certification, automated repair or publication in M1. |
| REQ-11 | Trace specs, implementation plans, status records and test references through explicit design revisions; status records link back to the applicable documents/tests. Routine code changes do not require rewriting architecture documents. |

**M1 remains the smallest usable release:** registry, schema, read-only CLI, documentation and tests. It provides inventory and metadata diagnostics plus history warnings before website edits. It needs no server, database, persistent cache, decision ledger, scheduler or repair command. M2 adds metadata and visible links; M3 separately reconciles prose/status records and backfills lifecycle links. M1 also validates explicit lifecycle references without running the referenced tests.

Remove the earlier exact-semantic-audit-reproduction and mandatory sub-500 ms claims. The review measured 1.574 seconds for eight sequential Windows Git calls and identified two timestamp false positives against editorial labels. Sub-500 ms is an optimization aspiration; record cold/warm end-to-end timings before promising hook suitability. Provisioning dependencies and building the site are separate from offline checker execution.

## 2. Evidence, Adjacent Work and Repository Boundaries

Original audit: monorepo `8b0c7b7`; original spec/plan landed at `777f507`; review inspected main `44046eb`; amendments based on `519a2f6`. Website rechecked read-only at `ebc836ad2dccfc357d57d4504a00bc4dd75a07bb`, clean. These describe local checkouts, not the deployed site.

Read package `CLAUDE.md`/`README.md` and outer `AGENTS.md`, `docs/AGENT_ROUTING.md`, `docs/WORKTREE_WORKFLOW.md`. Adjacent implementations: `tools/audit_metadata.py`, `tools/corpus_health/README.md`, `tools/project_steering/README.md`; associated specs/plans under `docs/superpowers/{specs,plans}/academic_hub/` and status records under `docs/status/academic_hub/`. Check `docs/trackers/academic_hub_to_do.md` and the concept-graph specs/plans/status when freezing scope. Existing steering reads a tracker; no website-finding ingestion API is established.

| Destination | Repository / ownership | Permitted writes |
| --- | --- | --- |
| Registry/schema, checker/tests, dependency manifest and docs | Outer `ai-sandbox-master`, owned task worktree | M1 |
| `content/projects/` | Independent website repository, owned website worktree | M2 and website portion of M3 |
| Summary-enhancement status and changed registry mappings | Outer monorepo | Separate M3 commits |
| Hugo generated output/cache | Owned website worktree or explicit isolated build destinations | Build validation only |
| Vault notes, live index, cloud outputs, Obsidian configuration | Outside task write scope | None |

Actual website root is `C:/Users/theaa/ai-sandbox-master/ai-sandbox/personal-website/AaronScherf.github.io`. Outer `git ls-files ai-sandbox/personal-website` lists no website files. Outer worktrees do not populate/isolate it. Website `CLAUDE.md`, `go.mod` and `config/_default/module.yaml` establish **HugoBlox Academic CV**, not Blowfish. Read its local `docs/AGENT_ROUTING.md`; website pushes to main deploy through GitHub Actions. Build provisioning may download modules/packages and is not part of the offline scan. Coordinate sole writers and build outputs; a worktree does not coordinate Obsidian or external sync.

## 3. Inventory and Discovery (D1)

The original audit matrix has 22 components plus one overview and six missing-page entries. The website has 16 existing component pages plus two overviews. Original Task 1's 21 entries omitted tutor diagnosis/Obsidian sync and added `core/env`. Current main adds `agent/concept_graph`, absent at `777f507`.

Proposed registry: **24 components plus two overviews**. Stable IDs below are proposed under D2; publication policies and overview membership require D1. Page suffixes are relative to `content/projects/`; actual registry values include that prefix.

| Stable ID | Package / logical label | Page suffix or disposition |
| --- | --- | --- |
| source_indexer | core/indexer | academic-hub/source_indexer/index.md |
| transcribe_notes | pipelines/transcribe_notes | academic-hub/notes_transcription/index.md |
| convert_textbook | pipelines/convert_textbook | academic-hub/marker_conversion/index.md |
| postprocess_notes | pipelines/postprocess_notes | academic-hub/postprocess_notes/index.md |
| generate_video_notes | pipelines/generate_video_notes | academic-hub/video_notes/index.md |
| convert_essays | pipelines/convert_essays | ai-research-assistant/research_notes_conversion/index.md |
| convert_journal_articles | pipelines/convert_journal_articles | ai-research-assistant/journal_article_transcription/index.md |
| discover_journal_articles | discovery/discover_journal_articles | ai-research-assistant/journal_discovery/index.md |
| rag | agent/rag | academic-hub/rag_analysis/index.md |
| tutor_diagnosis | agent/rag | academic-hub/tutor_diagnosis/index.md; code target `agent/rag/tutor_diagnosis.py` |
| socratic_tutor | agent/tutor | Missing: academic-hub/socratic_tutor/index.md |
| visualization | agent/viz | academic-hub/visualization/index.md |
| problem_generation | agent/problem_gen | academic-hub/problem_generation/index.md |
| problem_corpus | agent/problem_corpus | academic-hub/problem_corpus/index.md |
| study_guide | agent/study_guide | Missing: academic-hub/study_guide_pipeline/index.md |
| summary_enhancement | agent/summary_enhance | Missing: academic-hub/summary_enhancement/index.md |
| resume_manager | resume_manager | resume_manager/index.md |
| audio_generator | audio_generator | academic-hub/audio_generator/index.md |
| corpus_health | tools/corpus_health | Missing: academic-hub/corpus_health/index.md |
| project_steering | tools/project_steering | Missing: academic-hub/project_steering/index.md |
| guided_solutions | agent/problem_sets (operational label) | Missing: academic-hub/guided_solutions/index.md; no code folder |
| obsidian_git_sync | obsidian_git_sync (configuration label) | academic-hub/obsidian_git_sync/index.md; source root `ai-sandbox/.obsidian/` |
| core_env | core/env | Proposed internal infrastructure, no required page; retain reason |
| concept_graph | agent/concept_graph | Newly proposed: academic-hub/concept_graph/index.md |
| academic_hub_overview | null | academic-hub-overview/index.md; kind overview |
| research_overview | null | ai-research-assistant-overview/index.md; kind overview |

If D1 accepts these policies, M3 contains six original missing pages plus one newly scoped concept-graph page. Do not invent an eighth original target. Proposed overview membership: required academic-hub components for the hub overview; the three research-category components for the research overview. Shared infrastructure may be linked in prose without expanding that roster. Settle exact membership/category in D1 rather than hardcoding an 18-system claim.

Discovery is bounded filesystem/Git inventory, never imports. Inspect immediate child package directories under `core/`, `pipelines/`, `discovery/`, `agent/`, `tools/`, plus the two standalone apps. An initializer suffices for a candidate; no README prerequisite. Include non-ignored untracked candidates with untracked evidence. Explicit entries cover operational/configuration/file-level cases. Exclude archives, environments, caches, tests, internal subpackages and symlink traversal. Small standalone tool scripts are outside automatic package discovery; record specific package-candidate exclusions with rationale. An unknown candidate triggers review, not page creation.

## 4. Proposed Data Contract (D2)

Files: `docs/trackers/subproject_registry.json` and adjacent `subproject_registry.schema.json`, relative to `academic-rag-model/`. The `subprojects` object is keyed by immutable ID. Package labels are neither IDs nor disk paths. Components may share a package/code subtree but may not own the same page in M1. Combining summary enhancement into study-guide content is deferred unless a shared-page schema is separately reviewed.

| Field | Proposed contract |
| --- | --- |
| Envelope | Required `$schema` (exact adjacent filename), `version` (`1.0.0`), `baseline` (monorepo/website inventory commit IDs), `subprojects`, `discovery_exclusions`. Baseline records provenance, not runtime refs. |
| Entry `name`, `kind`, `category`, `lifecycle` | Nonempty name; kind code/operational/configuration/overview; category academic-hub/ai-research-assistant/standalone; lifecycle active/archived. |
| `package` | Component logical label; null for overview. Never concatenate into a disk path. |
| `code_paths` | Unique literal monorepo-relative files/directories. Nonempty for active code/configuration; empty for operational/overview. |
| `readme_path`, `readme_absence_reason` | README path or null; exactly one of path or nonempty reason populated. Never invent missing READMEs for core/env, postprocess or operational records. |
| `status_docs`, `status_absence_reason` | Unique records `{path, role, lifecycle_ids}`; lifecycle_ids identifies the applicable lifecycle records below (empty means not yet mapped and is reported); role current/historical. Nonempty list uses null absence reason; empty list requires a reason. Roles come from content, not filename dates. |
| `lifecycle_records` | Explicit revision records keyed by stable component-local ID; each separates specs, implementation_plans and test_paths and records state/supersession. Replaces the former untyped specs list; see Lifecycle traceability below. |
| `website` | `{policy, page, reason}`. Required: non-null website-relative target even before creation, null reason. Internal: null page, nonempty reason. |
| `members` | Overview-only nonempty list of existing non-overview IDs; empty for components. Active public rosters exclude internal/archived components. |
| `archive_reason` | Nonempty for archived; null for active. |
| `discovery_exclusions` | Unique `{path, reason}` records, monorepo-relative, for deliberately excluded package candidates. |

Illustrative entry (ID is the enclosing key): paths exist, but lifecycle association/state below is a proposed mapping, not an approved baseline or verified test run. T1 must inventory the other transcription features as separate records.

```json
{
  "transcribe_notes": {
    "name": "Notes Transcription Pipeline",
    "kind": "code",
    "category": "academic-hub",
    "lifecycle": "active",
    "package": "pipelines/transcribe_notes",
    "code_paths": [
      "ai-sandbox/academic-rag-model/pipelines/transcribe_notes"
    ],
    "readme_path": "ai-sandbox/academic-rag-model/pipelines/transcribe_notes/README.md",
    "readme_absence_reason": null,
    "status_docs": [
      {
        "path": "ai-sandbox/academic-rag-model/docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md",
        "role": "current",
        "lifecycle_ids": [
          "agent-driven-transcription"
        ]
      }
    ],
    "status_absence_reason": null,
    "website": {
      "policy": "required",
      "page": "content/projects/academic-hub/notes_transcription/index.md",
      "reason": null
    },
    "members": [],
    "archive_reason": null,
    "lifecycle_records": {
      "agent-driven-transcription": {
        "state": "proposed",
        "supersedes": [],
        "specs": [
          "ai-sandbox/academic-rag-model/docs/superpowers/specs/transcribe_notes/2026-10-09-agent-driven-transcription-design.md"
        ],
        "implementation_plans": [
          "ai-sandbox/academic-rag-model/docs/superpowers/plans/2026-10-09-agent-driven-transcription-plan.md"
        ],
        "test_paths": [
          "ai-sandbox/academic-rag-model/tests/pipelines/transcribe_notes/test_agent_driver.py"
        ],
        "absence_reasons": {
          "specs": null,
          "implementation_plans": null,
          "test_paths": null
        }
      }
    }
  }
}
```

Enumerate study-guide's canonical pipeline status and scattered run histories and indexer's multiple feature docs. Historical records receive existence/link checks but cannot prove current documentation freshness. Guided Solutions uses its operational status, empty code paths and an explained null README. Overview records use membership, not fake monorepo-root code history. Archived records retain identity and historical paths; missing historical source paths are informational after explicit archival, while owned pages still undergo metadata checks.

### Lifecycle traceability

Added at the owner's request on 2026-10-11. This extends D2's proposed schema; it does not approve D1-D3 or implement a migration. Keep the runtime as a local read-only checker, not a new lifecycle service.

Each `lifecycle_records` value contains `state` (proposed/current/superseded), `supersedes` (IDs within this component), unique `specs`, `implementation_plans`, and `test_paths` arrays, plus `absence_reasons` with exactly those three keys. Document paths are monorepo-relative Markdown files; test paths are explicit monorepo-relative files or directories, never shell commands or executable selectors. Shared files are allowed across components/revisions; duplicate paths within one list are not. Empty lists require a nonempty reviewed absence reason; populated lists require null reasons. An empty lifecycle_records object or empty status lifecycle_ids is allowed during inventory, but emits LIFECYCLE_UNMAPPED; do not disguise unknown inventory as an intentional absence. Overview/operational records may explicitly document why specs, a plan or automated tests are not applicable.

Validate record IDs, enums, all paths, absence conditions, dangling references and supersession cycles. Current implementation plans link back to their listed specs. Every mapped status record links back to the union of its lifecycle records' specs, implementation plans and test paths. One status may reference several feature/revision records; one spec may have several plans. Do not infer these relationships from filename similarity, dates, package nesting or latest commit time. Inspect both `docs/superpowers/{specs,plans}/` and `docs/brainstorms/` (this sync plan itself lives under a specs directory), and explicit cross-package documents. Directory location is not document kind.

The canonical mapping is the registry. For deterministic, human-readable backlinks, the proposed migration adds a `## Lifecycle references` section to status records and implementation plans. Inside it, use `### Specs`, `### Implementation plans` (status records only), and `### Tests` headings with ordinary inline Markdown links relative to the containing document. Empty categories state the matching absence reason. The checker resolves these links against the registry, validates containment/existence and compares sets; it does not parse arbitrary prose to infer relationships. Existing prose links may remain, but legacy documents lacking this section are reported as unmapped/backlink gaps until explicitly backfilled. No automatic Markdown rewrite is part of the scanner. For shared status files, compare against the union of mappings for that file across components to avoid contradictory requirements.

Backlink completeness is separate from evidence of execution. A status record claiming verification must also state the tested source revision, exact command/scope, observation date, outcome and evidence location when available; distinguish fixture results, live runs and unverified behavior. Old evidence retains its original revision/date. The checker validates reference structure and reports recorded evidence as unverified prose; it neither runs test commands nor treats a referenced test file as a passing test. Runtime evidence parsing/attestation remains outside M1.

Specs and plans are relatively stable baselines. Routine bug fixes, new tests, status updates, or plan checkbox updates do not require an architecture rewrite or trigger SPEC_OUTDATED/PLAN_OUTDATED warnings. An architectural change creates an explicitly reviewed new lifecycle record or amendment; `supersedes` states which earlier record(s) it replaces. Transition proposed -> current and old current -> superseded only by an explicit reviewed registry edit, never timestamps. Different active feature records may coexist. Historical status records keep their old revision links; current status records referencing only superseded records produce a review finding, not silent relinking. Renames update paths while retaining record IDs; missing historical docs/tests remain visible gaps rather than being erased. If a referenced file is amended in place, preserve the historical baseline with a Git commit link in the status evidence; the first-release checker verifies current-checkout file links only, not historical blobs. A moved/removed historical file therefore requires a reviewed mapping change or remains a reported missing path.

Website projection retains the status records with their lifecycle_ids, enabling page -> status -> lifecycle traceability without duplicating the entire lifecycle registry in frontmatter. M2's visible source/status links remain required; publishing additional design/test links is an explicit editorial choice. No private run artifacts are copied to the website. M1 reports lifecycle gaps immediately; M3 backfills existing monorepo status/plan links under a separate owned commit, independently of website edits.

### Schema and semantic validation

Propose JSON Schema Draft 2020-12 with required keys, `additionalProperties: false` at contract objects, strict versions/enums, nonempty strings, unique arrays and conditional nullability. The actual schema is an M1 Task 1 deliverable that must pass positive/negative fixtures before scanner logic; this prose is not evidence of an existing validated schema.

Reject duplicate JSON keys during loading. Semantic validation also rejects duplicate status paths even with different roles, page ownership collisions, Windows case collisions, invalid members and conflicting exclusions. Paths use forward slashes relative to their named repository root. Reject absolute/drive/UNC paths, backslashes, dot/traversal segments, wildcard/pathspec magic and resolved symlink escapes. Verify file/directory kinds. Lifecycle records use the same strict schema/path checks; reject dangling status lifecycle_ids and supersedes references and cycles. A well-formed registry pointing to a missing target yields a finding; registry/schema/YAML parse/read failure yields incomplete coverage.

D3 recommends existing PyYAML with safe loading plus duplicate-key rejection and an explicitly declared local `jsonschema` dependency. Remove the stdlib-only claim. No hand-written arbitrary-YAML parser. Resolve only the adjacent schema/local definitions, never remote schema URLs. Dependency provisioning is separate; select/test a compatible constraint in M1 after D3 is resolved.

### Website projection

Use `params.subproject`, preserving existing parameters and page fields. Hugo documents custom fields under `params` ([frontmatter](https://gohugo.io/content-management/front-matter/), [Page.Params](https://gohugo.io/methods/page/params/)); pinned HugoBlox build/render checks remain M2 gates. Do not alter type, body, dates, tags, images or draft state merely to add metadata.

```yaml
params:
  subproject:
    id: transcribe_notes
    package: pipelines/transcribe_notes
    code_paths:
      - ai-sandbox/academic-rag-model/pipelines/transcribe_notes
    readme_path: ai-sandbox/academic-rag-model/pipelines/transcribe_notes/README.md
    status_docs:
      - path: ai-sandbox/academic-rag-model/docs/status/transcribe_notes/2026-08-24-notes-transcription-status.md
        role: current
        lifecycle_ids: [agent-driven-transcription]
    members: []
```

Compare ID, package, code paths, README, status records and members to the same registry fields; list order is immaterial after uniqueness checks. Never compare package to code path. Overview projection has null package/README, empty code/status lists and populated members. Reject unknown keys within this block, allowing unrelated Hugo frontmatter. Missing/legacy top-level/dual blocks are diagnostics; M2 installs one canonical block. Duplicate owners and unknown IDs are reported in both scan directions.

Visible `links:` separately expose component source and every status record; metadata does not render links automatically. Derive GitHub tree/main URLs for directories and blob/main URLs for files from locally verified targets. Preserve overview root links and existing Obsidian status links. Guided Solutions can use its operational status as its source. No network URL probing in the checker.

## 5. Proposed CLI and Execution Contract (D3)

```powershell
# From the selected monorepo worktree's academic-rag-model directory:
python -B -m tools.audit_website_sync --website-root <absolute-website-checkout> `
  [--monorepo-root PATH] [--registry PATH] [--format text|json|markdown] `
  [--tolerance-seconds 3600] [--strict]
```

Brackets denote optional flags. No `--json`, `--check`, `--report`, output-file or sync flags in M1. Stdout only; external redirection is caller-owned and should target outside scanned inputs. `-B` prevents bytecode writes. No configuration rewriting or runtime prompts.

Website root is required to avoid guessing nested checkouts. Default monorepo derives from the executing module location, not cwd; explicit root must be the selected Git toplevel containing the expected package. Default registry is anchored to that selected root. User-supplied relative paths resolve against invocation cwd. Verify both toplevels and distinct Git common directories, including worktree `.git` files and standalone website clones. Wrong/missing roots fail incomplete, never fall back to the enclosing repo.

Module discovery still requires the package on Python's import path. Bare module invocation from arbitrary cwd is unsupported. From monorepo/website/unrelated cwd, use this wrapper:

```powershell
$syncMonorepo = 'C:\path\to\owned-monorepo-worktree'
$syncWebsite = 'C:\path\to\selected-website-checkout'
Push-Location (Join-Path $syncMonorepo 'ai-sandbox/academic-rag-model')
try {
    python -B -m tools.audit_website_sync --monorepo-root $syncMonorepo --website-root $syncWebsite --format json
    $syncExit = $LASTEXITCODE
} finally {
    Pop-Location
}
# Hook/CI wrappers propagate $syncExit to their caller.
```

### Snapshot and Git rules

M1 checks **workspace structure/metadata plus pinned HEAD history** for each checkout, not staged-index or arbitrary-ref snapshots. Resolve both HEAD SHAs independently at start; query each explicit SHA. Do not assume a website main branch or shared objects/refs.

Use Git argument arrays, verified `-C` roots, `--literal-pathspecs`, pinned SHA and `--` before paths. Sanitize inherited repository/index/object/config-selection environment (including GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE, GIT_COMMON_DIR, GIT_OBJECT_DIRECTORY, GIT_ALTERNATE_OBJECT_DIRECTORIES and config injection variables), disable optional locks/lazy fetch and specify/test supported Git behavior. No fetch/pull, external diff, shell interpolation, dotenv or pipeline/client imports. Missing local objects, shallow history, unborn HEAD, Git failure and timeout yield incomplete coverage. Use bounded subprocess timeouts, no implicit retry/download. See [Git command/environment reference](https://git-scm.com/docs/git).

Read disk metadata and report relevant staged/unstaged/untracked state. Unrelated dirtiness is repository-level information, not a failure for unaffected targets. Relevant dirty inputs undergo structural checks but freshness is unknown/incomplete. An untracked page can satisfy disk presence without having known committed history. An absent planned required page is an ordinary finding, not an operational failure. A deleted required source remains missing even if Git has old history.

Capture relevant path inventories, content fingerprints and HEADs before/after processing; observed changes yield incomplete coverage. Include tracked/untracked state for code directories. Consistency fingerprints do not constitute semantic approval. This detects observed changes without claiming a transactional snapshot of two writable repos. Never lock or mutate another writer's checkout. Clean owned worktrees provide reproducible acceptance inputs.

### History and finding semantics

For clean tracked inputs with complete history, use `git log -1 --format=%ct <pinned-head> -- <literal-path>`, caching unique path queries within a run. `t_code` is the maximum returned code-path timestamp, a defined heuristic, not a semantic change clock. Compare each current status record separately to code and page; do not aggregate all status docs into a freshness certification. Compare code to page when code exists. Operational records get doc-to-page checks; overview freshness is not assessed in M1. Historical docs are excluded from freshness comparisons. Specs, implementation plans and test paths receive lifecycle-reference checks only; their timestamps never determine architectural staleness. All lifecycle input files participate in consistency/dirty-input detection without becoming freshness inputs.

A gap strictly greater than nonnegative tolerance (default 3600 seconds) emits a warning; equality does not. The window cannot prove concurrent commits. Clock skew, rebases, cosmetic and metadata-only edits may give misleading ordering. Missing timestamps are unknown, never zero. A report with no history gaps does not certify prose. M2 metadata commits must never close the independent editorial backlog.

| Finding | Meaning / strict behavior |
| --- | --- |
| UNREGISTERED_COMPONENT | Candidate has no entry/exclusion; actionable |
| MISSING_WEBSITE_PAGE | Active required target absent on disk; actionable |
| MISSING_SOURCE_PATH / MISSING_README / MISSING_STATUS_DOC | Configured active path absent; actionable |
| MISSING_SPEC / MISSING_IMPLEMENTATION_PLAN / MISSING_TEST_PATH | Configured lifecycle target absent, including historical references; actionable |
| LIFECYCLE_UNMAPPED / LIFECYCLE_BACKLINK_MISMATCH / LIFECYCLE_REVIEW_REQUIRED | Missing inventory, missing/differing normalized backlink section, or current status referring only to superseded baselines; actionable, not age-based |
| METADATA_MISMATCH | Missing/differing projection, duplicate owner or differing required source/status links; actionable |
| ORPHANED_PAGE | Page claims unknown ID or conflicts with registered page ownership; actionable |
| WEBSITE_HISTORY_GAP / STATUS_HISTORY_GAP | Heuristic warning with source/target timestamps; actionable under strict mode |
| DIRTY_INPUT / HISTORY_UNAVAILABLE / INPUT_CHANGED / SCAN_ERROR | Relevant evidence unavailable/unstable; coverage incomplete |
| INTERNAL_COMPONENT / ARCHIVED_COMPONENT / FRESHNESS_NOT_APPLICABLE | Explained informational disposition; not strict failure |

Multiple findings coexist. Scan registered targets and all `content/projects/**/index.md` pages claiming canonical or legacy metadata. Unrelated portfolio pages without a claim are not orphaned. A registered page with deleted source receives a missing-source finding; successful historical lookup cannot conceal absence.

JSON envelope: report version, coverage_complete, absolute roots and HEADs, registry fingerprint, tolerance, dirty summaries, component results (ID, per-target evidence, metadata/freshness states, lifecycle records and normalized backlink results, findings), sorted findings and counts. Findings carry `(component_id, kind, target)` and input fingerprints; unknown pages retain claimed ID/path. Sort by ID/kind/target; diagnostics on stderr. All formats render one result model. Exclude volatile timing fields from deterministic payloads; measure performance separately.

Exit **0**: complete non-strict report, or complete strict report with no actionable finding. Exit **1**: complete strict report with any actionable finding. Exit **2**: usage/configuration/parse/Git failure or incomplete coverage regardless of strictness; takes precedence. Runtime failures after format selection produce structured error output; argparse usage failures may use stderr. Non-strict zero does not mean no findings or accurate prose.

## 6. Capability, Cost and Verification

| Capability | Discovery / scope | Side effects / cost | Output / idempotency | Evidence |
| --- | --- | --- | --- | --- |
| Registry validation | Selected registry/bundled schema | Local reads/imports | Stable diagnostics | Positive/negative fixtures and semantic checks |
| Inventory | Bounded packages, explicit operational/config records, claiming pages | Read-only enumeration | Repeatable findings on fixed inputs | Every approved row and missing/extra cases |
| History diagnostics | Separate roots/SHAs and literal paths | Local Git, no model/network | Per-path heuristic evidence | Independent Git fixtures and varied live sample |
| Metadata/links | Registered/claiming bundles | Safe YAML, no URL requests | Exact projection/local-link diagnostics | Multi-status, package-less, duplicate/unrelated cases |
| Lifecycle references | Explicit specs/plans/status/test paths and normalized backlink sections | Local reads only; never test execution | Deterministic revision/link gaps, no age-based invalidation | Multi-plan/multi-status, historical/superseded, missing-link and no-test-run fixtures |
| Reports | One model, three formats | Stdout only | Stable ordering/completeness | Format parity and all exits |
| M2 edits/build | Explicit website allowlist/build outputs | Website writes, build provisioning separate | Reviewed patch, no duplicate insertion | Diff, YAML, production build, rendered sample |
| Scheduler/steering/repair | Unsupported in this release | Would introduce writes/state | Deferred | Separate design/ingestion contract |

Measure cold/warm wall time, Git process count and inventory size on Windows. Cache/deduplicate per invocation; batch only with fixture evidence of equivalent behavior. Do not add a daemon or weaken checks to meet the 500 ms aspiration. A hook may use workspace diagnostics, but staged-content certification is deferred. CI must pre-provision both full-history checkouts; the checker never clones them.

## 7. Lifecycle, Human Decisions and Deferred Work

Renames retain immutable IDs and update paths. Archival is an explicit lifecycle edit with reason, never inferred from disappearance. Creating a predeclared page needs no registry change solely for existence; changed paths/new status docs/scope changes require a separate outer commit. M2 cannot approve or resolve M3 content tasks.

M1 has no accept/defer/decline store and prompts no human at runtime. Stdout is inspection output, not a hand-edited decision ledger; the package's interactive-Artifact rule does not require a new UI. Future owner decisions must use the established interactive-review convention. Stable finding IDs plus relevant evidence fingerprints must preserve unchanged declines/deferrals and invalidate resolutions after relevant input changes.

Scheduling/steering needs a later design naming execution mechanism/command, roots, measured scan cost, persistent machine state, atomic reports, retries, supported ingestion API and human review surface. No human available means pending findings, never automatic approval or repair. Any repair needs exact selectors, per-target results, all-writer coordination, atomic output and post-run audit before enabling.

## 8. Decisions and Release Gates

Substantive choices remain with Claude/the design author under the repository routing rules. These recommendations are reviewable; this revision does not record approval.

| Decision | Recommendation | Status |
| --- | --- | --- |
| D1 — Scope/policy | 24 components + two overviews; core_env internal; concept_graph required; one component per page; M2 covers 16 existing components + two overviews | Pending design-author decision |
| D2 — Schema/metadata | Stable-ID contract including lifecycle_records, status lifecycle_ids and normalized status/plan backlinks; strict local schema and params.subproject projection; shared component pages deferred | Pending design-author decision |
| D3 — Runtime | Workspace-plus-HEAD diagnostics, explicit website root, safe YAML/local jsonschema, 0/1/2 exits, stdout only, measured latency | Pending design-author decision |

After decisions, follow the plan's requirement-to-evidence gates. Schema validation precedes scanner logic; real-Git fixtures and live samples precede M2; production build/render inspection precede M2 completion. M3 editorial review/publication remain separate. This design claims no implemented scanner, passing fixtures, successful live run or deployed behavior.
