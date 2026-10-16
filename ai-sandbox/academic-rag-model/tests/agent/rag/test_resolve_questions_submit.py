import os
import tempfile
import unittest.mock

from agent.rag.resolve_questions import answers_cache_path_for, answers_meta_cache_path_for, keyterms_cache_path_for
from core.env.gemini_utils import load_json_cache
from core.indexer.index_card import compute_file_id
from core.indexer.questions import read_sidecar, sidecar_path_for
from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import ManifestEntry, doc_slug_for, load_manifest, save_manifest
from agent.rag.resolve_questions_submit import submit_doc, validate_answer_card_output, validate_keyterms_card_output


def test_validate_keyterms_card_output_parses_all_sections():
    raw = "--- KEYTERMS q1-abc ---\nHausdorff, Luce\n--- KEYTERMS q2-def ---\n\n"
    result = validate_keyterms_card_output(raw, expected_qids=["q1-abc", "q2-def"])
    assert result.pages == {"q1-abc": "Hausdorff, Luce", "q2-def": ""}
    assert result.bounce_reason is None  # an empty key-terms section is valid -- "no specific terms" is a real answer


def test_validate_keyterms_card_output_bounces_on_a_missing_section():
    raw = "--- KEYTERMS q1-abc ---\nHausdorff\n"
    result = validate_keyterms_card_output(raw, expected_qids=["q1-abc", "q2-def"])
    assert result.bounce_reason is not None
    assert "q2-def" in result.bounce_reason


def test_validate_answer_card_output_bounces_on_an_empty_answer():
    raw = "--- ANSWER q1-abc ---\n\n"
    result = validate_answer_card_output(raw, expected_qids=["q1-abc"])
    assert result.bounce_reason is not None


def test_submit_doc_writes_keyterms_cache_and_stages_the_answer_card():
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
        os.makedirs(notes_dir)
        raw_path = os.path.join(notes_dir, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("---\n---\n\n[Question] what is the Hausdorff distance?\n")

        doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        task_id = "task-0001"
        from core.indexer.questions import find_tags
        qid = find_tags("[Question] what is the Hausdorff distance?")[0].qid
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            f.write(f"## Agent output\n\n--- KEYTERMS {qid} ---\nHausdorff\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="keyterms", pages=[qid], status="pending")])

        with unittest.mock.patch(
            "agent.rag.resolve_questions_submit.QuestionResolverAgentDriver",
        ) as MockAgentDriver, unittest.mock.patch(
            "agent.rag.resolve_questions.retrieve_passages", return_value=[],
        ):
            mock_instance = MockAgentDriver.return_value
            mock_instance.stage_answers.side_effect = AgentPending()
            status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

        assert "incomplete" in status
        mock_instance.stage_answers.assert_called_once()


def test_submit_doc_finalizes_into_the_sidecar_once_both_stages_are_cached(tmp_path):
    hub = str(tmp_path / "hub")
    notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
    os.makedirs(notes_dir)
    raw_path = os.path.join(notes_dir, "N.excalidraw.md")
    question = "[Question] what is the Hausdorff distance?"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(f"---\n---\n\n{question}\n")
    rag_path = raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(f"---\n---\n\n{question}\n")

    from core.indexer.questions import find_tags
    qid = find_tags(question)[0].qid
    doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
    doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
    os.makedirs(doc_dir)
    save_manifest(doc_dir, [
        ManifestEntry(task_id="task-0001", tier="keyterms", pages=[qid], status="submitted"),
        ManifestEntry(task_id="task-0002", tier="answers", pages=[qid], status="submitted"),
    ])
    import json
    with open(keyterms_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: ["Hausdorff"]}, f)
    with open(answers_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: "An explanation."}, f)
    with open(answers_meta_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: {"grounded": True, "sources": ["book.md (p. 1)"], "context": "ctx"}}, f)

    status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

    assert status == "complete"
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert entries[0].answer == "An explanation."
    assert entries[0].qid == qid
    assert entries[0].grounded is True
    assert entries[0].sources == ["book.md (p. 1)"]


def test_submit_doc_with_no_manifest_does_not_crash():
    # Review Focus: a mistyped doc-slug, or a note already fully submitted
    # and swept out of .agent_work/, must report "incomplete", not raise.
    with tempfile.TemporaryDirectory() as hub:
        raw_path = os.path.join(hub, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("---\n---\n\n[Question] x?\n")
        status = submit_doc(
            hub, hub, "run-1", "nonexistent-slug", raw_path, hub, client=object(), model_override="m",
            allow_api_fallback=True,
        )
    assert "incomplete" in status


def test_bounced_keyterms_card_is_marked_and_not_written_to_cache():
    # Review Focus: a bounced key-term card must not land in the cache --
    # a later resumed collect/submit must re-request it, not treat the
    # bounce as done.
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
        os.makedirs(notes_dir)
        raw_path = os.path.join(notes_dir, "N.excalidraw.md")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write("---\n---\n\n[Question] what is the Hausdorff distance?\n")
        from core.indexer.questions import find_tags
        qid = find_tags("[Question] what is the Hausdorff distance?")[0].qid

        doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
        doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
        os.makedirs(doc_dir)
        task_id = "task-0001"
        with open(os.path.join(doc_dir, f"{task_id}.md"), "w", encoding="utf-8") as f:
            # Filled, but with the wrong qid -- parse_card_output sees real
            # content (not "not filled yet"), so validation runs and bounces
            # on the missing expected qid, unlike a wholly-empty section
            # (which stays "pending" -- not yet filled -- by design).
            f.write(f"## Agent output\n\n--- KEYTERMS wrong-qid ---\nsome terms\n")
        save_manifest(doc_dir, [ManifestEntry(task_id=task_id, tier="keyterms", pages=[qid], status="pending")])

        status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

        assert "incomplete" in status
        cache = load_json_cache(keyterms_cache_path_for(raw_path))
        assert qid not in cache
        entries = load_manifest(doc_dir)
        assert entries[0].status == "bounced"


def test_submit_doc_warns_on_an_orphaned_manifest_qid_but_still_finalizes_the_rest(tmp_path, capsys):
    # Final-review Important finding #5: a manifest qid that no longer
    # matches any tag in the note (the question's text changed between
    # collect and submit, e.g. a retranscription ran in between) must warn,
    # not silently block every other already-submitted card in this run.
    hub = str(tmp_path / "hub")
    notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
    os.makedirs(notes_dir)
    raw_path = os.path.join(notes_dir, "N.excalidraw.md")
    question = "[Question] what is the Hausdorff distance?"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(f"---\n---\n\n{question}\n")
    rag_path = raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(f"---\n---\n\n{question}\n")

    from core.indexer.questions import find_tags
    qid = find_tags(question)[0].qid
    stale_qid = "q1-deadbeef"  # a qid this run collected that no tag matches any more
    doc_slug = doc_slug_for(raw_path, compute_file_id(raw_path))
    doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
    os.makedirs(doc_dir)
    save_manifest(doc_dir, [
        ManifestEntry(task_id="task-0001", tier="keyterms", pages=[qid, stale_qid], status="submitted"),
        ManifestEntry(task_id="task-0002", tier="answers", pages=[qid, stale_qid], status="submitted"),
    ])
    import json
    with open(keyterms_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: ["Hausdorff"], stale_qid: ["old"]}, f)
    with open(answers_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({qid: "An explanation.", stale_qid: "An old answer."}, f)
    with open(answers_meta_cache_path_for(raw_path), "w", encoding="utf-8") as f:
        json.dump({
            qid: {"grounded": True, "sources": [], "context": "ctx"},
            stale_qid: {"grounded": True, "sources": [], "context": "ctx"},
        }, f)

    status = submit_doc(hub, hub, "run-1", doc_slug, raw_path, hub, client=object(), model_override="m")

    assert status == "complete"
    assert "no longer match any tag" in capsys.readouterr().out
    _, entries = read_sidecar(sidecar_path_for(raw_path))
    assert [e.qid for e in entries] == [qid]


def test_finalize_note_answers_never_re_runs_retrieval_and_isolates_a_missing_meta_entry():
    # Review Focus: finalize_note_answers must never re-run retrieval (its
    # grounded/sources must match exactly what the agent was shown at
    # staging time, from the answers-meta cache) -- and a qid whose meta
    # entry is somehow missing must not lose every other already-cached
    # answer in the note, same resilience resolve_note's own sequential
    # loop already has.
    with tempfile.TemporaryDirectory() as hub:
        notes_dir = os.path.join(hub, "academic_notes", "c", "lecture_notes", "processed_outputs")
        os.makedirs(notes_dir)
        raw_path = os.path.join(notes_dir, "N.excalidraw.md")
        body = "[Question] first one?\n\n[Question] second one?\n"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(f"---\n---\n\n{body}")
        rag_path = raw_path.replace(".excalidraw.md", ".excalidraw.rag.md")
        with open(rag_path, "w", encoding="utf-8") as f:
            f.write(f"---\n---\n\n{body}")

        from core.indexer.questions import find_tags
        tags = find_tags(body)
        with open(answers_cache_path_for(raw_path), "w", encoding="utf-8") as f:
            import json
            json.dump({t.qid: f"answer for {t.text}" for t in tags}, f)
        # Only the second tag has staging metadata -- the first is missing it.
        with open(answers_meta_cache_path_for(raw_path), "w", encoding="utf-8") as f:
            json.dump({tags[1].qid: {"grounded": True, "sources": ["s"], "context": "ctx"}}, f)

        with unittest.mock.patch(
            "agent.rag.resolve_questions.retrieve_passages",
            side_effect=AssertionError("finalize must never call retrieval"),
        ):
            from agent.rag.resolve_questions_submit import finalize_note_answers
            finalize_note_answers(raw_path, hub)

        _, entries = read_sidecar(sidecar_path_for(raw_path))
        assert len(entries) == 1  # the first qid's missing metadata was isolated; the second still resolved
        assert entries[0].question == "second one?"
