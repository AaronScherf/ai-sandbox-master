import unittest

from agent.literature.transcript import check_quote, normalize, split_pages

MD = (
    "<!-- page 1 -->\n\nWe study cash trans-\nfers in rural Somalia using a panel of 1,200 households.\n\n"
    "<!-- page 2 -->\n\n| Source | DF |\n|---|---|\n| Diagnostic Test | 2 |\n\n"
    "The \u201cdifference-in-differences\u201d estimate is \ufb01rm and **robust**.\n"
)


class TestSplitPages(unittest.TestCase):
    def test_pages_are_keyed_by_marker_number(self):
        pages = split_pages(MD)
        self.assertEqual(sorted(pages), [1, 2])
        self.assertIn("rural Somalia", pages[1])
        self.assertNotIn("<!--", pages[1])

    def test_no_markers_means_no_pages(self):
        self.assertEqual(split_pages("just text"), {})


class TestNormalize(unittest.TestCase):
    def test_folds_ligatures_quotes_dashes_markup_and_hyphens(self):
        self.assertEqual(normalize("The \u201cfirm\u201d \ufb01rm -- **bold**"), normalize('the "firm" firm -- bold'))
        self.assertEqual(normalize("cash trans-\nfers"), normalize("cash transfers"))
        self.assertEqual(normalize("difference-in-differences"), normalize("difference-in-\ndifferences"))


class TestCheckQuote(unittest.TestCase):
    pages = split_pages(MD)

    def test_a_correct_quote_matches_despite_hyphenation_and_spacing(self):
        self.assertIsNone(check_quote("cash transfers in rural Somalia", 1, self.pages))

    def test_matches_across_ligatures_curly_quotes_and_markup(self):
        self.assertIsNone(check_quote('The "difference-in-differences" estimate is firm and robust', 2, self.pages))

    def test_table_text_matches_without_pipes(self):
        self.assertIsNone(check_quote("Diagnostic Test 2", 2, self.pages))

    def test_a_fabricated_quote_is_rejected_with_the_page_named(self):
        msg = check_quote("cash transfers reduced hunger by 40 percent", 1, self.pages)
        self.assertIn("page 1", msg)

    def test_the_right_text_on_the_wrong_page_is_rejected(self):
        self.assertIsNotNone(check_quote("cash transfers in rural Somalia", 2, self.pages))

    def test_a_list_locator_may_span_pages(self):
        self.assertIsNone(check_quote("1,200 households. Source DF", [1, 2], self.pages))

    def test_very_short_or_too_long_quotes_are_rejected(self):
        self.assertIn("at least", check_quote("the", 1, self.pages))
        self.assertIn("at most", check_quote("x" * 301, 1, self.pages))

    def test_bad_locators_are_rejected_in_plain_words(self):
        for bad in (None, 0, 9, "2", True, [], [1, 9], 1.5, [1, True]):
            with self.subTest(bad=bad):
                msg = check_quote("cash transfers in rural Somalia", bad, self.pages)
                self.assertIsNotNone(msg)
                self.assertIn("locator", msg)

    def test_non_text_quote_is_rejected(self):
        self.assertIsNotNone(check_quote(None, 1, self.pages))


if __name__ == "__main__":
    unittest.main()
