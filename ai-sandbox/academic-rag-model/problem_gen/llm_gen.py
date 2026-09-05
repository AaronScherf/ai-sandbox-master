"""
llm_gen.py
Local Ollama generation of a new practice problem plus a worked
solution, with self-verification and retry-with-feedback (spec:
docs/superpowers/specs/2026-09-03-problem-generation-design.md §4).
Much simpler than viz/llm_fallback.py by design: the output here is
text (a problem and a solution), not executable code, so there is no
subprocess execution or sandboxing involved at all.
"""
from __future__ import annotations

import os
import re

from common.ollama_utils import OLLAMA_TIMEOUT, call_ollama

PROBLEMGEN_OLLAMA_MODEL = os.environ.get("PROBLEMGEN_OLLAMA_MODEL", "qwen2.5-math:7b")
OLLAMA_REQUEST_TIMEOUT_SECONDS = 180
MAX_ATTEMPTS = 3

_GENERATION_PROMPT_TEMPLATE = """You are writing a NEW practice problem for a student studying {topic}, in \
the same style, notation, and difficulty as their own course's problem sets. Do NOT copy any of the example \
problems below verbatim -- write an original problem that tests the same kind of technique.
{style_block}{content_block}
Respond in exactly this format, with both sections present:

## Problem
<the new problem statement>

## Solution
<a full, correct, worked solution to the problem you just wrote>
"""

_VERIFICATION_PROMPT_TEMPLATE = """Check whether the solution below is actually correct and complete for the \
stated problem.

Problem:
{problem_text}

Solution:
{solution_text}

Respond with exactly "VALID" if the solution is correct and complete, or "INVALID: <short reason>" if it is \
wrong, incomplete, or the problem itself is ill-posed. Respond with nothing else."""

_SECTION_PATTERN = re.compile(r"##\s*Problem\s*\n(.*?)\n##\s*Solution\s*\n(.*)", re.IGNORECASE | re.DOTALL)
_INVALID_PATTERN = re.compile(r"INVALID:\s*(.*)", re.IGNORECASE | re.DOTALL)


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
        f"same '## Problem' / '## Solution' format."
    )


def _build_verification_prompt(problem_text: str, solution_text: str) -> str:
    return _VERIFICATION_PROMPT_TEMPLATE.format(problem_text=problem_text, solution_text=solution_text)


def _extract_problem_and_solution(response_text: str) -> tuple[str, str] | None:
    match = _SECTION_PATTERN.search(response_text)
    if match is None:
        return None
    problem_text, solution_text = match.group(1).strip(), match.group(2).strip()
    if not problem_text or not solution_text:
        return None
    return problem_text, solution_text


def _parse_verdict(response_text: str) -> str | None:
    """Returns None when the solution is verified VALID, or a short
    reason string when INVALID -- the reason is fed back into the next
    generation attempt's prompt. An unparseable response is treated as
    invalid (fail closed) rather than silently trusted as valid."""
    stripped = response_text.strip()
    if stripped.upper().startswith("VALID"):
        return None
    match = _INVALID_PATTERN.match(stripped)
    if match:
        return match.group(1).strip() or "the verification response gave no reason"
    return "the verification response was not in the expected VALID/INVALID format"


def generate_and_verify(
    topic: str, style_examples: list[str], content_excerpts: list[str],
) -> tuple[str, str] | None:
    """Returns (problem_text, solution_text) once verification confirms
    the solution is correct, or None if Ollama is unreachable or
    verification never passes within MAX_ATTEMPTS. Never raises."""
    try:
        previous_problem, previous_solution, previous_error = None, None, None
        for _ in range(MAX_ATTEMPTS):
            prompt = _build_generation_prompt(
                topic, style_examples, content_excerpts, previous_problem, previous_solution, previous_error,
            )
            print(f"Generating a practice problem via the local Ollama model ({PROBLEMGEN_OLLAMA_MODEL}) -- "
                  f"this can take a while...")
            response = call_ollama(prompt, PROBLEMGEN_OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT_SECONDS)
            if response is None:
                return None  # Ollama unreachable -- not worth retrying
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

            verify_prompt = _build_verification_prompt(problem_text, solution_text)
            verify_response = call_ollama(verify_prompt, PROBLEMGEN_OLLAMA_MODEL, OLLAMA_REQUEST_TIMEOUT_SECONDS)
            if verify_response is None:
                return None
            if verify_response is OLLAMA_TIMEOUT:
                previous_problem, previous_solution = problem_text, solution_text
                previous_error = "the verification request itself timed out"
                continue

            invalid_reason = _parse_verdict(verify_response)
            if invalid_reason is None:
                return problem_text, solution_text
            previous_problem, previous_solution, previous_error = problem_text, solution_text, invalid_reason
        return None
    except Exception as err:
        print(f"WARNING: problem generation failed unexpectedly ({err})")
        return None
