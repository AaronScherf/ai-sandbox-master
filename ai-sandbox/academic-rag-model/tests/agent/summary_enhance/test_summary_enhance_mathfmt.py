# tests/agent/summary_enhance/test_summary_enhance_mathfmt.py
import pytest

from agent.summary_enhance.mathfmt import SYMBOL_LIMIT, split_display_math, symbol_count


def test_limit_constant():
    assert SYMBOL_LIMIT == 10


def test_symbol_count_commands_chars_and_braces():
    assert symbol_count(r"\hat\theta") == 2
    assert symbol_count(r"x_{1}+y") == 5
    assert symbol_count(r"\frac{a}{b}") == 3
    assert symbol_count(r"a \, b") == 3
    assert symbol_count("  a  b ") == 2


@pytest.mark.parametrize("formula,converted", [("ab+cd+ef+g", False), ("ab+cd+ef+gh", True)])
def test_threshold_is_more_than_ten(formula, converted):
    text = f"Value ${formula}$ here."
    out = split_display_math(text)
    assert (out != text) is converted


def test_long_inline_becomes_display_block():
    out = split_display_math("The statistic is $ab+cd+ef+gh$ here.")
    assert out == "The statistic is\n\n$$\nab+cd+ef+gh\n$$\n\nhere."


def test_trailing_punctuation_moves_inside_the_block():
    out = split_display_math("We get $ab+cd+ef+gh$.")
    assert out == "We get\n\n$$\nab+cd+ef+gh.\n$$"


def test_formula_at_start_has_no_leading_blank():
    out = split_display_math("$ab+cd+ef+gh$ is the statistic.")
    assert out == "$$\nab+cd+ef+gh\n$$\n\nis the statistic."


def test_two_formulas_in_one_line():
    out = split_display_math("A $ab+cd+ef+gh$ and $ij+kl+mn+op$ end.")
    assert out == "A\n\n$$\nab+cd+ef+gh\n$$\n\nand\n\n$$\nij+kl+mn+op\n$$\n\nend."


def test_short_formulas_stay_inline_in_same_line_as_long_one():
    out = split_display_math("Let $x$ be $ab+cd+ef+gh$ today.")
    assert out == "Let $x$ be\n\n$$\nab+cd+ef+gh\n$$\n\ntoday."


def test_trailing_newline_preserved_only_if_present():
    assert split_display_math("a $ab+cd+ef+gh$\n").endswith("\n")
    assert not split_display_math("a $ab+cd+ef+gh$").endswith("\n")


def test_existing_display_math_untouched():
    text = "Before\n\n$$\\sum_{i=1}^{n} x_i + y_i + z_i$$\n\nAfter\n\n$$\na = b\n$$"
    assert split_display_math(text) == text


@pytest.mark.parametrize("line", [
    "- item $ab+cd+ef+gh$",
    "* item $ab+cd+ef+gh$",
    "1. item $ab+cd+ef+gh$",
    "2) item $ab+cd+ef+gh$",
    "| a | $ab+cd+ef+gh$ |",
    "> quote $ab+cd+ef+gh$",
])
def test_list_table_blockquote_lines_untouched(line):
    assert split_display_math(line) == line


def test_fenced_code_untouched():
    text = "```\nx = '$ab+cd+ef+gh$'\n```\n\nand $ab+cd+ef+gh$ outside"
    out = split_display_math(text)
    assert "x = '$ab+cd+ef+gh$'" in out
    assert out.endswith("$$\nab+cd+ef+gh\n$$\n\noutside")


def test_idempotent():
    once = split_display_math("A $ab+cd+ef+gh$ and $ij+kl+mn+op$, end.")
    assert split_display_math(once) == once


def test_plain_text_unchanged():
    text = "No math here.\n\nSecond paragraph with $x$ only."
    assert split_display_math(text) == text


def test_currency_dollar_signs_are_not_math():
    for text in ["Worker A earns $12 per hour while worker B earns $15 per hour.",
                 "Spend $5 on the formula $x$ now.",
                 "Prices of $5 and $6 differ a lot, and so on and so forth."]:
        assert split_display_math(text) == text


def test_escaped_dollar_is_literal_and_real_formula_still_converts():
    out = split_display_math(r"Costs \$5 and the formula $ab+cd+ef+gh$ matters.")
    assert out == "Costs \\$5 and the formula\n\n$$\nab+cd+ef+gh\n$$\n\nmatters."


def test_inline_code_untouched():
    text = "Use `$ab+cd+ef+gh$` literally."
    assert split_display_math(text) == text


def test_headings_untouched():
    text = r"### Test of $\beta_1 = \beta_2 = \beta_3 = 0$ end"
    assert split_display_math(text) == text


def test_space_padded_dollars_are_not_math():
    text = "a $ ab+cd+ef+gh $ b"
    assert split_display_math(text) == text
