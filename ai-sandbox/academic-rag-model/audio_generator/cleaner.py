"""
cleaner.py
Markdown-to-prose conversion for TTS narration: strips code blocks, LaTeX
delimiters, video_notes-style inline timestamp citations, and remaining
markdown syntax so the result reads as natural prose. Spec §3.
"""
from __future__ import annotations

import re

import markdown
from bs4 import BeautifulSoup

_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
_LATEX_BLOCK_PATTERN = re.compile(r"\$\$([^\$]+)\$\$")
_LATEX_INLINE_PATTERN = re.compile(r"\$([^\$]+)\$")
# Matches a video_notes-style citation attached to a sentence, e.g.
# "([04:12](https://youtu.be/abc123&t=252s))" -- only has value as a
# clickable link, meaningless read aloud (spec §3).
_CITATION_PATTERN = re.compile(r"\(\[[\d:]+\]\([^)]+\)\)")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_markdown_for_speech(md_text: str) -> str:
    """Converts raw Markdown into narration-ready prose (spec §3, steps 1-5,
    applied in this exact order)."""
    text = _CODE_BLOCK_PATTERN.sub(" [Code snippet omitted.] ", md_text)
    text = _INLINE_CODE_PATTERN.sub(r"\1", text)
    text = _LATEX_BLOCK_PATTERN.sub(r" Equation: \1. ", text)
    text = _LATEX_INLINE_PATTERN.sub(r" \1 ", text)
    text = _CITATION_PATTERN.sub("", text)
    html = markdown.markdown(text)
    soup = BeautifulSoup(html, "html.parser")
    clean_text = soup.get_text(separator=" ")
    return _WHITESPACE_PATTERN.sub(" ", clean_text).strip()
