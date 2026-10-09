# agent/study_guide/revise/audit.py
"""Correctness audit of one guide section against that section's own source passages."""
from __future__ import annotations

import json
import re

from agent.study_guide.revise.edits import Edit
from agent.study_guide.revise.segment import Block

AUDIT_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"block": {"type": "string"}, "quote": {"type": "string"},
                       "verdict": {"type": "string", "enum": ["unsupported", "contradicted", "arithmetic_error"]},
                       "explanation": {"type": "string"}, "source_label": {"type": ["string", "null"]},
                       "replacement": {"type": ["string", "null"]}},
        "required": ["block", "quote", "verdict", "explanation"]}}},
    "required": ["findings"],
}
_WORKED_RE = re.compile(r"problem|worked|step-by-step|example", re.I)


def build_audit_prompt(title: str, blocks: list[Block], passages: list[tuple[str, str, str]]) -> str:
    text = "\n\n".join(f"[{b.id}] {' > '.join(b.heading_path)}\n\"\"\"\n{b.text}\n\"\"\"" for b in blocks)
    sources = "\n\n".join(f"[{label}] {citation}\n\"\"\"\n{body}\n\"\"\"" for label, citation, body in passages)
    return (
        f"You are auditing the section \"{title}\" of a study guide against the source passages below. For each "
        "claim, equation or number in the section that is NOT supported by the passages, or that a passage "
        "contradicts, or that is arithmetically wrong, report a finding. A 'Constructed example (not from the "
        "sources)' is allowed to have no source, but its arithmetic must be right. Rules: 'quote' must be copied "
        "exactly from one block and occur once in it; give 'replacement' (the corrected text for that quote, "
        "supported by a passage) only when a passage supports the correction, and name that passage's label in "
        "'source_label'; otherwise leave 'replacement' null. Do not report style problems. Return JSON "
        "{\"findings\": [...]} (empty list if the section is sound).\n\n"
        f"=== SECTION BLOCKS ===\n{text}\n\n=== SOURCE PASSAGES ===\n{sources}\n")


def parse_audit(data: dict, blocks_by_id: dict[str, Block], labels: set[str], start: int) -> tuple[list[Edit], list[str]]:
    edits, problems, n = [], [], start
    for f in data.get("findings", []):
        block = blocks_by_id.get(f.get("block"))
        quote, label, replacement = f.get("quote", ""), f.get("source_label"), f.get("replacement")
        if block is None:
            problems.append(f"finding names an unknown block {f.get('block')!r}")
        elif block.text.count(quote) != 1 or not quote:
            problems.append(f"{block.id}: the quote is absent or not unique: {quote[:60]!r}")
        elif f.get("verdict") == "contradicted" and label not in labels:
            problems.append(f"{block.id}: the contradicting source {label!r} is not one of this section's passages")
        else:
            fixed = bool(replacement)
            edits.append(Edit(
                id=f"cor-{n:03d}", type="fix" if fixed else "note", stage="correctness", targets=[block.id],
                rationale=f"{f['verdict']}: {f['explanation']}", evidence=[label] if label else [],
                severity="high" if f["verdict"] != "unsupported" else "medium", confidence=0.6,
                replacement=replacement if fixed else None, quote=quote if fixed else None))
            n += 1
    return edits, problems


# A line states a computed result when an operator, fraction or root sits left of an "=" or "≈" that is followed by a number.
_RESULT_RE = re.compile(r"(?:=|≈|\\approx)\s*[-−]?\s*\d")
_OPERATION_RE = re.compile(r"\d\s*(?:[/*×+−^]|\\times|\\cdot|-\s*\d)|\\frac|\\sqrt")


def states_a_computed_result(text: str) -> bool:
    for line in text.splitlines():
        if any(_OPERATION_RE.search(line[:m.start()]) for m in _RESULT_RE.finditer(line)):
            return True
    return False


def needs_arithmetic_check(block: Block) -> bool:
    """Only a worked or constructed block that shows a calculation is rechecked in code (each recheck costs a call)."""
    worked = block.constructed or bool(_WORKED_RE.search(block.heading_path[-1] if block.heading_path else ""))
    return worked and states_a_computed_result(block.text)


def build_arith_prompt(block: Block) -> str:
    return (
        "Recompute every numerical result stated in the text below using Python (use the code tool). Reply with "
        "ONLY a JSON list of objects {\"quote\": <the stated result, copied>, \"computed\": <your value>, "
        "\"ok\": <true if the stated result matches to the precision shown>}.\n\n" + block.text + "\n")


def parse_arith(text: str, block: Block, start: int) -> list[Edit]:
    m = re.search(r"\[.*\]", text, re.S)
    try:
        rows = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        return []
    edits, n = [], start
    for r in rows:
        if isinstance(r, dict) and r.get("ok") is False:
            edits.append(Edit(
                id=f"cor-{n:03d}", type="note", stage="correctness", targets=[block.id], severity="high", confidence=0.7,
                rationale=f"arithmetic does not check: stated {r.get('quote', '')!r}, computed {r.get('computed', '')!r}"))
            n += 1
    return edits


def audit_section(llm, title: str, blocks: list[Block], passages: list[tuple[str, str, str]],
                  start: int = 1) -> tuple[list[Edit], list[str]]:
    data = llm.generate_structured(build_audit_prompt(title, blocks, passages), AUDIT_SCHEMA)
    edits, problems = parse_audit(data, {b.id: b for b in blocks}, {p[0] for p in passages}, start)
    for b in blocks:
        if needs_arithmetic_check(b):
            edits += parse_arith(llm.generate_text(build_arith_prompt(b), code_execution=True), b, start + len(edits))
    return edits, problems
