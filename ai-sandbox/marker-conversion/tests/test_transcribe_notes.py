import os
import tempfile
import unittest

from transcribe_notes import (
    build_accumulated_context,
    build_final_markdown,
    build_transcription_prompt,
    discover_pdf_files,
    has_reliable_pagination,
    parse_transcription_response,
    should_use_local_extraction,
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

    def test_high_confidence_hint_gets_different_framing(self):
        low_conf = build_transcription_prompt(
            accumulated_context="", hint_text="some text", page_number=1, total_pages=1,
            hint_is_high_confidence=False,
        )
        high_conf = build_transcription_prompt(
            accumulated_context="", hint_text="some text", page_number=1, total_pages=1,
            hint_is_high_confidence=True,
        )
        self.assertNotEqual(low_conf, high_conf)
        self.assertIn("?", high_conf)  # explains the '?' placeholder failure mode

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


class TestHasReliablePagination(unittest.TestCase):
    def test_latex_creator_is_reliable(self):
        # Real metadata from LN_Analysis.pdf.
        metadata = {"/Creator": "LaTeX with hyperref", "/Producer": "pdfTeX-1.40.27"}
        self.assertTrue(has_reliable_pagination(metadata))

    def test_generic_microsoft_print_driver_is_not_reliable(self):
        # "Microsoft Print to PDF" is a generic virtual printer -- it
        # could print anything, including a scan, so it's not real
        # evidence of a properly-typeset source the way "Word" or
        # "LaTeX" specifically are. Also guards against re-broadening
        # the markers back to a bare "microsoft", which previously
        # misclassified OneNote exports as reliable.
        metadata = {"/Creator": "", "/Producer": "Microsoft: Print To PDF"}
        self.assertFalse(has_reliable_pagination(metadata))

    def test_word_creator_with_trademark_symbol_is_reliable(self):
        # Real Word "Save as PDF" metadata often includes a trademark
        # symbol that would break a combined "microsoft word" phrase match.
        metadata = {"/Creator": "Microsoft® Word for Microsoft 365", "/Producer": ""}
        self.assertTrue(has_reliable_pagination(metadata))

    def test_nebo_myscript_is_not_reliable(self):
        # Real metadata from the Nebo-exported problem sets.
        metadata = {"/Creator": "Nebo", "/Producer": "MyScript interactive ink"}
        self.assertFalse(has_reliable_pagination(metadata))

    def test_onenote_is_not_reliable(self):
        # Real metadata from actual ta_notes files -- and the exact
        # regression this test guards against: "Microsoft OneNote"
        # contains "microsoft" as a substring, which an earlier, broader
        # marker list matched and misclassified as reliable. OneNote is
        # the canonical non-adjacent-paragraph-splitting source this
        # whole accumulating-context design exists to handle.
        metadata = {
            "/Creator": "Microsoft® OneNote® for Microsoft 365",
            "/Producer": "Microsoft® OneNote® for Microsoft 365",
        }
        self.assertFalse(has_reliable_pagination(metadata))

    def test_missing_metadata_defaults_to_unreliable(self):
        self.assertFalse(has_reliable_pagination(None))
        self.assertFalse(has_reliable_pagination({}))


class TestShouldUseLocalExtraction(unittest.TestCase):
    def test_clean_prose_sample_uses_local_extraction(self):
        samples = [
            "This is a normal paragraph of clean prose with no garbling at all.",
            "Another page of ordinary sentences, still perfectly readable throughout.",
        ]
        self.assertTrue(should_use_local_extraction(samples))

    def test_garbled_math_sample_does_not_use_local_extraction(self):
        # Real garbled pypdf output from LN_Analysis.pdf page 10 -- every
        # math symbol/variable came through as a bare '?'.
        samples = [
            "Returning to ?=[0,1), we have inf?=0,sup?=1. Since0??, min?=inf?=0.",
            "Let??R be nonempty. If max?exists, then sup?=max?.",
        ]
        self.assertFalse(should_use_local_extraction(samples))

    def test_no_extractable_text_does_not_use_local_extraction(self):
        self.assertFalse(should_use_local_extraction(["", ""]))

    def test_occasional_real_question_mark_does_not_trigger_false_positive(self):
        samples = [
            "Is this proof correct? Let's check each step carefully before moving on to "
            "the next part of the argument, which follows from the previous lemma.",
        ]
        self.assertTrue(should_use_local_extraction(samples))

    def test_garbling_confined_to_one_page_among_many_clean_ones_is_still_caught(self):
        # Regression: an earlier sampled version of this check (5 evenly-
        # spaced pages out of a full document) missed real garbling on
        # real documents purely by landing on unrepresentative pages --
        # this fixture models exactly that shape (mostly clean, garbling
        # concentrated on pages a sparse sample could plausibly skip) to
        # confirm the caller-must-pass-every-page contract actually
        # matters, not just that the ratio math itself is correct.
        pages = ["Clean prose page."] * 20 + [
            "Returning to ?=[0,1), we have inf?=0,sup?=1. Since0??, min?=inf?=0. "
            "Let??R be nonempty. If max?exists, then sup?=max?."
        ] * 5
        self.assertFalse(should_use_local_extraction(pages))


if __name__ == "__main__":
    unittest.main()
