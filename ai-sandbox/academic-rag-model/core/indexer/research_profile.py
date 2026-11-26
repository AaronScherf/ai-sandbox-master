"""Research profile: extra card fields for research documents (spec A, section 3).

The profile is a nested `research_profile` dict on the index card. Course-material cards never receive the key,
so their shards stay byte-identical. Layer 4 fields (estimates, replication, outcome_status) belong to spec B and
are not part of this version.
"""

from core.indexer.index_card import (
    _replace_card,
    find_card_by_file_id,
    load_shard,
    save_shard,
)

RESEARCH_PROFILE_VERSION = 1

REPORT_TYPES = frozenset({
    "journal_article", "book", "book_chapter", "thesis", "protocol", "working_paper", "program_document", "report",
    "notes", "other",
})
# Who issued the document, separate from its form. `provenance` is taken: it records which agent filled each stage.
PUBLISHER_TYPES = frozenset({"academic", "research_institute", "multilateral", "government", "ngo", "other"})
# Types that go on to 3ie tagging; notes and other stop after the classification card.
RESEARCH_REPORT_TYPES = REPORT_TYPES - {"notes", "other"}
METHOD_CLASSES = frozenset({"quantitative", "qualitative", "mixed_methods", "other"})
ORIENTATIONS = frozenset({"retrospective", "prospective"})
EVIDENCE_ROLES = frozenset({"primary_evaluation", "synthesis", "other"})
APPLICABILITY = frozenset({"both", "intervention_only", "outcome_only", "not_applicable", "not_assessed"})

PROFILE_FIELDS = frozenset({
    "research_profile_version",
    "report_type", "report_type_proposed", "subtype", "publisher", "publisher_type",
    "title", "authors", "doi", "publication_year", "journal", "openalex_id", "doi_verified", "bibliography_mismatches",
    "discipline", "discipline_confidence", "discipline_source", "discipline_check", "discipline_domain",
    "openalex_subfields", "openalex_topics", "discipline_primary",
    "secondary_discipline", "secondary_score", "discipline_fit", "discipline_scores",
    "country", "admin1", "country_income_group", "intervention_start_year", "intervention_start_year_approximate",
    "method_class", "study_design", "orientation", "evidence_role",
    "intervention_tags", "outcome_tags", "applicability", "projects",
    "needs_review", "review_reasons", "skipped_reason", "provenance",
})

_ENUMS = {
    "method_class": METHOD_CLASSES,
    "orientation": ORIENTATIONS,
    "evidence_role": EVIDENCE_ROLES,
    "applicability": APPLICABILITY,
    "publisher_type": PUBLISHER_TYPES,
}


def derive_applicability(intervention_tags: list[dict] | None, outcome_tags: list[dict] | None, *,
                         assessed: bool) -> str:
    """Mechanical label from the two tag lists. `not_assessed` when tagging was skipped for this document."""
    if not assessed:
        return "not_assessed"
    has_i, has_o = bool(intervention_tags), bool(outcome_tags)
    if has_i and has_o:
        return "both"
    if has_i:
        return "intervention_only"
    if has_o:
        return "outcome_only"
    return "not_applicable"


def validate_profile(profile: dict) -> list[str]:
    """Problems with a (partial) profile; an empty list means valid."""
    problems = [f"unknown field: {key}" for key in sorted(set(profile) - PROFILE_FIELDS)]
    report_type = profile.get("report_type")
    if report_type is not None and report_type not in REPORT_TYPES and not profile.get("report_type_proposed"):
        problems.append(f"report_type {report_type!r} is not in the starter set; mark report_type_proposed to propose it")
    for name, allowed in _ENUMS.items():
        value = profile.get(name)
        if value is not None and value not in allowed:
            problems.append(f"{name} {value!r} must be one of {sorted(allowed)}")
    return problems


def set_research_profile(academic_hub_root: str, file_id: str, fields: dict) -> bool:
    """Merges `fields` into the card's research_profile without touching any other card key. False when there is
    no card; ValueError for an unknown profile key."""
    unknown = set(fields) - PROFILE_FIELDS
    if unknown:
        raise ValueError(f"not research profile fields: {sorted(unknown)}")
    found = find_card_by_file_id(academic_hub_root, file_id)
    if found is None:
        return False
    course, card = found
    profile = {**card.get("research_profile", {}), **fields, "research_profile_version": RESEARCH_PROFILE_VERSION}
    updated = {**card, "research_profile": profile}
    if updated != card:
        save_shard(academic_hub_root, course, _replace_card(load_shard(academic_hub_root, course), file_id, updated))
    return True
