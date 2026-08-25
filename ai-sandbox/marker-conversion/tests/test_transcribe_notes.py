import os
import tempfile
import unittest

from transcribe_notes import (
    build_accumulated_context,
    build_batch_transcription_prompt,
    build_final_markdown,
    build_frontmatter,
    build_transcription_prompt,
    derive_folder_category,
    discover_pdf_files,
    get_bookend_context,
    group_into_runs,
    has_reliable_pagination,
    page_looks_defective,
    parse_batch_transcription_response,
    parse_transcription_response,
    split_run_into_batches,
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
        self.assertIn("delimiter", high_conf)  # explains the real corruption failure mode

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


class TestPageLooksDefective(unittest.TestCase):
    def test_clean_prose_is_not_defective(self):
        text = "This is a normal paragraph of clean prose with no garbling at all."
        self.assertFalse(page_looks_defective(text))

    def test_real_delimiter_glyph_corruption_is_defective(self):
        # Real pattern from LN_Linear Algebra.pdf page 170 -- a big
        # matrix bracket's stacked glyph pieces came through as garbage
        # characters with no whitespace between them.
        text = "adj(𝐴)=\n'›››››\n«\n𝐶11 𝐶12 ···𝐶 1𝑛\n\"ﬁﬁﬁﬁﬁ\n‹\n."
        self.assertTrue(page_looks_defective(text))

    def test_real_word_spacing_collapse_is_defective(self):
        # Real pattern from LN_Linear Algebra.pdf page 170.
        text = "This leadstoanexplicitformulafortheinverseofanonsingularmatrixand consequence."
        self.assertTrue(page_looks_defective(text))

    def test_blank_page_is_not_defective(self):
        self.assertFalse(page_looks_defective(""))

    def test_ordinary_long_technical_word_is_not_defective(self):
        text = "This is a counterexample to the proposition, not a corrupted transcription."
        self.assertFalse(page_looks_defective(text))

    def test_real_confirmed_clean_math_content_is_not_defective(self):
        # Real, directly-verified-correct extraction from LN_Analysis.pdf
        # pages 10 and 100 -- must never be flagged, or the whole point
        # of local extraction is defeated.
        text = (
            "Returning to 𝐴=[0,1), we have inf𝐴=0,sup𝐴=1. Since0∈𝐴, min𝐴=inf𝐴=0. "
            "But since1∉𝐴, there is no maximum. Proposition 1.7 — Maximum and Supremum. "
            "Let𝐴⊆Rbe nonempty. 𝑥≤𝑎∗∀𝑥∈𝐴, 𝑎∗ is an upper bound of𝐴. "
            "∇𝑓(𝛾(𝑡0))·𝛾′(𝑡0)=0. ∥𝑥−𝑎∥≤∥ℎ∥. 𝜕𝑗𝑓(𝜉𝑗)−𝜕𝑗𝑓(𝑎)."
        )
        self.assertFalse(page_looks_defective(text))

    def test_dense_unspaced_equation_is_not_a_collapsed_prose_run(self):
        # Regression: real, confirmed-correct content from LN_Analysis.pdf
        # page 100. A dense equation with no internal whitespace looks
        # superficially like collapsed prose (one long "word"), but it's
        # legitimate -- normal math notation just doesn't have spaces
        # between operators/parens/variables. Real collapsed prose is
        # pure ASCII letters; this is not.
        text = "Then 𝑓(𝑎+ℎ)=𝑓(𝑎)+∇𝑓(𝑎)·ℎ+𝑜(∥ℎ∥) gives the first-order expansion."
        self.assertFalse(page_looks_defective(text))

    def test_repeated_page_number_digits_are_not_defective(self):
        # Regression: real false positive against LN_Analysis.pdf's own
        # table of contents -- a page number like "111" isn't corruption.
        text = "6.3 The Hessian and Symmetry of Second Derivatives . . . . . . . . . . . 111"
        self.assertFalse(page_looks_defective(text))

    def test_repeated_roman_numeral_letters_are_not_defective(self):
        # Regression: real false positive against LN_Analysis.pdf's
        # references section -- "Mathematical Analysis III" isn't corruption.
        text = "V. A. Zorich, Mathematical Analysis III, 2nd ed., Universitext, 2015."
        self.assertFalse(page_looks_defective(text))


class TestGroupIntoRuns(unittest.TestCase):
    def test_empty_list_returns_empty(self):
        self.assertEqual(group_into_runs([]), [])

    def test_single_page_is_its_own_run(self):
        self.assertEqual(group_into_runs([5]), [[5]])

    def test_consecutive_pages_form_one_run(self):
        self.assertEqual(group_into_runs([3, 4, 5]), [[3, 4, 5]])

    def test_separate_runs_stay_separate(self):
        self.assertEqual(group_into_runs([3, 4, 10, 20, 21, 22]), [[3, 4], [10], [20, 21, 22]])


class TestSplitRunIntoBatches(unittest.TestCase):
    def test_run_shorter_than_cap_is_one_batch(self):
        self.assertEqual(split_run_into_batches([1, 2, 3], max_batch_size=12), [[1, 2, 3]])

    def test_run_longer_than_cap_splits_into_multiple_batches(self):
        run = list(range(1, 26))  # 25 pages
        batches = split_run_into_batches(run, max_batch_size=12)
        self.assertEqual(len(batches), 3)
        self.assertEqual([len(b) for b in batches], [12, 12, 1])
        self.assertEqual([p for b in batches for p in b], run)  # nothing lost or reordered

    def test_empty_run_returns_empty_list(self):
        self.assertEqual(split_run_into_batches([], max_batch_size=12), [])


class TestGetBookendContext(unittest.TestCase):
    def test_run_in_middle_gets_both_neighbors(self):
        # 1-indexed pages 1..5; run is page 3 (index 2).
        all_texts = ["p1", "p2", "p3-defective", "p4", "p5"]
        before, after = get_bookend_context(all_texts, run=[3])
        self.assertEqual(before, "p2")
        self.assertEqual(after, "p4")

    def test_run_at_document_start_has_no_before_context(self):
        all_texts = ["p1-defective", "p2", "p3"]
        before, after = get_bookend_context(all_texts, run=[1])
        self.assertEqual(before, "")
        self.assertEqual(after, "p2")

    def test_run_at_document_end_has_no_after_context(self):
        all_texts = ["p1", "p2", "p3-defective"]
        before, after = get_bookend_context(all_texts, run=[3])
        self.assertEqual(before, "p2")
        self.assertEqual(after, "")

    def test_multi_page_run_uses_true_outer_neighbors(self):
        all_texts = ["p1", "p2", "p3-defective", "p4-defective", "p5-defective", "p6"]
        before, after = get_bookend_context(all_texts, run=[3, 4, 5])
        self.assertEqual(before, "p2")
        self.assertEqual(after, "p6")


class TestBuildBatchTranscriptionPrompt(unittest.TestCase):
    def test_includes_page_numbers_and_bookend_context(self):
        prompt = build_batch_transcription_prompt(
            page_numbers=[45, 46, 47],
            before_context="Prior clean page.",
            after_context="Following clean page.",
            total_pages=294,
        )
        self.assertIn("45", prompt)
        self.assertIn("46", prompt)
        self.assertIn("47", prompt)
        self.assertIn("294", prompt)
        self.assertIn("Prior clean page.", prompt)
        self.assertIn("Following clean page.", prompt)
        self.assertIn("PAGE", prompt)

    def test_handles_missing_bookend_context(self):
        prompt = build_batch_transcription_prompt(
            page_numbers=[1, 2], before_context="", after_context="", total_pages=10,
        )
        self.assertIsInstance(prompt, str)
        self.assertIn("PAGE", prompt)


class TestParseBatchTranscriptionResponse(unittest.TestCase):
    def test_parses_well_formed_multi_page_response(self):
        response = (
            "--- PAGE 45 ---\n"
            "Content for page 45.\n\n"
            "--- PAGE 46 ---\n"
            "Content for page 46.\n\n"
            "--- PAGE 47 ---\n"
            "Content for page 47.\n"
        )
        result = parse_batch_transcription_response(response, expected_page_numbers=[45, 46, 47])
        self.assertEqual(result[45], "Content for page 45.")
        self.assertEqual(result[46], "Content for page 46.")
        self.assertEqual(result[47], "Content for page 47.")

    def test_missing_page_is_simply_absent_not_an_error(self):
        # Forgiving by design -- caller detects the gap and decides what to do.
        response = "--- PAGE 45 ---\nContent for page 45.\n"
        result = parse_batch_transcription_response(response, expected_page_numbers=[45, 46])
        self.assertEqual(result, {45: "Content for page 45."})

    def test_unexpected_page_number_is_ignored(self):
        response = "--- PAGE 99 ---\nHallucinated page.\n"
        result = parse_batch_transcription_response(response, expected_page_numbers=[45])
        self.assertEqual(result, {})

    def test_strips_code_fence_within_a_page_section(self):
        response = "--- PAGE 1 ---\n```markdown\nFenced content.\n```\n"
        result = parse_batch_transcription_response(response, expected_page_numbers=[1])
        self.assertEqual(result[1], "Fenced content.")

    def test_empty_response_returns_empty_dict(self):
        self.assertEqual(parse_batch_transcription_response("", expected_page_numbers=[1, 2]), {})


class TestDeriveFolderCategory(unittest.TestCase):
    def test_returns_immediate_parent_folder_name(self):
        path = os.path.join("academic-hub", "academic_notes", "math-camp", "ta_notes", "LN_Analysis.pdf")
        self.assertEqual(derive_folder_category(path), "ta_notes")


class TestBuildFrontmatter(unittest.TestCase):
    def test_wraps_in_yaml_delimiters(self):
        result = build_frontmatter({"total_pages": 10})
        self.assertTrue(result.startswith("---\n"))
        self.assertIn("\n---\n", result)

    def test_renders_string_int_bool_and_list_values(self):
        result = build_frontmatter({
            "source_pdf": "LN_Analysis.pdf",
            "total_pages": 155,
            "routing": "hybrid",
            "pages_repaired": 3,
            "repaired_pages": [12, 45, 46],
            "tags": [],
        })
        self.assertIn("source_pdf: LN_Analysis.pdf", result)
        self.assertIn("total_pages: 155", result)
        self.assertIn("repaired_pages: [12, 45, 46]", result)
        self.assertIn("tags: []", result)

    def test_quotes_string_values_containing_yaml_special_characters(self):
        result = build_frontmatter({"source_pdf": "Notes: Part I (1).pdf"})
        self.assertIn('source_pdf: "Notes: Part I (1).pdf"', result)

    def test_output_is_valid_yaml_when_a_yaml_parser_is_available(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("pyyaml not installed locally -- structural tests above already cover this")
        result = build_frontmatter({
            "source_pdf": "Weird: Name.pdf",
            "total_pages": 42,
            "repaired_pages": [1, 2, 3],
            "tags": [],
        })
        inner = result.strip().strip("-").strip()
        parsed = yaml.safe_load(inner)
        self.assertEqual(parsed["source_pdf"], "Weird: Name.pdf")
        self.assertEqual(parsed["total_pages"], 42)
        self.assertEqual(parsed["repaired_pages"], [1, 2, 3])
        self.assertEqual(parsed["tags"], [])


if __name__ == "__main__":
    unittest.main()
