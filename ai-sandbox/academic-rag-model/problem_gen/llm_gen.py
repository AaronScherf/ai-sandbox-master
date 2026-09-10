"""
llm_gen.py
Generation of a new practice problem plus a worked solution, with
self-verification and retry-with-feedback (spec:
docs/superpowers/specs/2026-09-03-problem-generation-design.md §4).
Much simpler than viz/llm_fallback.py by design: the output here is
text (a problem and a solution), not executable code, so there is no
subprocess execution or sandboxing involved at all.

Two backends: Gemini (default) and local Ollama (opt-in via
PROBLEMGEN_BACKEND=ollama). 2026-09-06, defaulted to Gemini after a
real feasibility spike (see docs/status/2026-09-05-problem-generation-status.md):
local qwen2-math:7b never once produced an accepted result across two
independent real trials on a technique-constrained request, while
gemini-3.1-flash-lite passed 9/9 across three different topics in the
same testing, at negligible real cost and dramatically faster (seconds
vs 10-50 minutes per attempt). Local generation stays available as an
opt-in for fully free/private use.
"""
from __future__ import annotations

import os
import re

from common.gemini_utils import call_with_retries
from common.ollama_utils import OLLAMA_TIMEOUT, OllamaTimeout, call_ollama

PROBLEMGEN_BACKEND = os.environ.get("PROBLEMGEN_BACKEND", "gemini")  # "gemini" | "ollama"
PROBLEMGEN_GEMINI_MODEL = os.environ.get("PROBLEMGEN_GEMINI_MODEL", "gemini-3.1-flash-lite")
PROBLEMGEN_OLLAMA_MODEL = os.environ.get("PROBLEMGEN_OLLAMA_MODEL", "qwen2-math:7b")  # corrected
# 2026-09-05 during real-corpus validation (see docs/status/2026-09-05-problem-generation-status.md):
# the design's original choice, "qwen2.5-math:7b", is not a real pullable Ollama library
# model -- only a community upload under a different namespace, or this older-generation
# official one, actually exist. qwen2-math:7b is the one confirmed to pull and run.
OLLAMA_REQUEST_TIMEOUT_SECONDS = 300
# 2026-09-05, corrected during real-corpus validation (see
# docs/status/2026-09-05-problem-generation-status.md): the original value (180s,
# copied from viz/llm_fallback.py's own constant) was too short for this
# module's actual workload -- every real call on CPU-only inference hit
# the timeout. A real run measured on this machine's CPU-only Ollama
# (qwen2-math:7b, no GPU) took 22m43s wall-clock for one full
# generate-then-verify cycle (2 generation attempts + 2 verification
# calls) -- consistent with individual calls averaging several minutes
# each for this module's longer expected output (a full problem
# statement plus a full worked solution, vs viz's shorter code snippet).
# 300s is a real-evidence-backed increase, not a guess; a slow machine
# can still hit it on a verbose response, in which case the existing
# OLLAMA_TIMEOUT retry path (not a hard failure) handles it.
MAX_ATTEMPTS = 5
# 2026-09-06, bumped from 3 during real-corpus validation of the split
# TECHNIQUE/CORRECTNESS verification (see
# docs/status/2026-09-05-problem-generation-status.md): a real trial exhausted
# all 3 attempts with only 2 of them actually reaching a real generated
# response (the third was consumed entirely by an OLLAMA_TIMEOUT retry,
# not a bad proof) -- both real attempts were then correctly rejected
# for using the wrong technique, but there was no attempt left to see
# whether the model could ever produce a compliant one. 5 gives real
# headroom for that question without doubling the worst case.

_GENERATION_PROMPT_TEMPLATE = """You are writing a NEW practice problem for a student studying {topic}, in \
the same style, notation, and difficulty as their own course's problem sets. Do NOT copy any of the example \
problems below verbatim -- write an original problem that tests the same kind of technique.

Required constraint from the student's own request: "{topic}"
You MUST satisfy this constraint exactly, even if it means using a different technique or approach than \
the style examples below use.
{style_block}{content_block}
Respond in exactly this format, with both sections present:

## Problem
<the new problem statement>

## Solution
<a full, correct, worked solution to the problem you just wrote>
"""

_VERIFICATION_PROMPT_TEMPLATE = """Judge the problem and solution below on two SEPARATE questions -- answer \
each one independently, without letting your judgment on one influence the other. A single combined \
judgment tends to let an easy correctness call paper over a harder, unaddressed technique mismatch, so \
judge them one at a time.

Student's original request: "{topic}"

Problem:
{problem_text}

Solution:
{solution_text}

Respond with EXACTLY two lines, in this format:
TECHNIQUE: YES or NO -- does the solution actually use the specific technique or approach the student's \
request requires, not merely some other valid proof of the same fact? If NO, briefly say which technique \
it used instead.
CORRECTNESS: VALID, or INVALID: <short reason> -- is the solution mathematically correct and complete for \
the stated problem, independent of which technique it uses?

Respond with nothing else besides these two lines."""

_SECTION_PATTERN = re.compile(r"##\s*Problem\s*\n(.*?)\n##\s*Solution\s*\n(.*)", re.IGNORECASE | re.DOTALL)
_TECHNIQUE_LINE_PATTERN = re.compile(r"TECHNIQUE:[ \t]*(YES|NO)[ \t]*[:\-]?[ \t]*(.*)", re.IGNORECASE)
_CORRECTNESS_LINE_PATTERN = re.compile(r"CORRECTNESS:[ \t]*(VALID|INVALID)[ \t]*[:\-]?[ \t]*(.*)", re.IGNORECASE)
# [ \t]* (not \s*) between the YES/NO or VALID/INVALID token and its trailing detail --
# \s* also matches newlines, which let a bare "TECHNIQUE: NO" with nothing else on its own
# line swallow the *entire next line* (a separate "CORRECTNESS: ..." line) into its own
# detail capture, corrupting retry feedback with garbage like "used instead: CORRECTNESS:
# VALID" fed into the next generation attempt -- confirmed in a real trial, see
# docs/status/2026-09-05-problem-generation-status.md's 2026-09-06 entry.


def _build_generation_prompt(
    topic: str, style_examples: list[str], content_excerpts: list[str],
    previous_problem: str | None = None, previous_solution: str | None = None,
    previous_error: str | None = None,
) -> str:
    """Composes the prompt sent to Ollama to generate a new problem.
    First attempt (previous_error is None): topic + style examples +
    content excerpts only. Retry attempt (previous_error set): the same
    base prompt plus the previous attempt's problem/solution (if any --
    omitted when extraction itself failed, since there's nothing to
    show) and the exact failure reason, asking for a corrected pair."""
    style_block = ""
    if style_examples:
        examples = "\n\n".join(f"- {e}" for e in style_examples)
        style_block = (
            f"\nExample problems from the student's own course materials (for style and "
            f"difficulty only -- do not copy them):\n{examples}\n"
        )
    content_block = ""
    if content_excerpts:
        excerpts = "\n\n".join(content_excerpts)
        content_block = f"\nBackground from the student's own textbooks (for grounding correctness):\n{excerpts}\n"
    base = _GENERATION_PROMPT_TEMPLATE.format(topic=topic, style_block=style_block, content_block=content_block)
    if previous_error is None:
        return base
    previous_block = ""
    if previous_problem is not None:
        previous_block = (
            f"\nYour previous attempt produced:\n## Problem\n{previous_problem}\n\n"
            f"## Solution\n{previous_solution}\n"
        )
    return (
        f"{base}\n"
        f"{previous_block}"
        f"That attempt failed with: {previous_error}\n"
        f"Write a corrected problem and solution that fixes this specific issue. Respond in exactly the "
        f"same '## Problem' / '## Solution' format. Do not mention this correction, the previous attempt, "
        f"or the verification process anywhere in your answer -- write the corrected problem and solution "
        f"as if this were your first and only attempt."
    )


def _build_verification_prompt(topic: str, problem_text: str, solution_text: str) -> str:
    return _VERIFICATION_PROMPT_TEMPLATE.format(topic=topic, problem_text=problem_text, solution_text=solution_text)


def _extract_problem_and_solution(response_text: str) -> tuple[str, str] | None:
    match = _SECTION_PATTERN.search(response_text)
    if match is None:
        return None
    problem_text, solution_text = match.group(1).strip(), match.group(2).strip()
    if not problem_text or not solution_text:
        return None
    return problem_text, solution_text


def _parse_verdict(response_text: str) -> str | None:
    """Returns None only when both the TECHNIQUE and CORRECTNESS lines
    pass, or a short combined reason string otherwise -- fed back into
    the next generation attempt's prompt. Judged as two separately
    labeled lines rather than one combined verdict: a real trial showed
    a single combined verdict kept passing solutions that ignored an
    explicit technique constraint, since an easy correctness judgment
    could paper over a harder, unaddressed technique mismatch (see
    docs/status/2026-09-05-problem-generation-status.md's 2026-09-06 entry).
    Either line missing or unparseable fails closed for that check
    rather than being silently trusted as passing. Tolerates markdown
    bold markers (e.g. "**VALID**") around either label or value."""
    normalized = response_text.replace("*", "")  # tolerate markdown bold around either label or value
    reasons: list[str] = []

    technique_match = _TECHNIQUE_LINE_PATTERN.search(normalized)
    if technique_match is None:
        reasons.append("the response did not include a parseable 'TECHNIQUE: YES/NO' line")
    elif technique_match.group(1).upper() == "NO":
        detail = technique_match.group(2).strip(" -")
        reasons.append(
            f"the solution does not use the required technique"
            f"{f' (used instead: {detail})' if detail else ''}"
        )

    correctness_match = _CORRECTNESS_LINE_PATTERN.search(normalized)
    if correctness_match is None:
        reasons.append("the response did not include a parseable 'CORRECTNESS: VALID/INVALID' line")
    elif correctness_match.group(1).upper() == "INVALID":
        detail = correctness_match.group(2).strip(" -")
        reasons.append(f"the solution is incorrect or incomplete{f': {detail}' if detail else ''}")

    return "; ".join(reasons) if reasons else None


def _call_gemini(prompt: str, client) -> str | None:
    """Calls the configured Gemini model, relying on
    common.gemini_utils.call_with_retries for transient-failure retry/
    backoff (the same mechanism every other Gemini call in this project
    already uses) -- returns None only once those retries are
    exhausted, never raises."""
    try:
        response = call_with_retries(lambda: client.models.generate_content(
            model=PROBLEMGEN_GEMINI_MODEL, contents=prompt, config={"temperature": 0.2},
        ))
        return (response.text or "").strip()
    except Exception as err:
        print(f"WARNING: Gemini call to model '{PROBLEMGEN_GEMINI_MODEL}' failed after retries ({err})")
        return None


def _call_model(prompt: str, client) -> str | None | OllamaTimeout:
    """Dispatches to the configured backend (PROBLEMGEN_BACKEND) --
    Gemini by default, local Ollama if explicitly selected. Both return
    the same shape (str | None | OllamaTimeout) so generate_and_verify's
    retry loop doesn't need to know which backend is active: Gemini's
    own call_with_retries already handles transient retries internally,
    so its path never produces OLLAMA_TIMEOUT, only None (exhausted) or
    a real response -- the OLLAMA_TIMEOUT branch below simply never
    triggers when the Gemini backend is active. No status print here --
    this dispatcher is also used for the verification call, which isn't
    "generating a practice problem"; see generate_and_verify's own
    announcement before its generation call only."""
    if PROBLEMGEN_BACKEND == "ollama":
        return call_ollama(prompt, PROBLEMGEN_OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT_SECONDS)
    return _call_gemini(prompt, client)


def generate_and_verify(
    topic: str, style_examples: list[str], content_excerpts: list[str], client,
) -> tuple[str, str] | None:
    """Returns (problem_text, solution_text) once verification confirms
    the solution is correct, or None if the configured backend is
    unreachable or verification never passes within MAX_ATTEMPTS. Never
    raises. `client` is the Gemini client (unused when
    PROBLEMGEN_BACKEND=ollama, but always required so callers -- which
    already hold a Gemini client for retrieval embeddings -- don't need
    to branch on backend themselves)."""
    try:
        previous_problem, previous_solution, previous_error = None, None, None
        for _ in range(MAX_ATTEMPTS):
            prompt = _build_generation_prompt(
                topic, style_examples, content_excerpts, previous_problem, previous_solution, previous_error,
            )
            if PROBLEMGEN_BACKEND == "ollama":
                print(f"Generating a practice problem via the local Ollama model ({PROBLEMGEN_OLLAMA_MODEL}) -- "
                      f"this can take a while...")
            else:
                print(f"Generating a practice problem via the Gemini API ({PROBLEMGEN_GEMINI_MODEL})...")
            response = _call_model(prompt, client)
            if response is None:
                return None  # backend unreachable -- not worth retrying
            if response is OLLAMA_TIMEOUT:
                previous_problem, previous_solution = None, None
                previous_error = (
                    f"the request to Ollama itself timed out after {OLLAMA_REQUEST_TIMEOUT_SECONDS}s -- "
                    f"the model may just be slow; try to respond more concisely"
                )
                continue

            extracted = _extract_problem_and_solution(response)
            if extracted is None:
                previous_problem, previous_solution = None, None
                previous_error = "the response did not contain both a '## Problem' and '## Solution' section"
                continue
            problem_text, solution_text = extracted

            # A verification-call timeout says nothing about whether problem_text/
            # solution_text is any good -- retrying the SAME verification (bounded
            # to MAX_ATTEMPTS tries) instead of falling through to the outer loop
            # avoids discarding a possibly-good pair and burning a whole
            # regeneration attempt on a problem that was never actually judged.
            verify_prompt = _build_verification_prompt(topic, problem_text, solution_text)
            for _ in range(MAX_ATTEMPTS):
                verify_response = _call_model(verify_prompt, client)
                if verify_response is not OLLAMA_TIMEOUT:
                    break
            else:
                return None  # verification never got a real response -- give up
            if verify_response is None:
                return None

            invalid_reason = _parse_verdict(verify_response)
            if invalid_reason is None:
                return problem_text, solution_text
            previous_problem, previous_solution, previous_error = problem_text, solution_text, invalid_reason
        return None
    except Exception as err:
        print(f"WARNING: problem generation failed unexpectedly ({err})")
        return None
