import unittest

from textbook.toc_repair import (
    chapters_to_review_template,
    extract_heading_outline,
    find_large_heading_gaps,
    parse_classification_response,
    parse_table_repair_response,
    splice_repaired_table,
)


class TestExtractHeadingOutline(unittest.TestCase):
    def test_pairs_each_heading_with_its_nearest_preceding_page_tag(self):
        text = (
            "<!-- page 11 -->\n\n# TilE REAL AND COMPLEX NUMBER SYSTEMS\n\nbody\n\n"
            "<!-- page 13 -->\n\n## ORDERED SETS\n\nmore body\n"
        )
        outline = extract_heading_outline(text)
        self.assertEqual(
            outline.splitlines(),
            ["[page 11] # TilE REAL AND COMPLEX NUMBER SYSTEMS", "[page 13] ## ORDERED SETS"],
        )

    def test_heading_before_any_page_tag_is_marked_unknown(self):
        text = "# Title Page\n\n<!-- page 1 -->\n\n# Chapter One\n"
        outline = extract_heading_outline(text)
        self.assertEqual(outline.splitlines()[0], "[page ?] # Title Page")

    def test_no_headings_returns_empty_string(self):
        self.assertEqual(extract_heading_outline("just some prose, no headings"), "")


class TestFindLargeHeadingGaps(unittest.TestCase):
    # Real case this exists for (Hayashi): a 100+ page span with zero
    # headings at all meant three real chapters' own headings never
    # converted -- classification silently omitted them rather than
    # guessing, since there was nothing to point at. Flagging the gap
    # lets a human check the source PDF for a bad scan or missing pages
    # instead of just noticing chapters are missing after the fact.
    def test_finds_a_gap_exceeding_the_threshold(self):
        outline = "[page 10] # One\n[page 20] # Two\n[page 150] # Three\n[page 160] # Four\n"
        self.assertEqual(find_large_heading_gaps(outline), [(20, 150)])

    def test_no_gap_when_all_within_threshold(self):
        outline = "[page 10] # One\n[page 20] # Two\n[page 30] # Three\n"
        self.assertEqual(find_large_heading_gaps(outline), [])

    def test_ignores_unknown_page_markers(self):
        outline = "[page 10] # One\n[page ?] # Untagged\n[page 150] # Two\n"
        self.assertEqual(find_large_heading_gaps(outline), [(10, 150)])

    def test_empty_outline_returns_empty_list(self):
        self.assertEqual(find_large_heading_gaps(""), [])

    def test_respects_a_custom_threshold(self):
        outline = "[page 10] # One\n[page 20] # Two\n"
        self.assertEqual(find_large_heading_gaps(outline, min_gap_pages=5), [(10, 20)])
        self.assertEqual(find_large_heading_gaps(outline, min_gap_pages=20), [])


class TestParseClassificationResponse(unittest.TestCase):
    def test_parses_valid_array(self):
        response = '[{"title": "Vector Spaces", "page": 14}, {"title": "Logic", "page": 34}]'
        chapters = parse_classification_response(response)
        self.assertEqual(chapters, [{"title": "Vector Spaces", "page": 14}, {"title": "Logic", "page": 34}])

    def test_malformed_json_returns_empty_list(self):
        self.assertEqual(parse_classification_response("not json"), [])

    def test_non_list_returns_empty_list(self):
        self.assertEqual(parse_classification_response('{"title": "x", "page": 1}'), [])

    def test_drops_entries_missing_required_keys_or_wrong_types(self):
        response = (
            '[{"title": "Good", "page": 3}, {"title": "Bad"}, {"page": 5}, '
            '{"title": 7, "page": 8}, {"title": "AlsoBad", "page": "nine"}]'
        )
        chapters = parse_classification_response(response)
        self.assertEqual(chapters, [{"title": "Good", "page": 3}])


class TestChaptersToReviewTemplate(unittest.TestCase):
    def test_includes_book_name_review_warning_and_chapter_lines(self):
        content = chapters_to_review_template(
            "Sample_Book", [{"title": "Vector Spaces", "page": 14}, {"title": "Logic", "page": 34}]
        )
        self.assertIn("Sample_Book", content)
        self.assertIn("AI-generated", content)
        self.assertIn("review", content.lower())
        self.assertIn("Vector Spaces | 14", content)
        self.assertIn("Logic | 34", content)


class TestParseTableRepairResponse(unittest.TestCase):
    def test_parses_valid_response(self):
        response = (
            '{"toc_start_marker": "# Contents", "toc_end_marker": "some last line", '
            '"repaired_table_markdown": "| clean | table |"}'
        )
        result = parse_table_repair_response(response)
        self.assertEqual(result, {
            "toc_start_marker": "# Contents",
            "toc_end_marker": "some last line",
            "repaired_table_markdown": "| clean | table |",
        })

    def test_malformed_json_returns_none(self):
        self.assertIsNone(parse_table_repair_response("not json"))

    def test_missing_keys_returns_none(self):
        self.assertIsNone(parse_table_repair_response('{"toc_start_marker": "x"}'))

    def test_non_string_values_returns_none(self):
        response = '{"toc_start_marker": 1, "toc_end_marker": "y", "repaired_table_markdown": "z"}'
        self.assertIsNone(parse_table_repair_response(response))


class TestSpliceRepairedTable(unittest.TestCase):
    def test_replaces_the_verbatim_span_with_repaired_markdown(self):
        text = "before\n\n# Contents\n\ngarbled table stuff\nmore garbage\n\nafter"
        repair = {
            "toc_start_marker": "# Contents",
            "toc_end_marker": "more garbage",
            "repaired_table_markdown": "# Contents\n\n| Clean | Table |",
        }
        result = splice_repaired_table(text, repair)
        self.assertEqual(result, "before\n\n# Contents\n\n| Clean | Table |\n\nafter")

    def test_returns_none_when_start_marker_not_found(self):
        text = "before\n\nsome text\n\nafter"
        repair = {"toc_start_marker": "NOT PRESENT", "toc_end_marker": "some text", "repaired_table_markdown": "x"}
        self.assertIsNone(splice_repaired_table(text, repair))

    def test_returns_none_when_end_marker_not_found_after_start(self):
        text = "before\n\n# Contents\n\nafter"
        repair = {"toc_start_marker": "# Contents", "toc_end_marker": "NOT PRESENT", "repaired_table_markdown": "x"}
        self.assertIsNone(splice_repaired_table(text, repair))

    def test_returns_none_when_end_marker_appears_only_before_start(self):
        text = "end-marker-text\n\n# Contents\n\nafter"
        repair = {
            "toc_start_marker": "# Contents", "toc_end_marker": "end-marker-text", "repaired_table_markdown": "x",
        }
        self.assertIsNone(splice_repaired_table(text, repair))


if __name__ == "__main__":
    unittest.main()
