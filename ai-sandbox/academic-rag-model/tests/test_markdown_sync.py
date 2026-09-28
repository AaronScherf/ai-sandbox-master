import unittest

from resume_manager.markdown_sync import compute_yaml_hash, export_to_markdown, import_from_markdown

_RESUME = {
    "contact": {
        "name": "Aaron Scherf", "location": "New York, NY, USA", "email": "a@x.com",
        "linkedin_url": "https://linkedin.com/in/a", "github_url": "https://github.com/a",
        "website_url": "https://a.dev",
    },
    "work_experience": [
        {
            "id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present",
            "bullets": ["Grew revenue 30%", "Shipped a new feature to production"],
        },
        {
            "id": "acme-2", "org": "Acme", "role": "Senior Engineer", "location": "NYC",
            "start_date": "Not specified", "end_date": "Not specified",
            "bullets": ["Led a small team"],
        },
    ],
    "education": [
        {
            "id": "state-u-1", "institution": "State U", "degree": "BS", "gpa": "3.9",
            "location": "TX", "start_date": "2016", "end_date": "2020", "thesis": "Not specified",
        },
    ],
    "awards": [{"name": "Some Award", "description": "For doing things", "date": "2019"}],
    "publications": [
        {"title": "A Paper", "date": "2021", "venue": "A Venue", "link": "Not specified"},
        {"title": "Another Paper", "date": "2022", "venue": "Another Venue", "link": "https://example.com/paper"},
    ],
    "skills": [
        {"category": "Programming", "items": ["Python", "R"]},
        {"category": "Languages", "items": ["Spanish"]},
    ],
}


class TestRoundTrip(unittest.TestCase):
    def test_full_resume_round_trips_exactly(self):
        markdown = export_to_markdown(_RESUME)
        result = import_from_markdown(markdown)
        self.assertEqual(result, _RESUME)

    def test_work_experience_ids_are_preserved(self):
        markdown = export_to_markdown(_RESUME)
        result = import_from_markdown(markdown)
        self.assertEqual([e["id"] for e in result["work_experience"]], ["acme-1", "acme-2"])

    def test_duplicate_org_entries_stay_distinct(self):
        markdown = export_to_markdown(_RESUME)
        result = import_from_markdown(markdown)
        self.assertEqual(len(result["work_experience"]), 2)
        self.assertEqual(result["work_experience"][0]["bullets"], ["Grew revenue 30%", "Shipped a new feature to production"])
        self.assertEqual(result["work_experience"][1]["bullets"], ["Led a small team"])

    def test_missing_optional_category_round_trips_as_empty_list(self):
        resume = {**_RESUME, "publications": []}
        markdown = export_to_markdown(resume)
        result = import_from_markdown(markdown)
        self.assertEqual(result["publications"], [])

    def test_hash_embedded_and_stripped_on_import(self):
        markdown = export_to_markdown(_RESUME, embed_hash=True)
        self.assertIn("resume-master-yaml-hash:", markdown.splitlines()[0])
        result = import_from_markdown(markdown)
        self.assertEqual(result, _RESUME)

    def test_stray_unrecognized_text_does_not_crash_import(self):
        markdown = export_to_markdown(_RESUME) + "\n\nSome scratch note to self that isn't structured data.\n"
        result = import_from_markdown(markdown)
        self.assertEqual(result["contact"]["name"], "Aaron Scherf")


class TestComputeYamlHash(unittest.TestCase):
    def test_same_resume_produces_the_same_hash(self):
        self.assertEqual(compute_yaml_hash(_RESUME), compute_yaml_hash(_RESUME))

    def test_different_resume_produces_a_different_hash(self):
        changed = {**_RESUME, "contact": {**_RESUME["contact"], "name": "Someone Else"}}
        self.assertNotEqual(compute_yaml_hash(_RESUME), compute_yaml_hash(changed))


class TestExportFormat(unittest.TestCase):
    def test_id_marker_immediately_follows_entry_heading(self):
        markdown = export_to_markdown(_RESUME)
        self.assertIn("### Acme — Engineer\n<!-- id: acme-1 -->", markdown)

    def test_not_specified_placeholder_is_shown_not_hidden(self):
        # Deliberately different from render.py's PDF-facing output: this
        # is a data-editing view, so the real stored value (even a
        # placeholder) should be visible and editable, not hidden.
        markdown = export_to_markdown(_RESUME)
        self.assertIn("Thesis: Not specified", markdown)
