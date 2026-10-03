"""Builds the enhancement prompt. The contract here (grounded vs.
elaboration) is mirrored by schema.py/validate.py, which enforce it."""
from __future__ import annotations

import json

from agent.summary_enhance.schema import ELABORATION_KINDS, RESPONSE_SCHEMA
from agent.summary_enhance.source_loader import GuideInput

PROMPT_VERSION = "2026-10-03.1"

_INSTRUCTIONS = """\
You are improving a student's study guide. Below are (1) an existing LLM-generated
draft guide and (2) the exact textbook passages it was built from, each tagged
with a label like [S1]. Produce one coherent guide with one section per topic.

For each topic, return two separate arrays:

"grounded" -- synthesis the textbooks support.
  * Merge what the different sources say about the topic into one clear explanation;
    do not just summarize each book in turn.
  * Every block must list, in "sources", the labels of the passages it relies on.
  * Use ONLY what the passages state or directly imply. The draft guide is not a
    source: if a claim in it is not supported by a passage, leave it out of "grounded".
  * Where the sources differ (notation, assumptions, scope) or one is silent on
    something, say so plainly instead of papering over it.
  * Keep math in LaTeX with $...$ / $$...$$ delimiters. This is JSON, so every LaTeX
    backslash must be doubled ("\\beta", "\\frac"); a single backslash before b, t, f, r
    or n silently corrupts the formula.
  * Do NOT write [S#] markers inside "text"; put labels only in "sources".

"elaboration" -- your own additions that help a student: intuition, worked
examples, general background. These are NOT supported by the textbooks.
  * "kind" must be one of: {kinds}.
  * Never cite labels or attribute elaboration to the textbooks.
  * Rendered to the student under a "Not from the textbooks" callout.

Return ONLY JSON matching this schema, with no markdown fences or commentary:
{schema}
"""


def build_prompt(guide: GuideInput, topics: list[str], errors: list[str] | None = None) -> str:
    parts = [f"(prompt version {PROMPT_VERSION})\n"]
    parts.append(_INSTRUCTIONS.format(
        kinds=", ".join(ELABORATION_KINDS), schema=json.dumps(RESPONSE_SCHEMA, indent=2)))
    if topics:
        listed = "\n".join(f"  - {json.dumps(t)}" for t in topics)
        parts.append(f"Topics (use exactly these titles, in this order, one section each):\n{listed}\n")
    else:
        parts.append("Topics: choose the natural topics covered by the draft and passages, "
                     "one section each.\n")
    parts.append("=== DRAFT GUIDE (not a source) ===\n" + guide.body)
    parts.append("=== TEXTBOOK PASSAGES ===")
    for s in guide.sources:
        parts.append(f"[{s.label}] {s.citation} -- {s.path}\n\"\"\"\n{s.text}\n\"\"\"")
    if errors:
        bullet = "\n".join(f"  - {e}" for e in errors)
        parts.append("=== YOUR PREVIOUS ANSWER WAS REJECTED ===\nFix these problems and answer again:\n" + bullet)
    return "\n\n".join(parts) + "\n"
