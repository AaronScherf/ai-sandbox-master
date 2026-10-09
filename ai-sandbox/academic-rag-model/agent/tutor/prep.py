# agent/tutor/prep.py  (replace the whole file)
"""prep.py -- deterministic half of offline prep (v1 spec §3.1, v1.1 §3). collect()
parses the problem set, retrieves grounding passages and writes a packet skeleton
plus a worklist; the live IDE agent then authors the glossary, rubric, claims and
(in a blind second pass) the samples, and submit() validates them, including the
recognizer self-test. No LLM call happens here; the caller supplies `retrieve`."""
from __future__ import annotations

import json
import os
import re
from typing import Callable

from agent.rag.problem_set_parser import extract_question
from agent.tutor.packet import validate_packet, write_validated
from agent.tutor.paths import TutorPaths

WORKLIST = """# Prep worklist (for the IDE agent)

Complete these in `packet/`, then run `prep-submit` and fix every reported error. Do steps 1-5 first, then step 6
in a SEPARATE step as described.

1. `parts.json`: split each question into the parts the student will work through (one entry per sub-part is
   fine). Per part set `part_id` (unique, e.g. `q1_2`), `label`, `statement` (verbatim, neutral, no hints),
   `concept_tags` (kebab-case, reusable across problem sets), `expected_evidence` (what a correct attempt must show).
   Optional: `chat_statement` (Unicode math instead of LaTeX), `launch_style` (`"label"` default, or `"statement"`).
2. `glossary.json`: `{term: generic domain definition}` for every term a student might ask about. A definition
   must NOT use the problem's variables or notation and must NOT refer to a part or question number.
3. `rubric.json`: `{part_id: {axis: {rating: descriptor}}}` with axes `conceptual`, `rigor`, `directness` and
   ratings `Developing / Needs Review`, `Proficient`, `Mastered`.
4. `sealed/solution.md`: one `## <part_id>` section per part, copied verbatim from the guided solutions. Inside each
   section use `### Step N` headings, one per logical step; `verify` shows these steps to the tutor once, after the
   student has covered the part. `sealed/hints.md` is optional reference only and is not used at runtime.
5. `claims.json` (the claim ledger). Per part: `claims` (each: `id`, `text`, `object_terms`, `recognizer`), `routes`
   (name -> ordered claim ids; add a route for each genuinely different valid proof), `pitfalls` (each: `id`, `tag`,
   `axis`, `recognizer`, `repair_question`, optional `resolved_by` claim id), optional `final_answer` recognizer.
   A recognizer is `{"all": [[w, ...], ...], "window": N}`: every group must have a hit within N consecutive words.
   An entry matches a whole word; end it with `*` to match a prefix (`consider*`). Do not use plain `not`, `add` or
   `sum` expecting prefixes. Recognizers run on the STUDENT's words to detect claims and on the TUTOR's drafts to
   detect leaks, so make them specific to the idea, not to words already in the problem statement.
6. `samples.json`, written in a separate step, without reading the recognizers in `claims.json` (only the claim texts):
   per part `neutral_samples` (>=5 Socratic questions that reveal nothing); per claim `leak_samples` (>=10 sentences a
   tutor might say that reveal the claim) and `student_samples` (>=5 ways a student might state it); per pitfall
   `student_samples` (>=3). `prep-submit` runs every recognizer on these: it needs 90% of the leak samples and 80% of
   the student samples matched and no neutral sample matched.
7. Read `grounding.md` for the course's own notation and sources.
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
    for name in ("glossary.json", "rubric.json", "claims.json", "samples.json"):
        _write(os.path.join(d, name), "{}")
    _write(os.path.join(d, "grounding.md"), "\n".join(grounding))
    for rel, src in ((os.path.join("sealed", "hints.md"), hints_file), (os.path.join("sealed", "solution.md"), solutions_file)):
        text = ""
        if src:
            with open(src, "r", encoding="utf-8") as f:
                text = f.read()
        _write(os.path.join(d, rel), text)
    _write(os.path.join(d, "worklist.md"), WORKLIST)
    return {"ok": True, "packet_dir": d, "parts": [p["part_id"] for p in parts], "validated": False}


def submit(paths: TutorPaths) -> dict:
    errors = validate_packet(paths.packet_dir)
    if errors:
        return {"ok": False, "errors": errors}
    write_validated(paths.packet_dir)
    return {"ok": True}
