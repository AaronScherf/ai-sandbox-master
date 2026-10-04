# tests/agent/summary_enhance/test_summary_enhance_prompt.py
from agent.summary_enhance.prompt import (
    PROMPT_VERSION, build_plan_prompt, build_topic_prompt, build_worked_example_prompt,
)
from agent.summary_enhance.source_loader import load_guide


def test_version():
    assert PROMPT_VERSION == "2026-10-03.2"


def test_topic_prompt_contents(vault):
    guide = load_guide(vault.guide)
    prompt = build_topic_prompt(guide, "Wald test", ["LM test", "Likelihood ratio test"], 1400)
    for s in guide.sources:
        assert f"[{s.label}]" in prompt and s.text in prompt and s.citation in prompt
    assert "Body text." in prompt                      # draft guide included
    assert '"Wald test"' in prompt
    assert "LM test" in prompt and "Likelihood ratio test" in prompt   # other topics named
    assert PROMPT_VERSION in prompt
    assert '"sections"' in prompt                      # schema embedded
    assert "at least 3 sections" in prompt
    assert "1680 words" in prompt                      # 1400 * 1.2 target
    assert "half" in prompt                            # grounded share rule
    assert "ten symbols" in prompt                     # display-math instruction
    assert "(External context)" in prompt              # told not to write it


def test_topic_prompt_shows_doubled_backslashes_literally(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400)
    assert '"\\\\beta"' in prompt      # runtime text is "\\beta": two real backslashes


def test_topic_prompt_without_other_topics(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400)
    assert "Other topics" not in prompt


def test_topic_prompt_includes_retry_errors(vault):
    prompt = build_topic_prompt(load_guide(vault.guide), "Wald test", [], 1400,
                                errors=["topic has 900 words; at least 1400 are required"])
    assert "REJECTED" in prompt and "900 words" in prompt


def test_plan_prompt(vault):
    guide = load_guide(vault.guide)
    prompt = build_plan_prompt(guide)
    assert "3 to 8" in prompt and "Body text." in prompt and '"topics"' in prompt
    assert "REJECTED" in build_plan_prompt(guide, errors=["duplicate"])


def test_worked_example_prompt():
    prompt = build_worked_example_prompt("Wald test", "W = (r - t)' V^-1 (r - t)")
    assert '"Wald test"' in prompt and "V^-1" in prompt
    assert "code execution" in prompt and "illustrative" in prompt.lower()
    assert "REJECTED" in build_worked_example_prompt("T", "x", errors=["no math"])
