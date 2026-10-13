# Website sync M1 implementation status — 2026-10-11

**Current status (2026-10-13):** M1–M3 implementation and T6a are landed.
The seven new Academic Hub pages are public on website `main` at `88124e4`,
and that revision's GitHub Pages deployment succeeded. The latest strict audit
has complete coverage and zero errors. A readability review covered 28 project
pages and 10 blog posts; substantive prose revisions remain editorial work.
The M1 evidence and the M1–M3 closeout below record their historical gates.

The M1 checker landed on monorepo `main` at
`03ff76abe90b746f817d1ed4707a7980ac989a37`. Its G2 verification
subsequently landed at `106f1c8cd05fab6a4264bac3dcc7d36fd9d43399`.
This record does not certify website prose, repair pages, or close the M2/M3
backlog.

The implemented checker itself is a new inventory item, separate from the
26-record historical registry baseline: `tools/audit_website_sync.py` is the
CLI and local Git evidence layer, `tools/website_sync_scan.py` is the finding
engine, and `tools/website_sync_registry.py` loads the registry. Its website
publication policy has not been decided, so no page or registry component was
invented for it during G2.

Lifecycle sources: [design](../../../brainstorms/specs/2026-10-10-subproject-website-sync-design.md),
[plan](../../../brainstorms/specs/2026-10-10-subproject-website-sync-plan.md),
[scanner fixtures](../../../../tests/tools/test_website_sync_scan.py),
[Git fixtures](../../../../tests/tools/test_audit_website_sync_git.py), and
[registry fixtures](../../../../tests/tools/test_audit_website_sync.py).

## Evidence and limits

The Task 3 handoff reported 52 focused tests passing and a full landing suite
passing in 406.6 seconds. A live read-only strict scan of the separate
repositories returned 1 with expected structural blockers. Those are prior
handoff results, not a new G2 full-suite result.

G2's added local fixtures pass for metadata-only page commits, partial
staging, archived source paths, lifecycle ID projection, nonexecution of
referenced tests, nonmonotonic commit clocks, Git timeouts, and unchanged
repository bytes during a complete scan. The no-write fixture compares all
files including `.git` before and after; it denies Python socket connections,
routes any child HTTP transport to a closed local proxy, restricts child Git
to read-only subcommands, and asserts `GIT_NO_LAZY_FETCH=1` and
`GIT_OPTIONAL_LOCKS=0`. A real partial-clone fixture with a missing blob and
an unavailable promisor transport also fails incomplete with lazy fetching
disabled. Together these check Python calls, the permitted child Git commands,
child HTTP transport, and the missing-object path. They do not use a global
firewall rule. The combined registry/Git/scanner fixture command passed 60
tests in 169.67 seconds before five additional targeted fixtures passed.
The full repository suite then passed 3,459 tests and 34 subtests in 553.49
seconds, before the final routine-edit and renamed-historical-status fixtures
were added; both passed in targeted runs. The landing check will rerun the
suite on the final commit.

The live scan selected monorepo
`03ff76abe90b746f817d1ed4707a7980ac989a37` at
`C:\Users\theaa\ai-sandbox-master\.worktrees\codex-website-sync-m1-g2`
and website `ebc836ad2dccfc357d57d4504a00bc4dd75a07bb` at
`C:\Users\theaa\ai-sandbox-master\ai-sandbox\personal-website\AaronScherf.github.io`.
Both selected checkouts had no relevant dirty inputs. The registry held 26
records. Coverage was complete: 41 errors, 102 warnings and 3 informational
findings. The errors were 34 metadata mismatches and seven approved missing
pages. The warnings included 82 absent normalized lifecycle sections, 12
status history gaps and eight website history gaps. The lifecycle backlog is
enumerated for T6a; a zero-gap result is not an M1 acceptance condition.

Cold and warm in-process scans took 44.078 and 38.113 seconds, respectively,
with 265 child Git processes each. These are measurements on Windows with Git
2.45.1 and Python 3.13.7, using PyYAML 6.0.3 and jsonschema 4.26.0.
They do not establish a sub-second latency expectation. The dependency versions
were loaded from a local ignored dependency directory for focused tests;
no dependency change is part of this status record.

The documented PowerShell wrapper was invoked from the worktree root, outside
the package directory. It restored the caller's directory and returned strict
exit 1 with complete coverage and 146 findings, as expected for the current
metadata and missing-page backlog.

A varied read-only sample checked Source Indexer, Textbook Conversion,
Post-Processing, Video Notes, Study Guide, Guided Solutions, Tutor Diagnosis,
and Obsidian Git Sync. Direct file checks found all 16 referenced status files
present and none with a normalized `Lifecycle references` section. The two
planned Study Guide and Guided Solutions pages were absent. Source Indexer,
Textbook, Video Notes, Tutor Diagnosis and Obsidian pages existed; sampled
frontmatter lacked the canonical `params.subproject` projection, and sampled
links supported the reported missing/generic-link category. Direct Git history
confirmed a textbook source/status gap of 381,236 seconds and an Obsidian
source/status gap of 680,899 seconds. No discrepancy was found in this sample.
Git timestamps remain heuristic; a metadata-only page commit can clear the
history warning while leaving page prose stale, as a fixture now demonstrates.

## G2 landing gate and outcome

The full landing check passed on the final Task 4 commit at `106f1c8`,
running `tests/` in 906.5 seconds. The fixture set covers the specified local Git, lifecycle,
missing-history, source/page and exit-policy boundaries; its read-only and
offline evidence is described above.
At this M1 gate, the live global `--strict` result was expected to remain 1
until M2 metadata and M3 missing-page work. The owner accepted the concrete
registry/report and requested M2 website edits on 2026-10-11; later outcomes
are recorded below and in the implementation plan.

## M1–M3 implementation closeout (2026-10-12)

The delivered workflow is a **read-only local audit** of a canonical 26-entry
registry against independently pinned monorepo and website checkouts, followed
by separately reviewed website and source-document edits. It checks path
coverage, website metadata and visible links, lifecycle references, and Git
history. It does not synchronize prose automatically, certify semantic
accuracy, publish drafts, run referenced tests, or schedule unattended work.

- **M1 verification:** The registry, Draft 2020-12 schema, local Git evidence,
  deterministic reports and scanner landed through `106f1c8`. G2's 60 focused
  fixtures and the full landing suite passed; the M1 live sample and denied-
  network/no-write checks are recorded above. The owner accepted this gate
  before website edits. Those tests establish checker behavior, not page prose.
- **M2 website alignment:** Website `4e4d710` added canonical metadata and
  visible source/status links to 16 existing component pages and two overviews,
  including five corrected source URLs. An idempotent second pass, generated
  HTML/link checks and a production build passed. The deployment and a live
  Source Indexer page check succeeded; no page-body or publication fields were
  changed in this batch.
- **M3 content and status:** Website `a669436` added seven pages—Socratic
  Tutor, Study Guide, Summary Enhancement, Corpus Health, Project Steering,
  Guided Solutions and Concept Graph—with `draft: true`. Website `015954a`
  refreshed Source Indexer, Notes Transcription, RAG Analysis and Academic Hub
  overview. Monorepo `872cbbe` landed paired Summary Enhancement and Notes
  Transcription status updates. The website's production build and deployment
  succeeded at `015954a`; the drafts were absent from production output. These
  were source-backed editorial checks, not new live runs of those pipelines.
- **T6a lifecycle backfill:** Monorepo `11c184d` landed normalized references
  or explicit registry absence reasons in 36 status documents and 45 plans.
  Each of the 81 files retained its original bytes with only an appended
  section. The doc-only landing check passed; it skipped the test suite under
  the repository's Markdown-only rule.

The final clean read-only command, `python -B -m tools.audit_website_sync
--website-root <website-checkout> --format json --strict`, ran at monorepo
`11c184d` and website `015954a`. It exited **0** with complete coverage,
**zero errors**, **32 warnings**, and **three informational findings**. The
warnings are all `WEBSITE_HISTORY_GAP`: recently committed status documents
are newer than their website pages. They are timestamp prompts for editorial
review, not evidence that prose is inaccurate. There are no remaining
`LIFECYCLE_BACKFILL_PENDING` or `LIFECYCLE_BACKLINK_MISMATCH` findings. The
website deployment workflow for `015954a` completed successfully; this is
deployment evidence, not evidence of ongoing content synchronization.

**At this closeout:** The seven pages were still drafts. The 32 heuristic
history warnings were nonblocking editorial prompts. The local one-command
`pnpm run build` PATH/lockfile drift, any future scheduler, repair action,
and automated content sync were deferred; none was required for M1–M3.
No new pipeline run or longitudinal behavior was established by this closeout.

## Publication and readability review (2026-10-13)

Website `88124e4` changed the seven M3 pages to `draft: false` and updated
the Academic Hub overview to link to them as published pages. A site-wide
review of 28 substantive project pages and 10 substantive blog posts removed
26 unused image-generation prompts from frontmatter, 19 redundant `Figure:`
lines, and one reference to an earlier status narrative. Nine HugoBlox example
pages remain drafts. The review ranked pages for later nontechnical prose
revision; it did not rewrite the long implementation narratives or certify
every page's factual accuracy.

Hugo Extended 0.163.3 built 119 production pages locally. Generated output
included all seven newly public pages and excluded the example drafts. The
GitHub Pages workflow for `88124e4` built and deployed successfully. A clean
strict registry audit at monorepo `11c184d` and website `88124e4` exited 0
with complete coverage, zero errors, three nonblocking website-history
warnings, and three informational findings. This is publication and metadata
evidence, not a new run of the underlying study or research pipelines.

**Editorial follow-up:** Revise the most technical pages for nontechnical
readers, starting with Notes Transcription, Marker PDF Conversion, Resume
Manager, Visualization Sub-Agent, and Source Indexer. The deferred build-tool
PATH/lockfile issue and unattended sync/repair capabilities remain separate
work; neither blocks the published pages.
