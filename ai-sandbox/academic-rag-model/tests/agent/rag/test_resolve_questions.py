from unittest.mock import MagicMock

import pytest

from agent.rag.resolve_questions import (
    RESOLVER_MODEL,
    build_answer_prompt,
    question_context,
    resolve_question,
)
from core.indexer.index_search import PassageResult
from core.indexer.questions import find_tags

BODY = (
    "**[Slide]**\nSlide A text about completeness\n\n"
    "**[Handwritten]**\nnotes [Question] why not reflexivity?\nmore\n\n"
    "**[Slide]**\nSlide B text\n\n"
    "**[Handwritten]**\n[Question] what if X is infinite?\n"
)


def test_default_model_is_the_stronger_tier():
    assert RESOLVER_MODEL == "gemini-3.6-flash"


def test_context_for_the_first_tag_includes_both_adjacent_slides():
    excerpt, neighbors = question_context(BODY, 1)
    assert "why not reflexivity?" in excerpt
    assert neighbors == ["Slide A text about completeness", "Slide B text"]


def test_context_for_the_last_tag_has_only_the_preceding_slide():
    excerpt, neighbors = question_context(BODY, 2)
    assert "what if X is infinite?" in excerpt
    assert neighbors == ["Slide B text"]


def test_context_for_an_unknown_ordinal_is_empty():
    assert question_context(BODY, 3) == ("", [])


def test_context_excerpt_is_windowed_and_slides_are_truncated():
    body = "**[Slide]**\n" + "s" * 2000 + "\n\n**[Handwritten]**\n" + "a " * 2000 + "[Question] why? " + "b " * 2000
    excerpt, neighbors = question_context(body, 1)
    assert "[Question] why?" in excerpt
    assert len(excerpt) <= 1600
    assert len(neighbors[0]) == 800


def test_grounded_prompt_carries_question_context_slides_and_excerpts():
    passage = PassageResult(chunk_id="c", file_id="f", path="book.md", course="c", score=0.9,
                            text="EXCERPT TEXT", citation="p. 3", root="/r")
    prompt = build_answer_prompt("why not reflexivity?", "my notes", ["Slide B text"], [passage])
    for needle in ("why not reflexivity?", "my notes", "Slide B text", "EXCERPT TEXT", "p. 3"):
        assert needle in prompt


def test_ungrounded_prompt_has_no_excerpts_and_asks_for_general_knowledge():
    prompt = build_answer_prompt("why not reflexivity?", "my notes", [], None)
    assert "general knowledge" in prompt
    assert "EXCERPT" not in prompt


def _client(text="An explanation."):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client


def _passage(text, path="book.md", citation="p. 3"):
    return PassageResult(chunk_id="c1", file_id="f1", path=path, course="c", score=0.9,
                         text=text, citation=citation, root="/r")


def _resolve(client, passages, key_terms, exclude=()):
    tag = find_tags("[Question] what is the Hausdorff distance?")[0]
    return resolve_question(
        tag, "ctx text", ["Slide text"], client=client, roots=["/r"], course="c", model="m",
        exclude_basenames=set(exclude), retrieve=lambda *a, **k: passages, extract=lambda q, c: key_terms,
    )


def test_grounded_when_a_passage_mentions_a_key_term():
    client = _client()
    entry = _resolve(client, [_passage("The Hausdorff metric is defined as ...")], ["Hausdorff"])
    assert entry.grounded is True
    assert entry.sources == ["book.md (p. 3)"]
    assert entry.answer == "An explanation."
    call = client.models.generate_content.call_args.kwargs
    assert call["model"] == "m" and "The Hausdorff metric is defined" in call["contents"]


def test_ungrounded_when_no_passage_mentions_any_key_term():
    client = _client()
    entry = _resolve(client, [_passage("Completely unrelated passage")], ["Hausdorff"])
    assert entry.grounded is False and entry.sources == []
    assert "Completely unrelated passage" not in client.models.generate_content.call_args.kwargs["contents"]


def test_ungrounded_when_nothing_was_retrieved_even_with_no_key_terms():
    assert _resolve(_client(), [], []).grounded is False


def test_grounded_when_there_are_no_key_terms_but_passages_exist():
    assert _resolve(_client(), [_passage("some passage")], []).grounded is True


def test_the_notes_own_files_are_excluded_from_grounding():
    own = _passage("The Hausdorff metric is defined as ...", path="lecture/N.excalidraw.rag.md")
    entry = _resolve(_client(), [own], ["Hausdorff"], exclude={"N.excalidraw.rag.md"})
    assert entry.grounded is False and entry.sources == []


def test_empty_model_answer_raises_so_no_partial_entry_is_recorded():
    with pytest.raises(ValueError):
        _resolve(_client(text="  "), [_passage("Hausdorff")], ["Hausdorff"])


def test_entry_records_identity_model_and_context():
    entry = _resolve(_client(), [_passage("Hausdorff")], ["Hausdorff"])
    tag = find_tags("[Question] what is the Hausdorff distance?")[0]
    assert entry.qid == tag.qid and entry.question == tag.text
    assert entry.model == "m" and entry.resolved_at and entry.stale is False
    assert entry.context == "ctx text"


import os
from unittest.mock import patch

from agent.rag import resolve_questions as rq
from agent.rag.resolve_questions import discover_notes, resolve_note
from core.indexer.index_card import save_shard
from core.indexer.questions import Entry, read_sidecar, rag_path_for, sidecar_path_for

RAW_FM = "---\nchunks: 1\nembedded_slides: true\n---\n\n"
RAG_TEXT = "---\nx: y\n---\n\nProse [Question] why not reflexivity?\n\nMore [Question] what if X is infinite?\n"


def _hub(tmp_path, course="microecon", raw_body=BODY, name="N 2026-09-15"):
    hub = tmp_path / "hub"
    out = hub / "academic_notes" / course / "lecture_notes" / "processed_outputs"
    out.mkdir(parents=True)
    raw = out / f"{name}.excalidraw.md"
    raw.write_text(RAW_FM + raw_body, encoding="utf-8")
    (out / f"{name}.excalidraw.rag.md").write_text(RAG_TEXT, encoding="utf-8")
    return str(hub), str(raw)


def _fake_resolve(failing_ordinals=()):
    def fake(tag, context, neighbors, **kwargs):
        if tag.ordinal in failing_ordinals:
            raise RuntimeError("boom")
        return Entry(qid=tag.qid, question=tag.text, grounded=True, model=kwargs["model"],
                     resolved_at="t", answer="A", sources=["s"])
    return fake


def test_resolve_note_writes_the_sidecar_and_marks_the_rag(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        result = resolve_note(raw, hub, client=object(), roots=[hub])
    assert (result.resolved, result.skipped, result.failed) == (2, 0, [])
    _, entries = read_sidecar(sidecar_path_for(raw))
    assert [e.question for e in entries] == ["why not reflexivity?", "what if X is infinite?"]
    rag = open(rag_path_for(raw), encoding="utf-8").read()
    assert rag.count("[Question: answered ->") == 2


def test_second_run_skips_answered_questions_and_redo_redoes_them(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        resolve_note(raw, hub, client=object(), roots=[hub])
        assert mock.call_count == 2
        again = resolve_note(raw, hub, client=object(), roots=[hub])
        assert mock.call_count == 2 and (again.resolved, again.skipped) == (0, 2)
        resolve_note(raw, hub, client=object(), roots=[hub], redo=True)
        assert mock.call_count == 4


def test_one_failing_question_does_not_stop_the_others_and_is_retried_alone(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve(failing_ordinals={1})):
        result = resolve_note(raw, hub, client=object(), roots=[hub])
    assert result.resolved == 1 and len(result.failed) == 1 and result.failed[0].startswith("q1-")
    _, entries = read_sidecar(sidecar_path_for(raw))
    assert [e.question for e in entries] == ["what if X is infinite?"]
    rag = open(rag_path_for(raw), encoding="utf-8").read()
    assert rag.count("[Question: answered ->") == 1 and "[Question] why not reflexivity?" in rag
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        retry = resolve_note(raw, hub, client=object(), roots=[hub])
    assert mock.call_count == 1 and retry.resolved == 1 and retry.failed == []


def test_budget_caps_the_number_of_questions_resolved(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        result = resolve_note(raw, hub, client=object(), roots=[hub], budget=1)
    assert result.resolved == 1
    assert len(read_sidecar(sidecar_path_for(raw))[1]) == 1


def test_discover_notes_finds_only_raw_transcripts_that_have_tags(tmp_path):
    hub, raw = _hub(tmp_path)
    out = os.path.dirname(raw)
    open(os.path.join(out, "Plain 2026-09-16.excalidraw.md"), "w", encoding="utf-8").write(RAW_FM + "no tags here")
    open(os.path.join(out, "Plain 2026-09-16.excalidraw.rag.md"), "w", encoding="utf-8").write("[Question] x?")
    open(os.path.join(out, "N 2026-09-15.excalidraw.questions.md"), "w", encoding="utf-8").write("[Question] x?")
    assert discover_notes(hub) == [raw]
    assert discover_notes(hub, course="other") == []
    assert discover_notes(hub, note="2026-09-15") == [raw]
    assert discover_notes(hub, note="nomatch") == []


def test_cli_dry_run_lists_questions_without_any_api_call(tmp_path, capsys):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "get_gemini_client", side_effect=AssertionError("no client in dry-run")), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("no resolve in dry-run")):
        assert rq.main(["--root", hub, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "2 question(s)" in out and "why not reflexivity?" in out
    assert not os.path.exists(sidecar_path_for(raw))


def test_cli_skips_notes_that_are_a_subset_of_another(tmp_path, capsys):
    hub, raw = _hub(tmp_path)
    rel_rag = os.path.relpath(rag_path_for(raw), hub).replace(os.sep, "/")
    save_shard(hub, "microecon", [{"file_id": "x", "path": rel_rag, "subset_of": "y"}])
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("subset must be skipped")):
        assert rq.main(["--root", hub]) == 0
    assert "subset" in capsys.readouterr().out
    assert not os.path.exists(sidecar_path_for(raw))


def test_cli_full_run_returns_zero_and_nonzero_on_failure(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        assert rq.main(["--root", hub]) == 0
    os.remove(sidecar_path_for(raw))
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve(failing_ordinals={1})):
        assert rq.main(["--root", hub]) == 1


def test_cli_max_questions_stops_after_the_budget(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        rq.main(["--root", hub, "--max-questions", "1"])
    assert mock.call_count == 1
