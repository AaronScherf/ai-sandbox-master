import os
import tempfile
import unittest
from unittest.mock import patch

import json

from textbook.describe_images import (
    build_description_prompt,
    build_rag_markdown,
    extract_paragraph_context,
    filter_front_matter,
    find_image_references,
    link_rag_md,
    load_front_matter_end,
    nearest_preceding_heading,
    parse_description_response,
    process_book,
    reconcile_book_naming,
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

            with patch("textbook.describe_images.set_rag_md_path", return_value=True) as mock_set:
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
            with patch("textbook.describe_images.set_rag_md_path") as mock_set:
                found = link_rag_md(book_dir, "SomeBook_2025", rag_path, tmp)
            self.assertFalse(found)
            mock_set.assert_not_called()

    def test_returns_false_but_still_writes_metadata_when_no_card_exists_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._book_dir_with_metadata(tmp, {"source_pdf_file_id": "fid1"})
            rag_path = os.path.join(book_dir, "SomeBook_2025.rag.md")
            with patch("textbook.describe_images.set_rag_md_path", return_value=False):
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


class TestReconcileBookNaming(unittest.TestCase):
    # A Hansen econometrics textbook, converted before
    # extract_bibliographic_info_from_filename() existed, came out named
    # "UnknownAuthor_Econometrics_0000" even though its source filename
    # ("Hansen_Econometrics_2022.pdf") had the author and year in it. This
    # naming-reconciliation pass re-derives the ideal name from what's
    # already recorded in _metadata.json (no re-conversion, no LLM call) and
    # fixes already-converted books on disk.

    def _make_book(self, tmp, folder_name, metadata, with_rag_md=False, with_card=False):
        processed_outputs = os.path.join(tmp, "processed_outputs")
        book_dir = os.path.join(processed_outputs, folder_name)
        os.makedirs(book_dir)
        with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
            f.write("# Book content\n")
        with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        if with_rag_md:
            with open(os.path.join(book_dir, f"{folder_name}.rag.md"), "w", encoding="utf-8") as f:
                f.write("# Book content\n")
        if with_card:
            from indexer.index_card import save_shard
            save_shard(tmp, "econ-101", [{
                "file_id": metadata["source_pdf_file_id"],
                "path": f"processed_outputs/{folder_name}/{folder_name}.md",
                "course": "econ-101",
                "title": "",
            }])
        return book_dir

    def test_prefers_source_pdf_filename_over_corrupted_source_pdf_path(self):
        # Real, confirmed incident: for a book converted from a gs:// input,
        # source_pdf_path actually records the local *temp download's* path
        # (e.g. ".../temp_gcs_input_Econometrics_Bruce_E_Hansen_1962_....pdf"),
        # not the real source filename -- reading that here extracted
        # "temp" as the book's "author". source_pdf_filename (added
        # alongside it in convert_textbook.py specifically for this) must
        # take priority whenever both are present.
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "Econometrics_ECONOMETRICS_1962", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "", "author": "", "year": ""},
                "source_pdf_path": "temp_gcs_input_Econometrics_Bruce_E_Hansen_1962_Princeton_New_Jersey_2022.pdf",
                "source_pdf_filename": "Econometrics -- Bruce E Hansen, 1962- -- Princeton, New Jersey, 2022.pdf",
                "source_pdf_file_id": "fid1",
            })

            new_dir = reconcile_book_naming(book_dir, tmp)

            self.assertEqual(os.path.basename(new_dir), "Hansen_Econometrics_2022")

    def test_falls_back_to_source_pdf_path_when_source_pdf_filename_missing(self):
        # A book converted before source_pdf_filename existed -- same
        # (imperfect) behavior as before this fix, not a regression.
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "UnknownAuthor_Contents_0000", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "Contents", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hayashi_Econometrics_2000.pdf",
                "source_pdf_file_id": "fid1",
            })

            new_dir = reconcile_book_naming(book_dir, tmp)

            self.assertEqual(os.path.basename(new_dir), "Hayashi_Contents_2000")

    def test_renames_folder_and_files_when_filename_recovers_missing_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "UnknownAuthor_Econometrics_0000", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "Econometrics", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hansen_Econometrics_2022.pdf",
                "source_pdf_file_id": "fid1",
            }, with_card=True)

            new_dir = reconcile_book_naming(book_dir, tmp)

            self.assertEqual(os.path.basename(new_dir), "Hansen_Econometrics_2022")
            self.assertFalse(os.path.exists(book_dir))
            self.assertTrue(os.path.exists(os.path.join(new_dir, "Hansen_Econometrics_2022.md")))
            self.assertTrue(os.path.exists(os.path.join(new_dir, "Hansen_Econometrics_2022_metadata.json")))

            from indexer.index_card import load_shard
            card = load_shard(tmp, "econ-101")[0]
            self.assertEqual(card["path"], "processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.md")

    def test_also_renames_rag_md_and_updates_its_recorded_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "UnknownAuthor_Econometrics_0000", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "Econometrics", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hansen_Econometrics_2022.pdf",
                "source_pdf_file_id": "fid1",
                "rag_md_path": "processed_outputs/UnknownAuthor_Econometrics_0000/UnknownAuthor_Econometrics_0000.rag.md",
            }, with_rag_md=True, with_card=True)

            new_dir = reconcile_book_naming(book_dir, tmp)

            self.assertTrue(os.path.exists(os.path.join(new_dir, "Hansen_Econometrics_2022.rag.md")))
            with open(os.path.join(new_dir, "Hansen_Econometrics_2022_metadata.json"), encoding="utf-8") as f:
                metadata = json.load(f)
            self.assertEqual(
                metadata["rag_md_path"],
                "processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.rag.md",
            )

            from indexer.index_card import load_shard
            card = load_shard(tmp, "econ-101")[0]
            self.assertEqual(
                card.get("rag_md_path"),
                "processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.rag.md",
            )

    def test_already_ideal_name_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "Hansen_Econometrics_2022", {
                "source_pdf_document_info": {"title": "Econometrics", "author": "Hansen", "year": "2022"},
                "markdown_parsed_info": {"title": "", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hansen_Econometrics_2022.pdf",
                "source_pdf_file_id": "fid1",
            })

            new_dir = reconcile_book_naming(book_dir, tmp)

            self.assertEqual(new_dir, book_dir)
            self.assertTrue(os.path.exists(book_dir))

    def test_dry_run_reports_but_does_not_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "UnknownAuthor_Econometrics_0000", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "Econometrics", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hansen_Econometrics_2022.pdf",
                "source_pdf_file_id": "fid1",
            })

            result = reconcile_book_naming(book_dir, tmp, dry_run=True)

            self.assertEqual(result, book_dir)
            self.assertTrue(os.path.exists(book_dir))

    def test_missing_metadata_file_returns_original_dir_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = os.path.join(tmp, "processed_outputs", "SomeBook_2025")
            os.makedirs(book_dir)  # no _metadata.json written at all
            result = reconcile_book_naming(book_dir, tmp)
            self.assertEqual(result, book_dir)

    def test_skips_rename_when_target_folder_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_book(tmp, "UnknownAuthor_Econometrics_0000", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "Econometrics", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hansen_Econometrics_2022.pdf",
                "source_pdf_file_id": "fid1",
            })
            # Target name already taken by an unrelated, real folder.
            os.makedirs(os.path.join(tmp, "processed_outputs", "Hansen_Econometrics_2022"))

            result = reconcile_book_naming(book_dir, tmp)

            self.assertEqual(result, book_dir)
            self.assertTrue(os.path.exists(book_dir))


class TestRagMdLivesInAcademicNotes(unittest.TestCase):
    # Only the final .rag.md syncs to the tablet: for a book under
    # academic_resources/, it's written to (and renamed within) the
    # mirrored academic_notes/ path, while the raw .md, images/, and JSON
    # sidecars stay put.

    def _make_resources_book(self, tmp, folder_name, metadata):
        book_dir = os.path.join(tmp, "academic_resources", "econ-101", "textbooks", "processed_outputs", folder_name)
        os.makedirs(os.path.join(book_dir, "images"))
        with open(os.path.join(book_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
            f.write("# Book content\n")
        with open(os.path.join(book_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        return book_dir

    def test_process_book_writes_rag_md_into_the_mirrored_notes_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = self._make_resources_book(tmp, "Hansen_Econometrics_2022", {"source_pdf_file_id": "fid1"})

            process_book(book_dir, client=None, model="unused", academic_hub_root=tmp)

            rel = "academic_notes/econ-101/textbooks/processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.rag.md"
            self.assertTrue(os.path.exists(os.path.join(tmp, rel)))
            self.assertFalse(os.path.exists(os.path.join(book_dir, "Hansen_Econometrics_2022.rag.md")))
            with open(os.path.join(book_dir, "Hansen_Econometrics_2022_metadata.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["rag_md_path"], rel)

    def test_reconcile_book_naming_renames_the_mirrored_rag_md_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_rel = ("academic_notes/econ-101/textbooks/processed_outputs/"
                       "UnknownAuthor_Econometrics_0000/UnknownAuthor_Econometrics_0000.rag.md")
            book_dir = self._make_resources_book(tmp, "UnknownAuthor_Econometrics_0000", {
                "source_pdf_document_info": {"title": "", "author": "", "year": ""},
                "markdown_parsed_info": {"title": "Econometrics", "author": "", "year": ""},
                "source_pdf_path": "academic_resources/econometrics/Hansen_Econometrics_2022.pdf",
                "source_pdf_file_id": "fid1",
                "rag_md_path": old_rel,
            })
            os.makedirs(os.path.dirname(os.path.join(tmp, old_rel)))
            with open(os.path.join(tmp, old_rel), "w", encoding="utf-8") as f:
                f.write("# Book content\n")

            new_dir = reconcile_book_naming(book_dir, tmp)

            new_rel = ("academic_notes/econ-101/textbooks/processed_outputs/"
                       "Hansen_Econometrics_2022/Hansen_Econometrics_2022.rag.md")
            self.assertTrue(os.path.exists(os.path.join(tmp, new_rel)))
            self.assertFalse(os.path.exists(os.path.dirname(os.path.join(tmp, old_rel))))
            with open(os.path.join(new_dir, "Hansen_Econometrics_2022_metadata.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["rag_md_path"], new_rel)


if __name__ == "__main__":
    unittest.main()
