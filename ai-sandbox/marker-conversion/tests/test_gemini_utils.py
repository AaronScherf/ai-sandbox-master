import os
import tempfile
import unittest

from common.gemini_utils import (
    extract_retry_delay_seconds,
    load_json_cache,
    save_json_cache,
)


class TestExtractRetryDelaySeconds(unittest.TestCase):
    def test_parses_retryDelay_field_from_real_429_response(self):
        # Verbatim shape from a real 429 hit against gemini-3.6-flash.
        error_text = (
            "429 RESOURCE_EXHAUSTED. {'error': {'code': 429, "
            "'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', "
            "'retryDelay': '52s'}]}}"
        )
        self.assertEqual(extract_retry_delay_seconds(error_text), 52.0)

    def test_parses_fractional_retry_in_phrasing(self):
        error_text = "Please retry in 45.368129527s."
        self.assertAlmostEqual(extract_retry_delay_seconds(error_text), 45.368129527)

    def test_returns_none_when_no_delay_present(self):
        self.assertIsNone(extract_retry_delay_seconds("some unrelated error"))

    def test_accepts_exception_object_not_just_string(self):
        error = RuntimeError("429 RESOURCE_EXHAUSTED ... 'retryDelay': '16s' ...")
        self.assertEqual(extract_retry_delay_seconds(error), 16.0)


class TestJsonCache(unittest.TestCase):
    def test_round_trips_through_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cache.json")
            data = {"pg_1_x.jpeg": {"skip": False, "description": "A plot."}}
            save_json_cache(path, data)
            loaded = load_json_cache(path)
            self.assertEqual(loaded, data)

    def test_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "does_not_exist.json")
            self.assertEqual(load_json_cache(path), {})

    def test_malformed_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cache.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            self.assertEqual(load_json_cache(path), {})


if __name__ == "__main__":
    unittest.main()
