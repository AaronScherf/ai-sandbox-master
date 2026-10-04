# tests/agent/summary_enhance/test_summary_enhance_render.py
import json

from agent.summary_enhance.prompt import PROMPT_VERSION
from agent.summary_enhance.render import EXTERNAL_TAG, WORKED_TAG, render
from agent.summary_enhance.schema import Block, Enhanced, Section, Topic
from agent.summary_enhance.source_loader import load_guide

INTRO = ("*Study guide synthesized from the course textbooks. Passages marked (External context) "
         "or (Worked example) come from outside the textbooks.*")


def _enhanced(worked=None):
    return Enhanced([Topic("Wald test", [
        Section("Setup", [
            Block("grounded", "The Wald statistic uses the unrestricted fit.", ["S1", "S3"]),
            Block("external", "Think of it as a distance.", []),
        ]),
        Section("Statistic", [Block("grounded", "See the formula $ab+cd+ef+gh$ below.", ["S2"])]),
    ], worked_example=worked)])


def _render(vault, enhanced, **kw):
    guide = load_guide(vault.guide)
    args = dict(model="fake-model", generated_at="2026-10-03T12:00:00+00:00", worked_example=False, min_words=1400)
    args.update(kw)
    return guide, render(guide, enhanced, **args)


def _front(text):
    front, body = text.split("\n---\n\n", 1)
    return front, body


def _field(front, key):
    line = next(l for l in front.splitlines() if l.startswith(f"{key}: "))
    return line[len(key) + 2:]


def test_body_exact(vault):
    _, text = _render(vault, _enhanced(worked="We draw data. $t=2$."), worked_example=True)
    _, body = _front(text)
    assert body == (
        "# Wald and LM tests (enhanced)\n\n"
        f"{INTRO}\n\n"
        "## Wald test\n\n"
        "### Setup\n\n"
        "The Wald statistic uses the unrestricted fit.\n\n"
        "*(External context)* Think of it as a distance.\n\n"
        "### Statistic\n\n"
        "See the formula\n\n$$\nab+cd+ef+gh\n$$\n\nbelow.\n\n"
        "### Worked example\n\n"
        "*(Worked example — illustrative data, not from the textbooks)*\n\n"
        "We draw data. $t=2$.\n"
    )


def test_body_has_no_citation_machinery(vault):
    _, text = _render(vault, _enhanced())
    _, body = _front(text)
    assert "[S" not in body and "Sources" not in body and "<!--" not in body
    assert "Not from the textbooks" not in body
    assert "Worked example" not in body.split("## Wald test", 1)[1]  # no worked example requested


def test_frontmatter_fields(vault):
    guide, text = _render(vault, _enhanced())
    front, _ = _front(text)
    assert front.startswith("---\ntitle:")
    assert "llm_generated: true" in front and "content_kind: enhanced_summary" in front
    assert "format_version: 2" in front
    assert _field(front, "enhancement_model") == '"fake-model"'
    assert _field(front, "prompt_version") == json.dumps(PROMPT_VERSION)
    assert _field(front, "generated_at") == "2026-10-03T12:00:00+00:00"
    assert json.loads(_field(front, "source_summary")) == {
        "path": "academic_notes/econ/summaries/guide.md", "sha256": guide.sha256}
    assert json.loads(_field(front, "topics")) == ["Wald test"]
    assert json.loads(_field(front, "options")) == {"worked_example": False, "min_words": 1400}
    assert json.loads(_field(front, "external_context_marker")) == "(External context)"
    assert "indexer_source_refs" not in front


def test_source_map_lists_cited_chunks_with_sections(vault):
    guide, text = _render(vault, _enhanced())
    front, _ = _front(text)
    smap = json.loads(_field(front, "source_map"))
    assert [e["chunk_id"] for e in smap] == ["cam-1", "cam-2", "han-1"]
    assert smap[0] == {"chunk_id": "cam-1", "file_id": "cam",
                       "path": "academic_notes/econ/textbooks/cam.rag.md",
                       "citation": "§7.2.3 Wald Test Statistic, p. 249",
                       "used_in": ["Wald test > Setup"]}
    assert smap[1]["used_in"] == ["Wald test > Statistic"]
    assert smap[2]["used_in"] == ["Wald test > Setup"]
    assert str(guide.root) not in text  # no absolute local path anywhere


def test_source_map_only_cited_and_no_duplicate_sections(vault):
    enhanced = Enhanced([Topic("Wald test", [
        Section("A", [Block("grounded", "x", ["S2"]), Block("grounded", "y", ["S2"])]),
        Section("B", [Block("external", "z", [])]),
    ])])
    _, text = _render(vault, enhanced)
    smap = json.loads(_field(_front(text)[0], "source_map"))
    assert [e["chunk_id"] for e in smap] == ["cam-2"]
    assert smap[0]["used_in"] == ["Wald test > A"]


def test_external_tag_on_every_paragraph(vault):
    enhanced = Enhanced([Topic("T", [Section("A", [Block("external", "First.\n\nSecond.", [])])])])
    _, body = _front(_render(vault, enhanced)[1])
    assert f"{EXTERNAL_TAG} First.\n\n{EXTERNAL_TAG} Second." in body


def test_external_tag_goes_on_own_line_before_structure(vault):
    enhanced = Enhanced([Topic("T", [Section("A", [
        Block("external", "$$x+y$$ is the form", []),
        Block("external", "- a\n- b", []),
        Block("external", "| a | b |\n|---|---|\n| 1 | 2 |", []),
    ])])])
    _, body = _front(_render(vault, enhanced)[1])
    assert f"{EXTERNAL_TAG}\n\n$$x+y$$ is the form" in body
    assert f"{EXTERNAL_TAG}\n\n- a\n- b" in body
    assert f"{EXTERNAL_TAG}\n\n| a | b |" in body


def test_worked_example_options_recorded(vault):
    _, text = _render(vault, _enhanced(worked="Data."), worked_example=True, min_words=900)
    assert json.loads(_field(_front(text)[0], "options")) == {"worked_example": True, "min_words": 900}


def test_tags_constants():
    assert EXTERNAL_TAG == "*(External context)*"
    assert WORKED_TAG == "*(Worked example — illustrative data, not from the textbooks)*"
