# agent/summary_enhance/prompt.py
"""Prompts for the enhancement pipeline. The contract here (grounded vs. external
blocks, formatting rules) is mirrored by schema.py/validate.py, which enforce it."""
from __future__ import annotations

import json

from agent.summary_enhance.schema import PLAN_SCHEMA, TOPIC_SCHEMA
from agent.summary_enhance.source_loader import GuideInput
from agent.summary_enhance.validate import MIN_SECTIONS, PLAN_MAX, PLAN_MIN

PROMPT_VERSION = "2026-10-05.1"

# Runtime text: "\\beta", "\\frac" (two real backslashes). A plain "\beta" here would
# teach the model the exact mistake we are warning about.
_DOUBLED_EXAMPLE = '"\\\\beta", "\\\\frac"'
_LENGTH_FACTOR = 1.2

_TOPIC_INSTRUCTIONS = """\
You are writing one topic of a thorough, standalone study guide for a graduate student.
You are given (1) an existing LLM-generated draft guide and (2) the exact textbook passages
it was built from, each tagged with a label such as [S1]. Write the topic "{topic}".
{others_line}
Length and structure
  * Write at least {target} words in total across all blocks (several pages). Depth matters
    more than brevity: state the assumptions, build the derivation step by step, explain what
    each term in the statistic measures, give the decision rule, say when the test is valid or
    breaks down, compare how the different textbooks present it, and list common pitfalls.
  * Organize the topic into at least {min_sections} sections. Each section has a short
    descriptive "heading" (one line, plain words, no markdown symbols) and ordered "blocks".
    A block is one or more paragraphs.

Two block types
  * "grounded": synthesis the textbooks support. List in "sources" the bare labels such as "S1"
    (no brackets) of every passage the block relies on. Merge the sources into one coherent explanation instead of summarizing
    each book in turn. Use ONLY what the passages state or directly imply. The draft guide is
    not a source: leave out of grounded blocks anything the passages do not support. Where the
    sources differ (notation, assumptions, scope) or one is silent, say so plainly. At least
    half of all your words must be in grounded blocks.
  * "external": your own additions that help a student (intuition, examples, general
    background) that the textbooks do not support. "sources" must be empty. Do not write
    "(External context)" or any tag yourself; which paragraphs are external is recorded separately.

Text rules
  * Never write [S#] markers or any citation inside "text".
  * Do not use markdown headings (#) or blockquotes (>) in "text", and do not write the phrases
    "(External context)" or "(Worked example". Lists and tables are fine.
  * Math is LaTeX in $...$ (inline) or $$...$$ (display). Put any formula longer than
    about ten symbols in its own $$...$$ block; keep short formulas inline. This is JSON, so
    every LaTeX backslash must be doubled ({doubled}); a single backslash before b, t, f, r
    or n silently corrupts the formula.

Return ONLY JSON matching this schema, with no markdown fences or commentary:
{schema}
"""

_PLAN_INSTRUCTIONS = """\
Read the draft study guide and the textbook passages below. List the {lo} to {hi} distinct
topics a student should have a dedicated section on, in a sensible teaching order. Titles are
short, unique, single-line phrases.

Return ONLY JSON matching this schema, with no markdown fences or commentary:
{schema}
"""

_WORKED_INSTRUCTIONS = """\
Below are the explanation and formulas for the topic "{title}" from a study guide. Write a
worked numeric example showing how to compute the test statistic, apply its decision rule, and
reach a conclusion.
  * Invent a small, simple dataset (a few observations or a small table) and state it
    explicitly. Call it illustrative.
  * Use the code execution tool to do ALL the arithmetic; report only numbers you computed.
    Show each intermediate quantity (estimates, variance pieces, the statistic, the critical
    value or p-value, the decision) with a short step-by-step explanation.
  * Use the same notation as the explanation below.
  * Plain Markdown paragraphs, lists and tables only. LaTeX math in $...$ or $$...$$; put any
    formula longer than about ten symbols in its own $$...$$ block.
  * No headings (#), no blockquotes (>), no citations, and do not write the phrases
    "(External context)" or "(Worked example".
  * At least 200 words. Return only the example.

=== EXPLANATION ===
{grounded}
"""


_IMPROVE_INSTRUCTIONS = """\

This is an IMPROVEMENT pass. The baseline guide below was written earlier from some of these
passages. Keep what the passages support (and its good structure where it helps), correct or
tighten anything the passages do not support, and integrate the additional passages (those marked
as class notes, slides, recitations, or other textbook sections). Rules:
  * Where a textbook and class notes or slides differ in notation, assumptions or claims, say so
    plainly in a grounded block that cites both labels, and prefer the textbook.
  * Class notes and slides may be hand-written or transcribed and can contain errors; do not repeat
    a class-note claim that a textbook contradicts without saying so.
  * Do not copy asides that are not about this topic (administrative remarks, other lectures).
  * A class-notes point is grounded only if a class-notes passage supports it; your own additions
    stay "external".
"""

_KIND_TEXT = {
    "textbook": "textbook", "ta_notes": "class notes/slides", "handwritten_notes": "hand-written class notes",
    "problem_set": "problem set", "excalidraw_notes": "lecture notes",
}


def _kind(source) -> str:
    if not source.doc_type:
        return ""
    kind = _KIND_TEXT.get(source.doc_type, source.doc_type)
    return f" ({kind}, {source.offering} offering)" if source.offering else f" ({kind})"


def _passages(guide: GuideInput, labels: set[str] | None = None, mode: str = "rewrite",
              body: str | None = None) -> str:
    if mode == "improve":
        head = ("=== BASELINE GUIDE (existing draft; keep what the passages support, correct or extend "
                "the rest; it is not a source) ===\n")
    else:
        head = "=== DRAFT GUIDE (not a source) ===\n"
    parts = [head + (guide.body if body is None else body), "=== TEXTBOOK PASSAGES ===" if mode != "improve" else "=== SOURCE PASSAGES ==="]
    for s in guide.sources:
        if labels is not None and s.label not in labels:
            continue
        parts.append(f"[{s.label}]{_kind(s)} {s.citation} -- {s.path}\n\"\"\"\n{s.text}\n\"\"\"")
    return "\n\n".join(parts)


def _rejected(errors: list[str] | None) -> str:
    if not errors:
        return ""
    bullet = "\n".join(f"  - {e}" for e in errors)
    return "\n\n=== YOUR PREVIOUS ANSWER WAS REJECTED ===\nFix these problems and answer again:\n" + bullet


def build_plan_prompt(guide: GuideInput, errors: list[str] | None = None) -> str:
    head = f"(prompt version {PROMPT_VERSION})\n\n" + _PLAN_INSTRUCTIONS.format(
        lo=PLAN_MIN, hi=PLAN_MAX, schema=json.dumps(PLAN_SCHEMA, indent=2))
    return head + "\n" + _passages(guide) + _rejected(errors) + "\n"


def build_topic_prompt(guide: GuideInput, topic: str, other_topics: list[str], min_words: int,
                       errors: list[str] | None = None, *, source_labels: set[str] | None = None,
                       mode: str = "rewrite", baseline_body: str | None = None) -> str:
    others_line = ""
    if other_topics:
        listed = ", ".join(json.dumps(t) for t in other_topics)
        others_line = (f"Other topics ({listed}) get their own sections of the finished guide; "
                       "do not duplicate their content beyond what this topic needs.\n")
    head = f"(prompt version {PROMPT_VERSION})\n\n" + _TOPIC_INSTRUCTIONS.format(
        topic=topic, others_line=others_line, target=int(min_words * _LENGTH_FACTOR),
        min_sections=MIN_SECTIONS, doubled=_DOUBLED_EXAMPLE,
        schema=json.dumps(TOPIC_SCHEMA, indent=2))
    if mode == "improve":
        head += _IMPROVE_INSTRUCTIONS
    return head + "\n" + _passages(guide, source_labels, mode, baseline_body) + _rejected(errors) + "\n"


def build_worked_example_prompt(topic_title: str, grounded_text: str, errors: list[str] | None = None) -> str:
    return (f"(prompt version {PROMPT_VERSION})\n\n"
            + _WORKED_INSTRUCTIONS.format(title=topic_title, grounded=grounded_text)
            + _rejected(errors) + "\n")
