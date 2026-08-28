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
    reconstruct_line_with_scripts,
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

    def test_window_excludes_pages_older_than_the_window(self):
        cache = {"1": "Page one.", "2": "Page two.", "3": "Page three.", "4": "Page four."}
        context = build_accumulated_context(cache, up_to_page=5, window=2)
        self.assertNotIn("Page one.", context)
        self.assertNotIn("Page two.", context)
        self.assertIn("Page three.", context)
        self.assertIn("Page four.", context)

    def test_window_larger_than_available_history_includes_everything(self):
        cache = {"1": "Page one.", "2": "Page two."}
        context = build_accumulated_context(cache, up_to_page=3, window=10)
        self.assertIn("Page one.", context)
        self.assertIn("Page two.", context)

    def test_window_none_still_includes_full_history(self):
        cache = {"1": "Page one.", "5": "Page five."}
        context = build_accumulated_context(cache, up_to_page=6, window=None)
        self.assertIn("Page one.", context)
        self.assertIn("Page five.", context)


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

    def test_replaces_unicode_replacement_character_with_em_dash(self):
        # Real, repeated pattern from live responses (LN_Analysis.pdf,
        # LN_Optimization.pdf): the model's own em-dash comes back as the
        # Unicode replacement character (U+FFFD) instead, consistently
        # where "Title — Subtitle" or "clause — continuation" belongs.
        # U+FFFD is never a legitimate intentional character -- it only
        # ever means "a byte sequence couldn't be decoded" -- so this
        # substitution is safe regardless of exact root cause.
        response = "Theorem 6.5 � Equality of Mixed Second Partial Derivatives"
        self.assertEqual(
            parse_transcription_response(response),
            "Theorem 6.5 — Equality of Mixed Second Partial Derivatives",
        )

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

    def test_lost_exponent_on_isolated_variable_is_defective(self):
        # Real pattern from Practice Sheet.pdf page 34 -- plain-text
        # extraction (pypdf or PyMuPDF, either one) has no way to represent
        # a superscript at all, so "D^5" comes out as bare "D5". Unlike the
        # word-spacing bug, no extraction library can fix this -- it's
        # information genuinely absent from the text stream.
        text = "(d) Show that I + D is invertible. (c) Explain why D5 = 0."
        self.assertTrue(page_looks_defective(text))

    def test_lost_exponent_on_set_notation_is_defective(self):
        # Real pattern from LN_Linear Algebra.pdf -- "R^2" (Euclidean
        # plane) losing its superscript reads as bare "R2".
        text = "Let v1, v2 be vectors that span R2."
        self.assertTrue(page_looks_defective(text))

    def test_embedded_hex_hash_is_not_flagged_as_lost_exponent(self):
        # Regression: real false positive found against Real Analysis
        # Problem Set_Solutions.pdf -- an embedded comment-link's hex hash
        # ID (e.g. "...app/06b7ab97dac5cbbb>") alternates letters and
        # digits constantly and would trip a naive letter-immediately-
        # followed-by-digit check on nearly every page. A real lost
        # exponent is always a short, boundary-delimited token ("D5", "R2")
        # standing on its own between spaces/punctuation, not embedded
        # inside a much longer unbroken alphanumeric run.
        text = "See the comment thread at https://mail.google.com/app/06b7ab97dac5cbbb> for context."
        self.assertFalse(page_looks_defective(text))

    def test_lost_exponent_inside_an_already_reconstructed_script_group_is_not_defective(self):
        # Real case from Analysis_Exercises.pdf page 1 (post dict-mode
        # fix): reconstruct_line_with_scripts() correctly wraps a compound
        # subscript as one group, but doesn't recursively re-nest a
        # sub-subscript within it -- "B_{infinity,r1}(x)" instead of the
        # fully-nested "B_{infinity,r_1}(x)". The bare "r1" inside that
        # group is not a still-lost exponent (the content IS already
        # inside a script group); re-flagging it would be a false
        # positive that inflates the defect ratio for no real problem.
        text = "B_{∞,r1}(x) ⊆ B_{2,r}(x)."
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


def _span(text, size, origin_y, origin_x=0.0, bbox=None):
    """Builds a PyMuPDF-shaped span dict with just the fields reconstruct_line_with_scripts reads."""
    span = {"text": text, "size": size, "origin": (origin_x, origin_y)}
    if bbox is not None:
        span["bbox"] = bbox
    return span


class TestReconstructLineWithScripts(unittest.TestCase):
    def test_plain_line_is_unchanged(self):
        spans = [_span("This is a normal sentence.", 10.91, 100.0)]
        self.assertEqual(reconstruct_line_with_scripts(spans), "This is a normal sentence.")

    def test_empty_line_returns_empty_string(self):
        self.assertEqual(reconstruct_line_with_scripts([]), "")

    def test_real_superscript_case_is_wrapped(self):
        # Real span data from Practice Sheet.pdf page 2: "Explain why D^5 = 0."
        # -- the "5" is smaller (7.97 vs 10.91) and raised (origin_y 151.18
        # vs the surrounding baseline 155.14).
        spans = [
            _span("why ", 10.91, 155.14),
            _span("D", 10.91, 155.14),
            _span("5", 7.97, 151.18),
            _span(" = 0.", 10.91, 155.14),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "why D^{5} = 0.")

    def test_real_subscript_case_is_wrapped(self):
        # Real span data from Practice Sheet.pdf page 2: "Let V = P_4(R)"
        # -- the "4" is smaller (7.97 vs 10.91) and lowered (origin_y 94.83
        # vs the surrounding baseline 93.20).
        spans = [
            _span("Let V = ", 10.91, 93.20),
            _span("P", 10.91, 93.20),
            _span("4", 7.97, 94.83),
            _span("(R)", 10.91, 93.20),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "Let V = P_{4}(R)")

    def test_multi_character_exponent_is_grouped_into_one_run(self):
        spans = [
            _span("x", 10.91, 100.0),
            _span("1", 7.97, 96.0),
            _span("2", 7.97, 96.0),
            _span(" is large", 10.91, 100.0),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "x^{12} is large")

    def test_smaller_symbol_at_same_baseline_is_not_wrapped(self):
        # Real case from LN_Linear Algebra.pdf: a symbol font renders "K"
        # larger (11.49) than the surrounding body text (10.91) with no
        # vertical offset at all -- confirms size alone isn't sufficient;
        # this test covers the mirror case (smaller, but same baseline).
        spans = [
            _span("multiplication with multiplication in", 10.91, 100.0),
            _span(" small", 8.0, 100.0),
            _span(" text", 10.91, 100.0),
        ]
        self.assertEqual(
            reconstruct_line_with_scripts(spans),
            "multiplication with multiplication in small text",
        )

    def test_larger_symbol_at_same_baseline_is_not_wrapped(self):
        # Real case from LN_Linear Algebra.pdf page 5: a blackboard-bold
        # "K" rendered at 11.49pt inline with 10.91pt body text, same
        # origin_y -- must not be treated as a script just for being a
        # different size.
        spans = [
            _span("multiplication in", 10.91, 100.0),
            _span(" K", 11.49, 100.0),
            _span(":", 10.91, 100.0),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "multiplication in K:")

    def test_non_adjacent_subscripts_are_wrapped_separately(self):
        # Real pattern from LN_Linear Algebra.pdf page 7: "x_1, . . . , x_n"
        # -- two separate single-span subscripts, not one combined run.
        spans = [
            _span("x", 10.91, 100.0),
            _span("1", 7.97, 101.6),
            _span(", . . . , x", 10.91, 100.0),
            _span("n", 7.97, 101.6),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "x_{1}, . . . , x_{n}")

    def test_single_span_line_is_unchanged(self):
        self.assertEqual(reconstruct_line_with_scripts([_span("Solo line.", 10.91, 42.0)]), "Solo line.")

    def test_position_only_gap_gets_a_synthetic_space(self):
        # Real span data from LN_Analysis.pdf page 59: "f" ends at
        # bbox x=206.42, "uniformly." starts at x=211.39 -- a 4.97pt gap
        # (~0.46x the 10.91pt body size) with NO space character in the
        # PDF's own content stream at all, just a positional offset (a
        # common LaTeX/PDF pattern: justified text using kerning-level
        # positioning instead of literal space glyphs). Plain span-text
        # concatenation silently drops this, producing "funiformly.".
        spans = [
            _span("f", 10.91, 498.78, bbox=(203.39, 498.78, 206.42, 509.69)),
            _span("uniformly.", 10.91, 499.57, bbox=(211.39, 499.57, 261.68, 510.58)),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "f uniformly.")

    def test_tight_attachment_gap_gets_no_synthetic_space(self):
        # Real span data from the same page: "f" ends at x=178.52, its
        # own subscript "k" starts at x=178.92 -- a 0.40pt gap (~0.04x
        # the body size), two orders of magnitude smaller than the real
        # word-boundary gap above. Must not get a space inserted --
        # "f_{k}" is correct, "f _{k}" is not.
        spans = [
            _span("f", 10.91, 401.53, bbox=(175.28, 401.53, 178.52, 412.44)),
            _span("k", 7.97, 405.60, bbox=(178.92, 405.60, 182.46, 413.57)),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "f_{k}")

    def test_explicit_space_span_is_not_doubled(self):
        # Real span data: "that" ends at x=170.58, an explicit space span
        # (text=" ") occupies 170.58 to 175.49, then "f" starts at
        # exactly 175.49 -- the gap check on either side of the real
        # space span is ~0, so no synthetic space should be added on top
        # of the real one already there.
        spans = [
            _span("that", 10.91, 499.57, bbox=(85.89, 499.57, 170.58, 510.58)),
            _span(" ", 10.91, 498.78, bbox=(170.58, 498.78, 175.49, 509.69)),
            _span("f", 10.91, 498.78, bbox=(175.49, 498.78, 178.52, 509.69)),
        ]
        self.assertEqual(reconstruct_line_with_scripts(spans), "that f")

    def test_missing_bbox_falls_back_to_no_gap_check(self):
        # Spans without a "bbox" key (e.g. synthetic/test spans built
        # before this feature existed) must not crash -- gap-based space
        # insertion is simply skipped for that pair, same as before.
        spans = [_span("Let V", 10.91, 100.0), _span(" be", 10.91, 100.0)]
        self.assertEqual(reconstruct_line_with_scripts(spans), "Let V be")


if __name__ == "__main__":
    unittest.main()
