import unittest
from unittest.mock import MagicMock, patch

from pipelines.transcribe_notes.agent_driver import AgentPending, ApiDriver, NullDriver, NullDriverFired


class TestApiDriver(unittest.TestCase):
    def test_transcribe_batch_calls_repair_batch_through_retries(self):
        client = MagicMock()
        driver = ApiDriver(client)
        with patch("pipelines.transcribe_notes.agent_driver.repair_batch", return_value={1: "page one"}) as mock_repair:
            with patch("pipelines.transcribe_notes.agent_driver.call_with_retries", side_effect=lambda fn: fn()):
                result = driver.transcribe_batch("fake.pdf", "model-x", [1, 2], "prompt")
        self.assertEqual(result, {1: "page one"})
        mock_repair.assert_called_once_with(client, "model-x", "fake.pdf", [1, 2], "prompt")

    def test_transcribe_page_calls_transcribe_page_via_gemini_through_retries(self):
        client = MagicMock()
        driver = ApiDriver(client)
        with patch("pipelines.transcribe_notes.agent_driver.transcribe_page_via_gemini", return_value="text") as mock_t:
            with patch("pipelines.transcribe_notes.agent_driver.call_with_retries", side_effect=lambda fn: fn()):
                result = driver.transcribe_page("fake.pdf", "model-x", 3, "prompt", b"bytes", 10)
        self.assertEqual(result, "text")
        mock_t.assert_called_once_with(client, "model-x", b"bytes", "prompt")


class TestNullDriver(unittest.TestCase):
    def test_transcribe_batch_raises_null_driver_fired(self):
        driver = NullDriver()
        with self.assertRaises(NullDriverFired):
            driver.transcribe_batch("fake.pdf", "model-x", [1, 2], "prompt")

    def test_transcribe_page_raises_null_driver_fired(self):
        driver = NullDriver()
        with self.assertRaises(NullDriverFired):
            driver.transcribe_page("fake.pdf", "model-x", 1, "prompt", b"bytes", 5)

    def test_null_driver_fired_is_a_runtime_error(self):
        # Code that still catches the old RuntimeError type keeps working.
        self.assertTrue(issubclass(NullDriverFired, RuntimeError))


class TestAgentPending(unittest.TestCase):
    def test_is_an_exception_not_caught_by_bare_except_exception_shadowing(self):
        # AgentPending must subclass Exception (so it IS catchable), but callers
        # must check for it with its own except clause before a generic one.
        self.assertTrue(issubclass(AgentPending, Exception))


if __name__ == "__main__":
    unittest.main()
