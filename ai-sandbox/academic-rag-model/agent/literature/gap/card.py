"""The optional free-text front door: a card that turns a research question into facet constraints.

The agent only names vocabulary terms; `submit` checks every one against the vocabularies and writes constraints.json, which
`gap run` then reads like typed `--where` constraints."""
from __future__ import annotations

import json
import os
from pathlib import Path

from core.agent_tasks.tasks import Task

from .. import schema
from ..cluster import FACETS
from ..stage import Target, _vocab_listing
from ..vocab import is_country
from .corpus import Corpus
from .resolve import shortlist

STAGE = "gap"

INSTRUCTIONS = """\
Turn the research question below into facet constraints, as a YAML mapping under `## Result`:

  constraints:
    - {facet: intervention, term_id: "intervention.some_term", phrase: "the words from the question"}
    - {facet: countries, term_id: "SO", phrase: "Somalia"}
  unmapped: ["a phrase no vocabulary term fits"]

Rules:
- `facet` is one of: intervention, outcome, study_design, sector, population, data_sources, countries.
- `term_id` must be an id from the vocabulary listing for that facet below (the shortlist shows the closest terms to the
  question), or an upper-case ISO 3166-1 alpha-2 code for `countries`. Never invent an id.
- Choose the most specific term the question supports. If a phrase fits no listed term, put it under `unmapped`.
- Map only what the question asks for; leave a facet out if the question does not constrain it."""


def make_tasks(target: Target, question: str, run_id: str, report_root, corpus: Corpus | None = None):
    corpus = corpus or Corpus()
    lines = ["Question: " + question, "", "Closest vocabulary terms to the question, per facet:"]
    for facet in schema.FACETS:
        terms = shortlist(corpus, target.vocabs, facet, question)
        lines += [f"- {facet}: " + ("; ".join(f"{c.term_id} ({c.label})" for c in terms) if terms else "(none)")]
    context = "\n".join(lines) + "\n" + _vocab_listing(target.vocabs)
    task = Task(id=f"gap-{run_id}", stage=STAGE, subject={"run_id": run_id, "question": question, "report_root": str(report_root)},
                instructions=INSTRUCTIONS, context=context)
    return [task], {}


def validate_result(entry: dict, result, target: Target) -> list[str]:
    if not isinstance(result, dict):
        return ["result: must be a mapping with constraints and unmapped"]
    out: list[str] = []
    rows = result.get("constraints")
    if not isinstance(rows, list) or not rows:
        out.append("constraints: give at least one constraint")
        rows = []
    for n, row in enumerate(rows, 1):
        where = f"constraints[{n}]"
        if not isinstance(row, dict):
            out.append(f"{where}: must be a mapping with facet, term_id and phrase")
            continue
        facet, term_id, phrase = row.get("facet"), row.get("term_id"), row.get("phrase")
        if not isinstance(phrase, str) or not phrase.strip():
            out.append(f"{where}.phrase: required")
        if facet not in FACETS:
            out.append(f"{where}.facet: {facet!r} is not one of {', '.join(FACETS)}")
        elif facet == "countries":
            if not is_country(term_id):
                out.append(f"{where}.term_id: {term_id!r} is not an upper-case ISO 3166-1 alpha-2 code")
        else:
            vocab = target.vocabs.get(schema.FACETS[facet])
            if vocab is None or term_id not in vocab.terms:
                out.append(f"{where}.term_id: {term_id!r} is not a term of the {schema.FACETS[facet]} vocabulary")
    unmapped = result.get("unmapped", [])
    if not isinstance(unmapped, list) or not all(isinstance(u, str) for u in unmapped):
        out.append("unmapped: must be a list of phrases")
    return out


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    path = Path(s["report_root"]) / s["run_id"] / "constraints.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"question": s["question"],
            "constraints": [{"facet": r["facet"], "value": r["term_id"], "phrase": r["phrase"].strip()} for r in result["constraints"]],
            "unmapped": list(result.get("unmapped", []))}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return None
