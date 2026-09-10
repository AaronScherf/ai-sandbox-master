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


class TestRenderResumePdf(unittest.TestCase):
    def test_writes_a_non_empty_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path)

            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))
