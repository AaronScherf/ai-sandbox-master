import unittest.mock

import pytest

from pipelines.transcribe_notes.agent_driver import NullDriverFired
from agent.rag.resolve_questions_driver import QuestionResolverApiDriver, QuestionResolverNullDriver


def test_api_driver_extract_key_terms_calls_gemini():
    client = unittest.mock.MagicMock()
    client.models.generate_content.return_value = unittest.mock.MagicMock(text="Hausdorff, Luce")
    driver = QuestionResolverApiDriver(client)
    result = driver.extract_key_terms("note.excalidraw.md", "q1-abc", "prompt text")
    assert result == "Hausdorff, Luce"
    call = client.models.generate_content.call_args.kwargs
    assert call["contents"] == "prompt text"


def test_api_driver_generate_answer_calls_gemini():
    client = unittest.mock.MagicMock()
    client.models.generate_content.return_value = unittest.mock.MagicMock(text="An explanation.")
    driver = QuestionResolverApiDriver(client)
    result = driver.generate_answer("note.excalidraw.md", "q1-abc", "answer prompt")
    assert result == "An explanation."


def test_null_driver_raises_on_every_method():
    driver = QuestionResolverNullDriver()
    with pytest.raises(NullDriverFired):
        driver.extract_key_terms("note.excalidraw.md", "q1-abc", "p")
    with pytest.raises(NullDriverFired):
        driver.generate_answer("note.excalidraw.md", "q1-abc", "p")
    with pytest.raises(NullDriverFired):
        driver.stage_key_terms("note.excalidraw.md", [("q1-abc", "p")])
    with pytest.raises(NullDriverFired):
        driver.stage_answers("note.excalidraw.md", [("q1-abc", "p")])
