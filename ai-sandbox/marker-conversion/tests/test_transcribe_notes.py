import os
import tempfile
import unittest

from transcribe_notes import (
    build_accumulated_context,
    build_final_markdown,
    build_transcription_prompt,
    discover_pdf_files,
    parse_transcription_response,
)


class TestDiscoverPdfFiles(unittest.TestCase):
    def test_finds_pdf_files_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ["b.pdf", "a.pdf", "notes.txt"]:
                open(os.path.join(tmp, name), "w").close()
            files = discover_pdf_files(tmp)
            self.assertEqual([os.path.basename(f) for f in files], ["a.pdf", "b.pdf"])

    def test_filters_to_one_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ["a.pdf", "b.pdf"]:
                open(os.path.join(tmp, name), "w").close()
            files = discover_pdf_files(tmp, file_filter="b.pdf")
            self.assertEqual([os.path.basename(f) for f in files], ["b.pdf"])

    def test_missing_directory_returns_empty_list(self):
        self.assertEqual(discover_pdf_files("/no/such/dir"), [])

    def test_ignores_non_pdf_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "notes.txt"), "w").close()
            self.assertEqual(discover_pdf_files(tmp), [])


class TestBuildAccumulatedContext(unittest.TestCase):
    def test_joins_prior_pages_in_order(self):
        cache = {"1": "First page text.", "2": "Second page text."}
        context = build_accumulated_context(cache, up_to_page=3)
        self.assertIn("First page text.", context)
        self.assertIn("Second page text.", context)
        self.assertLess(context.index("First page text."), context.index("Second page text."))

    def test_no_prior_pages_returns_empty_string(self):
        self.assertEqual(build_accumulated_context({}, up_to_page=1), "")

    def test_only_includes_pages_before_the_target(self):
        cache = {"1": "Page one.", "2": "Page two.", "3": "Page three (should not appear)."}
        context = build_accumulated_context(cache, up_to_page=3)
        self.assertIn("Page one.", context)
        self.assertIn("Page two.", context)
        self.assertNotIn("should not appear", context)

    def test_gap_in_cache_is_skipped_gracefully(self):
        # Page 2 missing (e.g. a prior run failed there) -- shouldn't crash,
        # just omit it from context.
        cache = {"1": "Page one.", "3": "Page three."}
        context = build_accumulated_context(cache, up_to_page=4)
        self.assertIn("Page one.", context)
        self.assertIn("Page three.", context)


class TestBuildTranscriptionPrompt(unittest.TestCase):
    def test_includes_context_and_hint_and_page_numbers(self):
        prompt = build_transcription_prompt(
            accumulated_context="Prior page content.",
            hint_text="raw pypdf text",
            page_number=3,
            total_pages=10,
        )
        self.assertIn("Prior page content.", prompt)
        self.assertIn("raw pypdf text", prompt)
        self.assertIn("3", prompt)
        self.assertIn("10", prompt)
        self.assertIn("OneNote", prompt)

    def test_handles_empty_context_and_hint(self):
        prompt = build_transcription_prompt(
            accumulated_context="", hint_text="", page_number=1, total_pages=1,
        )
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)


class TestParseTranscriptionResponse(unittest.TestCase):
    def test_strips_surrounding_whitespace(self):
        self.assertEqual(parse_transcription_response("  \n  Some text.  \n  "), "Some text.")

    def test_strips_markdown_code_fence(self):
        response = "```markdown\n# Problem 1\n\nSolve for x.\n```"
        self.assertEqual(parse_transcription_response(response), "# Problem 1\n\nSolve for x.")

    def test_strips_bare_code_fence(self):
        response = "```\nSome content.\n```"
        self.assertEqual(parse_transcription_response(response), "Some content.")

    def test_leaves_content_without_fence_untouched(self):
        response = "# Problem 1\n\nNo fence here."
        self.assertEqual(parse_transcription_response(response), "# Problem 1\n\nNo fence here.")

    def test_handles_none_gracefully(self):
        self.assertEqual(parse_transcription_response(None), "")


class TestBuildFinalMarkdown(unittest.TestCase):
    def test_assembles_pages_in_order_with_tags(self):
        cache = {"1": "First page.", "2": "Second page."}
        md = build_final_markdown(cache, total_pages=2)
        self.assertIn("<!-- page 1 -->", md)
        self.assertIn("<!-- page 2 -->", md)
        self.assertIn("First page.", md)
        self.assertIn("Second page.", md)
        self.assertLess(md.index("First page."), md.index("Second page."))

    def test_skips_missing_pages_gracefully(self):
        cache = {"1": "First page.", "3": "Third page."}
        md = build_final_markdown(cache, total_pages=3)
        self.assertIn("First page.", md)
        self.assertIn("Third page.", md)
        self.assertNotIn("<!-- page 2 -->", md)


if __name__ == "__main__":
    unittest.main()
