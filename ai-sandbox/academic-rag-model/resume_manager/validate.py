"""
validate.py
Per-entry bullet-metric fact-diff (spec §5 Revision 2): flags any metric
token in a rewritten bullet that isn't traceable to that SAME entry's
original bullets -- narrower and stronger than v1's whole-document check,
made possible by knowing exactly which master entry a rewritten bullet
came from. Never blocks rendering.

Bidirectional as of the first real tailoring run (2026-09-09): the
original design only checked the invented direction. That run's rewrite
compressed three bullets into two and lost every one of their $ figures
along the way ($1.5M, $450M, $5Bn) -- not a fabrication, but a real
quality loss the invented-only check couldn't see. Now also flags a
metric present in the original bullets that doesn't survive into ANY
rewritten bullet for that entry (checked against all of them jointly, so
splitting one bullet's content across two rewritten bullets doesn't
falsely look like a drop).

Also flags a repeated bullet-opening phrase across the WHOLE tailored
resume (spec: 2026-09-09 status doc §11) -- the same real run's rewrite
opened two different roles' first bullet with the near-identical
"Researches, analyzes, consolidates, and presents information..." (an
echo of the job description's own repeated phrasing, not a fabrication
or a dropped fact, but real quality loss the metric checks above have no
way to see).
"""
from __future__ import annotations

from resume_manager.fact_diff import metrics_not_traceable

_OPENING_WORD_COUNT = 6


def _opening_phrase(bullet: str) -> str:
    words = bullet.split()[:_OPENING_WORD_COUNT]
    return " ".join(words).lower()


def validate_tailored(master: dict, tailoring_result: dict) -> list[str]:
    """Returns a list of human-readable warnings; empty means nothing was
    flagged. Also flags any included id absent from the master -- should
    be structurally impossible given tailor.apply_tailoring's own
    skip-and-report behavior, but checked here too so a report is never
    silently missing an issue apply_tailoring already knows about."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    bullets_by_id = tailoring_result.get("bullets_by_id") or {}
    problems: list[str] = []
    openings: dict[str, int] = {}
    for entry_id in tailoring_result.get("included_ids") or []:
        source = master_by_id.get(entry_id)
        if source is None:
            problems.append(f"included id '{entry_id}' not found in master resume")
            continue
        original_text = "\n".join(source.get("bullets") or [])
        rewritten_bullets = bullets_by_id.get(entry_id) or []
        rewritten_text = "\n".join(rewritten_bullets)
        for metric in metrics_not_traceable(rewritten_text, original_text):
            problems.append(f"{entry_id}: possible invented metric '{metric}' not found in original bullets")
        for metric in metrics_not_traceable(original_text, rewritten_text):
            problems.append(f"{entry_id}: possible dropped metric '{metric}' from original bullets not found in rewritten bullets")
        for bullet in rewritten_bullets:
            opening = _opening_phrase(bullet)
            if len(opening.split()) == _OPENING_WORD_COUNT:
                openings[opening] = openings.get(opening, 0) + 1

    for opening, count in openings.items():
        if count > 1:
            problems.append(
                f"repeated bullet opening: {count} bullets start with \"{opening}...\" -- vary the phrasing"
            )
    return problems


def format_report(problems: list[str]) -> str:
    if not problems:
        return "Validation: no discrepancies flagged."
    lines = [f"Validation flagged {len(problems)} possible issue(s) -- review before submitting:"]
    lines.extend(f"- {p}" for p in problems)
    return "\n".join(lines)
