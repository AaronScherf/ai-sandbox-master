# Website sync M1 implementation status — 2026-10-11

The M1 checker landed on monorepo `main` at
`03ff76abe90b746f817d1ed4707a7980ac989a37`. Its G2 verification is
being completed in `codex/website-sync-m1-g2`; this record
does not certify website prose, repair pages, or close the M2/M3 backlog.

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

## G2 landing gate

The remaining automated gate is the full landing check on the final Task 4
commit. The fixture set now covers the specified local Git, lifecycle,
missing-history, source/page and exit-policy boundaries; its read-only and
offline evidence is described above.
The live global `--strict` result is expected to remain 1 until M2 metadata
and M3 missing-page work. Do not install a global strict hook before those
blockers are resolved. User review of the concrete registry and report remains
the gate before website edits.
