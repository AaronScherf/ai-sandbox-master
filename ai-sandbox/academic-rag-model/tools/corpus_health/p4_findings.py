"""Hub-path-resilience P4 findings shared by `scan` and `apply`.

Both commands end in `store.refresh`, whose default sweep vanishes every kind it was not given. These
kinds are produced here, so both callers add them first and pass `skipped_kinds(...)` as the refresh's
`exclude_kinds`: a producer that did not run (no hub, failure) must not vanish its pending entries.
"""
from __future__ import annotations

P4_KINDS = frozenset({"duplicate_hub_id", "vocab_name"})


def add_p4_findings(report, config) -> set[str]:
    """Extend `report.findings` with duplicate-hub_id and new-folder-name findings (read only).
    Returns the kinds whose producer ran; a failure is a warning, never an error."""
    ran: set[str] = set()
    if not config.academic_hub_root.is_dir():
        return ran
    hub_root = str(config.academic_hub_root)
    try:
        from tools.corpus_health.duplicates import duplicate_findings
        report.findings.extend(duplicate_findings(hub_root))
        ran.add("duplicate_hub_id")
    except Exception as exc:  # noqa: BLE001 - infra failures must not break the scan
        report.warnings.append(f"duplicate hub_id check skipped: {exc}")
    try:
        from tools.corpus_health.vocab import vocab_findings
        report.findings.extend(vocab_findings(hub_root))
        ran.add("vocab_name")
    except Exception as exc:  # noqa: BLE001 - infra failures must not break the scan
        report.warnings.append(f"vocabulary check skipped: {exc}")
    return ran


def skipped_kinds(ran: set[str]) -> frozenset[str]:
    return P4_KINDS - ran
