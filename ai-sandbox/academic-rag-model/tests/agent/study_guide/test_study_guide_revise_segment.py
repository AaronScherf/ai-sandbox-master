# tests/agent/study_guide/test_study_guide_revise_segment.py
from agent.study_guide.revise.segment import check_headings, segment, split_frontmatter

BODY = ("# T\n\nintro text\n\n## A\n\nalpha\n\n### A1\n\n$$\nx=1\n$$\n\n"
        "**Constructed example (not from the sources)** n=3 and more words here\n\n## B\n\nbeta\n")


def test_split_frontmatter():
    assert split_frontmatter("---\ntitle: x\n---\n\n# T\n") == ("---\ntitle: x\n---\n\n", "# T\n")
    assert split_frontmatter("# T\n") == ("", "# T\n")


def test_blocks_follow_headings_with_paths_and_counts():
    blocks = segment(BODY)
    assert [b.heading_path for b in blocks] == [("T",), ("T", "A"), ("T", "A", "A1"), ("T", "B")]
    assert [b.level for b in blocks] == [1, 2, 3, 2]
    a1 = blocks[2]
    assert a1.equations == 1 and a1.constructed is True and a1.words > 8
    assert blocks[1].equations == 0 and blocks[1].constructed is False


def test_text_before_the_first_heading_is_a_level_zero_block():
    blocks = segment("preface words\n\n# T\n\nbody\n")
    assert blocks[0].level == 0 and blocks[0].heading_path == () and "preface" in blocks[0].text


def test_ids_are_stable_when_other_blocks_change():
    before, after = segment(BODY), segment(BODY.replace("beta", "gamma changed"))
    assert [b.id for b in before[:3]] == [b.id for b in after[:3]] and before[3].id != after[3].id


def test_identical_blocks_get_distinct_ids():
    blocks = segment("# T\n\n## A\n\nsame\n\n## A\n\nsame\n")
    assert len({b.id for b in blocks}) == len(blocks)


def test_headings_inside_code_fences_are_ignored():
    blocks = segment("# T\n\n```\n# not a heading\n```\n\n## A\n\nx\n")
    assert [b.heading_path for b in blocks] == [("T",), ("T", "A")]


def test_start_and_end_index_the_original_lines():
    lines = BODY.split("\n")
    for b in segment(BODY):
        assert "\n".join(lines[b.start:b.end]).rstrip("\n") == b.text


def test_check_headings():
    assert check_headings(BODY) == []
    assert any("extra H1" in p for p in check_headings("# T\n\n# U\n"))
    assert any("jumps" in p for p in check_headings("# T\n\n#### Deep\n"))
    assert any("duplicate" in p for p in check_headings("# T\n\n## A\n\n## a\n"))
