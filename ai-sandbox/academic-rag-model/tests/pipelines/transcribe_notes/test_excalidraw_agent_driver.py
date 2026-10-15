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


def test_api_driver_stage_chunks_transcribes_each_missing_one():
    with unittest.mock.patch(
        "pipelines.transcribe_notes.excalidraw_agent_driver.transcribe_page_via_gemini",
        side_effect=["text 0", "text 2"],
    ):
        driver = ExcalidrawApiDriver(client=object())
        result = driver.stage_chunks(
            "note.excalidraw.md", "model",
            missing=[(0, "prompt 0", b"img0"), (2, "prompt 2", b"img2")], total_chunks=3,
        )
    assert result == {0: "text 0", 2: "text 2"}


def test_null_driver_stage_chunks_raises_when_anything_is_missing():
    driver = ExcalidrawNullDriver()
    with pytest.raises(NullDriverFired):
        driver.stage_chunks("note.excalidraw.md", "model", missing=[(0, "p", b"img")], total_chunks=1)
