import unittest

from audio_generator.textbook_chapters import ChapterSpan, split_into_chapters

# Synthetic markdown mirroring the real structure confirmed against a real
# converted textbook (Axler's Linear Algebra Done Right, academic-hub,
# gitignored/not committed -- see TODO-0057 report): a printed TOC made of
# a standalone "#### Chapter N" marker line followed by a "# *Title*
# **folio**" line, and every page tagged "<!-- page P -->" optionally
# followed immediately by "<!-- folio F -->" once convert_textbook found a
# confident folio offset during conversion. No verbatim copyrighted text is
# used -- only this structural pattern.
_BOOK_WITH_FOLIO_TAGS = """\
<!-- page 0 -->

# *Some Book*

<!-- page 1 -->

# *Contents*

#### Chapter 1
# *Vector Spaces* **1**
#### Chapter 2
# *Finite-Dimensional Vector Spaces* **27**
#### Chapter 3
# *Linear Maps* **51**

<!-- page 13 -->

Front matter filler text that should never end up in any chapter.

<!-- page 14 --><!-- folio 1 -->

# Chapter 1 *Vector Spaces*

Chapter one body text about vector spaces.

<!-- page 39 --><!-- folio 26 -->

More chapter one body text near its end.

<!-- page 40 --><!-- folio 27 -->

## Chapter 2 *Finite-Dimensional Vector Spaces*

Chapter two body text.

<!-- page 64 --><!-- folio 51 -->

Chapter three body text (note: its own heading is malformed/missing in
this synthetic fixture, mirroring a real OCR gap -- the folio tag is what
actually resolves this boundary, not the heading text).
"""

_BOOK_WITHOUT_FOLIO_TAGS = """\
<!-- page 0 -->

# *Contents*

#### Chapter 1
# *Vector Spaces* **1**
#### Chapter 2
# *Finite-Dimensional Vector Spaces* **27**

<!-- page 14 -->

# Chapter 1 *Vector Spaces*

Body text, but this book's conversion run never derived a folio offset,
so no <!-- folio N --> tags exist anywhere -- chapter_index.py's own
bootstrap step returned None for this book.
"""

_BOOK_WITH_NO_TOC = """\
<!-- page 0 -->

Just a short document with page tags but no parseable table of contents
at all -- e.g. a single-chapter pamphlet, or a TOC-less scan.

<!-- page 1 --><!-- folio 1 -->

More text.
"""


class TestSplitIntoChapters(unittest.TestCase):
    def test_resolves_chapter_boundaries_from_toc_and_folio_tags(self):
        spans = split_into_chapters(_BOOK_WITH_FOLIO_TAGS)

        self.assertEqual([s.title for s in spans], ["Vector Spaces", "Finite-Dimensional Vector Spaces", "Linear Maps"])
        self.assertEqual([s.index for s in spans], [1, 2, 3])

    def test_front_matter_before_the_first_chapter_is_excluded(self):
        spans = split_into_chapters(_BOOK_WITH_FOLIO_TAGS)

        for span in spans:
            self.assertNotIn("Front matter filler text", span.text)

    def test_each_chapter_span_contains_only_its_own_body_text(self):
        spans = split_into_chapters(_BOOK_WITH_FOLIO_TAGS)

        self.assertIn("Chapter one body text about vector spaces.", spans[0].text)
        self.assertNotIn("Chapter two body text.", spans[0].text)

        self.assertIn("Chapter two body text.", spans[1].text)
        self.assertNotIn("Chapter one body text", spans[1].text)

        self.assertIn("mirroring a real OCR gap", spans[2].text)

    def test_last_chapter_span_runs_to_the_end_of_the_document(self):
        spans = split_into_chapters(_BOOK_WITH_FOLIO_TAGS)

        # The last resolved chapter must extend to the literal end of the
        # document, not stop early.
        self.assertTrue(_BOOK_WITH_FOLIO_TAGS.endswith(spans[-1].text))

    def test_falls_back_to_no_chapters_when_no_folio_tags_exist(self):
        # A book whose conversion run never found a confident folio offset
        # (chapter_index.bootstrap_chapter_index_from_front_matter returned
        # None for it) has a parseable TOC but no way to anchor it to
        # physical pages in the final markdown -- must not guess.
        spans = split_into_chapters(_BOOK_WITHOUT_FOLIO_TAGS)
        self.assertEqual(spans, [])

    def test_falls_back_to_no_chapters_when_there_is_no_toc(self):
        spans = split_into_chapters(_BOOK_WITH_NO_TOC)
        self.assertEqual(spans, [])

    def test_single_resolved_chapter_is_not_treated_as_a_split(self):
        # Only one TOC entry resolves to a physical page -- not enough to
        # justify a "split" (same consensus bar chapter_index.py uses
        # elsewhere for trusting sparse matches).
        only_one = """\
#### Chapter 1
# *Vector Spaces* **1**

<!-- page 14 --><!-- folio 1 -->

Body text.
"""
        spans = split_into_chapters(only_one)
        self.assertEqual(spans, [])

    def test_chapter_span_is_a_dataclass_with_index_title_and_text(self):
        spans = split_into_chapters(_BOOK_WITH_FOLIO_TAGS)
        self.assertIsInstance(spans[0], ChapterSpan)
        self.assertEqual(spans[0].index, 1)
        self.assertEqual(spans[0].title, "Vector Spaces")
        self.assertIsInstance(spans[0].text, str)


if __name__ == "__main__":
    unittest.main()
