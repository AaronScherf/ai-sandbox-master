import pytest

from agent.summary_enhance.paragraphs import (
    MAX_SENTENCES, is_prose, split_long_paragraph, split_paragraphs, split_sentences,
)


def _sents(n):
    return " ".join(f"Sentence number {i} is here." for i in range(1, n + 1))


def test_limit_constant():
    assert MAX_SENTENCES == 5


def test_split_paragraphs_on_blank_lines():
    assert split_paragraphs("One.\n\nTwo.\n\n\nThree.") == ["One.", "Two.", "Three."]


def test_split_paragraphs_keeps_fences_and_display_math_whole():
    text = "Intro.\n\n```python\nx=1\n\ny=2\n```\n\n$$\na\n\n+b\n$$\n\nEnd."
    assert split_paragraphs(text) == ["Intro.", "```python\nx=1\n\ny=2\n```", "$$\na\n\n+b\n$$", "End."]


def test_sentence_counting_basic():
    assert len(split_sentences(_sents(7))) == 7
    assert split_sentences("One. Two! Three? Four.") == ["One.", "Two!", "Three?", "Four."]


@pytest.mark.parametrize("text,count", [
    ("Cameron et al. (2005) show this. Hansen agrees.", 2),            # et al.
    ("Use it, e.g. Hansen's test. Then stop.", 2),                    # e.g.
    ("That is, i.e. the same thing. Next point.", 2),                 # i.e.
    ("See p. 249 for details. Then continue.", 2),                    # p.
    ("The value is 5.99 at the 5% level. It rejects.", 2),            # decimal
    ("Anderson, T. W. proved it. Later work extended it.", 2),        # initials
    ("The statistic is $x.$ Then it is compared. Done.", 2),          # a period inside math is hidden, so "$x.$ Then" is no boundary
    ("Compare $a. B$ to $c$. Next.", 2),                              # period inside math span
    ("Result (see Eq. 3). The next step follows.", 2),                # Eq.
    ("a lowercase continuation. follows here. Still one more. Fine.", 3),  # lowercase after a period is not a boundary
])
def test_sentence_protections(text, count):
    assert len(split_sentences(text)) == count


def test_five_or_fewer_sentences_untouched():
    for n in range(1, 6):
        text = _sents(n)
        assert split_long_paragraph(text) == [text]


@pytest.mark.parametrize("n,sizes", [(6, [3, 3]), (7, [4, 3]), (8, [4, 4]), (10, [5, 5]),
                                     (11, [4, 4, 3]), (12, [4, 4, 4]), (16, [4, 4, 4, 4]), (17, [5, 4, 4, 4])])
def test_long_paragraph_is_cut_into_even_groups(n, sizes):
    parts = split_long_paragraph(_sents(n))
    assert [len(split_sentences(p)) for p in parts] == sizes
    assert all(len(split_sentences(p)) <= MAX_SENTENCES for p in parts)


def test_content_is_unchanged_by_splitting():
    text = _sents(9)
    parts = split_long_paragraph(text)
    assert " ".join(parts).split() == text.split()


def test_splitting_is_idempotent():
    parts = split_long_paragraph(_sents(13))
    again = [q for p in parts for q in split_long_paragraph(p)]
    assert again == parts


@pytest.mark.parametrize("paragraph", [
    "- " + _sents(8),
    "1. " + _sents(8),
    "| a | b |\n|---|---|\n| " + _sents(8) + " | 2 |",
    "> " + _sents(8),
    "```\n" + _sents(8) + "\n```",
    "$$\n" + _sents(8) + "\n$$",
    "### " + _sents(8),
])
def test_non_prose_paragraphs_are_never_split(paragraph):
    assert not is_prose(paragraph)
    assert split_long_paragraph(paragraph) == [paragraph]


def test_prose_detection():
    assert is_prose("Plain sentence here.")
    assert is_prose("The statistic $W$ grows.")
    assert not is_prose("$$a+b$$")


def test_inline_math_with_sentence_punctuation_does_not_create_boundaries():
    text = " ".join(["Let $a. B$ be given."] * 3 + ["Then $c! D$ holds."] * 3)
    assert len(split_sentences(text)) == 6
    parts = split_long_paragraph(text)
    assert len(parts) == 2 and all("$a. B$" in p or "$c! D$" in p for p in parts)
