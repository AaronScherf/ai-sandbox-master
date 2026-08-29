import os
import tempfile
import unittest

from chunk_index import (
    chunks_path, load_chunks, save_chunks,
    _page_markers, _strip_front_matter_by_page, _strip_yaml_frontmatter,
    _Span, _split_by_headings, _detect_problem_boundaries, _split_by_pages,
)


class TestChunkStorage(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_chunks(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            chunks = [{"chunk_id": "abc-000", "file_id": "abc", "text": "hello"}]
            save_chunks(tmp, "math-camp", chunks)
            self.assertEqual(load_chunks(tmp, "math-camp"), chunks)

    def test_chunks_path_lives_under_index_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = chunks_path(tmp, "math-camp")
            self.assertTrue(path.replace("\\", "/").endswith(".index/chunks/math-camp.json"))

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_chunks(tmp, "math-camp", [])
            self.assertTrue(os.path.isdir(os.path.join(tmp, ".index", "chunks")))


class TestStripYamlFrontmatter(unittest.TestCase):
    def test_strips_frontmatter_block(self):
        text = "---\nsource_pdf: a.pdf\ntags: []\n---\n\nBody content."
        self.assertEqual(_strip_yaml_frontmatter(text), "Body content.")

    def test_no_frontmatter_returns_text_unchanged(self):
        text = "<!-- page 1 -->\n\nBody content."
        self.assertEqual(_strip_yaml_frontmatter(text), text)


class TestStripFrontMatterByPage(unittest.TestCase):
    def test_drops_pages_at_or_before_the_boundary(self):
        body = (
            "<!-- page 1 -->\n\nTitle page.\n\n"
            "<!-- page 14 -->\n\nTable of contents.\n\n"
            "<!-- page 15 -->\n\nReal chapter 1 content."
        )
        result = _strip_front_matter_by_page(body, front_matter_end=14)
        self.assertNotIn("Title page", result)
        self.assertNotIn("Table of contents", result)
        self.assertIn("Real chapter 1 content", result)
        self.assertTrue(result.startswith("<!-- page 15 -->"))

    def test_every_page_is_front_matter_keeps_everything(self):
        body = "<!-- page 1 -->\n\nOnly page."
        self.assertEqual(_strip_front_matter_by_page(body, front_matter_end=99), body)


class TestPageMarkers(unittest.TestCase):
    def test_finds_every_marker_with_offsets(self):
        body = "before<!-- page 1 -->mid<!-- page 2 -->after"
        markers = _page_markers(body)
        self.assertEqual([p for p, _ in markers], [1, 2])
        self.assertEqual(body[markers[0][1]:markers[0][1] + 6], "<!-- p")

    def test_no_markers_returns_empty_list(self):
        self.assertEqual(_page_markers("no markers here"), [])


class TestSplitByHeadings(unittest.TestCase):
    def test_splits_at_each_heading_with_correct_spans(self):
        body = "# One\n\nFirst section.\n\n# Two\n\nSecond section."
        spans = _split_by_headings(body)
        self.assertEqual(len(spans), 2)
        self.assertEqual(body[spans[0].start:spans[0].end], "# One\n\nFirst section.\n\n")
        self.assertEqual(body[spans[1].start:spans[1].end], "# Two\n\nSecond section.")

    def test_nested_headings_build_a_heading_path(self):
        body = (
            "# 3 Optimization in Euclidean Space\n\nIntro.\n\n"
            "## 3.7 Optimization over a Convex Set\n\nContent."
        )
        spans = _split_by_headings(body)
        self.assertEqual(spans[0].heading_path, ["3 Optimization in Euclidean Space"])
        self.assertEqual(
            spans[1].heading_path,
            ["3 Optimization in Euclidean Space", "3.7 Optimization over a Convex Set"],
        )

    def test_sibling_after_deeper_heading_pops_the_stack(self):
        body = (
            "# One\n\nA.\n\n## One point one\n\nB.\n\n# Two\n\nC."
        )
        spans = _split_by_headings(body)
        # "Two" is a sibling of "One", not nested under "One point one"
        self.assertEqual(spans[2].heading_path, ["Two"])

    def test_every_span_tagged_with_heading_tier(self):
        body = "# One\n\nA.\n\n# Two\n\nB."
        spans = _split_by_headings(body)
        self.assertTrue(all(s.tier == "heading" for s in spans))
        self.assertTrue(all(s.problem_label is None for s in spans))

    def test_too_few_headings_returns_none(self):
        # Confirmed live: old_exam_2021.md has exactly 1 heading in a
        # 22-page document -- not real structure, must fall through to
        # the next tier rather than produce one giant "chunk".
        body = "Some text.\n\n### Standard Counterexamples\n\nMore text."
        self.assertIsNone(_split_by_headings(body))

    def test_no_headings_returns_none(self):
        self.assertIsNone(_split_by_headings("Just plain text, no headings at all."))


class TestDetectProblemBoundaries(unittest.TestCase):
    def test_plain_numbered_problems(self):
        # Real convention confirmed live in old_problem_set.md.
        body = (
            "1. For each of the following functions, state...\n\n"
            "2. Consider a production function...\n\n"
            "3. In an economy with n goods...\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")
        self.assertEqual(spans[2].problem_label, "Problem 3")
        self.assertTrue(all(s.tier == "problem_number" for s in spans))

    def test_bold_practice_problem_convention(self):
        # Real convention confirmed live in Practice Sheet.md -- doesn't
        # match a bare "N." pattern since it's wrapped in ** and has a title.
        body = (
            "**Practice Problem 1. Involutions**\n\nLet V be...\n\n"
            "**Practice Problem 2. Norms**\n\nShow that...\n\n"
            "**Practice Problem 3. Rank**\n\nDetermine...\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0].problem_label, "Problem 1")

    def test_points_annotated_problems(self):
        # Real convention confirmed live in old_exam_2021.md.
        body = (
            "1. **(40 points)** Are the following statements true or false?\n\n"
            "2. **(15 points)** Consider the following matrix\n\n"
            "3. **(15 points)**. Consider the following function\n\n"
        )
        spans = _detect_problem_boundaries(body)
        self.assertEqual(len(spans), 3)

    def test_too_few_matches_returns_none(self):
        # A single accidental match (e.g. one stray "1." in prose) must
        # not be trusted as real document structure -- same "empirically
        # validate before trusting" bar retag.py's discovery phase uses.
        body = "Some prose that happens to mention item 1. and nothing else numbered."
        self.assertIsNone(_detect_problem_boundaries(body))

    def test_no_matches_returns_none(self):
        self.assertIsNone(_detect_problem_boundaries("No numbered problems in here."))


class TestSplitByPages(unittest.TestCase):
    def test_one_span_per_page_marker(self):
        body = "<!-- page 1 -->\n\nFirst.\n\n<!-- page 2 -->\n\nSecond."
        spans = _split_by_pages(body)
        self.assertEqual(len(spans), 2)
        self.assertTrue(all(s.tier == "page" for s in spans))
        self.assertEqual(body[spans[0].start:spans[0].end], "<!-- page 1 -->\n\nFirst.\n\n")

    def test_no_page_markers_returns_one_span_covering_everything(self):
        body = "Just some text with nothing structural in it at all."
        spans = _split_by_pages(body)
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].start, 0)
        self.assertEqual(spans[0].end, len(body))


if __name__ == "__main__":
    unittest.main()
