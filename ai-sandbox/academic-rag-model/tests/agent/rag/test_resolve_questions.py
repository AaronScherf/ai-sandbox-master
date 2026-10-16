from unittest.mock import MagicMock

import pytest

from agent.rag.resolve_questions import (
    RESOLVER_MODEL,
    answers_cache_path_for,
    build_answer_prompt,
    keyterms_cache_path_for,
    question_context,
    resolve_question,
)
from core.indexer.index_search import PassageResult
from core.indexer.questions import find_tags


def test_keyterms_cache_path_sits_next_to_the_sidecar():
    path = keyterms_cache_path_for("/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.md")
    assert path == "/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.keyterms_cache.json"


def test_answers_cache_path_sits_next_to_the_sidecar():
    path = answers_cache_path_for("/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.md")
    assert path == "/hub/academic_notes/c/lecture_notes/processed_outputs/N.excalidraw.answers_cache.json"

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
        exclude_paths=set(exclude), retrieve=lambda *a, **k: passages, extract=lambda q, c: key_terms,
    )


def test_resolve_question_routes_key_terms_and_answer_through_a_driver():
    class FakeDriver:
        def __init__(self):
            self.calls = []

        def extract_key_terms(self, note_key, qid, prompt):
            self.calls.append(("extract", note_key, qid))
            return "Hausdorff"

        def generate_answer(self, note_key, qid, prompt):
            self.calls.append(("answer", note_key, qid))
            assert "Hausdorff metric" in prompt  # the retrieved passage reached the prompt
            return "An explanation via the driver."

    driver = FakeDriver()
    tag = find_tags("[Question] what is the Hausdorff distance?")[0]
    entry = resolve_question(
        tag, "ctx text", ["Slide text"], client=object(), roots=["/r"], course="c", model="m",
        exclude_paths=set(), retrieve=lambda *a, **k: [_passage("The Hausdorff metric is defined as ...")],
        driver=driver, note_key="note.excalidraw.md",
    )
    assert entry.answer == "An explanation via the driver."
    assert entry.grounded is True
    assert [c[0] for c in driver.calls] == ["extract", "answer"]
    assert all(c[1] == "note.excalidraw.md" for c in driver.calls)
    assert all(c[2] == tag.qid for c in driver.calls)


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
    entry = _resolve(_client(), [own], ["Hausdorff"], exclude={"lecture/N.excalidraw.rag.md"})
    assert entry.grounded is False and entry.sources == []


def test_a_same_named_note_in_another_folder_is_not_excluded():
    other = _passage("The Hausdorff metric is defined as ...", path="week2/N.excalidraw.rag.md")
    entry = _resolve(_client(), [other], ["Hausdorff"], exclude={"lecture/N.excalidraw.rag.md"})
    assert entry.grounded is True
    assert entry.sources == ["week2/N.excalidraw.rag.md (p. 3)"]


def test_windows_style_passage_paths_still_match_the_exclusion():
    own = _passage("The Hausdorff metric is defined as ...", path="lecture\\N.excalidraw.rag.md")
    entry = _resolve(_client(), [own], ["Hausdorff"], exclude={"lecture/N.excalidraw.rag.md"})
    assert entry.grounded is False


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


def test_resolve_note_collect_mode_stages_key_terms_for_every_pending_question(tmp_path):
    hub, raw = _hub(tmp_path)

    class FakeDriver:
        def __init__(self):
            self.staged = None

        def stage_key_terms(self, note_key, missing):
            self.staged = missing
            return {}  # nothing returned yet -- simulates an AgentDriver-style "card written" collect

    driver = FakeDriver()
    resolve_note(raw, hub, client=None, roots=[hub], driver=driver, collect_mode=True)
    assert driver.staged is not None
    assert {qid for qid, _prompt in driver.staged} == {
        t.qid for t in find_tags(_read_body_for_test(raw))
    }


def _read_body_for_test(raw_path):
    from core.env.frontmatter import parse_frontmatter
    with open(raw_path, encoding="utf-8") as f:
        return parse_frontmatter(f.read())[1]


def test_redo_in_collect_mode_does_not_re_extract_already_cached_key_terms(tmp_path):
    # Review Focus: redo must force re-answering, not force re-extracting
    # key terms that are already cached under the same qid (the question
    # text, and therefore its qid, hasn't changed just because --redo was
    # passed) -- a deliberate scope decision, pinned here so it isn't later
    # "fixed" into silently diverging from the plain API path.
    hub, raw = _hub(tmp_path)
    tags = find_tags(BODY)
    import json
    with open(keyterms_cache_path_for(raw), "w", encoding="utf-8") as f:
        json.dump({t.qid: ["already cached"] for t in tags}, f)
    # Also mark both questions already answered, so only --redo makes them pending.
    from core.indexer.questions import Entry, write_sidecar
    write_sidecar(sidecar_path_for(raw), {}, [
        Entry(qid=t.qid, question=t.text, grounded=True, model="m", resolved_at="t", answer="old answer")
        for t in tags
    ])

    class FakeDriver:
        def stage_key_terms(self, note_key, missing):
            pytest.fail("key-term stage must not run -- every qid is already cached")

        def stage_answers(self, note_key, missing):
            return {}

    with patch.object(rq, "retrieve_passages", return_value=[]):
        resolve_note(raw, hub, client=object(), roots=[hub], driver=FakeDriver(), collect_mode=True, redo=True)


def test_resolve_note_collect_mode_stages_answers_once_key_terms_are_cached(tmp_path):
    hub, raw = _hub(tmp_path)

    class FakeDriver:
        def __init__(self):
            self.answer_calls = None

        def stage_key_terms(self, note_key, missing):
            pytest.fail("key-term stage must not run again -- cache already has both questions")

        def stage_answers(self, note_key, missing):
            self.answer_calls = missing
            return {}

    # Pre-seed the key-terms cache as if a prior collect already filled it.
    tags = find_tags(BODY)
    import json
    with open(keyterms_cache_path_for(raw), "w", encoding="utf-8") as f:
        json.dump({t.qid: ["term"] for t in tags}, f)

    driver = FakeDriver()
    with patch.object(rq, "retrieve_passages", return_value=[]):
        resolve_note(raw, hub, client=object(), roots=[hub], driver=driver, collect_mode=True)
    assert driver.answer_calls is not None
    assert {qid for qid, _prompt in driver.answer_calls} == {t.qid for t in tags}


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


def test_resolve_note_excludes_the_notes_own_files_by_hub_relative_path(tmp_path):
    hub, raw = _hub(tmp_path)
    seen = []

    def spy(tag, context, neighbors, **kwargs):
        seen.append(kwargs["exclude_paths"])
        return _fake_resolve()(tag, context, neighbors, **kwargs)

    with patch.object(rq, "resolve_question", side_effect=spy):
        resolve_note(raw, hub, client=object(), roots=[hub])
    base = "academic_notes/microecon/lecture_notes/processed_outputs/N 2026-09-15"
    assert seen[0] == {base + ".excalidraw.rag.md", base + ".excalidraw.questions.md"}


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


def test_cli_default_driver_is_agent_not_api():
    parser = rq._build_arg_parser()
    parsed = parser.parse_args([])
    assert parsed.driver == "agent"
    assert parsed.allow_api_fallback is False


def test_cli_dry_run_lists_questions_without_any_api_call(tmp_path, capsys):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "get_gemini_client", side_effect=AssertionError("no client in dry-run")), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("no resolve in dry-run")):
        assert rq.main(["--root", hub, "--dry-run", "--driver", "api"]) == 0
    out = capsys.readouterr().out
    assert "2 question(s)" in out and "why not reflexivity?" in out
    assert not os.path.exists(sidecar_path_for(raw))


def test_cli_dry_run_works_under_the_default_agent_driver_without_collect_or_submit(tmp_path, capsys):
    # --dry-run never calls a driver at all, so it must not be blocked by
    # the "--driver agent requires --collect or --submit" guard.
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "get_gemini_client", side_effect=AssertionError("no client in dry-run")), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("no resolve in dry-run")):
        assert rq.main(["--root", hub, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "2 question(s)" in out and "why not reflexivity?" in out


def test_cli_skips_notes_that_are_a_subset_of_another(tmp_path, capsys):
    hub, raw = _hub(tmp_path)
    rel_rag = os.path.relpath(rag_path_for(raw), hub).replace(os.sep, "/")
    save_shard(hub, "microecon", [{"file_id": "x", "path": rel_rag, "subset_of": "y"}])
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=AssertionError("subset must be skipped")):
        assert rq.main(["--root", hub, "--driver", "api"]) == 0
    assert "subset" in capsys.readouterr().out
    assert not os.path.exists(sidecar_path_for(raw))


def test_cli_full_run_returns_zero_and_nonzero_on_failure(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        assert rq.main(["--root", hub, "--driver", "api"]) == 0
    os.remove(sidecar_path_for(raw))
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve(failing_ordinals={1})):
        assert rq.main(["--root", hub, "--driver", "api"]) == 1


def test_cli_max_questions_stops_after_the_budget(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()), \
         patch.object(rq, "resolve_question", side_effect=_fake_resolve()) as mock:
        rq.main(["--root", hub, "--max-questions", "1", "--driver", "api"])
    assert mock.call_count == 1


def test_cli_submit_warns_and_skips_an_orphaned_collected_doc(tmp_path, capsys):
    # Review Focus: if a note's raw transcript changes between --collect and
    # --submit (e.g. a retranscription ran in between), compute_file_id
    # changes, so the doc_slug under .agent_work/<run>/ no longer matches
    # any currently-discoverable note. Must warn and skip, never crash.
    hub, raw = _hub(tmp_path)
    run_dir = os.path.join(hub, ".agent_work", "run-1", "orphaned-doc--deadbeef")
    os.makedirs(run_dir)
    with patch.object(rq, "load_dotenv_override"), patch.object(rq, "get_gemini_client", return_value=object()):
        assert rq.main(["--root", hub, "--submit", "run-1"]) == 0
    assert "no matching pending note" in capsys.readouterr().out


def test_resolve_note_reuses_an_answer_whose_ordinal_shifted_in_a_retranscription(tmp_path):
    hub, raw = _hub(tmp_path)
    with patch.object(rq, "resolve_question", side_effect=_fake_resolve()):
        resolve_note(raw, hub, client=object(), roots=[hub])
    # re-transcription dropped the first question above the second: ordinal 2 becomes 1
    shifted_body = BODY.replace("notes [Question] why not reflexivity?\nmore", "notes\nmore")
    with open(raw, "w", encoding="utf-8") as f:
        f.write(RAW_FM + shifted_body)
    with patch.object(rq, "resolve_question", side_effect=AssertionError("answered question must be reused")) as mock:
        result = resolve_note(raw, hub, client=object(), roots=[hub])
    assert (result.resolved, result.skipped, result.failed) == (0, 1, [])
    mock.assert_not_called()
    new_qid = find_tags(shifted_body)[0].qid
    assert new_qid.startswith("q1-")
    _, entries = read_sidecar(sidecar_path_for(raw))
    assert new_qid in {e.qid for e in entries}
