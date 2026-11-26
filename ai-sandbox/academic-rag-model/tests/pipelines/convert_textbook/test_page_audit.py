import io
import unittest

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from pipelines.convert_textbook import page_audit
from pipelines.convert_textbook.page_markers import remap_page_markers

SEP = "-" * 48


def _reader(*page_streams):
    """A PDF with one page per argument; each is a raw content stream (b"" = blank)."""
    writer = PdfWriter()
    for stream in page_streams:
        page = writer.add_blank_page(width=200, height=200)
        content = DecodedStreamObject()
        content.set_data(stream)
        page[NameObject("/Contents")] = writer._add_object(content)
    buf = io.BytesIO()
    writer.write(buf)
    return PdfReader(io.BytesIO(buf.getvalue()))


class TestRemapConsecutiveEmptyPages(unittest.TestCase):
    def test_every_separator_is_rewritten_when_pages_are_empty(self):
        raw = f"\n\n{{0}}{SEP}\n\n{{1}}{SEP}\n\n{{2}}{SEP}\n\n{{3}}{SEP}"
        out = remap_page_markers(raw, 250, None, 999)
        for page in (250, 251, 252, 253):
            self.assertIn(f"<!-- page {page} -->", out)
        self.assertNotIn(SEP, out)


class TestEmptyPages(unittest.TestCase):
    def test_reports_tag_only_and_missing_pages(self):
        text = ("<!-- page 4 -->\n\nreal text\n\n<!-- page 5 --><!-- folio 1 -->\n\n"
                "<span id=\"page-5-0\"></span>\n\n<!-- page 6 -->\n\n![](pg_1_a.jpeg)")
        self.assertEqual(page_audit.empty_pages(text, 4, 8), [5, 7])

    def test_unremapped_separator_and_failure_flag_are_not_content(self):
        text = (f"<!-- page 0 -->\n\n{{1}}{SEP}\n\n"
                f"<!-- page 1 -->\n\n{page_audit.UNCONVERTED_FLAG}")
        self.assertEqual(page_audit.empty_pages(text, 0, 2), [0, 1])

    def test_format_runs(self):
        self.assertEqual(page_audit.format_runs([1, 2, 3, 7, 9, 10]), "1-3, 7, 9-10")
        self.assertEqual(page_audit.format_runs([]), "none")


class TestReplacePage(unittest.TestCase):
    def test_replaces_only_that_page_and_keeps_order(self):
        text = "<!-- page 0 -->\n\nzero\n\n<!-- page 1 -->\n\n<!-- page 2 -->\n\ntwo"
        out = page_audit.replace_page(text, 1, "<!-- page 1 -->\n\none")
        self.assertLess(out.index("zero"), out.index("one"))
        self.assertLess(out.index("one"), out.index("two"))
        self.assertEqual(out.count("<!-- page 1 -->"), 1)

    def test_inserts_a_page_that_had_no_tag(self):
        text = "<!-- page 0 -->\n\nzero\n\n<!-- page 2 -->\n\ntwo"
        out = page_audit.replace_page(text, 1, "<!-- page 1 -->\n\none")
        self.assertEqual(page_audit.empty_pages(out, 0, 3), [])
        self.assertLess(out.index("one"), out.index("two"))


class TestIsBlankPage(unittest.TestCase):
    def test_white_page_is_blank_and_inked_page_is_not(self):
        reader = _reader(b"", b"0 g 40 40 120 120 re f")
        self.assertTrue(page_audit.is_blank_page(reader, 0))
        self.assertFalse(page_audit.is_blank_page(reader, 1))

    def test_edge_shadow_alone_is_blank(self):
        reader = _reader(b"0 g 0 0 6 200 re f")
        self.assertTrue(page_audit.is_blank_page(reader, 0))

    def test_unrenderable_page_is_treated_as_not_blank(self):
        self.assertFalse(page_audit.is_blank_page(_reader(b""), 5))


if __name__ == "__main__":
    unittest.main()
