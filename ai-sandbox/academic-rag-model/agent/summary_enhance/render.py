# agent/summary_enhance/render.py
"""Deterministic Markdown rendering of validated enhancement output.

The body is a clean study document: no citation markers, no Sources list, no
comments and no inline provenance tags. Provenance lives in the frontmatter:
`source_map` (chunk -> sections that rely on it) and `paragraph_kinds` (for each
section, one letter per body paragraph: G textbook-grounded, E external, W worked
example). Long prose paragraphs are cut at sentence boundaries for readability."""
from __future__ import annotations

import json

from agent.summary_enhance.mathfmt import split_display_math
from agent.summary_enhance.paragraphs import split_long_paragraphs, split_paragraphs
from agent.summary_enhance.schema import Enhanced
from agent.summary_enhance.source_loader import GuideInput

GENERATED_BY = "academic-rag-model/agent/summary_enhance/enhance.py"
FORMAT_VERSION = 3
INTRO = ("*Study guide synthesized from the course textbooks; the added intuition and worked "
         "examples are not from the textbooks.*")


def _paragraphs_for(text: str) -> list[str]:
    """Long formulas first, then paragraph boundaries (fence/display aware), then the
    five-sentence rule."""
    return split_long_paragraphs(split_paragraphs(split_display_math(text.strip())))


def render(guide: GuideInput, enhanced: Enhanced, *, model: str, generated_at: str,
           worked_example: bool, min_words: int) -> str:
    from agent.summary_enhance.prompt import PROMPT_VERSION

    used_in: dict[str, list[str]] = {}
    kinds: dict[str, str] = {}
    parts = [f"# {guide.title} (enhanced)", INTRO]
    for topic in enhanced.topics:
        parts.append(f"## {topic.title}")
        for section in topic.sections:
            parts.append(f"### {section.heading}")
            where = f"{topic.title} > {section.heading}"
            letters = []
            for block in section.blocks:
                paragraphs = _paragraphs_for(block.text)
                parts.extend(paragraphs)
                letters.append(("G" if block.type == "grounded" else "E") * len(paragraphs))
                if block.type == "grounded":
                    for label in block.sources:
                        places = used_in.setdefault(label, [])
                        if where not in places:
                            places.append(where)
            kinds[where] = kinds.get(where, "") + "".join(letters)
        if topic.worked_example:
            parts.append("### Worked example")
            paragraphs = _paragraphs_for(topic.worked_example)
            parts.extend(paragraphs)
            key = f"{topic.title} > Worked example"
            kinds[key] = kinds.get(key, "") + "W" * len(paragraphs)

    source_map = [
        {"chunk_id": s.chunk_id, "file_id": s.file_id, "path": s.path, "citation": s.citation,
         "used_in": used_in[s.label]}
        for s in guide.sources if s.label in used_in
    ]
    front_fields = {
        "title": json.dumps(f"{guide.title} (enhanced)", ensure_ascii=False),
        "llm_generated": "true",
        "content_kind": "enhanced_summary",
        "format_version": str(FORMAT_VERSION),
        "generated_by": GENERATED_BY,
        "enhancement_model": json.dumps(model),
        "prompt_version": json.dumps(PROMPT_VERSION),
        "generated_at": generated_at,
        "source_summary": json.dumps({"path": guide.rel_path, "sha256": guide.sha256}),
        "topics": json.dumps([t.title for t in enhanced.topics], ensure_ascii=False),
        "options": json.dumps({"worked_example": worked_example, "min_words": min_words}),
        "paragraph_kinds": json.dumps(kinds, ensure_ascii=False, separators=(",", ":")),
        "source_map": json.dumps(source_map, ensure_ascii=False, separators=(",", ":")),
    }
    frontmatter = "---\n" + "".join(f"{k}: {v}\n" for k, v in front_fields.items()) + "---\n\n"
    return frontmatter + "\n\n".join(parts) + "\n"
