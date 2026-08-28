import os
import tempfile
import unittest
from unittest.mock import patch

import json

from describe_images import (
    build_description_prompt,
    build_rag_markdown,
    extract_paragraph_context,
    filter_front_matter,
    find_image_references,
    link_rag_md,
    load_front_matter_end,
    nearest_preceding_heading,
    parse_description_response,
)


class TestFindImageReferences(unittest.TestCase):
    def test_finds_single_image_reference(self):
        text = "Some text.\n\n![](pg_124__page_0_Picture_0.jpeg)\n\nMore text."
        refs = find_image_references(text)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].filename, "pg_124__page_0_Picture_0.jpeg")
        self.assertEqual(refs[0].physical_page, 124)

    def test_finds_multiple_in_document_order(self):
        text = (
            "![](pg_5__page_0_Figure_1.jpeg)\n\n"
            "Text between.\n\n"
            "![](pg_42__page_0_Diagram_3.jpeg)"
        )
        refs = find_image_references(text)
        self.assertEqual([r.physical_page for r in refs], [5, 42])
        self.assertLess(refs[0].start, refs[1].start)

    def test_ignores_non_image_markdown_links(self):
        # A real pattern from the pipeline's own output: internal chapter
        # links use "[text](#page-N-M)" -- no leading "!", must not match.
        text = '# *[Vector Spaces](#page-14-0)*\n\nNo images here.'
        refs = find_image_references(text)
        self.assertEqual(refs, [])

    def test_skips_image_link_without_pg_prefix(self):
        # Defensive: output converted before the link-remap fix shipped
        # (or any other unprefixed image) shouldn't crash the parser --
        # it just can't be page-attributed, so it's skipped.
        text = "![](_page_1_Picture_5.jpeg)"
        refs = find_image_references(text)
        self.assertEqual(refs, [])


class TestFilterFrontMatter(unittest.TestCase):
    def test_excludes_pages_at_or_before_front_matter_end(self):
        text = (
            "![](pg_20__page_0_Picture_0.jpeg)\n\n"
            "![](pg_21__page_0_Picture_1.jpeg)"
        )
        refs = find_image_references(text)
        kept = filter_front_matter(refs, front_matter_end=20)
        self.assertEqual([r.physical_page for r in kept], [21])

    def test_no_front_matter_end_keeps_everything(self):
        text = "![](pg_1__page_0_Picture_0.jpeg)"
        refs = find_image_references(text)
        kept = filter_front_matter(refs, front_matter_end=None)
        self.assertEqual(len(kept), 1)


class TestExtractParagraphContext(unittest.TestCase):
    def test_grabs_paragraph_before_and_after(self):
        text = (
            "This is the paragraph before the figure.\n\n"
            "![](pg_10__page_0_Figure_0.jpeg)\n\n"
            "This is the paragraph after the figure."
        )
        refs = find_image_references(text)
        before, after = extract_paragraph_context(text, refs[0])
        self.assertIn("paragraph before", before)
        self.assertIn("paragraph after", after)

    def test_skips_page_and_folio_tags_when_gathering_context(self):
        text = (
            "Real prose paragraph.\n\n"
            "<!-- page 10 --><!-- folio 3 -->\n\n"
            "![](pg_10__page_0_Figure_0.jpeg)\n\n"
            "<!-- page 11 -->\n\n"
            "Following prose paragraph."
        )
        refs = find_image_references(text)
        before, after = extract_paragraph_context(text, refs[0])
        self.assertIn("Real prose paragraph.", before)
        self.assertNotIn("<!--", before)
        self.assertIn("Following prose paragraph.", after)
        self.assertNotIn("<!--", after)

    def test_image_at_start_of_document_has_no_before_context(self):
        text = "![](pg_1__page_0_Figure_0.jpeg)\n\nAfter text."
        refs = find_image_references(text)
        before, after = extract_paragraph_context(text, refs[0])
        self.assertEqual(before, "")
        self.assertIn("After text.", after)

    def test_image_at_end_of_document_has_no_after_context(self):
        text = "Before text.\n\n![](pg_1__page_0_Figure_0.jpeg)"
        refs = find_image_references(text)
        before, after = extract_paragraph_context(text, refs[0])
        self.assertIn("Before text.", before)
        self.assertEqual(after, "")


class TestNearestPrecedingHeading(unittest.TestCase):
    def test_finds_nearest_heading_above(self):
        text = (
            "# Chapter 3: Proofs\n\n"
            "Some intro text.\n\n"
            "## Direct Proofs\n\n"
            "More text.\n\n"
            "![](pg_10__page_0_Figure_0.jpeg)"
        )
        refs = find_image_references(text)
        heading = nearest_preceding_heading(text, refs[0].start)
        self.assertEqual(heading, "Direct Proofs")

    def test_returns_none_when_no_heading_present(self):
        text = "Just prose.\n\n![](pg_1__page_0_Figure_0.jpeg)"
        refs = find_image_references(text)
        heading = nearest_preceding_heading(text, refs[0].start)
        self.assertIsNone(heading)


class TestBuildDescriptionPrompt(unittest.TestCase):
    def test_includes_context_and_heading(self):
        prompt = build_description_prompt(
            context_before="Before paragraph.",
            context_after="After paragraph.",
            heading="Direct Proofs",
        )
        self.assertIn("Before paragraph.", prompt)
        self.assertIn("After paragraph.", prompt)
        self.assertIn("Direct Proofs", prompt)
        self.assertIn("skip", prompt)
        self.assertIn("description", prompt)

    def test_handles_missing_heading_and_context(self):
        prompt = build_description_prompt(context_before="", context_after="", heading=None)
        self.assertIsInstance(prompt, str)
        self.assertIn("skip", prompt)


class TestParseDescriptionResponse(unittest.TestCase):
    def test_parses_valid_describe_response(self):
        result = parse_description_response('{"skip": false, "description": "A bar chart."}')
        self.assertFalse(result["skip"])
        self.assertEqual(result["description"], "A bar chart.")

    def test_parses_valid_skip_response(self):
        result = parse_description_response('{"skip": true, "description": ""}')
        self.assertTrue(result["skip"])

    def test_malformed_json_falls_back_to_skip(self):
        result = parse_description_response("not valid json at all")
        self.assertTrue(result["skip"])
        self.assertEqual(result["description"], "")

    def test_missing_keys_fall_back_to_skip(self):
        result = parse_description_response('{"unexpected": "shape"}')
        self.assertTrue(result["skip"])


class TestLoadFrontMatterEnd(unittest.TestCase):
    def test_reads_front_matter_end_from_first_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run_config.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"boundaries": [[0, 20], [20, 55]], "folio_offset": 3, "folio_start_page": 20}, f)
            self.assertEqual(load_front_matter_end(tmp), 20)

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_front_matter_end(tmp))

    def test_malformed_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run_config.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid")
            self.assertIsNone(load_front_matter_end(tmp))

    def test_missing_boundaries_key_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run_config.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"folio_offset": None}, f)
            self.assertIsNone(load_front_matter_end(tmp))


class TestBuildRagMarkdown(unittest.TestCase):
    def test_inserts_description_beneath_described_image(self):
        text = "Intro.\n\n![](pg_10__page_0_Figure_0.jpeg)\n\nOutro."
        results = {"pg_10__page_0_Figure_0.jpeg": {"skip": False, "description": "A bar chart."}}
        rag_text = build_rag_markdown(text, results)
        self.assertIn("![](pg_10__page_0_Figure_0.jpeg)", rag_text)
        self.assertIn("A bar chart.", rag_text)
        fig_pos = rag_text.index("![](pg_10__page_0_Figure_0.jpeg)")
        desc_pos = rag_text.index("A bar chart.")
        self.assertLess(fig_pos, desc_pos)

    def test_leaves_skipped_image_untouched(self):
        text = "Intro.\n\n![](pg_10__page_0_Picture_0.jpeg)\n\nOutro."
        results = {"pg_10__page_0_Picture_0.jpeg": {"skip": True, "description": ""}}
        rag_text = build_rag_markdown(text, results)
        self.assertEqual(rag_text, text)

    def test_image_missing_from_results_is_left_untouched(self):
        text = "Intro.\n\n![](pg_10__page_0_Picture_0.jpeg)\n\nOutro."
        rag_text = build_rag_markdown(text, {})
        self.assertEqual(rag_text, text)

    def test_original_text_outside_images_is_never_altered(self):
        text = (
            "# Chapter 1\n\nIntro paragraph.\n\n"
            "![](pg_5__page_0_Figure_0.jpeg)\n\n"
            "Middle paragraph.\n\n"
            "![](pg_9__page_0_Figure_1.jpeg)\n\n"
            "Outro paragraph."
        )
        results = {
            "pg_5__page_0_Figure_0.jpeg": {"skip": False, "description": "First figure."},
            "pg_9__page_0_Figure_1.jpeg": {"skip": False, "description": "Second figure."},
        }
        rag_text = build_rag_markdown(text, results)
        for chunk in ["# Chapter 1", "Intro paragraph.", "Middle paragraph.", "Outro paragraph."]:
            self.assertIn(chunk, rag_text)
        self.assertIn("First figure.", rag_text)
        self.assertIn("Second figure.", rag_text)
        self.assertLess(rag_text.index("First figure."), rag_text.index("Middle paragraph."))
        self.assertLess(rag_text.index("Middle paragraph."), rag_text.index("Second figure."))


class TestLinkRagMd(unittest.TestCase):
    def _book_dir_with_metadata(self, tmp, metadata):
        book_dir = os.path.join(tmp, "processed_outputs", "SomeBook_2025")
        os.makedirs(book_dir)
        with open(os.path.join(book_dir, "SomeBook_2025_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        return book_dir

    def test_writes_rag_md_path_into_metadata_and_the_matching_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {"source_pdf_file_id": "fid1"})
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")

            with patch("describe_images.set_rag_md_path", return_value=True) as mock_set:
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)

            self.assertTrue(found)
            mock_set.assert_called_once()
            self.assertEqual(mock_set.call_args[0][0], tmp)
            self.assertEqual(mock_set.call_args[0][1], "fid1")
            self.assertEqual(mock_set.call_args[0][2], "processed_outputs/SomeBook_2025/SomeBook_2025.rag.md")

            with open(os.path.join(book_dir, "SomeBook_2025_metadata.json"), encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["rag_md_path"], "processed_outputs/SomeBook_2025/SomeBook_2025.rag.md")
            self.assertEqual(metadata["source_pdf_file_id"], "fid1")  # untouched

    def test_returns_false_when_metadata_has_no_source_pdf_file_id_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {})  # predates this field
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            with patch("describe_images.set_rag_md_path") as mock_set:
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)
            mock_set.assert_not_called()

    def test_returns_false_but_still_writes_metadata_when_no_card_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {"source_pdf_file_id": "fid1"})
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            with patch("describe_images.set_rag_md_path", return_value=False):
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)
            with open(os.path.join(book_dir, "SomeBook_2025_metadata.json"), encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(metadata["rag_md_path"], "processed_outputs/SomeBook_2025/SomeBook_2025.rag.md")

    def test_missing_metadata_file_returns_false_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = os.path.join(tmp, "processed_outputs", "SomeBook_2025")
            os.makedirs(book_dir)  # no _metadata.json written at all
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)


if __name__ == "__main__":
    unittest.main()
