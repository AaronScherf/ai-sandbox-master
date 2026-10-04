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
