# agent/tutor/sample_packet.py  (replace the whole file)
"""sample_packet.py -- a small valid v1.1 packet used by tests and docs. Not real course content."""
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
SOLUTION = """\
## q1
### Step 1
The probabilities of choosing the alternatives in a menu sum to one.

### Step 2
Walking away is the case where none of the other alternatives is chosen, so its probability equals one minus the sum of the other choice probabilities.

## q2
### Step 1
Every non-positive number is indifferent to every other, so the preference is flat there.

### Step 2
Any representing function is therefore constant on the non-positives and strictly increasing on the positives.

### Step 3
A function that is constant and then strictly increasing cannot be concave, so no concave function represents the preference.
"""


def _rec(groups, window):
    return {"all": groups, "window": window}


CLAIMS = {
    "q1": {
        "claims": [
            {"id": "C1", "text": "the choice probabilities in a menu sum to one", "object_terms": ["the probabilities in the menu"],
             "recognizer": _rec([["sum*", "total*"], ["one", "1"]], 10)},
            {"id": "C2", "text": "walking away is the case where nothing else is chosen", "object_terms": ["walking away"],
             "recognizer": _rec([["default", "walk*", "away"], ["remains", "rest", "left", "nothing", "none", "complement*"]], 12)},
            {"id": "C3", "text": "so the walk-away probability is one minus the sum of the others", "object_terms": ["the other probabilities"],
             "recognizer": _rec([["one", "1"], ["minus", "subtract*", "except", "excluding"], ["sum*", "total", "others", "rest"]], 14)}],
        "routes": {"A": ["C1", "C2", "C3"]},
        "pitfalls": [{"id": "P1", "tag": "multiplies-instead-of-subtracting", "axis": "rigor", "resolved_by": "C3",
                      "recognizer": _rec([["multipl*", "product"], ["probabilit*"]], 10),
                      "repair_question": "What must all the choice probabilities in a menu add up to?"}]},
    "q2": {
        "claims": [
            {"id": "C1", "text": "all non-positive numbers are indifferent to each other", "object_terms": ["the non-positive numbers"],
             "recognizer": _rec([["indifferent", "indifference", "flat", "constant", "equally"], ["negative*", "zero", "non", "nonpositive"]], 14)},
            {"id": "C2", "text": "a representing function is flat on the non-positives and strictly increasing above zero", "object_terms": ["a representing function"],
             "recognizer": _rec([["flat", "constant"], ["increasing", "rises", "rising"], ["positive*", "above", "zero"]], 20)},
            {"id": "C3", "text": "a flat-then-increasing function cannot be concave", "object_terms": ["concavity"],
             "recognizer": _rec([["concave", "concavity"], ["flat", "constant", "kink"], ["increasing", "rises", "rising", "strictly"]], 20)}],
        "routes": {"A": ["C1", "C2", "C3"]},
        "pitfalls": [{"id": "P1", "tag": "confuses-concave-with-quasiconcave", "axis": "conceptual", "resolved_by": "C3",
                      "recognizer": _rec([["quasi*"], ["same", "equivalent", "like"]], 10),
                      "repair_question": "What does concavity require that quasiconcavity does not?"}]},
}

_PREFIXES = ["Remember that", "Keep in mind that", "It turns out that", "You should see that", "Here is the thing:"]


def _leaks(*cores):
    return [f"{p} {c}" for p in _PREFIXES for c in cores]


_NEUTRAL = ["What have you tried so far?", "Which part of the model feels least clear?",
            "How would you say the setup in your own words?", "What does the problem ask you to show?",
            "Which assumption have you not used yet?", "What would a simple example look like?"]

SAMPLES = {
    "q1": {
        "claims": {
            "C1": {"leak_samples": _leaks("the probabilities of all the alternatives must sum to one",
                                          "the total probability across the menu is one"),
                   "student_samples": ["probabilities of everything in the set sum to 1", "the total probability is one",
                                       "the sum of everything is one", "choice probabilities total one", "they must sum to one"]},
            "C2": {"leak_samples": _leaks("the default is what remains when nothing else is picked",
                                          "walking away is the complement of choosing something else"),
                   "student_samples": ["the default is whatever is left", "walking away is when nothing else gets chosen",
                                       "the default is the rest", "if none of the others is chosen she walks away",
                                       "default means nothing else was picked"]},
            "C3": {"leak_samples": _leaks("so the default probability equals one minus the sum of the others",
                                          "subtract the total of the other choice probabilities from one"),
                   "student_samples": ["one minus the sum of the others", "1 minus the total of the other probabilities",
                                       "I subtract the sum of the other options from one", "it is one except the sum of the rest",
                                       "p of d is 1 minus everything else summed"]}},
        "pitfalls": {"P1": {"student_samples": ["multiplying the probabilities of the others", "take the product of the choice probabilities",
                                                "I multiply the probabilities"]}},
        "neutral_samples": _NEUTRAL},
    "q2": {
        "claims": {
            "C1": {"leak_samples": _leaks("every non-positive number is indifferent to every other",
                                          "the preference is flat on the negatives and zero"),
                   "student_samples": ["all the non-positive numbers are indifferent", "it is flat on the negatives",
                                       "zero and below are equally good", "the preference is constant for negative numbers",
                                       "nonpositive numbers are all indifferent"]},
            "C2": {"leak_samples": _leaks("any representing function is flat up to zero and then strictly increasing",
                                          "utility is constant on the non-positives and rises on the positives"),
                   "student_samples": ["the utility must be flat then strictly increasing for positive numbers",
                                       "constant up to zero and rising after", "it rises above zero and is flat below",
                                       "flat on the left and increasing on the positive side", "increasing above zero but constant before"]},
            "C3": {"leak_samples": _leaks("a function that is flat and then increasing cannot be concave",
                                          "concavity fails because the graph is constant and then rises"),
                   "student_samples": ["flat then increasing cannot be concave", "a concave function cannot be constant then strictly increasing",
                                       "concavity rules out a flat part followed by rising values", "the kink makes it non concave and it rises after",
                                       "constant and then increasing means not concave"]}},
        "pitfalls": {"P1": {"student_samples": ["quasiconcave is the same as concave here", "a quasiconcave function is equivalent to a concave one",
                                                "quasi concave is like concave"]}},
        "neutral_samples": _NEUTRAL},
}


def write_sample_packet(paths: TutorPaths) -> None:
    d = paths.packet_dir
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    rubric = {
        p["part_id"]: {a: {r: f"{p['part_id']} {a} {r} descriptor" for r in RATINGS} for a in AXES} for p in PARTS
    }
    for name, payload in (("parts.json", PARTS), ("glossary.json", GLOSSARY), ("rubric.json", rubric),
                          ("claims.json", CLAIMS), ("samples.json", SAMPLES)):
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    with open(os.path.join(d, "grounding.md"), "w", encoding="utf-8") as f:
        f.write("# Grounding (sample)\n")
    with open(os.path.join(d, "sealed", "solution.md"), "w", encoding="utf-8") as f:
        f.write(SOLUTION)
    write_validated(d)
