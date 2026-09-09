"""
validate.py
Per-entry bullet-metric fact-diff (spec §5 Revision 2): flags any metric
token in a rewritten bullet that isn't traceable to that SAME entry's
original bullets -- narrower and stronger than v1's whole-document check,
made possible by knowing exactly which master entry a rewritten bullet
came from. Never blocks rendering.
"""
from __future__ import annotations

from resume_manager.fact_diff import metrics_not_traceable


def validate_tailored(master: dict, tailoring_result: dict) -> list[str]:
    """Returns a list of human-readable warnings; empty means nothing was
    flagged. Also flags any included id absent from the master -- should
    be structurally impossible given tailor.apply_tailoring's own
    skip-and-report behavior, but checked here too so a report is never
    silently missing an issue apply_tailoring already knows about."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    bullets_by_id = tailoring_result.get("bullets_by_id") or {}
    problems: list[str] = []
    for entry_id in tailoring_result.get("included_ids") or []:
        source = master_by_id.get(entry_id)
        if source is None:
            problems.append(f"included id '{entry_id}' not found in master resume")
            continue
        original_text = "\n".join(source.get("bullets") or [])
        rewritten_text = "\n".join(bullets_by_id.get(entry_id) or [])
        for metric in metrics_not_traceable(rewritten_text, original_text):
            problems.append(f"{entry_id}: possible invented metric '{metric}' not found in original bullets")
    return problems


def format_report(problems: list[str]) -> str:
    if not problems:
        return "Validation: no discrepancies flagged."
    lines = [f"Validation flagged {len(problems)} possible issue(s) -- review before submitting:"]
    lines.extend(f"- {p}" for p in problems)
    return "\n".join(lines)
