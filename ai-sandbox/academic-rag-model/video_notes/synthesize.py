"""
synthesize.py
Builds the per-group synthesis prompt (multi-video, timestamp-linked)
and calls a local Ollama model to produce the final Markdown note. No
paid API call. Spec §3 step 5, §6, §7.
"""
from __future__ import annotations

import os

from common.ollama_utils import OLLAMA_TIMEOUT, call_ollama

VIDEONOTES_OLLAMA_MODEL = os.environ.get("VIDEONOTES_OLLAMA_MODEL", "qwen2.5:7b-instruct")
VIDEONOTES_OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("VIDEONOTES_OLLAMA_TIMEOUT", "1800"))

_PROMPT_TEMPLATE = """You are an expert pedagogue. Review the following raw lecture transcript(s) \
for "{group_title}", embedded with chronological timeline links back to their source video(s).

Synthesize the core theoretical framework, main results, and structural takeaways into a polished, \
scannable academic report covering all the lectures together as one cohesive whole.

STRICT FORMATTING RULES:
1. Use clear Markdown headers and bullet points.
2. Wrap all mathematical variables, expressions, and formulas in LaTeX delimiters \
(inline `$x^2$`, block `$$ ... $$`).
3. Cite the provided timestamp links inline at the end of the sentence introducing each key concept, \
theorem, or step transition, exactly as given (they already identify which lecture they come from), \
so the reader can click through to that exact moment.

--- TRANSCRIPT START ---
{transcript_block}
--- TRANSCRIPT END ---"""


def _format_timestamp(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _timestamp_url(video_url: str, seconds: int) -> str:
    separator = "&" if "?" in video_url else "?"
    return f"{video_url}{separator}t={seconds}s"


def build_synthesis_prompt(
    group_title: str, member_video_ids: list, videos_by_id: dict, transcripts_by_id: dict,
) -> str:
    """Every transcript line is tagged with its own video's label and
    timestamp link, so a group spanning multiple videos can still cite
    the correct source video, not just a bare second count (spec §6)."""
    multi_video = len(member_video_ids) > 1
    lines = []
    for index, video_id in enumerate(member_video_ids, start=1):
        video = videos_by_id[video_id]
        label = f"Lecture {index}" if multi_video else video.title
        for segment in transcripts_by_id[video_id]:
            seconds = int(segment.start)
            timestamp = _format_timestamp(seconds)
            url = _timestamp_url(video.url, seconds)
            lines.append(f"[{label} @ {timestamp}]({url}): {segment.text.strip()}")
    return _PROMPT_TEMPLATE.format(group_title=group_title, transcript_block="\n".join(lines))


def synthesize_group_note(
    prompt: str, model: str = VIDEONOTES_OLLAMA_MODEL, request_timeout: int = VIDEONOTES_OLLAMA_TIMEOUT_SECONDS,
) -> str | None:
    result = call_ollama(prompt, model, request_timeout)
    if result is None:
        print(f"WARNING: could not reach Ollama to synthesize lecture notes (model={model}).")
        return None
    if result is OLLAMA_TIMEOUT:
        print(f"WARNING: Ollama synthesis call timed out after {request_timeout}s (model={model}).")
        return None
    return result
