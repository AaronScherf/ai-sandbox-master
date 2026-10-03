import os

from agent.summary_enhance import enhance
from agent.summary_enhance.enhance import run
from conftest import write_guide

TOPICS = ["Wald test", "LM test"]


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def test_happy_path_writes_default_output_and_leaves_original(vault, make_llm, good_response):
    original = vault.guide.read_bytes()
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 0
    out = _out(vault)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "content_kind: enhanced_summary" in text and 'enhancement_model: "fake-model"' in text
    assert "## Wald test" in text and "## LM test" in text
    assert vault.guide.read_bytes() == original
    assert len(llm.calls) == 1


def test_explicit_output_path(vault, make_llm, good_response):
    target = vault.guide.parent / "custom.md"
    assert run(str(vault.guide), topics=TOPICS, output=str(target), llm=make_llm(good_response)) == 0
    assert target.is_file() and not _out(vault).exists()


def test_refuses_to_overwrite_without_force(vault, make_llm, good_response):
    _out(vault).write_text("precious", encoding="utf-8")
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 2
    assert _out(vault).read_text(encoding="utf-8") == "precious" and llm.calls == []
    assert run(str(vault.guide), topics=TOPICS, force=True, llm=make_llm(good_response)) == 0
    assert "enhanced_summary" in _out(vault).read_text(encoding="utf-8")


def test_refuses_output_equal_to_input_even_with_different_spelling(vault, make_llm, good_response):
    spelled = vault.guide.parent / ".." / "summaries" / "guide.md"
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, output=str(spelled), force=True, llm=llm) == 2
    assert llm.calls == []


def test_refuses_output_outside_vault(vault, tmp_path, make_llm, good_response):
    llm = make_llm(good_response)
    assert run(str(vault.guide), topics=TOPICS, output=str(tmp_path / "leak.md"), llm=llm) == 2
    assert not (tmp_path / "leak.md").exists() and llm.calls == []


def test_refuses_non_markdown_output(vault, make_llm, good_response):
    out = vault.guide.parent / "x.txt"
    assert run(str(vault.guide), topics=TOPICS, output=str(out), llm=make_llm(good_response)) == 2


def test_dry_run_makes_no_llm_call_and_writes_nothing(vault, make_llm, capsys):
    llm = make_llm()
    assert run(str(vault.guide), topics=TOPICS, dry_run=True, llm=llm) == 0
    assert llm.calls == [] and not _out(vault).exists()
    printed = capsys.readouterr().out
    assert "3 chunks" in printed and "guide.enhanced.md" in printed


def test_dry_run_does_not_require_an_api_key(vault, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not build a client in dry-run")
    monkeypatch.setattr(enhance, "get_gemini_client", boom)
    assert run(str(vault.guide), topics=TOPICS, dry_run=True) == 0


def test_missing_chunks_exit_before_any_llm_call(vault, make_llm):
    write_guide(vault.guide, vault.refs + [{**vault.refs[0], "chunk_id": "gone"}])
    llm = make_llm()
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 2
    assert llm.calls == []


def test_retry_once_then_succeed(vault, make_llm, good_response):
    bad = {"topics": [{"title": "Wald test",
                       "grounded": [{"text": "x", "sources": ["S9"]}], "elaboration": []}]}
    llm = make_llm(bad, good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 0
    assert len(llm.calls) == 2 and "unknown label 'S9'" in llm.calls[1]


def test_persistent_validation_failure_writes_nothing(vault, make_llm):
    bad = {"topics": [{"title": "Wald test",
                       "grounded": [{"text": "x", "sources": []}], "elaboration": []}]}
    llm = make_llm(bad, bad)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 3
    assert not _out(vault).exists() and len(llm.calls) == 2


def test_unparseable_response_is_retried(vault, make_llm, good_response):
    llm = make_llm({"nope": 1}, good_response)
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 0
    assert len(llm.calls) == 2


def test_llm_exception_writes_nothing(vault, make_llm):
    llm = make_llm(RuntimeError("503"))
    assert run(str(vault.guide), topics=TOPICS, llm=llm) == 4
    assert not _out(vault).exists()


def test_missing_api_key_returns_1(vault, monkeypatch):
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(enhance, "get_gemini_client", lambda key_env_var="": None)
    assert run(str(vault.guide), topics=TOPICS) == 1
    assert not _out(vault).exists()


def test_paid_key_is_the_one_requested(vault, monkeypatch):
    seen = {}
    monkeypatch.setattr(enhance, "load_dotenv_override", lambda: None)

    def fake_client(key_env_var="GEMINI_API_KEY"):
        seen["k"] = key_env_var
        return None

    monkeypatch.setattr(enhance, "get_gemini_client", fake_client)
    run(str(vault.guide), topics=TOPICS)
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
    assert run(str(vault.guide), topics=TOPICS, env_file=str(env_file)) == 1
    assert seen["value"] == "from-env-file"
    monkeypatch.delenv("PAID_GEMINI_KEY", raising=False)  # dotenv wrote os.environ directly


def test_missing_env_file_is_an_input_error(vault, tmp_path, make_llm):
    assert run(str(vault.guide), topics=TOPICS, env_file=str(tmp_path / "nope.env")) == 2


def test_main_parses_args(vault, monkeypatch):
    captured = {}

    def fake_run(guide, **kw):
        captured.update(guide=guide, **kw)
        return 0

    monkeypatch.setattr(enhance, "run", fake_run)
    rc = enhance.main([str(vault.guide), "--topic", "A", "--topic", "B", "--dry-run", "--force",
                       "--output", "o.md", "--model", "m", "--env-file", "e.env"])
    assert rc == 0
    assert captured["topics"] == ["A", "B"] and captured["dry_run"] and captured["force"]
    assert captured["output"] == "o.md" and captured["model"] == "m" and captured["env_file"] == "e.env"
