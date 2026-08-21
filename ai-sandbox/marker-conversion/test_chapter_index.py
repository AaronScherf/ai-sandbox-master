import io
import unittest

from pypdf import PdfReader, PdfWriter

from chapter_index import ChapterEntry, get_outline_chapters, _parse_folio_token, parse_printed_toc, detect_printed_folio, match_chapter_titles, compute_folio_offset


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


class TestDetectPrintedFolio(unittest.TestCase):
    def test_arabic_footer(self):
        page = "Some body text on this page.\n\nMore text.\n\n157"
        self.assertEqual(detect_printed_folio(page), (157, False, "157"))

    def test_roman_header_with_ocr_artifact(self):
        page = "lX\n\nPreface text starts here and continues for a while."
        self.assertEqual(detect_printed_folio(page), (9, True, "lX"))

    def test_no_folio_present(self):
        page = "Just a page of ordinary prose with no isolated page number."
        self.assertIsNone(detect_printed_folio(page))

    def test_empty_page(self):
        self.assertIsNone(detect_printed_folio(""))


class TestMatchAndOffset(unittest.TestCase):
    def _outline(self):
        return [
            ChapterEntry(title="Vector Spaces", physical_page=14),
            ChapterEntry(title="Finite-Dimensional Vector Spaces", physical_page=40),
            ChapterEntry(title="Linear Maps", physical_page=64),
        ]

    def _toc(self, offset=13):
        return [
            ChapterEntry(title="Vector Spaces", folio_page=14 - offset, folio_is_roman=False),
            ChapterEntry(title="Finite-Dimensional Vector Spaces", folio_page=40 - offset, folio_is_roman=False),
            ChapterEntry(title="Linear Maps", folio_page=64 - offset, folio_is_roman=False),
        ]

    def test_match_by_fuzzy_title(self):
        pairs = match_chapter_titles(self._outline(), self._toc())
        self.assertEqual(len(pairs), 3)
        self.assertEqual(pairs[0][0].title, "Vector Spaces")
        self.assertEqual(pairs[0][1].title, "Vector Spaces")

    def test_offset_consensus(self):
        offset = compute_folio_offset(self._outline(), self._toc(offset=13))
        self.assertEqual(offset, 13)

    def test_offset_disagreement_returns_none(self):
        toc = self._toc(offset=13)
        toc[1].folio_page = 999  # deliberately inconsistent with the others
        self.assertIsNone(compute_folio_offset(self._outline(), toc))

    def test_too_few_samples_returns_none(self):
        outline = [ChapterEntry(title="Only One Chapter", physical_page=14)]
        toc = [ChapterEntry(title="Only One Chapter", folio_page=1)]
        self.assertIsNone(compute_folio_offset(outline, toc))


if __name__ == "__main__":
    unittest.main()
