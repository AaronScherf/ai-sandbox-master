# agent/study_guide/revise/inline.py
"""Inline sweep: out-of-scope sentences inside blocks that are otherwise on topic.

Block-level relevance cannot remove one sentence from a block that is mostly relevant. The spec lists
`scope_terms`; blocks containing one are shown to the model, which proposes exact quotes to cut or shorten."""
from __future__ import annotations

import re

from agent.study_guide.revise.edits import Edit
from agent.study_guide.revise.segment import Block

BATCH = 8
BLOCK_CHARS = 4000

INLINE_SCHEMA = {
    "type": "object",
    "properties": {"findings": {"type": "array", "items": {
        "type": "object",
        "properties": {"block": {"type": "string"}, "quote": {"type": "string"},
                       "replacement": {"type": "string"}, "rationale": {"type": "string"}},
        "required": ["block", "quote", "replacement", "rationale"]}}},
    "required": ["findings"],
}


def terms_in(text: str, terms: tuple[str, ...]) -> list[str]:
    return [t for t in terms if re.search(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", text, re.I)]


def inline_candidates(blocks: list[Block], terms: tuple[str, ...]) -> list[Block]:
    return [b for b in blocks if b.level and terms_in(b.text, terms)]


def build_inline_prompt(scope: str, blocks: list[Block], terms: tuple[str, ...]) -> str:
    listed = "\n\n".join(f"[{b.id}] {' > '.join(b.heading_path)}\n\"\"\"\n{b.text[:BLOCK_CHARS]}\n\"\"\"" for b in blocks)
    return (
        "A study guide has this scope:\n" + (scope or "(none given)") + "\n\n"
        f"The blocks below mention at least one of these out-of-scope terms: {', '.join(terms)}. For each sentence or "
        "clause that exists only to teach or illustrate something outside the scope (software commands, code syntax, "
        "other model-selection material), report a finding: 'quote' is the exact text to cut, copied once from one "
        "block, and 'replacement' is the text to put in its place, which must be shorter than the quote and may be "
        "empty. Keep every formula, definition, number and on-topic statement; a sentence that only mentions a term "
        "in passing while teaching an on-topic point stays. Do not add new content. If a block needs no change, "
        "report nothing for it. Return JSON {\"findings\": [{\"block\", \"quote\", \"replacement\", \"rationale\"}]}.\n\n"
        + listed + "\n")


def parse_inline(data: dict, blocks_by_id: dict[str, Block], start: int) -> tuple[list[Edit], list[str]]:
    edits, problems, n = [], [], start
    for f in data.get("findings", []):
        block, quote, repl = blocks_by_id.get(f.get("block")), f.get("quote", ""), f.get("replacement", "")
        if block is None:
            problems.append(f"inline: unknown block {f.get('block')!r}")
        elif not quote or block.text.count(quote) != 1:
            problems.append(f"{block.id}: the quote is absent or not unique: {quote[:60]!r}")
        elif len(repl.split()) >= len(quote.split()):
            problems.append(f"{block.id}: the replacement is not shorter than the quote: {quote[:60]!r}")
        else:
            edits.append(Edit(id=f"inl-{n:03d}", type="fix", stage="inline", targets=[block.id],
                              rationale=f"out of scope: {f.get('rationale', '')}", severity="low", confidence=0.6,
                              replacement=repl, quote=quote))
            n += 1
    return edits, problems


def inline_edits(llm, scope: str, blocks: list[Block], terms: tuple[str, ...], start: int = 1) -> tuple[list[Edit], list[str]]:
    by_id = {b.id: b for b in blocks}
    cands = inline_candidates(blocks, terms)
    edits: list[Edit] = []
    problems: list[str] = []
    for i in range(0, len(cands), BATCH):
        batch = cands[i:i + BATCH]
        try:
            data = llm.generate_structured(build_inline_prompt(scope, batch, terms), INLINE_SCHEMA)
        except ValueError as err:  # an unusable reply must not lose the run
            problems.append(f"inline: a batch of {len(batch)} blocks was skipped: {err}")
            continue
        found, bad = parse_inline(data, by_id, start + len(edits))
        edits += found
        problems += bad
    return edits, problems
