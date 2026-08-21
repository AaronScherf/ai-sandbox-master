import io
import unittest

from pypdf import PdfReader, PdfWriter

from chapter_index import ChapterEntry, get_outline_chapters


def _pdf_with_outline(entries):
    """entries: list of (title, page_index) for top-level outline items."""
    writer = PdfWriter()
    for _ in range(10):
        writer.add_blank_page(width=200, height=200)
    for title, page_index in entries:
        writer.add_outline_item(title, page_index)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return PdfReader(buf)


class TestGetOutlineChapters(unittest.TestCase):
    def test_extracts_top_level_entries_with_physical_pages(self):
        reader = _pdf_with_outline([("Vector Spaces", 0), ("Finite-Dimensional Vector Spaces", 3)])
        chapters = get_outline_chapters(reader)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0], ChapterEntry(title="Vector Spaces", physical_page=0))
        self.assertEqual(chapters[1], ChapterEntry(title="Finite-Dimensional Vector Spaces", physical_page=3))

    def test_no_outline_returns_empty_list(self):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        reader = PdfReader(buf)
        self.assertEqual(get_outline_chapters(reader), [])


from chapter_index import _parse_folio_token


class TestParseFolioToken(unittest.TestCase):
    def test_arabic(self):
        self.assertEqual(_parse_folio_token("157"), (157, False, "157"))

    def test_roman(self):
        self.assertEqual(_parse_folio_token("xvii"), (17, True, "xvii"))

    def test_ocr_lowercase_l_for_i(self):
        # Rudin's printed "ix" (9) was OCR'd as literal "lX".
        self.assertEqual(_parse_folio_token("lX"), (9, True, "lX"))

    def test_genuine_capital_l_not_misread(self):
        # A real roman numeral "L" (50) is uppercase in print; a lowercase
        # 'l' as the whole token is ambiguous OCR noise, not confidently
        # correctable, so it's rejected outright rather than guessed at.
        self.assertEqual(_parse_folio_token("l"), (None, False, None))

    def test_not_a_folio(self):
        self.assertEqual(_parse_folio_token("Sets"), (None, False, None))
        self.assertEqual(_parse_folio_token("12345"), (None, False, None))  # too long to be a folio


if __name__ == "__main__":
    unittest.main()
