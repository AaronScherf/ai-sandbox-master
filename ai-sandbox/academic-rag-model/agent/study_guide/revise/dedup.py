# agent/study_guide/revise/dedup.py
"""Find blocks that restate each other (embedding similarity or shared equations) and ask for a decision."""
from __future__ import annotations

import re
from typing import Callable

from agent.study_guide.revise.edits import Edit, ReviseError
from agent.study_guide.revise.relevance import cosine
from agent.study_guide.revise.segment import Block

MAX_CLUSTER = 6
_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.S)
_SIZING_RE = re.compile(r"\\(?:left|right|displaystyle|bigg?|Bigg?|quad|qquad|,|;|:|!)(?![A-Za-z])")

DEDUP_SCHEMA = {
    "type": "object",
    "properties": {
        "canonical": {"type": "string"},
        "actions": {"type": "array", "items": {
            "type": "object",
            "properties": {"block": {"type": "string"}, "action": {"type": "string", "enum": ["link", "delete", "keep"]},
                           "replacement": {"type": ["string", "null"]}, "rationale": {"type": "string"}},
            "required": ["block", "action", "rationale"]}},
    },
    "required": ["canonical", "actions"],
}


def normalize_latex(s: str) -> str:
    return re.sub(r"\s+", "", _SIZING_RE.sub("", s).replace("\\widehat", "\\hat"))


def equation_set(text: str) -> set[str]:
    return {normalize_latex(m) for m in _DISPLAY_RE.findall(text)}


def find_duplicate_clusters(blocks: list[Block], embed: Callable[[str], list[float]], *, similarity: float,
                            min_words: int, eq_overlap: float = 0.6) -> list[list[str]]:
    pool = [b for b in blocks if b.words >= min_words]
    vecs = {b.id: embed(b.text) for b in pool}
    eqs = {b.id: equation_set(b.text) for b in pool}
    parent = {b.id: b.id for b in pool}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(pool):
        for b in pool[i + 1:]:
            union = eqs[a.id] | eqs[b.id]
            shared = len(eqs[a.id] & eqs[b.id]) / len(union) if union else 0.0
            if cosine(vecs[a.id], vecs[b.id]) >= similarity or (len(union) >= 2 and shared >= eq_overlap):
                parent[find(a.id)] = find(b.id)
    groups: dict[str, list[str]] = {}
    for b in pool:
        groups.setdefault(find(b.id), []).append(b.id)
    return [ids for ids in groups.values() if len(ids) > 1]


def build_dedup_prompt(blocks: list[Block]) -> str:
    listed = "\n\n".join(f"[{b.id}] {' > '.join(b.heading_path)}\n\"\"\"\n{b.text}\n\"\"\"" for b in blocks)
    return (
        "These blocks of one study guide restate overlapping material. Choose the canonical block: the one "
        "that explains the idea best and should stay. For every other block decide: 'link' (replace it with a "
        "short block that keeps its heading and points to the canonical heading with an Obsidian link such as "
        "[[#Heading]], giving the full replacement text in 'replacement'), 'delete' (it adds nothing), or "
        "'keep' (it adds value here). Never add new claims; do not rewrite the canonical block.\n\n"
        "Return JSON: {\"canonical\": <block id>, \"actions\": [{\"block\", \"action\", \"replacement\", \"rationale\"}]}\n\n"
        f"Blocks:\n{listed}\n")


def parse_dedup(data: dict, cluster: list[str], blocks_by_id: dict, start: int) -> list[Edit]:
    canonical = data.get("canonical")
    if canonical not in cluster:
        raise ReviseError(f"dedup: canonical block {canonical!r} is not in the cluster")
    edits, n = [], start
    for a in data.get("actions", []):
        block, action = a.get("block"), a.get("action")
        if block not in cluster:
            raise ReviseError(f"dedup: block {block!r} is not in the cluster")
        if block == canonical:
            raise ReviseError("dedup: the canonical block cannot be an action target")
        if action == "keep":
            continue
        if action == "link" and not a.get("replacement"):
            raise ReviseError(f"dedup: link for {block} needs a replacement")
        edits.append(Edit(
            id=f"ded-{n:03d}", type=action, stage="dedup", targets=[block], rationale=a.get("rationale", ""),
            evidence=[canonical], severity="low", confidence=0.6, replacement=a.get("replacement")))
        n += 1
    return edits


def dedup_edits(llm, blocks: list[Block], embed, *, similarity: float, min_words: int, start: int = 1) -> list[Edit]:
    by_id = {b.id: b for b in blocks}
    edits: list[Edit] = []
    for cluster in find_duplicate_clusters(blocks, embed, similarity=similarity, min_words=min_words):
        members = sorted(cluster, key=lambda i: -by_id[i].words)[:MAX_CLUSTER]
        try:
            data = llm.generate_structured(build_dedup_prompt([by_id[i] for i in members]), DEDUP_SCHEMA)
            edits += parse_dedup(data, members, by_id, start + len(edits))
        except (ReviseError, ValueError) as err:  # one bad response must not lose the whole run
            print(f"WARNING: dedup skipped a cluster of {len(members)} blocks: {err}")
    return edits
