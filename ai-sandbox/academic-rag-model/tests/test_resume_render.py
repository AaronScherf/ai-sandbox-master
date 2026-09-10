import os
import tempfile
import unittest

from resume_manager.render import build_markdown, render_resume_pdf

_RESUME = {
    "contact": {
        "name": "Aaron Scherf", "location": "USA", "email": "a@x.com",
        "linkedin_url": "https://linkedin.com/in/a", "github_url": "https://github.com/a",
        "website_url": "https://a.dev",
    },
    "work_experience": [{
        "org": "Acme", "role": "Engineer", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
    }],
    "education": [{
        "institution": "State U", "degree": "BS", "gpa": "3.9", "location": "TX",
        "start_date": "2016", "end_date": "2020", "thesis": None,
    }],
    "awards": [{"name": "Award", "description": "For doing things", "date": "2019"}],
    "publications": [{"title": "A Paper", "date": "2021", "venue": "A Venue", "link": None}],
    "skills": [{"category": "Programming", "items": ["Python", "R"]}],
}


class TestBuildMarkdown(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(build_markdown(_RESUME), build_markdown(_RESUME))

    def test_includes_every_category(self):
        markdown_text = build_markdown(_RESUME)
        for expected in ["Aaron Scherf", "Acme", "State U", "Award", "A Paper", "Python"]:
            self.assertIn(expected, markdown_text)

    def test_missing_optional_category_is_omitted_cleanly(self):
        resume = {**_RESUME, "publications": []}
        markdown_text = build_markdown(resume)
        self.assertNotIn("Research Presentations", markdown_text)

    def test_not_specified_contact_fields_render_as_blank(self):
        # Real, confirmed request (2026-09-10): a genuinely-missing field
        # should render as nothing at all, not the literal placeholder
        # text -- the placeholder is only meant for the YAML data layer.
        resume = {
            **_RESUME,
            "contact": {
                "name": "Aaron Scherf", "location": "Not specified", "email": "Not specified",
                "linkedin_url": "Not specified", "github_url": "Not specified", "website_url": "Not specified",
            },
        }
        markdown_text = build_markdown(resume)
        self.assertNotIn("Not specified", markdown_text)
        self.assertIn("Aaron Scherf", markdown_text)

    def test_work_experience_with_both_dates_not_specified_omits_the_parenthetical(self):
        resume = {**_RESUME, "work_experience": [{
            "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "Not specified", "end_date": "Not specified", "bullets": ["Did a thing"],
        }]}
        markdown_text = build_markdown(resume)
        self.assertNotIn("Not specified", markdown_text)
        self.assertIn("### Acme — Engineer", markdown_text)
        # No dangling empty parenthetical or stray dash left behind.
        self.assertNotIn("()", markdown_text)
        self.assertNotIn("( – )", markdown_text)

    def test_work_experience_present_end_date_still_renders_normally(self):
        # "Present" is real content, not a placeholder -- must not be
        # blanked out by the same logic.
        markdown_text = build_markdown(_RESUME)
        self.assertIn("(2020 – Present)", markdown_text)

    def test_education_not_specified_gpa_and_thesis_render_as_blank(self):
        resume = {**_RESUME, "education": [{
            "institution": "State U", "degree": "BS", "gpa": "Not specified", "location": "TX",
            "start_date": "2016", "end_date": "2020", "thesis": "Not specified",
        }]}
        markdown_text = build_markdown(resume)
        self.assertNotIn("Not specified", markdown_text)
        self.assertNotIn("GPA:", markdown_text)
        self.assertNotIn("Thesis:", markdown_text)
        self.assertIn("BS", markdown_text)

    def test_publication_not_specified_link_renders_as_blank(self):
        resume = {**_RESUME, "publications": [
            {"title": "A Paper", "date": "2021", "venue": "A Venue", "link": "Not specified"},
        ]}
        markdown_text = build_markdown(resume)
        self.assertNotIn("Not specified", markdown_text)
        self.assertNotIn("[link]", markdown_text)


class TestRenderResumePdf(unittest.TestCase):
    def test_writes_a_non_empty_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path)

            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))
