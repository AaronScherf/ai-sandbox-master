"""sample_packet.py -- a small valid packet used by tests and docs. Not real course content."""
from __future__ import annotations

import json
import os

from agent.tutor.packet import write_validated
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import AXES, RATINGS

Q1 = (
    "Question 1. Choice overload suggests a consumer may walk away without choosing. Let $d$ be the default "
    "alternative and let $p(d, A)$ denote the probability that she walks away from the set $A$. Express "
    "$p(d, A)$ in terms of the probabilities of choosing each element of $A$."
)
Q2 = (
    "Question 2. Let $\\succeq$ be a preference relation on $\\mathbb{R}$ that ranks every non-positive number "
    "below every positive number but reverses the usual order on each side. Show that no concave function "
    "represents $\\succeq$."
)
PARTS = [
    {"part_id": "q1", "label": "Question 1", "statement": Q1,
     "concept_tags": ["random-consideration-set", "default-alternative"],
     "expected_evidence": ["identifies p(d, A) as the complement of the choice probabilities"]},
    {"part_id": "q2", "label": "Question 2", "statement": Q2,
     "concept_tags": ["preference-topology", "concavity"],
     "expected_evidence": ["finds a violation of concave representability"]},
]
GLOSSARY = {
    "choice overload": "The empirical finding that facing many options can make a person less likely to choose anything at all.",
    "concave function": "A function whose value at any weighted average of two points is at least the weighted average of its values at those points.",
}
HINTS = "## q1\nThink about what the probabilities must sum to.\n\n## q2\nConsider how a concave function behaves on an interval.\n"
SOLUTION = (
    "## q1\nThe probability of walking away equals one minus the total probability of choosing any listed alternative from the set.\n\n"
    "## q2\nA concave function would have to be monotone across the break and also jump, which no concave function on the real line can do.\n"
)


def write_sample_packet(paths: TutorPaths) -> None:
    d = paths.packet_dir
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    rubric = {
        p["part_id"]: {a: {r: f"{p['part_id']} {a} {r} descriptor" for r in RATINGS} for a in AXES} for p in PARTS
    }
    for name, payload in (("parts.json", PARTS), ("glossary.json", GLOSSARY), ("rubric.json", rubric)):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    with open(os.path.join(d, "grounding.md"), "w", encoding="utf-8") as f:
        f.write("# Grounding (sample)\n")
    for name, text in (("hints.md", HINTS), ("solution.md", SOLUTION)):
        with open(os.path.join(d, "sealed", name), "w", encoding="utf-8") as f:
            f.write(text)
    write_validated(d)
