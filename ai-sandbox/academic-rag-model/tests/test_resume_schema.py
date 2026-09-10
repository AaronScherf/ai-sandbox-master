import unittest

from resume_manager.schema import assign_ids, slugify, verify_entry_fields


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify("U.S. Agency for International Development"), "u-s-agency-for-international-development")

    def test_empty_input_falls_back_to_entry(self):
        self.assertEqual(slugify("   "), "entry")


class TestAssignIds(unittest.TestCase):
    def test_disambiguates_duplicate_keys_with_ordinals(self):
        entries = [{"org": "USAID"}, {"org": "USAID"}, {"org": "USAID"}]
        assign_ids(entries, "org")
        self.assertEqual([e["id"] for e in entries], ["usaid-1", "usaid-2", "usaid-3"])

    def test_distinct_keys_get_distinct_slugs(self):
        entries = [{"org": "Acme"}, {"org": "Globex"}]
        assign_ids(entries, "org")
        self.assertEqual([e["id"] for e in entries], ["acme-1", "globex-1"])


class TestVerifyEntryFields(unittest.TestCase):
    def test_clean_entry_has_no_problems(self):
        entry = {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "2022", "bullets": ["Did a thing"],
        }
        raw = "Acme\nEngineer\nNYC\n2020 - 2022\nDid a thing"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"], ["bullets"])
        self.assertEqual(problems, [])

    def test_empty_required_field_is_flagged(self):
        entry = {"id": "acme-1", "org": "Acme", "role": "", "location": "NYC", "start_date": "2020", "end_date": "2022"}
        raw = "Acme\nNYC\n2020 - 2022"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"])
        self.assertTrue(any("role" in p for p in problems))

    def test_untraceable_field_value_is_flagged(self):
        entry = {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "Los Angeles",
            "start_date": "2020", "end_date": "2022",
        }
        raw = "Acme\nEngineer\nNYC\n2020 - 2022"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"])
        self.assertTrue(any("location" in p for p in problems))

    def test_present_end_date_is_never_flagged_as_untraceable(self):
        entry = {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present",
        }
        raw = "Acme\nEngineer\nNYC\n2020"
        problems = verify_entry_fields(entry, raw, ["org", "role", "location", "start_date", "end_date"])
        self.assertEqual(problems, [])

    def test_untraceable_list_item_is_flagged(self):
        entry = {"id": "acme-1", "bullets": ["Did a thing that never appears in the raw text"]}
        raw = "Acme\nEngineer"
        problems = verify_entry_fields(entry, raw, [], ["bullets"])
        self.assertTrue(any("bullets" in p for p in problems))

    def test_mid_word_line_wrap_in_raw_text_is_not_flagged(self):
        # Real, confirmed false positive against the actual resume
        # bootstrap (2026-09-09): the source PDF line-wraps mid-sentence
        # ("...randomized control\ntrial to evaluate..."), and the LLM
        # correctly joins it into flowing prose with a single space. A
        # literal substring check flags this as "invented" even though
        # every word is faithfully preserved.
        entry = {"id": "acme-1", "bullets": ["...randomized control trial to evaluate..."]}
        raw = "...randomized control\ntrial to evaluate..."
        problems = verify_entry_fields(entry, raw, [], ["bullets"])
        self.assertEqual(problems, [])

    def test_non_breaking_space_and_double_spacing_in_raw_text_is_not_flagged(self):
        # Real, confirmed false positive: the source PDF's text layer uses
        # non-breaking spaces and doubled spacing between words in some
        # sections ("Natural\xa0\xa0Language\xa0\xa0Processing"), which the
        # LLM correctly normalizes to single ordinary spaces.
        entry = {"id": "s-1", "category": "x", "items": ["Natural Language Processing"]}
        raw = "Natural\xa0\xa0Language\xa0\xa0Processing"
        problems = verify_entry_fields(entry, raw, [], ["items"])
        self.assertEqual(problems, [])

    def test_capitalization_difference_is_not_flagged(self):
        # Real, confirmed false positive: the LLM capitalized the first
        # letter of an extracted description sentence
        # ("in partnership..." -> "In partnership...") -- faithful
        # content, trivial cosmetic normalization.
        entry = {"id": "a-1", "description": "In partnership with Amnesty International"}
        raw = "Humanity in Action Senior Fellow (in partnership with Amnesty International)"
        problems = verify_entry_fields(entry, raw, ["description"])
        self.assertEqual(problems, [])

    def test_genuinely_fabricated_value_is_still_flagged_despite_normalization(self):
        entry = {"id": "acme-1", "role": "Chief Executive Officer"}
        raw = "Acme\nSenior Engineer\n2020"
        problems = verify_entry_fields(entry, raw, ["role"])
        self.assertTrue(any("role" in p for p in problems))
