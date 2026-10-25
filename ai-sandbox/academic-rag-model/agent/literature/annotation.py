"""The deterministic per-paper annotation: what the record says, with tiers and result ids; and citation keys."""
from __future__ import annotations

import re

from .tiers import at_least, tiered_facts

_RESULT_KEYS = ("claim", "effect_direction", "magnitude", "quote", "locator")


def annotation_of(records, file_id: str, vocabs: dict | None = None, floor: str = "B", proposals=None) -> dict:
    record = records.read(file_id, "a")
    facts: dict = {}
    for item in at_least(tiered_facts(records, file_id, vocabs, proposals), floor):
        facts.setdefault(item["facet"], []).append(
            {k: item[k] for k in ("label", "tier", "quote", "locator")})
    results = [{"id": f"R{n}", **{k: r.get(k) for k in _RESULT_KEYS}}
               for n, r in enumerate(record["core"].get("results") or [], 1)]
    return {"file_id": file_id, "identity": record["identity"], "facts": facts, "results": results,
            "confidence": (record.get("appraisal") or {}).get("confidence")}


def render_annotation_md(ann: dict, label: str) -> str:
    ident = ann["identity"]
    lines = [f"{label}: {ident.get('title') or ann['file_id']} ({ident.get('publication_year', 'year unknown')})"]
    for facet in sorted(ann["facts"]):
        lines.append(f"  {facet.replace('_', ' ')}: " + "; ".join(f"{f['label']} [{f['tier']}]" for f in ann["facts"][facet]))
    for r in ann["results"]:
        lines.append(f"  {label}.{r['id']}: {r['claim']} | direction {r['effect_direction']} | magnitude {r['magnitude']}"
                     f" | page {r['locator']}")
    if ann.get("confidence"):
        lines.append(f"  extractor confidence: {ann['confidence']}")
    return "\n".join(lines)


_STOP = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
_KEY_WORDS = 12


def _key_words(title: str) -> list:
    """The first clause of the title (up to a colon, question mark or dash), at most 12 words, never ending on a stopword."""
    clause = re.split(r"[:?–—]| - ", title)[0]
    words = re.findall(r"[A-Za-z0-9]+", clause)[:_KEY_WORDS] or ["paper"]
    while len(words) > 1 and words[-1].lower() in _STOP:
        words.pop()
    return words


def cite_keys(identities: dict) -> dict:
    """A short readable key per paper: first words of the title and the year; clashes get a letter."""
    taken: dict = {}
    used: set = set()
    out = {}
    for fid in sorted(identities):
        ident = identities[fid]
        words = _key_words(ident.get("title") or "paper")
        base = " ".join(words) + (f" {ident['publication_year']}" if ident.get("publication_year") else "")
        n = taken.get(base, 0)
        key = base
        while key in used or key == base and n:
            n += 1
            key = f"{base}{chr(ord('a') + n)}" if n < 26 else f"{base} {n}"
        taken[base] = n + 1
        used.add(key)
        out[fid] = key
    return out
