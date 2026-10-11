"""
sections.py
Section-aware episode splitting for audio_generator (spec §3.2): splits a
raw .md at every header level, narrates/cleans each section independently
(reusing narrate.py/cleaner.py completely unchanged), then groups
consecutive sections into episodes targeting a real, measured listening
length instead of one unbounded MP3 per source file. notes content type
only -- textbook has its own separate, PDF-anchored chapter-boundary
system (textbook/chapter_index.py) worth investigating for reuse instead
of duplicating this header-based approach (spec §9).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from core.env.gemini_utils import get_gemini_client, load_dotenv_override

from audio_generator.cleaner import clean_markdown_for_speech
from audio_generator.narrate import _split_into_pieces, chunk_for_narration, narrate_chunks

AUDIOGEN_SECTIONS_CHARS_PER_MINUTE = int(os.environ.get("AUDIOGEN_SECTIONS_CHARS_PER_MINUTE", "969"))
AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES = int(os.environ.get("AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES", "10"))
AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES = int(os.environ.get("AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES", "20"))

_HEADER_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+)$", re.MULTILINE)


@dataclass
class Section:
    title: str | None  # None for content before the first header
    body: str  # raw markdown, header line itself excluded


@dataclass
class NarratedSection:
    title: str  # already narrated+cleaned; "" if the section had no title
    text: str  # already narrated+cleaned body


@dataclass
class Episode:
    text: str  # concatenated title+body for every section in this episode
    section_titles: list[str] = field(default_factory=list)


def _split_oversized_section(section: Section, max_chars: int) -> list[Section]:
    """Split a long raw section on narration's paragraph/code-block boundaries.

    Cleaner later flattens whitespace, so these boundaries must be kept as
    separate sections before narration. An indivisible paragraph can still
    exceed the target; it remains intact rather than being cut mid-sentence.
    Repeating the title gives each continuation a useful episode label.
    """
    title_len = len(section.title or "") + (2 if section.title else 0)
    if title_len + len(section.body) <= max_chars:
        return [section]

    pieces = [piece.strip() for piece in _split_into_pieces(section.body)]
    if len(pieces) < 2:
        return [section]

    split_sections: list[Section] = []
    current: list[str] = []
    for piece in pieces:
        candidate = "\n\n".join([*current, piece])
        if current and title_len + len(candidate) > max_chars:
            split_sections.append(Section(title=section.title, body="\n\n".join(current)))
            current = []
        current.append(piece)
    if current:
        split_sections.append(Section(title=section.title, body="\n\n".join(current)))
    return split_sections


def split_into_sections(
    md_text: str,
    max_chars: int = AUDIOGEN_SECTIONS_CHARS_PER_MINUTE * AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES,
) -> list[Section]:
    """Split raw Markdown at every ATX header, then oversized leaf sections
    at paragraph boundaries before narration removes those boundaries.
    """
    matches = list(_HEADER_PATTERN.finditer(md_text))
    if not matches:
        return _split_oversized_section(Section(title=None, body=md_text), max_chars)

    sections: list[Section] = []
    if matches[0].start() > 0 and md_text[:matches[0].start()].strip():
        sections.append(Section(title=None, body=md_text[:matches[0].start()]))

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        sections.append(Section(title=match.group(2).strip(), body=md_text[start:end]))
    return [part for section in sections for part in _split_oversized_section(section, max_chars)]


def narrate_sections(sections: list[Section]) -> list[NarratedSection]:
    """Narrates and cleans every section's body via ONE shared, concurrent
    dispatch across the whole document's chunks (spec §3.2) -- every
    section's chunks are flattened into a single list *before* narrating
    anything, rather than looping section-by-section and calling
    narrate_for_speech() once per section (which would confine each
    section's concurrency to its own separate, serialized batch instead of
    giving the whole document's chunks one shared concurrency budget).
    Results are regrouped back into per-section text by position after the
    single narrate_chunks() call returns -- order-preserving, not
    completion-order-dependent, same guarantee narrate_chunks() itself
    provides for individual chunks.

    A section's title is cleaned (regex-only, no LLM call -- titles are
    short and essentially never equation-dense) but never flattened in
    with body chunks: headers must be resolved before any text reaches
    the LLM, not recovered from its output."""
    load_dotenv_override()
    client = get_gemini_client()

    chunk_lists = [chunk_for_narration(section.body) for section in sections]
    flat_chunks = [chunk for chunks in chunk_lists for chunk in chunks]
    flat_narrated = narrate_chunks(flat_chunks, client=client)

    result = []
    pos = 0
    for section, chunks in zip(sections, chunk_lists):
        narrated_chunks = flat_narrated[pos:pos + len(chunks)]
        pos += len(chunks)
        title = clean_markdown_for_speech(section.title) if section.title else ""
        text = clean_markdown_for_speech("\n\n".join(narrated_chunks))
        result.append(NarratedSection(title=title, text=text))
    return result


def _episode_text(parts: list[NarratedSection]) -> str:
    pieces = [f"{p.title}. {p.text}".strip() if p.title else p.text for p in parts if p.title or p.text]
    return "\n\n".join(pieces)


def group_sections_into_episodes(
    narrated_sections: list[NarratedSection],
    chars_per_minute: int = AUDIOGEN_SECTIONS_CHARS_PER_MINUTE,
    target_min_minutes: int = AUDIOGEN_SECTIONS_TARGET_MIN_MINUTES,
    target_max_minutes: int = AUDIOGEN_SECTIONS_TARGET_MAX_MINUTES,
) -> list[Episode]:
    """Greedily pack consecutive narrated sections up to target_max.

    The minimum is a soft target: a paragraph boundary may force a shorter
    episode. An indivisible paragraph can still exceed the maximum on its
    own, but no neighbor is merged into that episode.
    """
    max_chars = chars_per_minute * target_max_minutes

    episodes: list[Episode] = []
    current: list[NarratedSection] = []
    for section in narrated_sections:
        if current and len(_episode_text([*current, section])) > max_chars:
            episodes.append(Episode(text=_episode_text(current), section_titles=[s.title for s in current if s.title]))
            current = []
        current.append(section)
    if current:
        episodes.append(Episode(text=_episode_text(current), section_titles=[s.title for s in current if s.title]))
    return episodes
