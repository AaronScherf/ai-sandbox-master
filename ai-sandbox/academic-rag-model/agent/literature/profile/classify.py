"""Classification task cards (spec A, step 2): one card per document, two prompt variants.

Variant `a` classifies the document (report type, discipline, subfields, geography, method flags). Variant `b` is a
differently worded prompt that only re-reads the discipline; it never overwrites the primary reading.
"""

from dataclasses import dataclass, field
from pathlib import Path

from agent.literature.profile.derive import country_income_group, resolve_start_year
from agent.literature.profile.discipline import OTHER, resolve_discipline, subfields_from_topics
from agent.literature.profile.taxonomy import OpenAlexTaxonomy, load_openalex
from agent.literature.transcript import split_pages
from agent.literature.vocab import Vocabulary, load_vocab_dir
from core.agent_tasks.tasks import Passage, Task
from core.indexer.index_card import find_card_by_file_id
from core.indexer.research_profile import (
    EVIDENCE_ROLES, METHOD_CLASSES, ORIENTATIONS, REPORT_TYPES, RESEARCH_REPORT_TYPES, set_research_profile,
)

STAGE = "classify"
PROMPT_VERSION = "classify-v1"
CARD_PAGES = 3
FALLBACK_CHARS = 12_000

INSTRUCTIONS_A = """\
Classify this document for a research corpus index. Use only the pages on the card.
Give a `## Result` YAML block with these keys:
- report_type: one of journal_article, working_paper, report, program_document, grey_literature, thesis, protocol, notes, other. If none fits, use a short snake_case value and set report_type_proposed: true.
- subtype: for a journal article one of empirical_study, systematic_review, methodology, qualitative_assessment, scientific_experiment, discussion_paper; for a program document one of design, procurement, monitoring_report, evaluation_report, supporting_document; otherwise a short word.
- discipline: exactly one OpenAlex field name from the list below, or `other`. discipline_confidence: 0 to 1.
- subfields: up to 3 OpenAlex subfield names that belong to that field (empty when discipline is other).
- country: list of countries where the studied intervention or population is (empty if none); admin1: first-level regions if stated.
- method_class: quantitative, qualitative, mixed_methods or other. study_design: a study design from the list below, if any.
- orientation: retrospective (reports what happened) or prospective (plans, designs or simulates what would happen).
- evidence_role: primary_evaluation (evaluates a program, policy or practice itself), synthesis (reviews several studies) or other.
- intervention_start_year: the year the studied intervention began, if stated.
Leave out method_class, study_design, orientation, evidence_role and intervention_start_year for notes, essays and other non-research documents."""

INSTRUCTIONS_B = """\
Act as a librarian shelving this document. From the pages on the card, decide which single academic field a reader
would look for it under. Give a `## Result` YAML block with: discipline (exactly one OpenAlex field name from the list
below, or `other`), discipline_confidence (0 to 1) and subfields (up to 3 OpenAlex subfield names of that field)."""


@dataclass
class Target:
    index_root: str
    taxonomy: OpenAlexTaxonomy = field(default_factory=load_openalex)
    study_designs: Vocabulary = field(default_factory=lambda: load_vocab_dir()["study_design"])


def _field_listing(tax: OpenAlexTaxonomy) -> str:
    lines = ["OpenAlex fields and their subfields:"]
    for fid, label in tax.fields.items():
        subs = [s for sid, s in tax.subfields.items() if tax.subfield_field(sid) == fid]
        lines.append(f"- {label}: " + "; ".join(subs))
    return "\n".join(lines)


def _design_listing(vocab: Vocabulary) -> str:
    return "Study designs: " + "; ".join(t.label for t in vocab.terms.values())


def _first_pages(markdown: str) -> list[tuple[int, str]]:
    pages = split_pages(markdown)
    if pages:
        return sorted(pages.items())[:CARD_PAGES]
    return [(1, markdown[:FALLBACK_CHARS])]


def make_tasks(target: Target, cards: list[dict], *, variant: str = "a", redo: bool = False):
    """One card per document. Returns (tasks, skipped) with skipped mapping file_id to the reason."""
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    instructions = INSTRUCTIONS_A if variant == "a" else INSTRUCTIONS_B
    for card in cards:
        fid = card["file_id"]
        done = (card.get("research_profile") or {}).get("provenance", {}).get(f"classify_{variant}", {})
        if done.get("prompt_version") == PROMPT_VERSION and not redo:
            skipped[fid] = "already classified with this prompt version (use redo to run again)"
            continue
        try:
            markdown = (Path(target.index_root) / card["path"]).read_text(encoding="utf-8")
        except (OSError, KeyError) as exc:
            skipped[fid] = f"cannot read the transcript: {exc}"
            continue
        ident = [f"Title on record: {card.get('title') or fid}", f"file_id: {fid}"]
        ident += [f"{k}: {card[k]}" for k in ("doi", "publication_year") if card.get(k)]
        context = "\n".join(ident + ["", _field_listing(target.taxonomy)]
                            + ([_design_listing(target.study_designs)] if variant == "a" else []))
        passages = [Passage(id=f"P{n}", source=card.get("title") or fid, ref=f"page {n}", text=text)
                    for n, text in _first_pages(markdown)]
        tasks.append(Task(id=f"classify-{variant}-{fid}", stage=STAGE,
                          subject={"file_id": fid, "variant": variant, "prompt_version": PROMPT_VERSION},
                          instructions=instructions, context=context, passages=passages))
    return tasks, skipped


def _field_id(tax: OpenAlexTaxonomy, label: str) -> str | None:
    return next((fid for fid, name in tax.fields.items() if name.casefold() == str(label).casefold()), None)


def _subfield_id(tax: OpenAlexTaxonomy, value: str) -> str | None:
    return next((sid for sid, name in tax.subfields.items()
                 if name.casefold() == str(value).casefold() or sid == str(value)), None)


def validate_result(entry: dict, result: dict, target: Target) -> list[str]:
    tax = target.taxonomy
    problems: list[str] = []
    variant = entry["subject"].get("variant", "a")
    discipline = result.get("discipline")
    field_id = _field_id(tax, discipline) if discipline else None
    if discipline != OTHER and field_id is None:
        problems.append(f"discipline: {discipline!r} is not one of the OpenAlex field names on the card (or `other`)")
    confidence = result.get("discipline_confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        problems.append("discipline_confidence: give a number from 0 to 1")
    for sub in result.get("subfields") or []:
        sid = _subfield_id(tax, sub)
        if sid is None or discipline == OTHER or tax.subfield_field(sid) != field_id:
            problems.append(f"subfield: {sub!r} is not an OpenAlex subfield of the chosen field")
    if variant != "a":
        return problems
    report_type = result.get("report_type")
    if report_type not in REPORT_TYPES and not result.get("report_type_proposed"):
        problems.append(f"report_type: {report_type!r} is not in the starter set; "
                        "set report_type_proposed: true to propose it")
    if report_type in RESEARCH_REPORT_TYPES or result.get("report_type_proposed"):
        for key, allowed in (("method_class", METHOD_CLASSES), ("orientation", ORIENTATIONS),
                             ("evidence_role", EVIDENCE_ROLES)):
            if result.get(key) not in allowed:
                problems.append(f"{key}: must be one of {sorted(allowed)}")
    for key in ("country", "admin1"):
        value = result.get(key)
        if value is not None and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            problems.append(f"{key}: give a YAML list of strings (e.g. [Kenya]), not {value!r}")
    year = result.get("intervention_start_year")
    if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1800 <= year <= 2100):
        problems.append(f"intervention_start_year: give a four-digit year as a number, or leave it out ({year!r})")
    design = result.get("study_design")
    if design and _design_term(target.study_designs, design) is None:
        problems.append(f"study_design: {design!r} is not a study design on the card")
    return problems


def _design_term(vocab: Vocabulary, value: str):
    return vocab.find(value) or vocab.find(f"study_design.{value}")


def _provenance(profile: dict, variant: str, provenance: dict) -> dict:
    merged = dict(profile.get("provenance") or {})
    merged[f"classify_{variant}"] = {"prompt_version": PROMPT_VERSION, **provenance}
    return merged


def _llm_subfields(tax: OpenAlexTaxonomy, values) -> list[dict]:
    out = []
    for value in values or []:
        sid = _subfield_id(tax, value)
        if sid is not None:
            out.append({"id": sid, "label": tax.subfields[sid], "source": "llm", "score": None})
    return out


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    fid, variant = s["file_id"], s.get("variant", "a")
    card = find_card_by_file_id(target.index_root, fid)[1]
    profile = card.get("research_profile") or {}
    field_id = _field_id(target.taxonomy, result["discipline"])
    discipline = target.taxonomy.fields[field_id] if field_id is not None else OTHER  # canonical case, so counts and folders agree
    primary = {"discipline": discipline, "discipline_confidence": float(result["discipline_confidence"])}
    subfields = _llm_subfields(target.taxonomy, result.get("subfields"))
    if variant == "a":
        fields = {"report_type": result["report_type"], "subtype": result.get("subtype"),
                  "country": list(result.get("country") or []), "admin1": list(result.get("admin1") or []),
                  "discipline_primary": primary, "openalex_subfields": subfields}
        if result.get("report_type_proposed"):
            fields["report_type_proposed"] = True
        for key in ("method_class", "orientation", "evidence_role"):
            if result.get(key) is not None:
                fields[key] = result[key]
        year, approximate = resolve_start_year(result.get("intervention_start_year"), None,
                                               card.get("publication_year"))
        if year is not None:
            fields["intervention_start_year"] = year
            fields["intervention_start_year_approximate"] = approximate
            fields["country_income_group"] = country_income_group(fields["country"], year)
        if result.get("study_design"):
            fields["study_design"] = _design_term(target.study_designs, result["study_design"]).id
        if result["report_type"] not in RESEARCH_REPORT_TYPES:
            fields["applicability"] = "not_assessed"
    else:
        fields = {"discipline_check": {**primary, "subfields": [x["label"] for x in subfields]}}
    fields["provenance"] = _provenance(profile, variant, provenance)
    set_research_profile(target.index_root, fid, fields)
    _refresh_discipline(target, fid)
    return None


def _refresh_discipline(target: Target, fid: str) -> None:
    tax = target.taxonomy
    profile = find_card_by_file_id(target.index_root, fid)[1].get("research_profile") or {}
    if "discipline_primary" not in profile:
        return
    resolved = resolve_discipline(profile["discipline_primary"], profile.get("discipline_check"),
                                  profile.get("openalex_topics"), taxonomy=tax)
    field_id = _field_id(tax, resolved["discipline"])
    fields = {k: resolved[k] for k in ("discipline", "discipline_confidence", "discipline_source", "secondary_discipline",
                                       "secondary_score", "discipline_fit", "discipline_scores")}
    fields["discipline_domain"] = tax.domains[tax.field_domain(field_id)] if field_id else None
    scored = subfields_from_topics(profile.get("openalex_topics"), field_id, taxonomy=tax)
    if scored:
        fields["openalex_subfields"] = scored
    reasons = [r for r in profile.get("review_reasons", []) if not r.startswith("discipline:")]
    if resolved["needs_review"]:
        reasons.append("discipline: " + resolved["reason"])
    fields["review_reasons"] = sorted(reasons, key=lambda r: not r.startswith("discipline: strong"))
    fields["needs_review"] = bool(reasons)
    set_research_profile(target.index_root, fid, fields)
