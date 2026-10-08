# tests/agent/study_guide/test_study_guide_prompts.py
import hashlib

from agent.study_guide.prompts import (
    GUIDE_V1_TEMPLATE, TUTOR_V1_TEMPLATE, guide_v1_prompt, tutor_v1_prompt, tutor_v1_question,
)


def test_tutor_template_is_frozen():
    # A transcription guard for the copy of rag_agent._ANSWER_PROMPT_TEMPLATE taken on 2026-10-05.
    # If the tutor template is changed deliberately later, this copy stays as it is (baseline
    # reproduction); only change this hash if the frozen copy itself is meant to change.
    assert len(TUTOR_V1_TEMPLATE) == 668
    assert hashlib.sha256(TUTOR_V1_TEMPLATE.encode("utf-8")).hexdigest() == (
        "e5615eb6fdbfd36db10d3ea27ab29274d817383b0fbf112e4559d0537830b0d6")


def test_tutor_question_wording():
    assert tutor_v1_question("Wald test", "Explain it.") == (
        "Wald test. Explain it. Use only these excerpts. Cite each substantive claim by its exact source "
        "label. State plainly where the excerpts do not support an answer.")


def test_tutor_prompt_structure():
    prompt = tutor_v1_prompt("Q", [("A, p. 1", "text one"), ("B, p. 2", "text two")])
    assert prompt.startswith("You are tutoring a student using ONLY the excerpts below")
    assert "Excerpts:\n[A, p. 1]\ntext one\n\n[B, p. 2]\ntext two\n\nQuestion: Q\n\nAnswer:" in prompt
    assert "{history_block}" not in prompt and "{gap_hint_block}" not in prompt and prompt.endswith("Answer:")


def test_guide_prompt_contents():
    prompt = guide_v1_prompt("Wald test", "Cover the statistic.", [("A, p. 1", "text one")])
    assert "Section: Wald test" in prompt and "Focus: Cover the statistic." in prompt
    assert "[A, p. 1]\ntext one" in prompt and "800 words" in prompt and "###" in prompt
    assert "prefer the textbook" in prompt and prompt.endswith("Section text:")
    assert "{" not in GUIDE_V1_TEMPLATE.replace("{title}", "").replace("{instruction}", "").replace("{excerpts_block}", "").replace("{min_words}", "").replace("{examples_block}", "")


def test_guide_prompt_word_target_is_configurable():
    prompt = guide_v1_prompt("Wald test", "Cover it.", [("A, p. 1", "t")], min_words=1800)
    assert "at least 1800 words" in prompt and "at least 800 words" not in prompt


def test_constructed_examples_block_only_when_requested():
    plain = guide_v1_prompt("LR", "Cover it.", [("A, p. 1", "t")])
    assert "Constructed example (not from the sources)" not in plain
    asked = guide_v1_prompt("LR", "Cover it.", [("A, p. 1", "t")], construct_examples=True)
    assert "Constructed example (not from the sources)" in asked
    assert "show every intermediate calculation" in asked and asked.endswith("Section text:")
