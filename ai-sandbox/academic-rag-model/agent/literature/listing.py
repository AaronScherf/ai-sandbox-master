"""Shared vocabulary tree rendering for extraction cards."""
import random


def tree_listing(vocab, terms, pass_label: str = "a", file_id: str = "", facet: str = "") -> str:
    selected = {t.id: t for t in terms}
    children = {}
    for term in terms:
        parent = term.parent if term.parent in selected else None
        children.setdefault(parent, []).append(term)
    rng = random.Random(f"{file_id}:{facet}") if pass_label == "b" else None
    lines = []

    def visit(parent, depth):
        siblings = list(children.get(parent, []))
        if rng:
            rng.shuffle(siblings)
        for term in siblings:
            lines.append("  " * depth + f"- {term.id}: {term.label}" +
                         (f" - {term.definition}" if term.definition else ""))
            visit(term.id, depth + 1)

    visit(None, 0)
    return "\n".join(lines)
