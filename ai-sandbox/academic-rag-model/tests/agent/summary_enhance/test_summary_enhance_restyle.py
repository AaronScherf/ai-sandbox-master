import json
import re

import pytest

from agent.summary_enhance.paragraphs import split_paragraphs, split_sentences
from agent.summary_enhance.render import INTRO
from agent.summary_enhance.restyle import RestyleError, main, restyle_file, restyle_text

OLD_INTRO = ("*Study guide synthesized from the course textbooks. Passages marked (External context) "
             "or (Worked example) come from outside the textbooks.*")
FRONT = """---
title: "T (enhanced)"
llm_generated: true
content_kind: enhanced_summary
format_version: 2
options: {"worked_example": true, "min_words": 1400}
external_context_marker: "(External context)"
source_map: []
---

"""


def _v2(body):
    return FRONT + f"# T (enhanced)\n\n{OLD_INTRO}\n\n" + body


BODY = """## Topic

### Setup

Grounded one.

*(External context)* External text.

$$
a+b
$$

*(External context)* Tail external.

Grounded two.

### Worked example

*(Worked example — illustrative data, not from the textbooks)*

We compute. $t=2$.
"""


def _split(text):
    front, body = text.split("\n---\n\n", 1)
    return front, body


def _field(front, key):
    line = next(l for l in front.splitlines() if l.startswith(f"{key}: "))
    return line[len(key) + 2:]


def test_tags_removed_and_intro_replaced():
    front, body = _split(restyle_text(_v2(BODY)))
    assert "External context" not in body and "illustrative data" not in body
    assert INTRO in body and OLD_INTRO not in body
    assert "Grounded one.\n\nExternal text.\n\n$$\na+b\n$$\n\nTail external.\n\nGrounded two." in body


def test_frontmatter_is_updated():
    front, _ = _split(restyle_text(_v2(BODY)))
    assert "format_version: 3" in front and "format_version: 2" not in front
    assert "external_context_marker" not in front
    assert "paragraph_kinds_inferred: true" in front
    assert json.loads(_field(front, "paragraph_kinds")) == {
        "Topic > Setup": "GEEEG", "Topic > Worked example": "W"}
    assert "options:" in front and "source_map: []" in front       # untouched fields survive


def test_tag_on_its_own_line_marks_the_following_structure_as_external():
    body = "## Topic\n\n### S\n\nPlain.\n\n*(External context)*\n\n- a\n- b\n\nBack to grounded.\n"
    front, out = _split(restyle_text(_v2(body)))
    assert json.loads(_field(front, "paragraph_kinds")) == {"Topic > S": "GEG"}
    assert "Plain.\n\n- a\n- b\n\nBack to grounded." in out


def test_long_paragraphs_are_split_and_keep_their_kind():
    seven = " ".join(f"Sentence number {i} is here." for i in range(1, 8))
    body = f"## Topic\n\n### S\n\n*(External context)* {seven}\n\n{seven}\n"
    front, out = _split(restyle_text(_v2(body)))
    assert json.loads(_field(front, "paragraph_kinds")) == {"Topic > S": "EEGG"}
    for p in split_paragraphs(out.split("### S\n\n", 1)[1]):
        assert len(split_sentences(p)) <= 5


def test_words_are_preserved_apart_from_tags():
    before = _v2(BODY)
    after = restyle_text(before)
    strip = lambda t: re.sub(r"\*\(External context\)\*|\*\(Worked example[^)]*\)\*", "", t.split("\n---\n\n", 1)[1]
                             .replace(OLD_INTRO, "").replace(INTRO, "")).split()
    assert strip(after) == strip(before)


def test_kind_letters_match_body_paragraphs():
    seven = " ".join(f"Sentence number {i} is here." for i in range(1, 8))
    body = f"## Topic\n\n### S\n\n{seven}\n\n*(External context)* Aside.\n\n```\ncode\n\nmore\n```\n\nEnd.\n"
    front, out = _split(restyle_text(_v2(body)))
    kinds = json.loads(_field(front, "paragraph_kinds"))
    assert len(split_paragraphs(out.split("### S\n\n", 1)[1])) == len(kinds["Topic > S"])


@pytest.mark.parametrize("replacement", ["format_version: 3", "format_version: 1", "other_key: x"])
def test_only_format_2_is_accepted(replacement):
    with pytest.raises(RestyleError):
        restyle_text(_v2(BODY).replace("format_version: 2", replacement))


def test_no_frontmatter_rejected():
    with pytest.raises(RestyleError):
        restyle_text("# just a heading\n")


def _write(vault, text):
    path = vault.guide.parent / "g.enhanced.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_file_default_output_is_beside_input_and_input_untouched(vault):
    src = _write(vault, _v2(BODY))
    out = restyle_file(src)
    assert out.name == "g.enhanced.restyled.md" and out.parent == src.parent
    assert "format_version: 3" in out.read_text(encoding="utf-8")
    assert "format_version: 2" in src.read_text(encoding="utf-8")


def test_file_refuses_existing_output_without_force(vault):
    src = _write(vault, _v2(BODY))
    restyle_file(src)
    with pytest.raises(RestyleError):
        restyle_file(src)
    assert restyle_file(src, force=True).is_file()


def test_file_in_place_replaces_the_input(vault):
    src = _write(vault, _v2(BODY))
    out = restyle_file(src, in_place=True)
    assert out == src.resolve() and "format_version: 3" in src.read_text(encoding="utf-8")
    assert not list(src.parent.glob("*.tmp"))


def test_file_output_must_stay_in_the_vault(vault, tmp_path):
    src = _write(vault, _v2(BODY))
    with pytest.raises(RestyleError):
        restyle_file(src, output=tmp_path / "leak.md")


def test_file_must_be_inside_academic_notes(tmp_path):
    stray = tmp_path / "x.enhanced.md"
    stray.write_text(_v2(BODY), encoding="utf-8")
    with pytest.raises(RestyleError):
        restyle_file(stray)


def test_restyling_twice_is_rejected_not_repeated(vault):
    src = _write(vault, _v2(BODY))
    out = restyle_file(src)
    with pytest.raises(RestyleError):
        restyle_file(out, force=True)


def test_main_exit_codes(vault, capsys):
    src = _write(vault, _v2(BODY))
    assert main([str(src)]) == 0
    assert main([str(src)]) == 2            # output exists
    assert main([str(src), "--force", "--in-place"]) == 0
    assert main([str(vault.guide.parent / "missing.md")]) == 2
