"""The extraction stage for core.agent_tasks: build one card per paper, validate the agent's answer, write the record."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from . import schema
from .compare import reconcile
from .papers import Paper
from .proposals import Proposals
from .store import RecordStore
from .transcript import split_pages
from .validate import check_result

STAGE = "extract"
MAX_CARD_CHARS = 240_000  # about 60k tokens of transcript; longer papers need chunked extraction, which is not built


@dataclass
class Target:
    index_root: str
    records: RecordStore
    vocabs: dict
    proposals: Proposals


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
- Use a `vocab_id` from the vocabularies below when a term fits. If none fits, write `proposed: true` instead of a
  `vocab_id` and a short `value`. Never give both. Do not propose a term that is already listed.
- `countries` are upper-case ISO 3166-1 alpha-2 codes. `scale` is one of local, subnational, national, multi_country,
  global, not_stated. `effect_direction` is one of positive, negative, null, mixed, not_reported.
- `confidence` is your overall confidence in the study's causal claims: low, medium or high, with a one-line rationale.
- Write [] for any facet list the paper does not give. Give at least one result."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _task_id(file_id: str, pass_label: str) -> str:
    return f"extract-{file_id}" if pass_label == "a" else f"extract-{file_id}-{pass_label}"


def _vocab_listing(vocabs: dict) -> str:
    names = list(schema.FACETS.values()) + [v for m in schema.MODULE_FACETS.values() for v in m.values()]
    lines: list[str] = []
    for name in names:
        v = vocabs.get(name)
        if v is None:
            continue
        lines += ["", f"Vocabulary {name} (version {v.version}, {v.provenance}):"]
        for t in v.terms.values():
            lines.append(f"- {t.id}: {t.label}" + (f" - {t.definition}" if t.definition else ""))
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
                             _vocab_listing(target.vocabs)])
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
    reconcile(target.records, s["file_id"])
    for vocab_name, fact in _proposed_facts(result):
        if fact.get("proposed"):
            target.proposals.add(s["file_id"], vocab_name, fact["value"], fact["quote"], fact["locator"], label)
    return None
