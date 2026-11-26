"""Corpus summary: counts per profile field, per 3ie term (with leaf-to-ancestor rollup) and per inclusion profile.
Only cards with a research profile are counted; course-material cards are ignored."""

from collections import Counter

from agent.literature.profile.profiles import InclusionProfile, matches
from agent.literature.profile.review import effective_profile, method_disagrees
from agent.literature.profile.tagging import covered_terms
from core.indexer.research_profile import RESEARCH_REPORT_TYPES

FIELDS = ("report_type", "subtype", "discipline", "secondary_discipline", "discipline_fit", "discipline_domain", "method_class", "orientation",
          "evidence_role", "applicability")


def _flags(profile: dict) -> list[str]:
    reasons = list(profile.get("review_reasons", [])) if profile.get("needs_review") else []
    if (profile.get("doi_verified") or {}).get("match") == "mismatch":
        reasons.append("DOI mismatch: " + "; ".join(profile.get("bibliography_mismatches", [])))
    if profile.get("report_type") in RESEARCH_REPORT_TYPES and profile.get("applicability") == "not_assessed":
        reasons.append("research document with no applicability yet: run tag collect for it")
    if method_disagrees(profile):
        reasons.append(f"study_design {profile['study_design']} disagrees with method_class {profile['method_class']}")
    return reasons


def summarize(cards: list[dict], profile: InclusionProfile | None = None, vocabs: dict | None = None,
              index_root: str | None = None) -> dict:
    """`index_root` lets the owner's decisions override the model's values; without it the raw profile is counted."""
    research = [(c, effective_profile(index_root, c) if index_root else c["research_profile"])
                for c in cards if c.get("research_profile")]
    out: dict = {"n_documents": len(research)}
    for field in FIELDS:
        out[field] = dict(Counter(p[field] for _, p in research if p.get(field)))
    for kind, vocab in (vocabs or {}).items():
        counts: Counter = Counter()
        for _, p in research:
            counts.update(covered_terms(vocab, p.get(f"{kind}_tags", [])))
        out[f"{kind}_terms"] = dict(counts)
    out["flagged"] = [{"file_id": c["file_id"], "title": c.get("title"), "reasons": r}
                      for c, p in research if (r := _flags(p))]
    if profile is not None:
        verdicts = Counter()
        for c, p in research:
            ok, reason = matches(profile, {**p, "publication_year": p.get("publication_year") or c.get("publication_year")})
            verdicts["unclear" if reason.startswith("unclear") and ok else "included" if ok else "excluded"] += 1
        out["profile"] = {"name": profile.name, "included": verdicts["included"], "unclear": verdicts["unclear"],
                          "excluded": verdicts["excluded"]}
    return out


def render_summary(summary: dict) -> str:
    lines = [f"documents with a research profile: {summary['n_documents']}"]
    for field in FIELDS:
        if summary.get(field):
            lines.append(f"\n{field}:")
            lines += [f"  {k}: {v}" for k, v in sorted(summary[field].items(), key=lambda kv: (-kv[1], kv[0]))]
    for key in ("intervention_terms", "outcome_terms"):
        if summary.get(key):
            lines.append(f"\n{key} (papers covering each term, leaves rolled up to branch and sector):")
            lines += [f"  {k}: {v}" for k, v in sorted(summary[key].items(), key=lambda kv: (-kv[1], kv[0]))]
    if "profile" in summary:
        p = summary["profile"]
        lines.append(f"\ninclusion profile {p['name']}: included {p['included']}, unclear {p['unclear']}, excluded {p['excluded']}")
    if summary["flagged"]:
        lines.append(f"\nflagged for review ({len(summary['flagged'])}):")
        lines += [f"  {f['file_id']} {f['title']}: " + " | ".join(f["reasons"]) for f in summary["flagged"]]
    return "\n".join(lines)
