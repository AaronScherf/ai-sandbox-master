from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from core.env import gemini_utils
from core.indexer.index_card import compute_file_id
from pipelines.transcribe_notes import agent_submit, agent_work
from pipelines.transcribe_notes import excalidraw_agent_submit, excalidraw_agent_work
from pipelines.transcribe_notes import route_notes_transcribe as router


def _git_init(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def _setup(tmp_path, monkeypatch, argv, pdf_todo=None, excalidraw_todo=None, courses=None, resolve_questions_todo=None):
    outer = _git_init(tmp_path / "ai-sandbox")
    hub = outer / "academic-hub"
    hub.mkdir()
    _git_init(hub / "academic_notes")
    fake_script = outer / "academic-rag-model" / "pipelines" / "transcribe_notes" / "router.py"
    monkeypatch.setattr(router, "__file__", str(fake_script))
    monkeypatch.setattr(sys, "argv", ["route_notes_transcribe", *argv])
    monkeypatch.setattr(router, "build_plan", lambda *args, **kwargs: SimpleNamespace(
        pdf_todo=list(pdf_todo or []), pdf_skipped=[],
        excalidraw_todo=list(excalidraw_todo or []), excalidraw_skipped=[],
        courses=list(courses or []), resolve_questions_todo=list(resolve_questions_todo or []),
    ))
    monkeypatch.setattr(router, "print_summary", lambda *args: None)
    monkeypatch.setattr(router, "sync_resource_backups", lambda *args, **kwargs: [])
    monkeypatch.setattr(router, "print_backup_summary", lambda *args: None)
    monkeypatch.setattr(gemini_utils, "load_dotenv_override", lambda: None)
    monkeypatch.setattr(gemini_utils, "get_gemini_client", lambda *args: object())
    return hub


def test_default_driver_is_agent_not_api(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, [])
    parsed = router._build_arg_parser().parse_args([])
    assert parsed.driver == "agent"


def test_bootstrap_prints_contract_without_touching_the_corpus(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(router, "build_plan", lambda *a, **k: pytest.fail("bootstrap must not build a plan"))
    monkeypatch.setattr(sys, "argv", ["route_notes_transcribe", "--bootstrap", "run1"])

    router.main()

    out = capsys.readouterr().out
    assert "run1" in out
    assert "route_notes_transcribe --submit run1" in out
    assert "SEGMENT" in out


def test_dry_run_previews_chunk_eligibility_per_course(tmp_path, monkeypatch, capsys):
    _setup(tmp_path, monkeypatch, ["--dry-run"], courses=["microecon"])
    monkeypatch.setattr(
        router, "chunk_notes",
        lambda *args, **kwargs: {"chunked": 3, "unchanged": 5, "failed": 0, "skipped_no_embedding": 0},
    )

    router.main()

    out = capsys.readouterr().out
    assert "[chunk] microecon: 3 to (re)chunk, 5 unchanged" in out


def test_driver_agent_without_collect_or_submit_exits(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, ["--driver", "agent"], pdf_todo=["a.pdf"])
    with pytest.raises(SystemExit):
        router.main()


def test_collect_requires_agent_driver(tmp_path, monkeypatch):
    # --driver now defaults to "agent", so bare --collect is valid on its own;
    # this checks that --collect still conflicts with an *explicit* --driver api.
    _setup(tmp_path, monkeypatch, ["--collect", "--driver", "api"], pdf_todo=["a.pdf"])
    with pytest.raises(SystemExit):
        router.main()


def test_collect_includes_excalidraw_with_its_own_agent_driver(tmp_path, monkeypatch):
    _setup(
        tmp_path, monkeypatch, ["--driver", "agent", "--collect", "--run-id", "r1"],
        pdf_todo=[str(tmp_path / "a.pdf")],
        excalidraw_todo=[("note.excalidraw.md", "note.excalidraw.svg")],
    )

    captured_kwargs = {}

    def fake_run_plan(plan, client, academic_hub_root, **kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs["client"] = client
        captured_kwargs["excalidraw_todo"] = list(plan.excalidraw_todo)
        return SimpleNamespace(pdf_results=[], excalidraw_results=[])

    monkeypatch.setattr(router, "run_plan", fake_run_plan)
    monkeypatch.setattr(agent_work, "dedupe_by_file_id", lambda paths: (list(paths), {}))
    monkeypatch.setattr(agent_work, "AgentDriver", lambda hub_root, run_id: SimpleNamespace(
        hub_root=hub_root, run_id=run_id,
    ))
    monkeypatch.setattr(excalidraw_agent_work, "ExcalidrawAgentDriver", lambda hub_root, run_id: SimpleNamespace(
        hub_root=hub_root, run_id=run_id,
    ))

    router.main()

    assert captured_kwargs["collect_mode"] is True
    assert captured_kwargs["client"] is None
    assert captured_kwargs["excalidraw_todo"] == [("note.excalidraw.md", "note.excalidraw.svg")]
    assert captured_kwargs["excalidraw_driver"].run_id == "r1"


def test_submit_matches_collected_docs_by_slug_and_skips_unmatched(tmp_path, monkeypatch, capsys):
    pdf_path = tmp_path / "ai-sandbox" / "a.pdf"
    hub = _setup(
        tmp_path, monkeypatch, ["--submit", "r1"],
        pdf_todo=[str(pdf_path)],
    )
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"x")

    file_id = compute_file_id(str(pdf_path))
    known_slug = agent_work.doc_slug_for(str(pdf_path), file_id)
    run_dir = hub / ".agent_work" / "r1"
    (run_dir / known_slug).mkdir(parents=True)
    (run_dir / "unmatched--deadbeef").mkdir(parents=True)

    submitted = []
    monkeypatch.setattr(agent_submit, "submit_doc", lambda *args, **kwargs: submitted.append(args) or "ok")

    router.main()

    assert len(submitted) == 1
    assert submitted[0][3] == known_slug
    out = capsys.readouterr().out
    assert "no matching pending document" in out


def test_collect_stages_resolve_questions_via_its_own_agent_driver(tmp_path, monkeypatch):
    raw_path = tmp_path / "ai-sandbox" / "N.excalidraw.md"
    _setup(
        tmp_path, monkeypatch, ["--driver", "agent", "--collect", "--run-id", "r1"],
        resolve_questions_todo=[str(raw_path)],
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("content", encoding="utf-8")

    monkeypatch.setattr(
        router, "run_plan",
        lambda *a, **k: SimpleNamespace(pdf_results=[], excalidraw_results=[]),
    )
    monkeypatch.setattr(agent_work, "dedupe_by_file_id", lambda paths: (list(paths), {}))
    monkeypatch.setattr(agent_work, "AgentDriver", lambda hub_root, run_id: SimpleNamespace())
    monkeypatch.setattr(excalidraw_agent_work, "ExcalidrawAgentDriver", lambda hub_root, run_id: SimpleNamespace())
    monkeypatch.setattr(
        "agent.rag.resolve_questions_agent_work.QuestionResolverAgentDriver",
        lambda hub_root, run_id: SimpleNamespace(run_id=run_id),
    )

    resolved = []
    monkeypatch.setattr(
        "pipelines.transcribe_notes.route_notes_transcribe.resolve_note",
        lambda raw, hub, client, roots, **kwargs: resolved.append((raw, kwargs)),
    )

    router.main()

    assert len(resolved) == 1
    assert resolved[0][0] == str(raw_path)
    assert resolved[0][1]["collect_mode"] is True
    assert resolved[0][1]["driver"].run_id == "r1"


def test_collect_resolve_questions_tolerates_agent_pending_and_other_errors(tmp_path, monkeypatch, capsys):
    raw1 = tmp_path / "ai-sandbox" / "N1.excalidraw.md"
    raw2 = tmp_path / "ai-sandbox" / "N2.excalidraw.md"
    _setup(
        tmp_path, monkeypatch, ["--driver", "agent", "--collect", "--run-id", "r1"],
        resolve_questions_todo=[str(raw1), str(raw2)],
    )
    for raw in (raw1, raw2):
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text("content", encoding="utf-8")

    monkeypatch.setattr(
        router, "run_plan",
        lambda *a, **k: SimpleNamespace(pdf_results=[], excalidraw_results=[]),
    )
    monkeypatch.setattr(agent_work, "dedupe_by_file_id", lambda paths: (list(paths), {}))
    monkeypatch.setattr(agent_work, "AgentDriver", lambda hub_root, run_id: SimpleNamespace())
    monkeypatch.setattr(excalidraw_agent_work, "ExcalidrawAgentDriver", lambda hub_root, run_id: SimpleNamespace())
    monkeypatch.setattr(
        "agent.rag.resolve_questions_agent_work.QuestionResolverAgentDriver",
        lambda hub_root, run_id: SimpleNamespace(run_id=run_id),
    )

    from pipelines.transcribe_notes.agent_driver import AgentPending

    def fake_resolve_note(raw, hub, client, roots, **kwargs):
        if raw == str(raw1):
            raise AgentPending()
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "pipelines.transcribe_notes.route_notes_transcribe.resolve_note", fake_resolve_note,
    )

    router.main()  # must not raise -- both outcomes are handled per-note

    out = capsys.readouterr().out
    assert "ERROR: resolve-questions collect failed" in out


def test_submit_dispatches_a_resolve_questions_slug_and_isolates_chunk_failures(tmp_path, monkeypatch, capsys):
    from core.indexer.index_card import compute_file_id as _cfid
    from pipelines.transcribe_notes.agent_work import doc_slug_for as _dsf

    raw_path = tmp_path / "ai-sandbox" / "N.excalidraw.md"
    hub = _setup(
        tmp_path, monkeypatch, ["--submit", "r1"],
        courses=["bad", "good"],
        resolve_questions_todo=[str(raw_path)],
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("content", encoding="utf-8")

    known_slug = _dsf(str(raw_path), _cfid(str(raw_path)))
    run_dir = hub / ".agent_work" / "r1"
    (run_dir / known_slug).mkdir(parents=True)

    submitted = []
    monkeypatch.setattr(
        "agent.rag.resolve_questions_submit.submit_doc",
        lambda *args, **kwargs: submitted.append(args) or "complete",
    )
    monkeypatch.setattr(
        router, "chunk_notes",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("corrupt shard"))
        if kwargs.get("course") == "bad"
        else {"chunked": 1, "unchanged": 0, "failed": 0, "skipped_no_embedding": 0},
    )

    router.main()

    assert len(submitted) == 1
    assert submitted[0][3] == known_slug
    out = capsys.readouterr().out
    assert "chunking failed for course 'bad'" in out
    assert "Chunk/embed: 1 chunked, 0 unchanged, 1 failed, 0 skipped (no embedding)" in out
