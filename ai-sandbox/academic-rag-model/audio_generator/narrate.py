"""
narrate.py
Chunked, holistic LaTeX-to-narration rewrite via the Gemini API, running
before cleaner.py on the raw .md (spec §3.1 v3). Deliberately has zero
dependency on cleaner.py in either direction: a chunk this module can't
successfully rewrite is returned unmodified, and cleaner.py's existing
(unchanged) regex wrap catches whatever raw LaTeX survives downstream.

v3 (2026-09-09) replaces v2's local qwen2-math:7b call (measured at ~6h
for one equation-dense file -- impractical for real batch use) with
tiered Gemini API calls: a chunk with no LaTeX/math markers at all makes
zero API calls (free), a chunk with sparse/simple notation is routed to a
cheap model, and a chunk with dense equations or \\begin/\\end
environments is routed to a more capable model. No local-Ollama fallback
tier -- a missing/invalid GEMINI_API_KEY or an exhausted-retries API call
both degrade straight to the chunk's original, unmodified text.
"""
from __future__ import annotations

import os
import re

from common.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override

AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL = os.environ.get("AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL", "gemini-3.1-flash-lite")
AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL = os.environ.get("AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL", "gemini-2.5-flash")
_TIER_MODELS = {"light": AUDIOGEN_NARRATE_GEMINI_LIGHT_MODEL, "heavy": AUDIOGEN_NARRATE_GEMINI_HEAVY_MODEL}

AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD = float(os.environ.get("AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD", "0.15"))
AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD = int(os.environ.get("AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD", "3"))

_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
_PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")
_CHUNK_TARGET_SIZE = 2500
_MIN_LENGTH_RATIO = 0.5

_LATEX_SPAN_PATTERN = re.compile(r"\$\$[^\$]+\$\$|\$[^\$]+\$")
_LATEX_COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+")
_LATEX_ENV_PATTERN = re.compile(r"\\begin\{[^}]+\}")
# Greek letters + common math-operator/arrow ranges, for notation typed as
# literal Unicode rather than LaTeX (e.g. "the parameter α" in prose).
_MATH_UNICODE_PATTERN = re.compile("[\u0370-\u03ff\u2190-\u21ff\u2200-\u22ff]")

_PROMPT_TEMPLATE = """Rewrite this passage as natural spoken prose for audio narration. \
Describe mathematical notation in words rather than symbols. Do not omit or summarize any \
content -- rewrite every sentence, changing only how notation is expressed.

--- PASSAGE START ---
{chunk}
--- PASSAGE END ---"""


def _split_into_pieces(md_text: str) -> list[str]:
    """Splits on paragraph boundaries, treating a fenced code block as one
    atomic piece regardless of blank lines inside it (spec §3.1)."""
    pieces = []
    pos = 0
    for match in _CODE_BLOCK_PATTERN.finditer(md_text):
        before = md_text[pos:match.start()]
        pieces.extend(p for p in _PARAGRAPH_SPLIT_PATTERN.split(before) if p.strip())
        pieces.append(match.group())
        pos = match.end()
    pieces.extend(p for p in _PARAGRAPH_SPLIT_PATTERN.split(md_text[pos:]) if p.strip())
    return pieces


def _group_into_chunks(pieces: list[str]) -> list[str]:
    """Groups paragraph pieces into ~_CHUNK_TARGET_SIZE-character chunks.
    A code-block piece is never merged with anything else -- it always
    becomes its own chunk (spec §3.1)."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for piece in pieces:
        if _CODE_BLOCK_PATTERN.fullmatch(piece):
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.append(piece)
            continue
        if current and current_len + len(piece) > _CHUNK_TARGET_SIZE:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(piece)
        current_len += len(piece)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _classify_chunk(chunk: str) -> str:
    """Returns "skip" | "light" | "heavy" (spec §3.1 v3) -- thresholds are
    a starting guess, flagged in spec §9 for empirical tuning."""
    spans = _LATEX_SPAN_PATTERN.findall(chunk)
    if not spans and not _MATH_UNICODE_PATTERN.search(chunk):
        return "skip"
    if _LATEX_ENV_PATTERN.search(chunk):
        return "heavy"
    ratio = sum(len(s) for s in spans) / len(chunk) if chunk else 0.0
    command_count = len(_LATEX_COMMAND_PATTERN.findall(chunk))
    if ratio >= AUDIOGEN_NARRATE_MATH_RATIO_THRESHOLD or command_count >= AUDIOGEN_NARRATE_MATH_COMMAND_THRESHOLD:
        return "heavy"
    return "light"


def _passes_sanity_check(original: str, rewritten) -> bool:
    """Cheap proxy for 'did the model drop/summarize content' (spec §3.1,
    §9 -- exact ratio flagged as needing real tuning, not a validated
    constant)."""
    if not isinstance(rewritten, str) or not rewritten.strip():
        return False
    return len(rewritten) >= _MIN_LENGTH_RATIO * len(original)


def _call_gemini(prompt: str, model: str, client) -> str | None:
    """Mirrors viz/llm_fallback.py's _call_gemini exactly -- relies on
    common.gemini_utils.call_with_retries for transient-failure retry/
    backoff, the same mechanism every other Gemini call in this project
    already uses. Returns None only once retries are exhausted, never
    raises."""
    try:
        response = call_with_retries(lambda: client.models.generate_content(
            model=model, contents=prompt, config={"temperature": 0.2},
        ))
        return (response.text or "").strip()
    except Exception as err:
        print(f"WARNING: Gemini call to model '{model}' failed after retries ({err})")
        return None


def _narrate_chunk(chunk: str, client) -> str:
    """Rewrites one chunk via the tier-appropriate Gemini model (spec
    §3.1 v3). No local fallback if client is None or the call fails --
    just the chunk's original, unmodified text, exactly as v2 behaved on
    an unreachable server."""
    tier = _classify_chunk(chunk)
    if tier == "skip" or client is None:
        return chunk
    prompt = _PROMPT_TEMPLATE.format(chunk=chunk)
    result = _call_gemini(prompt, _TIER_MODELS[tier], client)
    if result is not None and _passes_sanity_check(chunk, result):
        return result
    return chunk


def narrate_for_speech(md_text: str) -> str:
    """Entry point pipeline.py calls first, on raw .md text, before
    cleaner.clean_markdown_for_speech() (spec §3.1). Builds one Gemini
    client per file (not per chunk) -- get_gemini_client() is cheap
    (no network call itself), and this keeps pipeline.py's call site
    completely unchanged from v2."""
    load_dotenv_override()
    client = get_gemini_client()
    chunks = _group_into_chunks(_split_into_pieces(md_text))
    narrated = [
        chunk if _CODE_BLOCK_PATTERN.fullmatch(chunk) else _narrate_chunk(chunk, client)
        for chunk in chunks
    ]
    return "\n\n".join(narrated)
