import io
import unittest

from pypdf import PdfReader, PdfWriter

from textbook.chapter_index import ChapterEntry
from textbook.toc_identify import (
    _dedupe_by_increasing_folio,
    generate_chapter_template,
    identify_chapters,
    identify_chapters_from_manual_list,
    identify_chapters_via_outline,
    parse_manual_chapter_list,
)


_HAMMACK_STYLE_TOC = (
    "## **Contents**\n\n"
    "| 1. Sets                             |                         |                            | 3          |\n"
    "|-------------------------------------|-------------------------|----------------------------|------------|\n"
    "| 2. Logic                            |                         |                            | 34         |\n"
)


def _folio_tag(n):
    return f"<!-- page {n} --><!-- folio {n} -->\n\n"


def _page_tag(n):
    return f"<!-- page {n} -->\n\n"


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


class TestIdentifyChapters(unittest.TestCase):
    def test_no_toc_is_not_confident(self):
        result = identify_chapters("Just some ordinary prose about eigenvalues.")
        self.assertFalse(result.confident)
        self.assertIn("table of contents", result.reason)

    def test_no_folio_tags_is_not_confident(self):
        text = _HAMMACK_STYLE_TOC + "\n# Sets\n\nChapter 1 body, no folio tags anywhere.\n"
        result = identify_chapters(text)
        self.assertFalse(result.confident)
        self.assertIn("folio", result.reason)

    def test_confident_when_every_chapter_folio_is_reached_in_order(self):
        text = _HAMMACK_STYLE_TOC + "\n" + _folio_tag(3) + "Chapter 1 body.\n\n" + _folio_tag(34) + "Chapter 2 body.\n"
        result = identify_chapters(text)
        self.assertTrue(result.confident)
        self.assertEqual([m.chapter.title for m in result.matches], ["Sets", "Logic"])
        self.assertEqual([m.matched_at for m in result.matches], [3, 34])
        self.assertLess(result.matches[0].offset, result.matches[1].offset)

    def test_first_folio_tag_reaching_the_target_is_used_not_an_exact_match_only(self):
        # Folio 34 itself is never explicitly tagged (a gap in the OCR'd
        # sequence) -- the first tag that *reaches* it (35) must be used.
        text = _HAMMACK_STYLE_TOC + "\n" + _folio_tag(3) + "Chapter 1 body.\n\n" + _folio_tag(35) + "Chapter 2 body.\n"
        result = identify_chapters(text)
        self.assertTrue(result.confident)
        self.assertEqual(result.matches[1].matched_at, 35)

    def test_not_confident_when_a_chapter_folio_is_never_reached(self):
        text = _HAMMACK_STYLE_TOC + "\n" + _folio_tag(3) + "Chapter 1 body, but folio never reaches 34.\n"
        result = identify_chapters(text)
        self.assertFalse(result.confident)
        self.assertIn("Logic", result.reason)

    def test_ignores_a_toc_look_alike_table_far_past_the_front_matter(self):
        # A second Contents-shaped table can appear deep in the document --
        # confirmed live in Rudin's rag.md, whose PDF bundles an appended
        # solutions manual with its own "Contents" page hundreds of pages
        # in. Only the real front-matter TOC (page <= ~50) should be used.
        text = (
            _HAMMACK_STYLE_TOC
            + "\n" + _folio_tag(3) + "Chapter 1 body.\n\n"
            + _folio_tag(34) + "Chapter 2 body.\n\n"
            + _folio_tag(400)
            + "| 1. Sets  |  | | 900 |\n|---|---|---|---|\n| 2. Logic |  | | 950 |\n"
        )
        result = identify_chapters(text)
        self.assertTrue(result.confident)
        self.assertEqual([m.chapter.title for m in result.matches], ["Sets", "Logic"])
        self.assertEqual([m.matched_at for m in result.matches], [3, 34])

    def test_drops_a_spurious_low_folio_entry_appearing_after_later_chapters(self):
        # Real bug (Cameron): the front-matter window's own text can
        # include the start of chapter 1's real body, and a numbered
        # subsection in there ("1.1 Introduction ... 3") gets misread by
        # parse_printed_toc as a bogus extra "chapter" with folio_page=3
        # -- tacked on the end of the TOC list, after chapters already
        # parsed at much higher folio numbers. Search-forward-from-cursor
        # then trivially "finds" the very next folio tag for it (since
        # virtually every remaining folio is >= 3), silently splitting
        # off a bogus near-empty extra chapter at the end.
        text = (
            _HAMMACK_STYLE_TOC
            + "\n" + _folio_tag(3) + "Chapter 1 body.\n\n"
            + _folio_tag(34) + "Chapter 2 body.\n\n"
            + _folio_tag(50) + "Some trailing content.\n"
        )
        toc_with_stray_entry = [
            ChapterEntry(title="Sets", folio_page=3),
            ChapterEntry(title="Logic", folio_page=34),
            ChapterEntry(title="Sets", folio_page=3),  # the misread stray entry
        ]
        self.assertEqual(
            [c.title for c in _dedupe_by_increasing_folio(toc_with_stray_entry)], ["Sets", "Logic"]
        )
        # And identify_chapters itself, on real text, never produces a
        # third match for a TOC that (after parsing) only has 2 real
        # entries -- this is the end-to-end guard.
        result = identify_chapters(text)
        self.assertTrue(result.confident)
        self.assertEqual(len(result.matches), 2)

    def test_never_skips_ahead_into_a_later_reprint_of_the_same_folio_range(self):
        # Real bug this guards: a chapter's real content can be followed,
        # much later in the same document, by an appended second document
        # whose own folio numbering is unrelated (e.g. a solutions manual
        # that also happens to reach folio 34 again deep in). Forward-only,
        # first-tag-reaching-target search must land on the near one.
        text = (
            _HAMMACK_STYLE_TOC
            + "\n" + _folio_tag(3) + "Chapter 1 body.\n\n"
            + _folio_tag(34) + "Chapter 2 real body.\n\n"
            + _folio_tag(900) + "Chapter 2 body again, from an appended document.\n"
        )
        result = identify_chapters(text)
        self.assertTrue(result.confident)
        self.assertEqual(result.matches[1].matched_at, 34)


class TestIdentifyChaptersViaOutline(unittest.TestCase):
    # Real case this exists for (Hansen): the book's own printed TOC
    # parsed to just 1 usable entry -- a separate OCR/table-format
    # failure -- even though the PDF's own outline was rich and
    # complete, and front-matter OCR never anchored a folio offset
    # either (no <!-- folio N --> tags at all). This path needs neither:
    # it reads numbered chapter-shaped titles directly off the PDF's own
    # outline, entirely independent of the printed TOC.
    def test_confident_when_outline_has_numbered_chapters_and_pages_are_reached(self):
        reader = _pdf_with_outline([("1. Sets", 3), ("1.1 A Subsection", 4), ("2. Logic", 8)])
        text = _page_tag(3) + "Chapter 1 body.\n\n" + _page_tag(8) + "Chapter 2 body.\n"
        result = identify_chapters_via_outline(text, reader)
        self.assertTrue(result.confident)
        # The decimal-numbered subsection entry is dropped, not split on.
        self.assertEqual([m.chapter.title for m in result.matches], ["Sets", "Logic"])
        self.assertEqual([m.matched_at for m in result.matches], [3, 8])

    def test_no_outline_is_not_confident(self):
        reader = _pdf_with_outline([])
        text = _page_tag(3) + "Chapter 1 body.\n"
        result = identify_chapters_via_outline(text, reader)
        self.assertFalse(result.confident)
        self.assertIn("outline", result.reason)

    def test_outline_with_no_numbered_chapter_entries_is_not_confident(self):
        # Part dividers and front-matter entries ("Preface", "Cover")
        # never look like "N. Title" -- nothing left to split on.
        reader = _pdf_with_outline([("Preface", 1), ("Part I. Regression", 2)])
        text = _page_tag(1) + "Front matter.\n"
        result = identify_chapters_via_outline(text, reader)
        self.assertFalse(result.confident)

    def test_no_page_tags_is_not_confident(self):
        reader = _pdf_with_outline([("1. Sets", 3), ("2. Logic", 8)])
        text = "No page tags at all.\n"
        result = identify_chapters_via_outline(text, reader)
        self.assertFalse(result.confident)
        self.assertIn("page", result.reason)

    def test_handles_letter_numbered_chapter_style(self):
        # Real bug (Ok, Real Analysis with Economic Applications): this
        # book's outline numbers chapters by letter ("Chapter A -
        # Preliminaries of Real Analysis"), not digit -- the bare-number
        # pattern alone missed all 267 outline entries. Subsections in
        # the same style ("A.1 - Elements of Set Theory") must still be
        # dropped, since they don't start with the literal word "Chapter".
        reader = _pdf_with_outline([
            ("Chapter A - Preliminaries of Real Analysis", 3),
            ("A.1 - Elements of Set Theory", 4),
            ("Chapter B - Metric Spaces", 8),
        ])
        text = _page_tag(3) + "Chapter A body.\n\n" + _page_tag(8) + "Chapter B body.\n"
        result = identify_chapters_via_outline(text, reader)
        self.assertTrue(result.confident)
        self.assertEqual(
            [m.chapter.title for m in result.matches],
            ["Preliminaries of Real Analysis", "Metric Spaces"],
        )


class TestParseManualChapterList(unittest.TestCase):
    def test_parses_title_pipe_page_lines(self):
        text = "Introduction | 12\nLinear Models | 45\n"
        chapters = parse_manual_chapter_list(text)
        self.assertEqual([(c.title, c.physical_page) for c in chapters], [("Introduction", 12), ("Linear Models", 45)])

    def test_ignores_comments_and_blank_lines(self):
        text = "# Chapter template\n\nIntroduction | 12\n# a comment\n\nLinear Models | 45\n"
        chapters = parse_manual_chapter_list(text)
        self.assertEqual(len(chapters), 2)

    def test_ignores_malformed_lines(self):
        text = "Introduction | 12\nThis line has no page number\nLinear Models | 45\n"
        chapters = parse_manual_chapter_list(text)
        self.assertEqual([c.title for c in chapters], ["Introduction", "Linear Models"])

    def test_strips_surrounding_whitespace(self):
        chapters = parse_manual_chapter_list("  Introduction   |   12  \n")
        self.assertEqual(chapters[0].title, "Introduction")
        self.assertEqual(chapters[0].physical_page, 12)


class TestIdentifyChaptersFromManualList(unittest.TestCase):
    def test_confident_when_every_chapter_page_is_reached_in_order(self):
        manual_text = "Sets | 3\nLogic | 8\n"
        text = _page_tag(3) + "Chapter 1 body.\n\n" + _page_tag(8) + "Chapter 2 body.\n"
        result = identify_chapters_from_manual_list(text, manual_text)
        self.assertTrue(result.confident)
        self.assertEqual([m.chapter.title for m in result.matches], ["Sets", "Logic"])

    def test_empty_template_is_not_confident(self):
        result = identify_chapters_from_manual_list("some text", "# just a comment\n")
        self.assertFalse(result.confident)

    def test_no_page_tags_is_not_confident(self):
        manual_text = "Sets | 3\n"
        result = identify_chapters_from_manual_list("no page tags here", manual_text)
        self.assertFalse(result.confident)
        self.assertIn("page", result.reason)

    def test_chapter_page_never_reached_is_not_confident(self):
        manual_text = "Sets | 3\nLogic | 999\n"
        text = _page_tag(3) + "Chapter 1 body.\n"
        result = identify_chapters_from_manual_list(text, manual_text)
        self.assertFalse(result.confident)
        self.assertIn("Logic", result.reason)


class TestGenerateChapterTemplate(unittest.TestCase):
    def test_includes_book_name_and_format_instructions(self):
        content = generate_chapter_template("Sample_Book_2020")
        self.assertIn("Sample_Book_2020", content)
        self.assertIn("|", content)
        self.assertTrue(all(line.startswith("#") or not line.strip() for line in content.splitlines()))


class TestDedupeByIncreasingFolio(unittest.TestCase):
    def test_drops_entries_that_do_not_strictly_increase(self):
        # Real bug (Cameron): a chapter title split across two table rows
        # parses as two ChapterEntry objects sharing the same folio_page --
        # the second one is not real chapter structure, just noise.
        chapters = [
            ChapterEntry(title="One", folio_page=3),
            ChapterEntry(title="Two", folio_page=34),
            ChapterEntry(title="Two again", folio_page=34),
            ChapterEntry(title="Three", folio_page=60),
        ]
        result = _dedupe_by_increasing_folio(chapters)
        self.assertEqual([c.title for c in result], ["One", "Two", "Three"])

    def test_keeps_a_clean_increasing_list_unchanged(self):
        chapters = [ChapterEntry(title="One", folio_page=3), ChapterEntry(title="Two", folio_page=34)]
        self.assertEqual(_dedupe_by_increasing_folio(chapters), chapters)

    def test_drops_entries_with_no_folio_page_at_all(self):
        chapters = [ChapterEntry(title="One", folio_page=3), ChapterEntry(title="No folio", folio_page=None)]
        result = _dedupe_by_increasing_folio(chapters)
        self.assertEqual([c.title for c in result], ["One"])


if __name__ == "__main__":
    unittest.main()
