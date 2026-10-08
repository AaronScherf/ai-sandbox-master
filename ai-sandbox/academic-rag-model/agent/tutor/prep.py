"""prep.py -- deterministic half of offline prep (spec §3.1). collect()
parses the problem set, retrieves grounding passages and writes a packet
skeleton plus a worklist; the live IDE agent then authors the glossary,
rubric, tags, evidence and sealed sections, and submit() validates them.
No LLM call happens here; the caller supplies `retrieve`."""
from __future__ import annotations

import json
import os
import re
from typing import Callable

from agent.rag.problem_set_parser import extract_question
from agent.tutor.packet import validate_packet, write_validated
from agent.tutor.paths import TutorPaths

WORKLIST = """# Prep worklist (for the IDE agent)

Complete these in `packet/`, then run `prep-submit` and fix every reported error.

1. `parts.json`: split each question into the parts the student will work through (one entry per sub-part is
   fine). Per part set `part_id` (unique, e.g. `q1_2`), `label`, `statement` (verbatim, neutral, no hints),
   `concept_tags` (kebab-case, reusable across problem sets), `expected_evidence` (what a correct attempt must show).
   Optional `chat_statement`: the statement with Unicode math instead of LaTeX, for chat bubbles.
2. `glossary.json`: `{term: generic domain definition}` for every term a student might ask about. A definition
   must NOT use the problem's variables or notation and must NOT refer to a part or question number.
3. `rubric.json`: `{part_id: {axis: {rating: descriptor}}}` with axes `conceptual`, `rigor`, `directness` and
   ratings `Developing / Needs Review`, `Proficient`, `Mastered`.
4. `sealed/hints.md` and `sealed/solution.md`: one `## <part_id>` section per part. Solutions are for internal
   verification only. If a guided-solutions file exists, restructure it into these sections; otherwise write them.
5. Read `grounding.md` for the course's own notation and sources; prefer it over generic textbook conventions.
"""


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _slug(ref: str) -> str:
    return "q" + re.sub(r"[^A-Za-z0-9]+", "_", ref).strip("_")


def collect(
    paths: TutorPaths, problem_set_file: str, question_refs: list[str], retrieve: Callable[[str], list],
    hints_file: str | None = None, solutions_file: str | None = None, force: bool = False,
) -> dict:
    d = paths.packet_dir
    if os.path.exists(os.path.join(d, "parts.json")) and not force:
        raise FileExistsError(f"{d}/parts.json already exists; pass force=True to overwrite")
    parts, grounding = [], ["# Grounding passages (internal; never quote to the student)\n"]
    for ref in question_refs:
        statement = extract_question(problem_set_file, ref)
        pid = _slug(ref)
        parts.append({"part_id": pid, "label": f"Question {ref}", "statement": statement,
                      "concept_tags": [], "expected_evidence": []})
        grounding.append(f"\n## {pid}\n")
        for p in retrieve(statement):
            snippet = p.text[:600].replace("\n", " ")
            grounding.append(f"- {p.citation} ({p.path}, score {p.score:.2f})\n  > {snippet}\n")
    _write(os.path.join(d, "parts.json"), json.dumps(parts, ensure_ascii=False, indent=2))
    _write(os.path.join(d, "glossary.json"), "{}")
    _write(os.path.join(d, "rubric.json"), "{}")
    _write(os.path.join(d, "grounding.md"), "\n".join(grounding))
    for name, src in (("hints.md", hints_file), ("solution.md", solutions_file)):
        text = ""
        if src:
            with open(src, "r", encoding="utf-8") as f:
                text = f.read()
        _write(os.path.join(d, "sealed", name), text)
    _write(os.path.join(d, "worklist.md"), WORKLIST)
    return {"ok": True, "packet_dir": d, "parts": [p["part_id"] for p in parts], "validated": False}


def submit(paths: TutorPaths) -> dict:
    errors = validate_packet(paths.packet_dir)
    if errors:
        return {"ok": False, "errors": errors}
    write_validated(paths.packet_dir)
    return {"ok": True}
