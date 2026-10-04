# agent/summary_enhance/render.py
"""Deterministic Markdown rendering of validated enhancement output.

The body is a clean study document: no citation markers, no Sources list, no
comments. Provenance lives in the frontmatter `source_map` (chunk -> sections
that rely on it). External paragraphs carry a light (External context) tag."""
from __future__ import annotations

import json
import re

from agent.summary_enhance.mathfmt import split_display_math
from agent.summary_enhance.schema import Block, Enhanced
from agent.summary_enhance.source_loader import GuideInput

GENERATED_BY = "academic-rag-model/agent/summary_enhance/enhance.py"
EXTERNAL_TAG = "*(External context)*"
WORKED_TAG = "*(Worked example — illustrative data, not from the textbooks)*"
EXTERNAL_MARKER = "(External context)"
_INTRO = ("*Study guide synthesized from the course textbooks. Passages marked (External context) "
          "or (Worked example) come from outside the textbooks.*")
_STRUCTURE_START_RE = re.compile(r"^\s*(?:\$|[-*+]\s|\d+[.)]\s|\||>|```|~~~)")
_FENCE_LINE_RE = re.compile(r"^\s*(?:```|~~~)")


def _paragraphs(text: str) -> list[str]:
    """Split on blank lines, except inside code fences and $$ display blocks."""
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = in_display = False
    for line in text.strip().split("\n"):
        if not in_fence and not in_display and not line.strip():
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
        if _FENCE_LINE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and line.count("$$") % 2 == 1:
            in_display = not in_display
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def _is_display_only(paragraph: str) -> bool:
    p = paragraph.strip()
    return p.startswith("$$") and p.endswith("$$")


def _tag_external(text: str) -> str:
    """Long formulas are split out first, so every resulting text paragraph keeps its tag.
    A structural paragraph (list, table, quote, fence, display math) is tagged on its own
    line only when it opens the block; mid-block it continues the tagged text above it."""
    tagged = []
    for i, p in enumerate(_paragraphs(split_display_math(text.strip()))):
        if i > 0 and (_is_display_only(p) or _STRUCTURE_START_RE.match(p)):
            tagged.append(p)
        elif _STRUCTURE_START_RE.match(p):
            tagged.append(f"{EXTERNAL_TAG}\n\n{p}")
        else:
            tagged.append(f"{EXTERNAL_TAG} {p}")
    return "\n\n".join(tagged)


def _block_text(block: Block) -> str:
    if block.type == "grounded":
        return split_display_math(block.text.strip())
    return _tag_external(block.text)


def render(guide: GuideInput, enhanced: Enhanced, *, model: str, generated_at: str,
           worked_example: bool, min_words: int) -> str:
    from agent.summary_enhance.prompt import PROMPT_VERSION

    used_in: dict[str, list[str]] = {}
    for topic in enhanced.topics:
        for section in topic.sections:
            where = f"{topic.title} > {section.heading}"
            for block in section.blocks:
                if block.type != "grounded":
                    continue
                for label in block.sources:
                    places = used_in.setdefault(label, [])
                    if where not in places:
                        places.append(where)
    source_map = [
        {"chunk_id": s.chunk_id, "file_id": s.file_id, "path": s.path, "citation": s.citation,
         "used_in": used_in[s.label]}
        for s in guide.sources if s.label in used_in
    ]

    front_fields = {
        "title": json.dumps(f"{guide.title} (enhanced)", ensure_ascii=False),
        "llm_generated": "true",
        "content_kind": "enhanced_summary",
        "format_version": "2",
        "generated_by": GENERATED_BY,
        "enhancement_model": json.dumps(model),
        "prompt_version": json.dumps(PROMPT_VERSION),
        "generated_at": generated_at,
        "source_summary": json.dumps({"path": guide.rel_path, "sha256": guide.sha256}),
        "topics": json.dumps([t.title for t in enhanced.topics], ensure_ascii=False),
        "options": json.dumps({"worked_example": worked_example, "min_words": min_words}),
        "external_context_marker": json.dumps(EXTERNAL_MARKER),
        "source_map": json.dumps(source_map, ensure_ascii=False, separators=(",", ":")),
    }
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front_fields.items()) + "---\n\n"

    parts = [f"# {guide.title} (enhanced)", _INTRO]
    for topic in enhanced.topics:
        parts.append(f"## {topic.title}")
        for section in topic.sections:
            parts.append(f"### {section.heading}")
            parts.extend(_block_text(b) for b in section.blocks)
        if topic.worked_example:
            parts.append("### Worked example")
            parts.append(WORKED_TAG)
            parts.append(split_display_math(topic.worked_example.strip()))
    return frontmatter + "\n\n".join(parts) + "\n"
