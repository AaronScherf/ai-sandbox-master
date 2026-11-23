"""Discipline resolution. One primary discipline (it drives folders): the OpenAlex field where its topic share is
strong, else the best-supported label from the pooled evidence (primary agent, second agent, OpenAlex topic shares).
A secondary discipline (the runner-up of that pooled evidence, kept for every paper) and a fit marker ("clear" or
"mixed") record how well the paper sits in one discipline, so mixed papers are not lost to an arbitrary choice.
Fields are the 26 OpenAlex fields plus "other"."""

from agent.literature.profile.taxonomy import OpenAlexTaxonomy, load_openalex

OTHER = "other"


def field_shares(topics: list[dict] | None) -> dict[str, float]:
    """Each OpenAlex field's share (0..1) of the summed topic scores."""
    totals: dict[str, float] = {}
    for t in topics or []:
        if t.get("field_id") and t.get("score"):
            totals[t["field_id"]] = totals.get(t["field_id"], 0.0) + float(t["score"])
    grand = sum(totals.values())
    return {k: v / grand for k, v in totals.items()} if grand else {}


def field_from_topics(topics: list[dict] | None) -> tuple[str | None, float]:
    """The field with the largest summed topic score and its share of the total score (0..1)."""
    shares = field_shares(topics)
    if not shares:
        return None, 0.0
    best = max(shares, key=lambda k: shares[k])
    return best, shares[best]


def subfields_from_topics(topics: list[dict] | None, field_id: str | None, *, limit: int = 3,
                          taxonomy: OpenAlexTaxonomy | None = None) -> list[dict]:
    """OpenAlex subfields of the chosen field, with their share of that field's topic score."""
    tax = taxonomy or load_openalex()
    totals: dict[str, float] = {}
    for t in topics or []:
        if t.get("field_id") == field_id and t.get("subfield_id") in tax.subfields and t.get("score"):
            totals[t["subfield_id"]] = totals.get(t["subfield_id"], 0.0) + float(t["score"])
    grand = sum(totals.values())
    ranked = sorted(totals, key=lambda k: totals[k], reverse=True)[:limit]
    return [{"id": sid, "label": tax.subfields[sid], "source": "openalex", "score": round(totals[sid] / grand, 3)}
            for sid in ranked]


CLEAR_SCORE = 0.6   # a clear fit needs the primary's pooled score at least this high ...
CLEAR_MARGIN = 0.3  # ... and at least this far ahead of the runner-up


def resolve_discipline(primary: dict, check: dict | None, topics: list[dict] | None, *, threshold: float = 0.8,
                       taxonomy: OpenAlexTaxonomy | None = None) -> dict:
    tax = taxonomy or load_openalex()
    shares = field_shares(topics)
    readings = [r for r in (primary, check) if r is not None]
    pooled: dict[str, float] = {}
    for reading in readings:
        pooled[reading["discipline"]] = pooled.get(reading["discipline"], 0.0) + float(reading["discipline_confidence"])
    for fid, share in shares.items():
        pooled[tax.fields[fid]] = pooled.get(tax.fields[fid], 0.0) + share
    weight = len(readings) + (1 if shares else 0)
    ranked = sorted(pooled, key=lambda label: (-pooled[label], label != primary["discipline"], label))
    scores = [{"discipline": label, "score": round(pooled[label] / weight, 3)} for label in ranked]

    topic_field, share = field_from_topics(topics)
    if topic_field and share >= threshold:
        label, confidence, source = tax.fields[topic_field], share, "openalex"
    else:
        label = ranked[0]
        source = "llm" if label == primary["discipline"] else "pooled"
        confidence = float(primary["discipline_confidence"]) if source == "llm" else pooled[label] / weight

    rest = [s for s in scores if s["discipline"] not in (label, OTHER)]
    secondary = rest[0] if rest else None
    top = scores[0]
    margin = top["score"] - (scores[1]["score"] if len(scores) > 1 else 0.0)
    clear = top["discipline"] == label and top["score"] >= CLEAR_SCORE and margin >= CLEAR_MARGIN
    reasons = ["no second agent check yet"] if check is None else []
    return {"discipline": label, "discipline_confidence": confidence, "discipline_source": source,
            "secondary_discipline": secondary["discipline"] if secondary else None,
            "secondary_score": secondary["score"] if secondary else None,
            "discipline_fit": "clear" if clear else "mixed", "discipline_scores": scores[:3],
            "needs_review": bool(reasons), "reason": " | ".join(reasons)}
