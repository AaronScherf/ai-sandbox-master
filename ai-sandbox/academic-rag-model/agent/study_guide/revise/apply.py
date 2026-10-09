# agent/study_guide/revise/apply.py
"""Apply accepted edits by block id, then check post-conditions. No model call."""
from __future__ import annotations

import re

from agent.study_guide.revise.edits import Edit, EditReport, ReviseError
from agent.study_guide.revise.segment import Block, check_headings, segment, subtree_ids

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


def _fixed(block: Block, edits: list[Edit]) -> str:
    """Apply the fixes of one block: a whole-block replacement, or one or more non-overlapping quote replacements."""
    if len(edits) == 1 and edits[0].quote is None:
        return edits[0].replacement or ""
    spans = []
    for e in edits:
        if e.quote is None or block.text.count(e.quote) != 1:
            raise ReviseError(f"{e.id}: the quote must occur exactly once in its block")
        i = block.text.index(e.quote)
        spans.append((i, i + len(e.quote), e))
    spans.sort(key=lambda s: s[0])
    for (_, end, a), (start, _, b) in zip(spans, spans[1:]):
        if start < end:
            raise ReviseError(f"{a.id} and {b.id} quote overlapping text in the same block; accept only one")
    text = block.text
    for start, end, e in reversed(spans):
        text = text[:start] + (e.replacement or "") + text[end:]
    return text


def apply_edits(body: str, report: EditReport, accepted: set[str]) -> str:
    by_id = {e.id: e for e in report.edits}
    unknown = sorted(accepted - set(by_id))
    if unknown:
        raise ReviseError(f"unknown edit id(s): {', '.join(unknown)}")
    selected = [by_id[i] for i in sorted(accepted) if by_id[i].type != "note"]
    blocks = segment(body)
    lines = body.split("\n")
    known = {b.id: b for b in blocks}
    for e in selected:
        for t in e.targets + ([e.anchor] if e.anchor else []):
            if t not in known:
                raise ReviseError(f"{e.id}: block {t} is not in this guide")
    # A delete or move covers the whole section: the heading block and every block beneath it.
    covered = {e.id: [m for t in e.targets for m in (subtree_ids(blocks, t) if e.type == "delete" else [t])]
               for e in selected}
    owner: dict[str, str] = {}
    quote_fix = {e.id for e in selected if e.type == "fix" and e.quote is not None}
    for e in selected:
        for t in covered[e.id]:
            if t in owner and not (e.id in quote_fix and owner[t] in quote_fix):
                raise ReviseError(f"{owner[t]} and {e.id} edit the same block ({t}); accept only one")
            owner.setdefault(t, e.id)
    delete, replace, moved, fixes = set(), {}, {}, {}
    for e in selected:
        first = known[e.targets[0]]
        if e.type == "delete":
            delete.update(covered[e.id])
        elif e.type in ("shrink", "link"):
            replace[first.id] = e.replacement or ""
        elif e.type == "retitle":
            replace[first.id] = _retitled(first, e.replacement or "", e.id)
        elif e.type == "fix":
            fixes.setdefault(first.id, []).append(e)
        elif e.type == "merge":
            replace[first.id] = e.replacement or ""
            delete.update(e.targets[1:])
        elif e.type == "move":
            if e.anchor in subtree_ids(blocks, e.targets[0]):
                raise ReviseError(f"{e.id}: cannot move a section to a place inside itself")
            if e.anchor in delete:
                raise ReviseError(f"{e.id}: the anchor block is deleted by another edit")
            moved.setdefault(subtree_ids(blocks, e.anchor)[-1], []).append(subtree_ids(blocks, e.targets[0]))
    for bid, group in fixes.items():
        replace[bid] = _fixed(known[bid], group)
    moving = {i for groups in moved.values() for ids in groups for i in ids}
    chained = sorted({a for a in (e.anchor for e in selected if e.type == "move") if a in moving})
    if chained:
        raise ReviseError(f"a move is anchored on a block that is itself moved ({', '.join(chained)}); "
                          "accept only one of the two moves")
    out: list[str] = list(lines[:blocks[0].start]) if blocks else []
    def emit(b: Block) -> list[str]:
        return _replace_block(b, lines, replace[b.id]) if b.id in replace else lines[b.start:b.end]

    for b in blocks:
        if not (b.id in delete or b.id in moving):
            out += emit(b)
        for group in moved.get(b.id, []):      # land after the last block of the anchor's section
            if out and out[-1]:
                out.append("")
            for mid in group:
                if mid not in delete:
                    out += emit(known[mid])
    after = "\n".join(out)
    _check_postconditions(body, after, blocks, selected, set(owner))
    return after


def _check_postconditions(before: str, after: str, blocks: list[Block], selected: list[Edit],
                          touched: set[str]) -> None:
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
        if b.id not in touched and b.text not in after:
            problems.append(f"block {b.id} was lost or changed without an accepted edit")
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
