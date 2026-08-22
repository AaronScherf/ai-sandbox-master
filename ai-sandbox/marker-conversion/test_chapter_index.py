import io
import unittest

from pypdf import PdfReader, PdfWriter

from chapter_index import ChapterEntry, get_outline_chapters, _parse_folio_token, parse_printed_toc, detect_printed_folio, match_chapter_titles, compute_folio_offset, bootstrap_chapter_index_from_front_matter, pack_chapters_into_chunks, resolve_probe_boundaries, _consensus_offset


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

    def test_offset_two_of_three_returns_consensus(self):
        # Two out of three chapters agree on offset=13; this is a majority (66%)
        # and should return the consensus, not None.
        toc = self._toc(offset=13)
        toc[1].folio_page = 999  # deliberately inconsistent: offset becomes 40-999=-959
        offset = compute_folio_offset(self._outline(), toc)
        self.assertEqual(offset, 13)

    def test_offset_three_of_four_returns_consensus(self):
        # Three out of four chapters agree on offset=13; this is a strong majority (75%)
        # and should return the consensus, not None.
        outline = [
            ChapterEntry(title="Chapter 1", physical_page=15),
            ChapterEntry(title="Chapter 2", physical_page=40),
            ChapterEntry(title="Chapter 3", physical_page=65),
            ChapterEntry(title="Chapter 4", physical_page=90),
        ]
        toc = [
            ChapterEntry(title="Chapter 1", folio_page=15 - 13, folio_is_roman=False),
            ChapterEntry(title="Chapter 2", folio_page=40 - 13, folio_is_roman=False),
            ChapterEntry(title="Chapter 3", folio_page=65 - 13, folio_is_roman=False),
            ChapterEntry(title="Chapter 4", folio_page=90 - 50, folio_is_roman=False),  # outlier: offset=40
        ]
        offset = compute_folio_offset(outline, toc)
        self.assertEqual(offset, 13)

    def test_too_few_samples_returns_none(self):
        outline = [ChapterEntry(title="Only One Chapter", physical_page=14)]
        toc = [ChapterEntry(title="Only One Chapter", folio_page=1)]
        self.assertIsNone(compute_folio_offset(outline, toc))

    def test_no_majority_agreement_returns_none(self):
        # Four samples, split 2-2 between two different offsets (13 and
        # 50) -- neither reaches a majority (need >= 3 of 4), so this must
        # return None rather than picking one arbitrarily. This is the
        # exact "agreeing < max(2, len(samples)//2+1)" branch that
        # regressed once already (unanimity vs. majority bug).
        outline = [
            ChapterEntry(title="Chapter 1", physical_page=15),
            ChapterEntry(title="Chapter 2", physical_page=40),
            ChapterEntry(title="Chapter 3", physical_page=65),
            ChapterEntry(title="Chapter 4", physical_page=90),
        ]
        toc = [
            ChapterEntry(title="Chapter 1", folio_page=15 - 13, folio_is_roman=False),
            ChapterEntry(title="Chapter 2", folio_page=40 - 13, folio_is_roman=False),
            ChapterEntry(title="Chapter 3", folio_page=65 - 50, folio_is_roman=False),
            ChapterEntry(title="Chapter 4", folio_page=90 - 50, folio_is_roman=False),
        ]
        self.assertIsNone(compute_folio_offset(outline, toc))


class TestBootstrap(unittest.TestCase):
    def test_bootstraps_physical_pages_from_folio_anchors(self):
        # Two anchor pages agree on offset=10 (11-1, 34-24), meeting the
        # >=2-sample consensus bar shared with compute_folio_offset.
        front_matter = (
            "<!-- page 9 -->\n\nPreface text.\n\nlX\n\n"
            "<!-- page 10 -->\n\n"
            "## CONTENTS\n\n"
            "| Chapter 1 The Real and Complex Number Systems | 1  |\n"
            "| Chapter 2 Basic Topology                      | 24 |\n\n"
            "<!-- page 11 -->\n\nThe Real and Complex Number Systems\n\nBody text.\n\n1\n\n"
            "<!-- page 34 -->\n\nBasic Topology\n\nBody text.\n\n24\n\n"
        )
        chapters, offset = bootstrap_chapter_index_from_front_matter(front_matter)
        self.assertEqual(offset, 10)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].physical_page, 11)  # 1 + 10
        self.assertEqual(chapters[1].physical_page, 34)  # 24 + 10

    def test_finds_anchor_via_a_later_chapter_when_first_chapters_page_has_no_folio(self):
        # Reproduces the real Rudin failure this fix targets: chapter 1's
        # opening page prints no folio at all (a common typesetting
        # convention for chapter-opening pages), but chapters 2 and 3's do.
        # The bootstrap must not depend on chapter 1's page specifically --
        # and once consensus is reached from later chapters, chapter 1's
        # own physical_page is still correctly derived via folio + offset,
        # even though its page never contributed a sample.
        front_matter = (
            "<!-- page 9 -->\n\nPreface text.\n\nlX\n\n"
            "<!-- page 10 -->\n\n"
            "## CONTENTS\n\n"
            "| Chapter 1 The Real and Complex Number Systems | 1  |\n"
            "| Chapter 2 Basic Topology                      | 24 |\n"
            "| Chapter 3 Numerical Sequences and Series       | 47 |\n\n"
            "<!-- page 11 -->\n\nThe Real and Complex Number Systems\n\nNo folio printed on this page.\n\n"
            "<!-- page 34 -->\n\nBasic Topology\n\nBody text.\n\n24\n\n"
            "<!-- page 57 -->\n\nNumerical Sequences and Series\n\nBody text.\n\n47\n\n"
        )
        chapters, offset = bootstrap_chapter_index_from_front_matter(front_matter)
        self.assertEqual(offset, 10)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].physical_page, 11)  # 1 + 10, derived even though page 11 is silent
        self.assertEqual(chapters[1].physical_page, 34)
        self.assertEqual(chapters[2].physical_page, 57)

    def test_single_matching_page_is_not_enough_for_consensus(self):
        # Only chapter 1's folio happens to match a scanned page; chapter
        # 2's page prints nothing. A single sample is deliberately not
        # trusted (matches compute_folio_offset's bar elsewhere) -- a lone
        # coincidental match could easily be wrong.
        front_matter = (
            "<!-- page 10 -->\n\n"
            "## CONTENTS\n\n"
            "| Chapter 1 Something | 1 |\n"
            "| Chapter 2 Something Else | 24 |\n\n"
            "<!-- page 11 -->\n\nSomething\n\nBody text.\n\n1\n\n"
            "<!-- page 40 -->\n\nSomething Else\n\nNo folio printed here either.\n\n"
        )
        chapters, offset = bootstrap_chapter_index_from_front_matter(front_matter)
        self.assertEqual(chapters, [])
        self.assertIsNone(offset)

    def test_no_toc_fails_gracefully(self):
        chapters, offset = bootstrap_chapter_index_from_front_matter("<!-- page 0 -->\n\nJust prose.")
        self.assertEqual(chapters, [])
        self.assertIsNone(offset)

    def test_no_anchor_page_found_fails_gracefully(self):
        front_matter = (
            "<!-- page 0 -->\n\n"
            "## CONTENTS\n\n"
            "| Chapter 1 Something | 1 |\n\n"
            "<!-- page 1 -->\n\nNo isolated folio number printed on this page at all, just prose.\n\n"
        )
        chapters, offset = bootstrap_chapter_index_from_front_matter(front_matter)
        self.assertEqual(chapters, [])
        self.assertIsNone(offset)


class TestConsensusOffset(unittest.TestCase):
    def test_majority_agreement(self):
        self.assertEqual(_consensus_offset([13, 13, 13, 50]), 13)

    def test_too_few_samples(self):
        self.assertIsNone(_consensus_offset([13]))
        self.assertIsNone(_consensus_offset([]))

    def test_no_majority(self):
        self.assertIsNone(_consensus_offset([13, 13, 50, 50]))

    def test_near_agreement_within_tolerance(self):
        self.assertEqual(_consensus_offset([13, 14, 13]), 13)


class TestPackChaptersIntoChunks(unittest.TestCase):
    def test_packs_multiple_chapters_under_cap(self):
        chapters = [
            ChapterEntry(title="Ch1", physical_page=14),
            ChapterEntry(title="Ch2", physical_page=40),
            ChapterEntry(title="Ch3", physical_page=64),
        ]
        chunks = pack_chapters_into_chunks(chapters, start_page=14, total_pages=200, max_chunk_size=150)
        # 40-14=26, 64-14=50, 200-14=186 (>150) -- cuts at the last chapter
        # boundary still under the cap, then takes the rest.
        self.assertEqual(chunks, [(14, 64), (64, 200)])

    def test_oversized_single_chapter_falls_back_to_cap(self):
        chapters = [
            ChapterEntry(title="Huge Chapter", physical_page=0),
            ChapterEntry(title="Ch2", physical_page=200),
        ]
        chunks = pack_chapters_into_chunks(chapters, start_page=0, total_pages=250, max_chunk_size=150)
        self.assertEqual(chunks, [(0, 150), (150, 250)])

    def test_no_chapters_produces_one_fixed_cap_chunk_sequence(self):
        chunks = pack_chapters_into_chunks([], start_page=0, total_pages=320, max_chunk_size=150)
        self.assertEqual(chunks, [(0, 150), (150, 300), (300, 320)])

    def test_chapter_pages_outside_range_are_ignored(self):
        chapters = [
            ChapterEntry(title="Front matter chapter-like entry", physical_page=5),  # before start_page
            ChapterEntry(title="Ch1", physical_page=20),
        ]
        chunks = pack_chapters_into_chunks(chapters, start_page=14, total_pages=100, max_chunk_size=150)
        self.assertEqual(chunks, [(14, 100)])


class TestResolveProbeBoundaries(unittest.TestCase):
    @staticmethod
    def _assert_contiguous(test, boundaries, expected_start, total_pages):
        test.assertEqual(boundaries[0][0], expected_start)
        test.assertEqual(boundaries[-1][1], total_pages)
        for i in range(len(boundaries) - 1):
            test.assertEqual(
                boundaries[i][1], boundaries[i + 1][0],
                f"gap/overlap between {boundaries[i]} and {boundaries[i + 1]}",
            )

    def test_probe_shift_carries_forward_into_next_chunk_start(self):
        # Basic case: two non-chapter-aligned cuts, each shifted forward by
        # the stub probe. Under the old (buggy) code, the second tuple's
        # start would stay at the ORIGINAL packed value (30) even though
        # the first chunk's shifted end is 33 -- producing an overlapping
        # chunk (30, 63) that duplicates pages 30-32. This asserts the
        # fixed contiguity invariant instead.
        packed = [(0, 30), (30, 60), (60, 100)]
        probe_fn = lambda end, hard_limit: min(end + 3, hard_limit)
        boundaries = resolve_probe_boundaries(packed, 0, 100, known_chapter_pages=set(), probe_fn=probe_fn)
        self.assertEqual(boundaries, [(0, 33), (33, 63), (63, 100)])
        self._assert_contiguous(self, boundaries, 0, 100)

    def test_large_shift_swallows_a_subsequent_packed_cut_without_overlap(self):
        # Reproduces the exact overlap scenario the reviewer found: a
        # probe shift big enough that it jumps past the next packed cut
        # entirely (10 -> 18 swallows the (10, 15) span). The old code
        # would append (10, 23) here -- overlapping the (0, 18) chunk that
        # already claimed pages 10-17. The fix must skip the swallowed
        # cut and keep the boundaries list contiguous.
        packed = [(0, 10), (10, 15), (15, 50)]
        probe_fn = lambda end, hard_limit: min(end + 8, hard_limit)
        boundaries = resolve_probe_boundaries(packed, 0, 50, known_chapter_pages=set(), probe_fn=probe_fn)
        self.assertEqual(boundaries, [(0, 18), (18, 50)])
        self._assert_contiguous(self, boundaries, 0, 50)

    def test_known_chapter_boundary_and_total_pages_are_not_probed(self):
        # A cut that lands exactly on a known chapter page, or on
        # total_pages, is already safe and must not be shifted at all --
        # confirmed here by a probe_fn that would corrupt the boundary
        # (shift to 999) if it were ever called on these cuts.
        def exploding_probe_fn(end, hard_limit):
            raise AssertionError(f"probe_fn should not be called for a known/total_pages cut (end={end})")

        packed = [(10, 40), (40, 70)]
        boundaries = resolve_probe_boundaries(
            packed, front_matter_end=10, total_pages=70,
            known_chapter_pages={40}, probe_fn=exploding_probe_fn,
        )
        self.assertEqual(boundaries, [(0, 10), (10, 40), (40, 70)])
        self._assert_contiguous(self, boundaries, 0, 70)

    def test_hard_limit_caps_at_next_known_chapter_page_not_total_pages(self):
        # A probe-shifted cut must never be allowed to swallow an entire
        # chapter start -- so hard_limit passed to probe_fn should be the
        # next known chapter page past the cut, not total_pages.
        seen_hard_limits = []

        def recording_probe_fn(end, hard_limit):
            seen_hard_limits.append(hard_limit)
            return end  # no-op shift; only care about what hard_limit was passed

        packed = [(0, 20), (20, 100)]
        resolve_probe_boundaries(
            packed, front_matter_end=0, total_pages=100,
            known_chapter_pages={50}, probe_fn=recording_probe_fn,
        )
        self.assertEqual(seen_hard_limits, [50])


if __name__ == "__main__":
    unittest.main()
