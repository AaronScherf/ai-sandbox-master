import unittest.mock

import pytest

from pipelines.transcribe_notes.agent_driver import NullDriverFired
from pipelines.transcribe_notes.excalidraw_agent_driver import ExcalidrawApiDriver, ExcalidrawNullDriver


def test_api_driver_transcribe_chunk_calls_gemini_through_retries():
    with unittest.mock.patch(
        "pipelines.transcribe_notes.excalidraw_agent_driver.transcribe_page_via_gemini",
        return_value="chunk text",
    ) as mock_call:
        driver = ExcalidrawApiDriver(client=object())
        result = driver.transcribe_chunk("note.excalidraw.md", "model", 0, 3, "prompt", b"img")
    assert result == "chunk text"
    mock_call.assert_called_once_with(driver.client, "model", b"img", "prompt")


def test_null_driver_transcribe_chunk_raises():
    driver = ExcalidrawNullDriver()
    with pytest.raises(NullDriverFired):
        driver.transcribe_chunk("note.excalidraw.md", "model", 0, 3, "prompt", b"img")
