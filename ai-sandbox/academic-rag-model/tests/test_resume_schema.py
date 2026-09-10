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
