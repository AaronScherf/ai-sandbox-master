import os
import tempfile
import unittest

from postprocess_discovery import (
    derive_eligible_pages,
    discover_markdown_files,
    is_correction_target,
    parse_frontmatter,
    split_pages_by_tag,
)


class TestParseFrontmatter(unittest.TestCase):
    def test_splits_real_hybrid_frontmatter_from_body(self):
        md_text = (
            "---\n"
            "source_pdf: Practice Sheet.pdf\n"
            "folder_category: problem_sets\n"
            "total_pages: 43\n"
            "routing: hybrid\n"
            "model: gemini-3.1-flash-lite\n"
            "pages_repaired: 2\n"
            "repaired_pages: [35, 43]\n"
            "tags: []\n"
            "---\n\n"
            "<!-- page 1 -->\n\nHello."
        )
        metadata, body = parse_frontmatter(md_text)
        self.assertEqual(metadata["routing"], "hybrid")
        self.assertEqual(metadata["total_pages"], 43)
        self.assertEqual(metadata["repaired_pages"], [35, 43])
        self.assertEqual(body, "<!-- page 1 -->\n\nHello.")

    def test_missing_frontmatter_returns_empty_dict_and_full_text(self):
        # Real case: Analysis_Exercises.md before its 2026-08-26 re-run
        # had no frontmatter block at all.
        md_text = "<!-- page 1 -->\n\nAnalysis: Guided Exercises"
        metadata, body = parse_frontmatter(md_text)
        self.assertEqual(metadata, {})
        self.assertEqual(body, md_text)


class TestSplitPagesByTag(unittest.TestCase):
    def test_splits_multiple_pages_by_their_tags(self):
        body = "<!-- page 1 -->\n\nFirst.\n\n<!-- page 2 -->\n\nSecond."
        pages = split_pages_by_tag(body)
        self.assertEqual(pages[1], "First.")
        self.assertEqual(pages[2], "Second.")

    def test_single_page_body(self):
        body = "<!-- page 1 -->\n\nOnly page."
        pages = split_pages_by_tag(body)
        self.assertEqual(pages, {1: "Only page."})

    def test_empty_body_returns_empty_dict(self):
        self.assertEqual(split_pages_by_tag(""), {})


class TestDeriveEligiblePages(unittest.TestCase):
    def test_local_routing_makes_every_page_eligible(self):
        frontmatter = {"routing": "local", "total_pages": 5}
        self.assertEqual(derive_eligible_pages(frontmatter), [1, 2, 3, 4, 5])

    def test_hybrid_routing_excludes_repaired_pages(self):
        frontmatter = {"routing": "hybrid", "total_pages": 5, "repaired_pages": [2, 4]}
        self.assertEqual(derive_eligible_pages(frontmatter), [1, 3, 5])

    def test_gemini_batched_has_no_eligible_pages(self):
        # Already fully model-verified -- nothing left for this pass to check.
        frontmatter = {"routing": "gemini_batched", "total_pages": 43, "repaired_pages": [1, 2, 3]}
        self.assertEqual(derive_eligible_pages(frontmatter), [])

    def test_gemini_accumulating_has_no_eligible_pages(self):
        frontmatter = {"routing": "gemini_accumulating", "total_pages": 25}
        self.assertEqual(derive_eligible_pages(frontmatter), [])

    def test_missing_routing_has_no_eligible_pages(self):
        # Textbook output, or any file without this project's own routing field.
        self.assertEqual(derive_eligible_pages({"total_pages": 300}), [])

    def test_missing_total_pages_has_no_eligible_pages(self):
        self.assertEqual(derive_eligible_pages({"routing": "local"}), [])


class TestIsCorrectionTarget(unittest.TestCase):
    def test_notes_document_not_yet_postprocessed_is_a_target(self):
        self.assertTrue(is_correction_target({"routing": "hybrid"}))

    def test_already_postprocessed_document_is_not_a_target(self):
        self.assertFalse(is_correction_target({"routing": "hybrid", "postprocessed": True}))

    def test_textbook_output_without_routing_is_not_a_target(self):
        self.assertFalse(is_correction_target({"total_pages": 300}))


class TestDiscoverMarkdownFiles(unittest.TestCase):
    def test_finds_md_files_only_under_processed_outputs_folders(self):
        with tempfile.TemporaryDirectory() as root:
            po1 = os.path.join(root, "problem_sets", "processed_outputs")
            po2 = os.path.join(root, "ta_notes", "processed_outputs")
            os.makedirs(po1)
            os.makedirs(po2)
            open(os.path.join(po1, "Practice Sheet.md"), "w").close()
            open(os.path.join(po2, "LN_Analysis.md"), "w").close()
            # A markdown file OUTSIDE any processed_outputs/ folder must not
            # be picked up -- e.g. a stray README living under the same root.
            open(os.path.join(root, "README.md"), "w").close()

            found = discover_markdown_files([root])

            self.assertEqual(len(found), 2)
            self.assertTrue(any(f.endswith("Practice Sheet.md") for f in found))
            self.assertTrue(any(f.endswith("LN_Analysis.md") for f in found))

    def test_multiple_root_dirs_in_one_call(self):
        with tempfile.TemporaryDirectory() as root1, tempfile.TemporaryDirectory() as root2:
            po1 = os.path.join(root1, "processed_outputs")
            po2 = os.path.join(root2, "processed_outputs")
            os.makedirs(po1)
            os.makedirs(po2)
            open(os.path.join(po1, "a.md"), "w").close()
            open(os.path.join(po2, "b.md"), "w").close()

            found = discover_markdown_files([root1, root2])

            self.assertEqual(len(found), 2)

    def test_no_processed_outputs_folder_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(discover_markdown_files([root]), [])


if __name__ == "__main__":
    unittest.main()
