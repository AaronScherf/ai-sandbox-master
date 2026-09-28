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


def validate_tailored(master: dict, tailored: dict) -> list[str]:
    """Returns a list of human-readable warnings; empty means nothing was
    flagged.

    Takes the already-reconstructed `tailored` resume (apply_tailoring's
    output), not tailor_resume()'s raw LLM response -- validates whatever
    actually made it into the final output, which since Revision 6 (spec
    §13b) is only the top `include_count` of tailor_resume()'s full
    `ranked_ids` candidate list, decided by tailor_resume.py's
    render-measure-retry fill loop. Checking the raw LLM response instead
    would validate entries that never made it into the rendered PDF at
    all. This also decouples validate.py from tailor.py's exact response
    field names (`ranked_ids`/`bullets_by_id`) entirely -- it only needs
    an id and its bullets, which `tailored["work_experience"]` already
    has spliced in.

    No longer separately flags an unresolvable id: apply_tailoring
    already guarantees every entry in `tailored["work_experience"]` has a
    real master source (an id it couldn't resolve is skipped and reported
    in apply_tailoring's own return value, which tailor_resume.py already
    merges with this function's problems) -- so by the time this function
    sees `tailored`, that check has nothing left to catch."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    problems: list[str] = []
    openings: dict[str, int] = {}
    for entry in tailored.get("work_experience") or []:
        entry_id = entry["id"]
        source = master_by_id.get(entry_id) or {}
        original_text = "\n".join(source.get("bullets") or [])
        rewritten_bullets = entry.get("bullets") or []
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
