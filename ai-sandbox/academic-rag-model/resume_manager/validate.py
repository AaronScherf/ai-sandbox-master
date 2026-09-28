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

import re

from rapidfuzz import fuzz

from resume_manager.fact_diff import metrics_not_traceable

_OPENING_WORD_COUNT = 6
_BULLET_DUPLICATE_THRESHOLD = 80
_RESPONSIBILITY_VERBS = {
    "administered", "built", "coordinated", "directed", "established", "implemented", "led",
    "managed", "owned", "oversaw", "supervised",
}


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = _normalized(phrase)
    if not normalized_phrase:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(normalized_phrase).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _fact_concepts_missing(fact: dict, bullets: list[str]) -> list[str]:
    """Return required concept groups not found in an entry's final bullets.

    Each group is a list of acceptable phrases. All groups must be covered;
    a group may provide synonyms for natural paraphrases.
    """
    text = _normalized(" ".join(bullets))
    missing = []
    for alternatives in fact.get("required_concepts") or []:
        if not any(_contains_phrase(text, phrase) for phrase in alternatives):
            missing.append(" / ".join(alternatives))
    return missing


def _opening_phrase(bullet: str) -> str:
    words = bullet.split()[:_OPENING_WORD_COUNT]
    return " ".join(words).lower()


def validate_tailored(master: dict, tailored: dict, user_facts: list[dict] | None = None) -> list[str]:
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
    tailored_by_id = {e["id"]: e for e in tailored.get("work_experience") or []}
    problems: list[str] = []
    openings: dict[str, int] = {}
    for entry in tailored.get("work_experience") or []:
        entry_id = entry["id"]
        source = master_by_id.get(entry_id) or {}
        original_text = "\n".join(source.get("bullets") or [])
        rewritten_bullets = entry.get("bullets") or []
        rewritten_text = "\n".join(rewritten_bullets)
        entry_facts = [f for f in (user_facts or []) if f.get("entry_id") == entry_id]
        fact_text = "\n".join(f.get("fact", "") for f in entry_facts)
        supported_text = "\n".join(part for part in (original_text, fact_text) if part)
        for metric in metrics_not_traceable(rewritten_text, supported_text):
            problems.append(f"[metrics] {entry_id}: possible invented metric '{metric}' not found in original bullets")
        for metric in metrics_not_traceable(original_text, rewritten_text):
            problems.append(f"[metrics] {entry_id}: possible dropped metric '{metric}' from original bullets not found in rewritten bullets")
        for index, bullet in enumerate(rewritten_bullets):
            for other in rewritten_bullets[index + 1:]:
                similarity = fuzz.ratio(bullet, other)
                if similarity >= _BULLET_DUPLICATE_THRESHOLD:
                    problems.append(
                        f"[duplicate bullets] {entry_id}: bullets are {similarity:.2f}% similar; review for redundancy"
                    )
        for index, bullet in enumerate(rewritten_bullets):
            leading = re.match(r"\s*([a-z]+)\b", bullet, re.IGNORECASE)
            supported_verbs = {
                match.group(1).lower()
                for match in re.finditer(r"(?i)\b([a-z]+)\b", original_text + " " + fact_text)
            }
            if leading and leading.group(1).lower() in _RESPONSIBILITY_VERBS and leading.group(1).lower() not in supported_verbs:
                problems.append(
                    f"[responsibility wording] {entry_id}: leading verb '{leading.group(1)}' is not explicit in the source bullets or tagged facts; review"
                )
        for bullet in rewritten_bullets:
            opening = _opening_phrase(bullet)
            if len(opening.split()) == _OPENING_WORD_COUNT:
                openings[opening] = openings.get(opening, 0) + 1

    for opening, count in openings.items():
        if count > 1:
            problems.append(
                f"[repeated openings] repeated bullet opening: {count} bullets start with \"{opening}...\" -- vary the phrasing"
            )
    for fact in user_facts or []:
        entry_id = fact["entry_id"]
        entry = tailored_by_id.get(entry_id)
        bullets = entry.get("bullets") or [] if entry else []
        missing = _fact_concepts_missing(fact, bullets)
        if missing:
            problems.append(
                f"[user fact coverage] {entry_id}: user-provided fact not fully reflected; missing concepts: "
                + "; ".join(missing)
            )
    return problems


def format_report(problems: list[str], brainstorm_status: str = "not used") -> str:
    lines = [f"Relevance brainstorm: {brainstorm_status}."]
    if not problems:
        return "\n".join([*lines, "Validation: no discrepancies flagged."])
    lines.append(f"Validation flagged {len(problems)} possible issue(s) -- review before submitting:")
    labels = {
        "[metrics]": "Numeric traceability",
        "[user fact coverage]": "User-provided fact coverage",
        "[duplicate bullets]": "Possible duplicate bullets",
        "[responsibility wording]": "Responsibility wording review",
        "[repeated openings]": "Repeated bullet openings",
        "[reconstruction]": "Reconstruction",
    }
    grouped: dict[str, list[str]] = {}
    for problem in problems:
        category = next((label for prefix, label in labels.items() if problem.startswith(prefix)), "Other review items")
        grouped.setdefault(category, []).append(problem.split("] ", 1)[-1])
    for category, items in grouped.items():
        lines.append(f"\n{category}:")
        lines.extend(f"- {item}" for item in items)
    return "\n".join(lines)
