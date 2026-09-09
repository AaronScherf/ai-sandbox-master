"""
validate.py
Automated fact-diff (spec §5): flags anything in a tailored resume
that doesn't trace back to the master resume -- never blocks
rendering.
"""
from __future__ import annotations

from resume_manager.fact_diff import entries_not_traceable, metrics_not_traceable


def validate_tailored(master_resume: str, tailored_resume: str) -> list[str]:
    """Returns a list of human-readable warnings; empty means nothing
    was flagged. Only checks the tailored-output direction -- a
    tailored resume dropping a master entry is expected behavior and
    never flagged (spec §5)."""
    problems = []
    for entry in entries_not_traceable(tailored_resume, master_resume):
        problems.append(
            f"possible fabricated entry: '{entry.org} — {entry.role} ({entry.dates})' "
            f"not found in the master resume"
        )
    for metric in metrics_not_traceable(tailored_resume, master_resume):
        problems.append(f"possible invented metric: '{metric}' not found in the master resume")
    return problems


def format_report(problems: list[str]) -> str:
    if not problems:
        return "Validation: no discrepancies flagged."
    lines = [f"Validation flagged {len(problems)} possible issue(s) -- review before submitting:"]
    lines.extend(f"- {p}" for p in problems)
    return "\n".join(lines)
