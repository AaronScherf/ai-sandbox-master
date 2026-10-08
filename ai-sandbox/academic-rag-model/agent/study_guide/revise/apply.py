# agent/study_guide/revise/apply.py
"""Apply accepted edits by block id, then check post-conditions. No model call."""
from __future__ import annotations

import re

from agent.study_guide.revise.edits import Edit, EditReport, ReviseError
from agent.study_guide.revise.segment import Block, check_headings, segment

_PAGE_CITE_RE = re.compile(r"\bpp?\.\s?\d+")


def _trailing_blanks(lines: list[str]) -> int:
    n = 0
    while n < len(lines) and not lines[-1 - n]:
        n += 1
    return n


def _replace_block(block: Block, lines: list[str], text: str) -> list[str]:
    return text.split("\n") + [""] * _trailing_blanks(lines[block.start:block.end])


def _retitled(block: Block, heading: str, edit_id: str = "") -> str:
    if "\n" in heading.strip():
        raise ReviseError(f"{edit_id}: a retitle replacement must be a single heading line")
    return "\n".join([heading] + block.text.split("\n")[1:])


def _fixed(block: Block, edit: Edit) -> str:
    if edit.quote is None:
        return edit.replacement or ""
    if block.text.count(edit.quote) != 1:
        raise ReviseError(f"{edit.id}: the quote must occur exactly once in its block")
    return block.text.replace(edit.quote, edit.replacement or "", 1)


def apply_edits(body: str, report: EditReport, accepted: set[str]) -> str:
    by_id = {e.id: e for e in report.edits}
    unknown = sorted(accepted - set(by_id))
    if unknown:
        raise ReviseError(f"unknown edit id(s): {', '.join(unknown)}")
    selected = [by_id[i] for i in sorted(accepted) if by_id[i].type != "note"]
    owner: dict[str, str] = {}
    for e in selected:
        for t in e.targets:
            if t in owner:
                raise ReviseError(f"{owner[t]} and {e.id} edit the same block ({t}); accept only one")
            owner[t] = e.id
    blocks = segment(body)
    lines = body.split("\n")
    known = {b.id: b for b in blocks}
    for e in selected:
        for t in e.targets + ([e.anchor] if e.anchor else []):
            if t not in known:
                raise ReviseError(f"{e.id}: block {t} is not in this guide")
    delete, replace, moved = set(), {}, {}
    for e in selected:
        first = known[e.targets[0]]
        if e.type == "delete":
            delete.update(e.targets)
        elif e.type in ("shrink", "link"):
            replace[first.id] = e.replacement or ""
        elif e.type == "retitle":
            replace[first.id] = _retitled(first, e.replacement or "", e.id)
        elif e.type == "fix":
            replace[first.id] = _fixed(first, e)
        elif e.type == "merge":
            replace[first.id] = e.replacement or ""
            delete.update(e.targets[1:])
        elif e.type == "move":
            if e.anchor in delete:
                raise ReviseError(f"{e.id}: the anchor block is deleted by another edit")
            moved.setdefault(e.anchor, []).append(first.id)
    moving = {i for ids in moved.values() for i in ids}
    out: list[str] = []
    for b in blocks:
        if b.id in delete or b.id in moving:
            continue
        out += _replace_block(b, lines, replace[b.id]) if b.id in replace else lines[b.start:b.end]
        for mid in moved.get(b.id, []):
            m = known[mid]
            if out and out[-1]:
                out.append("")
            out += lines[m.start:m.end]
    after = "\n".join(out)
    _check_postconditions(body, after, blocks, selected, set(owner), moving)
    return after


def _check_postconditions(before: str, after: str, blocks: list[Block], selected: list[Edit],
                          touched: set[str], moving: set[str]) -> None:
    problems = []
    allowed = sum(len((e.replacement or "").split()) for e in selected if e.type in ("fix", "retitle"))
    if len(after.split()) > len(before.split()) + allowed:
        problems.append("the revised guide is longer than the original")
    if len(_PAGE_CITE_RE.findall(after)) > len(_PAGE_CITE_RE.findall(before)):
        problems.append("the edits introduce a new page citation")
    new_heading = sorted(set(check_headings(after)) - set(check_headings(before)))
    if new_heading:
        problems.append("the edits introduce heading problems: " + "; ".join(new_heading))
    for b in blocks:
        if b.id not in touched and b.id not in moving and b.text not in after:
            problems.append(f"block {b.id} changed without an accepted edit")
    if problems:
        raise ReviseError("post-condition failed, nothing written: " + " | ".join(problems))


def changelog(report: EditReport, accepted: set[str]) -> str:
    rows = ["# Revision changelog", ""]
    for e in report.edits:
        if e.id not in accepted:
            continue
        verb = "acknowledged (advisory)" if e.type == "note" else "applied"
        rows.append(f"- **{e.id}** ({e.stage}, {e.type}) {verb}: {e.rationale}")
    return "\n".join(rows) + "\n"
