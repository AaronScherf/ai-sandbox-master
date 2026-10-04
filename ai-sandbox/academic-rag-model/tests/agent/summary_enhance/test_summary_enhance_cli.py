# tests/agent/summary_enhance/test_summary_enhance_cli.py
import os

import pytest

from agent.summary_enhance import enhance
from agent.summary_enhance.enhance import DEFAULT_MIN_WORDS, run
from conftest import PLAN_JSON, WORKED_TEXT, make_topic_json, write_guide

TOPICS = ["Wald test", "LM test"]
MIN = 100  # words; make_topic_json defaults produce 130 words per topic


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def _topic(title, **kw):
    return make_topic_json(title, **kw)


def _go(vault, llm, **kw):
    kw.setdefault("topics", TOPICS)
    kw.setdefault("min_words", MIN)
    return run(str(vault.guide), llm=llm, **kw)


def test_default_min_words():
    assert DEFAULT_MIN_WORDS == 1400


def test_happy_path_one_call_per_topic_and_clean_output(vault, make_llm):
    original = vault.guide.read_bytes()
    llm = make_llm(_topic("Wald test", labels=("S1", "S3")), _topic("LM test", labels=("S2",)))
    assert _go(vault, llm) == 0
    assert llm.kinds == ["structured", "structured"]
    text = _out(vault).read_text(encoding="utf-8")
    assert "## Wald test" in text and "## LM test" in text
    assert "format_version: 2" in text and "source_map:" in text and 'enhancement_model: "fake-model"' in text
    body = text.split("\n---\n\n", 1)[1]
    assert "[S" not in body and "Sources" not in body
    assert "*(External context)*" in body
    assert vault.guide.read_bytes() == original


def test_each_topic_prompt_names_the_other_topics(vault, make_llm):
    llm = make_llm(_topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert '"Wald test"' in llm.calls[0] and "LM test" in llm.calls[0]
    assert '"LM test"' in llm.calls[1] and "Wald test" in llm.calls[1]


def test_no_topics_triggers_one_planning_call_first(vault, make_llm):
    llm = make_llm(PLAN_JSON, _topic("Wald test"), _topic("Likelihood ratio test"), _topic("LM test"))
    assert _go(vault, llm, topics=[]) == 0
    assert llm.kinds == ["structured"] * 4
    assert "3 to 8" in llm.calls[0]  # the planning prompt
    text = _out(vault).read_text(encoding="utf-8")
    assert "## Likelihood ratio test" in text


def test_bad_plan_is_retried_then_aborts(vault, make_llm):
    llm = make_llm({"topics": ["A", "B"]}, {"topics": ["A", "B"]})
    assert _go(vault, llm, topics=[]) == 3
    assert not _out(vault).exists() and len(llm.calls) == 2


def test_requested_title_spelling_is_rendered(vault, make_llm):
    odd = _topic("Wald test")
    odd["title"] = "  wald TEST "  # same content, model-chosen spelling of the title only
    llm = make_llm(odd, _topic("LM test"))
    assert _go(vault, llm) == 0
    text = _out(vault).read_text(encoding="utf-8")
    assert "## Wald test" in text and "wald TEST" not in text


def test_worked_example_off_makes_no_text_calls(vault, make_llm):
    llm = make_llm(_topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert llm.code_execution == []
    assert "### Worked example" not in _out(vault).read_text(encoding="utf-8")


def test_worked_example_on_adds_one_code_execution_call_per_topic(vault, make_llm):
    llm = make_llm(_topic("Wald test"), WORKED_TEXT, _topic("LM test"), WORKED_TEXT)
    assert _go(vault, llm, worked_example=True) == 0
    assert llm.kinds == ["structured", "text", "structured", "text"]
    assert llm.code_execution == [True, True]
    assert "Wald test" in llm.calls[1]
    text = _out(vault).read_text(encoding="utf-8")
    assert text.count("### Worked example") == 2
    assert text.count("*(Worked example — illustrative data, not from the textbooks)*") == 2
    assert '"worked_example": true' in text


def test_bad_worked_example_is_retried(vault, make_llm):
    llm = make_llm(_topic("Wald test"), "too short $x$", WORKED_TEXT, _topic("LM test"), WORKED_TEXT)
    assert _go(vault, llm, worked_example=True) == 0
    assert llm.kinds.count("text") == 3 and "REJECTED" in llm.calls[2]


def test_too_short_topic_is_retried_with_the_errors(vault, make_llm):
    short = _topic("Wald test", per_section=5)
    llm = make_llm(short, _topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert len(llm.calls) == 3
    assert "REJECTED" in llm.calls[1] and "words" in llm.calls[1]


def test_persistent_validation_failure_writes_nothing(vault, make_llm):
    short = _topic("Wald test", per_section=5)
    llm = make_llm(short, short)
    assert _go(vault, llm) == 3
    assert not _out(vault).exists() and len(llm.calls) == 2


def test_truncated_or_invalid_response_is_retried_as_unusable(vault, make_llm):
    llm = make_llm(ValueError("response truncated (hit the output token limit)"),
                   _topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert "REJECTED" in llm.calls[1] and "unusable" in llm.calls[1]


def test_malformed_shape_is_retried(vault, make_llm):
    llm = make_llm({"nope": 1}, _topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 0
    assert len(llm.calls) == 3


def test_llm_exception_writes_nothing(vault, make_llm):
    llm = make_llm(RuntimeError("503"))
    assert _go(vault, llm) == 4
    assert not _out(vault).exists()


@pytest.mark.parametrize("bad", [0, -5])
def test_min_words_must_be_positive(vault, make_llm, bad):
    llm = make_llm()
    assert _go(vault, llm, min_words=bad) == 2
    assert llm.calls == []


def test_explicit_output_path(vault, make_llm):
    target = vault.guide.parent / "custom.md"
    assert _go(vault, make_llm(_topic("Wald test"), _topic("LM test")), output=str(target)) == 0
    assert target.is_file() and not _out(vault).exists()


def test_refuses_to_overwrite_without_force(vault, make_llm):
    _out(vault).write_text("precious", encoding="utf-8")
    llm = make_llm(_topic("Wald test"), _topic("LM test"))
    assert _go(vault, llm) == 2
    assert _out(vault).read_text(encoding="utf-8") == "precious" and llm.calls == []
    assert _go(vault, make_llm(_topic("Wald test"), _topic("LM test")), force=True) == 0
    assert "enhanced_summary" in _out(vault).read_text(encoding="utf-8")


def test_refuses_output_equal_to_input_even_with_different_spelling(vault, make_llm):
    spelled = vault.guide.parent / ".." / "summaries" / "guide.md"
    llm = make_llm()
    assert _go(vault, llm, output=str(spelled), force=True) == 2
    assert llm.calls == []


def test_refuses_output_outside_vault(vault, tmp_path, make_llm):
    llm = make_llm()
    assert _go(vault, llm, output=str(tmp_path / "leak.md")) == 2
    assert not (tmp_path / "leak.md").exists() and llm.calls == []


def test_refuses_non_markdown_output(vault, make_llm):
    assert _go(vault, make_llm(), output=str(vault.guide.parent / "x.txt")) == 2


def test_dry_run_reports_call_count_and_makes_no_call(vault, make_llm, capsys):
    llm = make_llm()
    assert _go(vault, llm, dry_run=True) == 0
    assert llm.calls == [] and not _out(vault).exists()
    printed = capsys.readouterr().out
    assert "3 chunks" in printed and "guide.enhanced.md" in printed and "2 calls" in printed
    assert _go(vault, llm, dry_run=True, worked_example=True) == 0
    assert "4 calls" in capsys.readouterr().out
    assert _go(vault, llm, dry_run=True, topics=[]) == 0
    assert "planning call" in capsys.readouterr().out


def test_dry_run_does_not_require_an_api_key(vault, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not build a client in dry-run")
    monkeypatch.setattr(enhance, "get_gemini_client", boom)
    assert run(str(vault.guide), topics=TOPICS, dry_run=True) == 0


def test_missing_chunks_exit_before_any_llm_call(vault, make_llm):
    write_guide(vault.guide, vault.refs + [{**vault.refs[0], "chunk_id": "gone"}])
    llm = make_llm()
    assert _go(vault, llm) == 2
    assert llm.calls == []


def test_write_failure_after_paid_calls_saves_a_recovery_copy_and_no_tmp(vault, make_llm, monkeypatch):
    def locked(src, dst):
        raise PermissionError("file is open in another program")

    monkeypatch.setattr(enhance.os, "replace", locked)
    assert _go(vault, make_llm(_topic("Wald test"), _topic("LM test"))) == 5
    folder = vault.guide.parent
    assert not _out(vault).exists() and not list(folder.glob("*.tmp"))
    recovered = folder / "guide.enhanced.recovered.md"
    assert recovered.is_file() and "## Wald test" in recovered.read_text(encoding="utf-8")


def test_missing_api_key_returns_1(vault, monkeypatch):
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(enhance, "get_gemini_client", lambda key_env_var="": None)
    assert run(str(vault.guide), topics=TOPICS, min_words=MIN) == 1
    assert not _out(vault).exists()


def test_paid_key_is_the_one_requested(vault, monkeypatch):
    seen = {}
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)

    def fake_client(key_env_var="GEMINI_API_KEY"):
        seen["k"] = key_env_var
        return None

    monkeypatch.setattr(enhance, "get_gemini_client", fake_client)
    run(str(vault.guide), topics=TOPICS, min_words=MIN)
    assert seen["k"] == "PAID_GEMINI_KEY"


def test_env_file_is_loaded_for_the_paid_key(vault, tmp_path, monkeypatch):
    env_file = tmp_path / "main.env"
    env_file.write_text("PAID_GEMINI_KEY=from-env-file\n", encoding="utf-8")
    monkeypatch.delenv("PAID_GEMINI_KEY", raising=False)
    seen = {}

    def fake_client(key_env_var="GEMINI_API_KEY"):
        seen["value"] = os.environ.get(key_env_var)
        return None

    monkeypatch.setattr(enhance, "get_gemini_client", fake_client)
    assert run(str(vault.guide), topics=TOPICS, min_words=MIN, env_file=str(env_file)) == 1
    assert seen["value"] == "from-env-file"
    monkeypatch.delenv("PAID_GEMINI_KEY", raising=False)  # dotenv wrote os.environ directly


def test_missing_env_file_is_an_input_error(vault, tmp_path):
    assert run(str(vault.guide), topics=TOPICS, min_words=MIN, env_file=str(tmp_path / "nope.env")) == 2


def test_main_parses_args(vault, monkeypatch):
    captured = {}

    def fake_run(guide, **kw):
        captured.update(guide=guide, **kw)
        return 0

    monkeypatch.setattr(enhance, "run", fake_run)
    rc = enhance.main([str(vault.guide), "--topic", "A", "--topic", "B", "--dry-run", "--force",
                       "--output", "o.md", "--model", "m", "--env-file", "e.env",
                       "--worked-example", "--min-words", "900"])
    assert rc == 0
    assert captured["topics"] == ["A", "B"] and captured["dry_run"] and captured["force"]
    assert captured["output"] == "o.md" and captured["model"] == "m" and captured["env_file"] == "e.env"
    assert captured["worked_example"] is True and captured["min_words"] == 900


def test_main_defaults(vault, monkeypatch):
    captured = {}
    monkeypatch.setattr(enhance, "run", lambda guide, **kw: captured.update(kw) or 0)
    enhance.main([str(vault.guide)])
    assert captured["worked_example"] is False and captured["min_words"] == DEFAULT_MIN_WORDS
