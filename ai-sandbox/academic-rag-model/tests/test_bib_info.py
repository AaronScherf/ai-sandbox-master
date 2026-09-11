import unittest

from textbook import bib_info


class TestSanitizeFilename(unittest.TestCase):
    # Real, confirmed incident: a source filename with its own mangled
    # underscore already in it ("Fumio Hayashi_,Princeton _ Princeton
    # University Press") combined with sanitize_filename's own "_"
    # separator to produce "Hayashi__Contents_2007" (double underscore)
    # instead of "Hayashi_Contents_2007".

    def test_collapses_repeated_underscores(self):
        self.assertEqual(bib_info.sanitize_filename("Hayashi_"), "Hayashi")

    def test_collapsed_underscore_does_not_double_up_with_separator(self):
        # Simulates derive_folder_name's own "_".join behavior downstream.
        lastname = bib_info.sanitize_filename("Hayashi_")
        self.assertEqual(f"{lastname}_Contents_2007", "Hayashi_Contents_2007")

    def test_strips_leading_and_trailing_underscores(self):
        self.assertEqual(bib_info.sanitize_filename("_Hayashi_"), "Hayashi")

    def test_normal_input_unaffected(self):
        self.assertEqual(bib_info.sanitize_filename("Bruce E Hansen"), "Bruce_E_Hansen")

    def test_empty_input(self):
        self.assertEqual(bib_info.sanitize_filename(""), "")


class TestExtractBibliographicInfoFromFilename(unittest.TestCase):
    # A Hansen econometrics textbook came out named "UnknownAuthor_..._0000"
    # even though its filename ("HansenEconometrics2022.pdf") had the author
    # and year in it -- there was no tier that ever looked at the filename
    # itself for structured info, only used it wholesale as a last-resort
    # folder name once every other tier came up empty.

    def test_camelcase_filename_recovers_author_title_year(self):
        info = bib_info.extract_bibliographic_info_from_filename("HansenEconometrics2022.pdf")
        self.assertEqual(info["author"], "Hansen")
        self.assertEqual(info["title"], "Econometrics")
        self.assertEqual(info["year"], "2022")

    def test_underscore_separated_filename(self):
        info = bib_info.extract_bibliographic_info_from_filename("/gcs/tmp/Hansen_Econometrics_2022.pdf")
        self.assertEqual(info["author"], "Hansen")
        self.assertEqual(info["title"], "Econometrics")
        self.assertEqual(info["year"], "2022")

    def test_multiword_title_after_author(self):
        info = bib_info.extract_bibliographic_info_from_filename("SimonBlumeMathematicsForEconomists1994.pdf")
        self.assertEqual(info["author"], "Simon")
        self.assertEqual(info["title"], "Blume Mathematics For Economists")
        self.assertEqual(info["year"], "1994")

    def test_single_word_filename_has_no_author_guess(self):
        # No second word to plausibly be a title -- guessing an author here
        # would just be a coin flip against the one word actually being the
        # title, so it's left as a title-only guess instead.
        info = bib_info.extract_bibliographic_info_from_filename("Econometrics2022.pdf")
        self.assertEqual(info["author"], "")
        self.assertEqual(info["title"], "Econometrics")
        self.assertEqual(info["year"], "2022")

    def test_pure_isbn_filename_yields_nothing(self):
        info = bib_info.extract_bibliographic_info_from_filename("9781107577223.pdf")
        self.assertEqual(info, {"title": "", "author": "", "year": ""})

    def test_year_not_matched_inside_longer_digit_run(self):
        # An ISBN can easily contain a "20xx"/"19xx"-shaped substring by
        # coincidence -- must not be misread as a publication year.
        info = bib_info.extract_bibliographic_info_from_filename("Hansen9781107577223.pdf")
        self.assertEqual(info["year"], "")


class TestExtractBibliographicInfoFromFilenameDashSegments(unittest.TestCase):
    # Real bug, caught from a real run (not anticipated in the abstract):
    # the camelCase heuristic above assumes "author is the first word,"
    # which is exactly backwards for the real filenames this pipeline's own
    # input actually uses -- library/ebook-repository-style " -- "-segmented
    # names put the TITLE first. A real Hayashi econometrics book came out
    # with "Econometrics" (its actual title) recorded as the AUTHOR because
    # of this, before it was caught. Both filenames below are real, taken
    # directly from a real conversion run's logs.

    def test_real_hansen_filename_title_then_author(self):
        info = bib_info.extract_bibliographic_info_from_filename(
            "Econometrics -- Bruce E Hansen, 1962- -- Princeton, New Jersey, 2022 -- "
            "Princeton University Press -- isbn13 9780691235899.pdf"
        )
        self.assertEqual(info["title"], "Econometrics")
        self.assertEqual(info["author"], "Bruce E Hansen, 1962-")
        # The publication year (2022) must win over the author's birth
        # year (1962), which appears earlier in the filename.
        self.assertEqual(info["year"], "2022")

    def test_real_hayashi_filename_title_then_author(self):
        info = bib_info.extract_bibliographic_info_from_filename(
            "Econometrics -- Fumio Hayashi -- Princeton University Press -- "
            "Princeton, N.J. -- 2000 -- Princeton University Press -- "
            "isbn13 9780691010182.pdf"
        )
        self.assertEqual(info["title"], "Econometrics")
        self.assertEqual(info["author"], "Fumio Hayashi")
        self.assertEqual(info["year"], "2000")

    def test_last_year_wins_over_an_earlier_birth_year(self):
        info = bib_info.extract_bibliographic_info_from_filename(
            "Some Title -- Some Author, 1930-2010 -- 2015.pdf"
        )
        self.assertEqual(info["year"], "2015")

    def test_dash_segment_convention_takes_priority_over_camelcase(self):
        # A filename with both a "--" separator AND camelCase-looking
        # segments should still use the segment convention (title-then-
        # author), not accidentally fall into the word-splitting path.
        info = bib_info.extract_bibliographic_info_from_filename(
            "SomeTitle -- SomeAuthor -- 2018.pdf"
        )
        self.assertEqual(info["title"], "SomeTitle")
        self.assertEqual(info["author"], "SomeAuthor")
        self.assertEqual(info["year"], "2018")


class TestFilenameBibInfoOnlyFillsGaps(unittest.TestCase):
    # merge_bibliographic_info() only fills blank fields -- confirms the
    # filename tier can't clobber a real title/author/year already found
    # from the PDF's own metadata or its markdown title page.

    def test_filename_info_does_not_override_existing_fields(self):
        primary = {"title": "Real Title From Markdown", "author": "", "year": ""}
        filename_info = bib_info.extract_bibliographic_info_from_filename("Hansen_Econometrics_2022.pdf")
        merged = bib_info.merge_bibliographic_info(primary, filename_info)
        self.assertEqual(merged["title"], "Real Title From Markdown")
        self.assertEqual(merged["author"], "Hansen")
        self.assertEqual(merged["year"], "2022")


class TestDeriveFolderName(unittest.TestCase):
    # This is the exact naming rule convert_textbook.py used to have inlined
    # in process_one_pdf -- pulled out here so describe_images.py's naming-
    # reconciliation pass (over already-converted books) can reuse the
    # identical rule instead of risking the two drifting apart.

    def test_descriptive_info_produces_author_title_year(self):
        bib = {"title": "Econometrics", "author": "Bruce Hansen", "year": "2022"}
        name = bib_info.derive_folder_name(bib, "irrelevant.pdf")
        self.assertEqual(name, "Hansen_Econometrics_2022")

    def test_title_only_falls_back_to_unknown_author_and_year(self):
        bib = {"title": "Econometrics", "author": "", "year": ""}
        name = bib_info.derive_folder_name(bib, "irrelevant.pdf")
        self.assertEqual(name, "UnknownAuthor_Econometrics_0000")

    def test_no_usable_info_falls_back_to_whole_sanitized_filename(self):
        bib = {"title": "", "author": "", "year": ""}
        name = bib_info.derive_folder_name(bib, "/gcs/tmp/some raw scan.pdf")
        self.assertEqual(name, "some_raw_scan")

    def test_blank_title_falls_back_to_filename_stem_for_title_part(self):
        bib = {"title": "", "author": "Bruce Hansen", "year": "2022"}
        name = bib_info.derive_folder_name(bib, "/gcs/tmp/Econometrics.pdf")
        self.assertEqual(name, "Hansen_Econometrics_2022")


if __name__ == "__main__":
    unittest.main()
