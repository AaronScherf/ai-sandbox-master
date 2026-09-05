import html
import os
import tempfile
import unittest
from dataclasses import dataclass

from rag.report_builder import build_report, report_path, _slugify


@dataclass
class _FakeCitation:
    chunk_id: str
    file_id: str
    path: str
    citation: str
    root: str


@dataclass
class _FakeViz:
    html_path: str
    title: str
    source: str
    fragment_html: str


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_replaces_punctuation(self):
        self.assertEqual(_slugify("What is the Spectral Theorem?"), "what-is-the-spectral-theorem")

    def test_empty_text_returns_fallback(self):
        self.assertEqual(_slugify(""), "report")


class TestReportPath(unittest.TestCase):
    def test_joins_reports_root_course_and_slug(self):
        path = report_path("What is X?", "/root/.reports", "math-camp")
        self.assertEqual(path, os.path.join("/root/.reports", "math-camp", "what-is-x.html"))

    def test_course_none_uses_uncategorized(self):
        path = report_path("What is X?", "/root/.reports", None)
        self.assertIn("uncategorized", path)


class TestBuildReport(unittest.TestCase):
    def test_all_three_pieces_present(self):
        citations = [_FakeCitation(chunk_id="a-0", file_id="a", path="a.md", citation="p. 1", root="/root")]
        viz = _FakeViz(html_path="/x/y.html", title="t", source="template", fragment_html="<div>PLOT-MARKER</div>")
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "report.html")
            result = build_report("What is X?", "X is Y.", citations, viz, output_path)
            self.assertEqual(result, output_path)
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertIn("What is X?", content)
        self.assertIn("X is Y.", content)
        self.assertIn("a.md", content)
        self.assertIn("p. 1", content)
        self.assertIn("PLOT-MARKER", content)

    def test_visualization_none_omits_visualization_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "report.html")
            build_report("What is X?", "X is Y.", [], None, output_path)
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertNotIn("Visualization", content)

    def test_html_special_characters_are_escaped(self):
        citations = [_FakeCitation(
            chunk_id="a-0", file_id="a", path="a.md", citation="<script>bad</script>", root="/root",
        )]
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "report.html")
            build_report(
                "A <b>question</b>?", "An answer with <em>markup</em> & an ampersand.",
                citations, None, output_path,
            )
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        self.assertNotIn("<b>question</b>", content)
        self.assertNotIn("<em>markup</em>", content)
        self.assertNotIn("<script>bad</script>", content)
        self.assertIn(html.escape("A <b>question</b>?"), content)

    def test_write_failure_returns_none_without_raising(self):
        # A path containing a null byte is invalid on every platform and
        # always fails inside open() -- a reliable, portable way to force
        # a write failure without depending on filesystem permissions.
        bad_path = "\0invalid.html"
        result = build_report("q", "a", [], None, bad_path)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
