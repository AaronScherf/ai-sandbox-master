"""The extraction stage for core.agent_tasks: build one card per paper, validate the agent's answer, write the record."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from . import schema
from .compare import reconcile
from .listing import tree_listing
from .papers import Paper
from .proposals import Proposals
from .store import RecordStore
from .transcript import split_pages
from .validate import check_result

STAGE = "extract"
LISTING_LIMIT = 150  # a vocabulary with more terms than this is listed by its grouping levels only
MAX_CARD_CHARS = 300_000  # about 75k tokens of transcript; longer papers need chunked extraction, which is not built (raised from 240_000 after the 2026-11-02 trial, see docs/status/literature/2026-11-02-phase1-quality-gate.md)


@dataclass
class Target:
    index_root: str
    records: RecordStore
    vocabs: dict
    proposals: Proposals


CHOOSING_RULE = """\n- Choosing a `vocab_id`: the vocabularies below are trees. An indented term is a child of the term above it, and most terms carry a definition. Work down the tree one level at a time:
  1. Start at the grouping term that holds the topic. It is a valid answer.
  2. Go to a child only if you can quote a passage showing that the paper itself does, studies or measures exactly what that child's definition says. The quote you give must be that passage. A
     passage about the topic in general, or about something close to the child, does not count.
  3. If you cannot, stay at the grouping term. Staying is correct, not a fallback or a lower-quality answer.
  4. Never choose a child because its label shares a theme with the paper, because the paper could be read as implying it, or because the child is the only one left after you rule out the others.
  `value` is the paper's own wording for the thing, and the chosen term must describe the same thing as `value`. If no listed term fits, write `proposed: true` instead of a `vocab_id` and a short
  `value`. Never give both. Do not propose a term that is already listed.
"""

FIT_TEST_EXAMPLES = """\n- Examples of the fit test.
  - A child fits: the paper evaluates a cash grant, the quote shows the grant, and a child's definition describes cash grants, so use that child.
  - Stay at the group: the paper discusses adaptation strategies in general, so use the grouping term for adaptation strategies, not any one practice beneath it.
  - A shared theme is not enough: the paper studies microcredit loans. A sibling term for savings groups is also about household finance, but the paper does not do or measure it, so do not choose it.
  - Report level decides the term: the paper reports household income overall. Use the income term at that level, not a child about one income source, unless the paper reports that source separately.
"""

INSTRUCTIONS = """\
Extract a structured study record from the paper whose pages are listed under "Offered passages". Put the answer as
a YAML mapping under `## Result`, in exactly this shape (quote every value that contains a colon):

  core:
    intervention: [{value: "cash transfers", vocab_id: intervention.cash_transfer, quote: "...", locator: 4}]
    outcome: []
    study_design: [{value: "synthetic control", proposed: true, quote: "...", locator: 3}]
    sector: []
    population: []
    data_sources: [{value: "FSNAU", vocab_id: data_source.fsnau, resolution: "district", quote: "...", locator: 5}]
    geography: {countries: [SO], regions: ["Gedo"], scale: subnational, quote: "...", locator: 2}
    results: [{claim: "...", effect_direction: positive, magnitude: "12%", quote: "...", locator: 8}]
  appraisal: {confidence: medium, rationale: "...", quote: "...", locator: 9}
  modules:            # optional
    disaster_conflict: {hazard_types: [], conflict_setting: null, social_protection_modality: null}

Rules:
- State only what the paper itself says. Do not extract from the reference list or from other papers it cites.
- Every fact needs a `quote` copied exactly from the page text (8 to 300 characters; the shortest passage that
  supports the fact) and a `locator`: the page number from the passage's ref (`ref: page 3` means locator 3), or a
  list of page numbers. A quote that is not on the page you cite is rejected.
""" + CHOOSING_RULE + """- Resilience outcomes concern a household's capacity to cope with shocks. A paper's adoption of adaptation or coping measures is not itself a resilience
  outcome: record the measures as an intervention, or as an adoption outcome where the vocabulary has one.
- `countries` are upper-case ISO 3166-1 alpha-2 codes. `scale` is one of local, subnational, national, multi_country,
  global, not_stated. `effect_direction` is one of positive, negative, null, mixed, not_reported.
- `confidence` is your overall confidence in the study's causal claims: low, medium or high, with a one-line rationale.
- Extract what this study itself does, uses and measures. Do not extract topics that appear only in the background or
  literature review, in cited studies, or in recommendations and future work.
- Be complete: list every distinct outcome, intervention and data source the study itself reports, not only the
  main one.
- `countries` are the countries of the paper's own sample or setting. For a review or overview, they are the countries
  it explicitly says it covers. A country named only in examples, in a list of illustrative programmes, in background
  statistics, or in funding and acknowledgements text is not a country of the study. A paper with no stated sample or
  setting (a global or multi-country overview) gets `countries: []` and a `scale` of multi_country or global.
- For a review, overview or competition paper, `data_sources` are only data the paper analysed itself. Data that the
  reviewed studies used, data described as other people's, and programme delivery channels are not data sources of the
  paper: leave them out.
""" + FIT_TEST_EXAMPLES + """- Write [] for any facet list the paper does not give. Give at least one result."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _task_id(file_id: str, pass_label: str) -> str:
    return f"extract-{file_id}" if pass_label == "a" else f"extract-{file_id}-{pass_label}"


def _vocab_listing(vocabs: dict, pass_label: str = "a", file_id: str = "") -> str:
    names = list(schema.FACETS.values()) + [v for m in schema.MODULE_FACETS.values() for v in m.values()]
    lines: list[str] = []
    for name in names:
        v = vocabs.get(name)
        if v is None:
            continue
        terms = list(v.terms.values())
        note = ""
        if len(terms) > LISTING_LIMIT:
            parents = {t.parent for t in terms if t.parent}
            terms = [t for t in terms if t.id in parents]
            note = (f"; {len(v.terms)} terms in all, only the grouping levels are listed. Choose the closest listed "
                    "grouping term and put the paper's own wording in `value`; a later pass narrows it to a specific "
                    "term using definitions")
        lines += ["", f"Vocabulary {name} (version {v.version}, {v.provenance}{note}):"]
        lines.append(tree_listing(v, terms, pass_label, file_id, name))
    return "\n".join(lines)


def make_tasks(target: Target, papers: list[Paper], *, pass_label: str = "a", redo: bool = False):
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    versions = {n: v.version for n, v in target.vocabs.items()}
    for paper in papers:
        try:
            md = (Path(target.index_root) / paper.path).read_text(encoding="utf-8")
        except OSError as exc:
            skipped[paper.file_id] = f"cannot read the transcript: {exc}"
            continue
        pages = split_pages(md)
        if not pages:
            skipped[paper.file_id] = "transcript has no page markers"
            continue
        size = sum(len(t) for t in pages.values())
        if size > MAX_CARD_CHARS:
            skipped[paper.file_id] = (f"transcript is {size} characters, over the {MAX_CARD_CHARS} limit for one card "
                                      f"(chunked extraction is not built)")
            continue
        sha = _sha(md)
        existing = target.records.read(paper.file_id, pass_label)
        if existing and existing.get("transcript_sha") == sha and not redo:
            skipped[paper.file_id] = "a current record already exists (use --redo to extract again)"
            continue
        ident = paper.identity
        context = "\n".join([f"Paper: {paper.title or paper.file_id}", f"file_id: {paper.file_id}",
                             *(f"{k}: {ident[k]}" for k in ("doi", "openalex_id", "publication_year") if k in ident),
                             _vocab_listing(target.vocabs, pass_label, paper.file_id)])
        passages = [Passage(id=f"P{n}", source=paper.title or paper.file_id, ref=f"page {n}", text=text)
                    for n, text in sorted(pages.items())]
        tasks.append(Task(
            id=_task_id(paper.file_id, pass_label), stage=STAGE,
            subject={"file_id": paper.file_id, "pass": pass_label, "transcript_sha": sha, "identity": ident,
                     "vocab_versions": versions},
            instructions=INSTRUCTIONS, context=context, passages=passages))
    return tasks, skipped


def _offered_pages(entry: dict) -> dict[int, str]:
    out: dict[int, str] = {}
    for p in entry.get("passages", []):
        m = re.fullmatch(r"page (\d+)", p.get("ref", ""))
        if m:
            out[int(m.group(1))] = p["text"]
    return out


def validate_result(entry: dict, result: dict, target: Target) -> list[str]:
    problems = check_result(result, target.vocabs, _offered_pages(entry))
    if problems:
        old = entry["subject"].get("vocab_versions", {})
        moved = [n for n, v in old.items() if n in target.vocabs and target.vocabs[n].version != v]
        gone = [n for n in old if n not in target.vocabs]
        if moved or gone:
            problems.append("note: the vocabulary changed since this card was made (" +
                            ", ".join(sorted(moved + gone)) + "); if a vocab_id was removed, run collect again with --redo")
    return problems


def _proposed_facts(result: dict):
    for facet, vocab_name in schema.FACETS.items():
        for fact in result["core"].get(facet, []):
            yield vocab_name, fact
    for module, facets in schema.MODULE_FACETS.items():
        for facet, vocab_name in facets.items():
            for fact in (result.get("modules", {}).get(module, {}) or {}).get(facet, []):
                yield vocab_name, fact


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    label = s["pass"]
    record = {"schema_version": schema.SCHEMA_VERSION, "identity": s["identity"], "transcript_sha": s["transcript_sha"],
              "core": result["core"], "appraisal": result["appraisal"]}
    if "modules" in result:
        record["modules"] = result["modules"]
    record["extractor"] = {
        "driver": provenance["driver"], "agent_name": provenance["agent"], "run_id": provenance["run"],
        "schema_version": schema.SCHEMA_VERSION, "prompt_version": schema.PROMPT_VERSION, "pass": label,
        "vocab_versions": s["vocab_versions"]}
    record["review"] = {"status": "unreviewed", "items_flagged": []}
    target.records.write(record, label)
    if label != "a":
        primary = target.records.read(s["file_id"], "a")
        if primary:
            for key in ("verification", "verification_full"):
                if key in primary:
                    primary[key]["items"] = [item for item in primary[key].get("items", [])
                                             if item.get("pass") != label]
            target.records.write(primary, "a")
    reconcile(target.records, s["file_id"], target.vocabs)
    for vocab_name, fact in _proposed_facts(result):
        if fact.get("proposed"):
            target.proposals.add(s["file_id"], vocab_name, fact["value"], fact["quote"], fact["locator"], label)
    return None
