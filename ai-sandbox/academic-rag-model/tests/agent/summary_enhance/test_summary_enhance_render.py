import json
import re

from agent.summary_enhance.paragraphs import split_paragraphs
from agent.summary_enhance.prompt import PROMPT_VERSION
from agent.summary_enhance.render import INTRO, render
from agent.summary_enhance.schema import Block, Enhanced, Section, Topic
from agent.summary_enhance.source_loader import load_guide


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


def _one_block(vault, kind, text, **kw):
    enhanced = Enhanced([Topic("T", [Section("A", [Block(kind, text, ["S1"] if kind == "grounded" else [])])],
                               **kw)])
    front, body = _front(_render(vault, enhanced)[1])
    return json.loads(_field(front, "paragraph_kinds")), body


def test_intro_is_one_neutral_sentence():
    assert INTRO == ("*Study guide synthesized from the course textbooks; the added intuition and "
                     "worked examples are not from the textbooks.*")


def test_body_exact_has_no_tags(vault):
    _, text = _render(vault, _enhanced(worked="We draw data. $t=2$."), worked_example=True)
    _, body = _front(text)
    assert body == (
        "# Wald and LM tests (enhanced)\n\n"
        f"{INTRO}\n\n"
        "## Wald test\n\n"
        "### Setup\n\n"
        "The Wald statistic uses the unrestricted fit.\n\n"
        "Think of it as a distance.\n\n"
        "### Statistic\n\n"
        "See the formula\n\n$$\nab+cd+ef+gh\n$$\n\nbelow.\n\n"
        "### Worked example\n\n"
        "We draw data. $t=2$.\n"
    )


def test_body_has_no_citation_or_tag_machinery(vault):
    _, text = _render(vault, _enhanced(worked="Data."), worked_example=True)
    _, body = _front(text)
    assert "[S" not in body and "Sources" not in body and "<!--" not in body
    assert "External context" not in text and "Not from the textbooks" not in body
    assert "illustrative data, not from" not in body


def test_frontmatter_fields(vault):
    guide, text = _render(vault, _enhanced())
    front, _ = _front(text)
    assert front.startswith("---\ntitle:")
    assert "llm_generated: true" in front and "content_kind: enhanced_summary" in front
    assert "format_version: 3" in front
    assert _field(front, "enhancement_model") == '"fake-model"'
    assert _field(front, "prompt_version") == json.dumps(PROMPT_VERSION)
    assert _field(front, "generated_at") == "2026-10-03T12:00:00+00:00"
    assert json.loads(_field(front, "source_summary")) == {
        "path": "academic_notes/econ/summaries/guide.md", "sha256": guide.sha256}
    assert json.loads(_field(front, "topics")) == ["Wald test"]
    assert json.loads(_field(front, "options")) == {"worked_example": False, "min_words": 1400}
    assert "external_context_marker" not in front and "indexer_source_refs" not in front


def test_paragraph_kinds_per_section(vault):
    _, text = _render(vault, _enhanced(worked="We draw data. $t=2$."), worked_example=True)
    kinds = json.loads(_field(_front(text)[0], "paragraph_kinds"))
    assert kinds == {"Wald test > Setup": "GE", "Wald test > Statistic": "GGG",
                     "Wald test > Worked example": "W"}


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
    assert str(guide.root) not in text


def test_source_map_only_cited_and_no_duplicate_sections(vault):
    enhanced = Enhanced([Topic("Wald test", [
        Section("A", [Block("grounded", "x", ["S2"]), Block("grounded", "y", ["S2"])]),
        Section("B", [Block("external", "z", [])]),
    ])])
    _, text = _render(vault, enhanced)
    smap = json.loads(_field(_front(text)[0], "source_map"))
    assert [e["chunk_id"] for e in smap] == ["cam-2"]
    assert smap[0]["used_in"] == ["Wald test > A"]


def test_external_paragraphs_are_plain_and_recorded_as_E(vault):
    kinds, body = _one_block(vault, "external", "First.\n\nSecond.")
    assert "First.\n\nSecond." in body and kinds == {"T > A": "EE"}


def test_external_text_after_a_long_formula_split_stays_E(vault):
    formula = r"W = n(\hat\theta-\theta_0)^2/V"
    kinds, body = _one_block(vault, "external", f"Intuition: the stat ${formula}$ grows, so large values reject.")
    assert f"Intuition: the stat\n\n$$\n{formula}\n$$\n\ngrows, so large values reject." in body
    assert kinds == {"T > A": "EEE"}


def test_code_fence_in_external_block_stays_intact(vault):
    kinds, body = _one_block(vault, "external", "Here is code:\n\n```python\nx=1\n\ny=2\n```\n\nAfter.")
    assert "Here is code:\n\n```python\nx=1\n\ny=2\n```\n\nAfter." in body
    assert kinds == {"T > A": "EEE"}


def test_display_math_with_a_blank_line_inside_is_not_split(vault):
    kinds, body = _one_block(vault, "external", "Start.\n\n$$\na\n\n+b\n$$\n\nEnd.")
    assert "Start.\n\n$$\na\n\n+b\n$$\n\nEnd." in body
    assert kinds == {"T > A": "EEE"}


def test_long_prose_paragraph_is_split_without_changing_the_words(vault):
    text = " ".join(f"Sentence number {i} is here." for i in range(1, 8))
    kinds, body = _one_block(vault, "grounded", text)
    section = body.split("### A\n\n", 1)[1].strip()
    paragraphs = section.split("\n\n")
    assert len(paragraphs) == 2 and kinds == {"T > A": "GG"}
    assert " ".join(paragraphs).split() == text.split()


def test_headings_are_never_math_or_sentence_split(vault):
    enhanced = Enhanced([Topic("T", [Section(r"Test of $\beta_1 = \beta_2 = \beta_3 = 0$",
                                             [Block("grounded", "x", ["S1"])])])])
    body = _front(_render(vault, enhanced)[1])[1]
    assert "### Test of $\\beta_1 = \\beta_2 = \\beta_3 = 0$\n" in body


def test_worked_example_gets_display_math_and_paragraph_splitting(vault):
    long_worked = " ".join(f"Step {i} is computed here." for i in range(1, 7)) + " Value $ab+cd+ef+gh$ here."
    enhanced = Enhanced([Topic("T", [Section("A", [Block("grounded", "x", ["S1"])])],
                               worked_example=long_worked)])
    front, body = _front(_render(vault, enhanced, worked_example=True)[1])
    kinds = json.loads(_field(front, "paragraph_kinds"))
    assert "\n\n$$\nab+cd+ef+gh\n$$\n\n" in body
    assert set(kinds["T > Worked example"]) == {"W"} and len(kinds["T > Worked example"]) >= 3


def test_duplicate_section_headings_merge_their_kinds(vault):
    enhanced = Enhanced([Topic("T", [
        Section("Same", [Block("grounded", "a", ["S1"])]),
        Section("Same", [Block("external", "b", [])]),
    ])])
    kinds = json.loads(_field(_front(_render(vault, enhanced)[1])[0], "paragraph_kinds"))
    assert kinds == {"T > Same": "GE"}


def test_kind_letters_always_match_the_body_paragraphs(vault):
    long_text = " ".join(f"Sentence {i} sits here." for i in range(1, 10))
    enhanced = Enhanced([Topic("T", [
        Section("One", [Block("grounded", long_text + " The form $ab+cd+ef+gh$ matters.", ["S1"]),
                        Block("external", "Aside.\n\n- a\n- b\n\nMore.", [])]),
        Section("Two", [Block("grounded", "```\ncode\n\nmore\n```\n\nAfter.", ["S2"])]),
    ], worked_example="Compute it. $t=2$.")])
    front, body = _front(_render(vault, enhanced, worked_example=True)[1])
    kinds = json.loads(_field(front, "paragraph_kinds"))
    sections = re.split(r"^### ", body, flags=re.M)[1:]
    for chunk in sections:
        heading, rest = chunk.split("\n", 1)
        key = ("T > Worked example" if heading == "Worked example" else f"T > {heading}")
        assert len(split_paragraphs(rest)) == len(kinds[key]), key
