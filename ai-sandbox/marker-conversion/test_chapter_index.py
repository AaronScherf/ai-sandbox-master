import io
import unittest

from pypdf import PdfReader, PdfWriter

from chapter_index import ChapterEntry, get_outline_chapters, _parse_folio_token, parse_printed_toc


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


class TestParsePrintedToc(unittest.TestCase):
    def test_axler_style_links_with_marker_line(self):
        # Real excerpt shape from Axler_Linear_Algebra_Done_Right_2026.md
        text = (
            "# *Contents*\n\n"
            "# *[About the Author](#page-1-0)* **v**\n\n"
            "### Chapter 1\n\n"
            "# *[Vector Spaces](#page-14-0)* **1**\n\n"
            "### 1A [Complex Numbers and Lists](#page-15-0) 2\n\n"
            "[Exercises 1A](#page-23-0) 10\n\n"
            "### Chapter 2\n\n"
            "# *[Finite-Dimensional Vector Spaces](#page-40-0)* **27**\n\n"
        )
        chapters = parse_printed_toc(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "Vector Spaces")
        self.assertEqual(chapters[0].physical_page, 14)
        self.assertEqual(chapters[0].folio_page, 1)
        self.assertEqual(chapters[1].title, "Finite-Dimensional Vector Spaces")
        self.assertEqual(chapters[1].physical_page, 40)
        self.assertEqual(chapters[1].folio_page, 27)

    def test_hammack_style_table_bare_number_prefix(self):
        # Real excerpt shape from Hammack_Book_of_Proof_2025.md, including
        # the messy split-cell subsection row that must NOT match.
        text = (
            "## **Contents**\n\n"
            "| 1. Sets                             |                         |                            | 3          |\n"
            "|-------------------------------------|-------------------------|----------------------------|------------|\n"
            "| 1.1.                                | Introduction            | to Sets                    | 3          |\n"
            "| 2. Logic                            |                         |                            | 34         |\n"
            "| 3.6.                                | Pascal's                | Triangle and the Binomial  | Theorem 90 |\n"
        )
        chapters = parse_printed_toc(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "Sets")
        self.assertEqual(chapters[0].folio_page, 3)
        self.assertIsNone(chapters[0].physical_page)  # no link in this book's TOC
        self.assertEqual(chapters[1].title, "Logic")
        self.assertEqual(chapters[1].folio_page, 34)

    def test_rudin_style_two_block_table_chapter_word_prefix(self):
        # Real excerpt shape from Rudin_Principles_of_Mathematical_Analysis_2014.md:
        # the TOC is rendered as two separate markdown tables (a page break
        # in the source) with no blank-line-free continuity between them.
        text = (
            "## CONTENTS\n\n"
            "| Preface                                       | lX |\n"
            "|-----------------------------------------------|----|\n"
            "| Chapter 1 The Real and Complex Number Systems | 1  |\n"
            "| Introduction                                  | 1  |\n\n"
            "| Connected Sets                                  | 42         |\n"
            "|-------------------------------------------------|------------|\n"
            "| <b>Chapter 3 Numerical Sequences and Series</b> | <b>47</b>  |\n"
        )
        chapters = parse_printed_toc(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].title, "The Real and Complex Number Systems")
        self.assertEqual(chapters[0].folio_page, 1)
        self.assertEqual(chapters[1].title, "Numerical Sequences and Series")
        self.assertEqual(chapters[1].folio_page, 47)

    def test_no_toc_returns_empty(self):
        self.assertEqual(parse_printed_toc("Just some ordinary prose about eigenvalues."), [])


if __name__ == "__main__":
    unittest.main()
