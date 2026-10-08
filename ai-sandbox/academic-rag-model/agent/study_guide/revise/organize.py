# agent/study_guide/revise/organize.py
"""Heading hierarchy and order: mechanical fixes plus one outline-only model call."""
from __future__ import annotations

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.segment import Block

ORGANIZE_SCHEMA = {
    "type": "object",
    "properties": {"edits": {"type": "array", "items": {
        "type": "object",
        "properties": {"type": {"type": "string", "enum": ["retitle", "move"]}, "block": {"type": "string"},
                       "new_heading": {"type": ["string", "null"]}, "after": {"type": ["string", "null"]},
                       "rationale": {"type": "string"}},
        "required": ["type", "block", "rationale"]}}},
    "required": ["edits"],
}


def mechanical_heading_edits(blocks: list[Block], start: int = 1) -> list[Edit]:
    edits, n, seen_h1 = [], start, False
    for b in blocks:
        if b.level == 1:
            if seen_h1:
                edits.append(Edit(id=f"org-{n:03d}", type="retitle", stage="organization", targets=[b.id],
                                  rationale="a second H1 swallows the sections after it; demote it to H2",
                                  severity="medium", confidence=0.9, replacement="## " + b.heading_path[-1]))
                n += 1
            seen_h1 = True
    return edits


def build_outline(blocks: list[Block], flags: dict[str, list[str]]) -> str:
    rows = []
    for b in blocks:
        if not b.level:
            continue
        tags = f"  [{', '.join(flags[b.id])}]" if flags.get(b.id) else ""
        rows.append(f"{b.id} | H{b.level} | {'  ' * (b.level - 1)}{b.heading_path[-1]} | {b.words} words{tags}")
    return (
        "Below is the heading outline of a study guide (no body text). Propose only changes that improve the "
        "hierarchy and order: 'retitle' (consistent, specific titles; give 'new_heading' text without #) or "
        "'move' (place a block after another block with 'after'). Do not propose deletions or content changes. "
        "Return JSON {\"edits\": [{\"type\", \"block\", \"new_heading\", \"after\", \"rationale\"}]}; an empty "
        "list is fine.\n\n" + "\n".join(rows) + "\n")


def parse_organize(data: dict, blocks_by_id: dict[str, Block], start: int) -> list[Edit]:
    edits, n = [], start
    for e in data.get("edits", []):
        kind, block = e.get("type"), blocks_by_id.get(e.get("block"))
        if block is None:
            raise ReviseError(f"organize: unknown block {e.get('block')!r}")
        if kind == "retitle":
            if not e.get("new_heading"):
                raise ReviseError(f"organize: retitle of {block.id} needs new_heading")
            edit = Edit(id=f"org-{n:03d}", type="retitle", stage="organization", targets=[block.id],
                        rationale=e.get("rationale", ""), severity="low", confidence=0.5,
                        replacement="#" * block.level + " " + e["new_heading"].lstrip("# ").strip())
        elif kind == "move":
            if e.get("after") not in blocks_by_id:
                raise ReviseError(f"organize: move of {block.id} names an unknown anchor {e.get('after')!r}")
            edit = Edit(id=f"org-{n:03d}", type="move", stage="organization", targets=[block.id],
                        rationale=e.get("rationale", ""), severity="low", confidence=0.5, anchor=e["after"])
        else:
            raise ReviseError(f"organize: unknown edit type {kind!r}")
        edits.append(edit)
        n += 1
    return edits


def organize_edits(llm, blocks: list[Block], flags: dict[str, list[str]], start: int = 1) -> list[Edit]:
    edits = mechanical_heading_edits(blocks, start)
    data = llm.generate_structured(build_outline(blocks, flags), ORGANIZE_SCHEMA)
    return edits + parse_organize(data, {b.id: b for b in blocks}, start + len(edits))
