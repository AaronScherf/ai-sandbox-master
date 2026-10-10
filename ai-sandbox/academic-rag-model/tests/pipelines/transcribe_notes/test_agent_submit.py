# tests/pipelines/transcribe_notes/test_agent_submit.py
import unittest

from pipelines.transcribe_notes.agent_submit import validate_card_output


class TestValidateCardOutput(unittest.TestCase):
    def _good_output(self, pages):
        return "\n\n".join(f"--- PAGE {p} ---\nSome transcribed text for page {p}." for p in pages)

    def test_all_pages_present_passes(self):
        result = validate_card_output(self._good_output([1, 2]), expected_pages=[1, 2], tier="batch")
        self.assertIsNone(result.bounce_reason)
        self.assertEqual(set(result.pages), {1, 2})

    def test_missing_page_bounces(self):
        result = validate_card_output(self._good_output([1]), expected_pages=[1, 2], tier="batch")
        self.assertIsNotNone(result.bounce_reason)
        self.assertIn("2", result.bounce_reason)

    def test_empty_page_bounces(self):
        output = "--- PAGE 1 ---\nSome text.\n\n--- PAGE 2 ---\n\n"
        result = validate_card_output(output, expected_pages=[1, 2], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_unclosed_code_fence_bounces(self):
        output = "--- PAGE 1 ---\n```\nsome code with no closing fence"
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_unbalanced_display_math_bounces(self):
        output = "--- PAGE 1 ---\nSome text with $$x^2 unclosed."
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_single_dollar_currency_does_not_bounce(self):
        output = "--- PAGE 1 ---\nThe price is $5 and the fee is $10."
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNone(result.bounce_reason)

    def test_repetition_loop_bounces(self):
        output = "--- PAGE 1 ---\n" + (". . . " * 60)
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_short_output_warns_not_bounces_for_tier2(self):
        output = "--- PAGE 1 ---\nshort"
        result = validate_card_output(
            output, expected_pages=[1], tier="batch", local_text_hints={1: "a" * 500},
        )
        self.assertIsNone(result.bounce_reason)
        self.assertTrue(result.warnings)

    def test_short_output_does_not_warn_for_tier3(self):
        output = "--- PAGE 1 ---\nshort"
        result = validate_card_output(
            output, expected_pages=[1], tier="tier3", local_text_hints={1: "a" * 500},
        )
        self.assertIsNone(result.bounce_reason)
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
