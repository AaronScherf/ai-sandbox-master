import unittest
from unittest.mock import patch

from resume_manager.normalize import extract_resume_schema, verify_extraction

_VALID_YAML_RESPONSE = """
contact:
  name: Aaron Scherf
  location: USA
  email: a@example.com
  linkedin_url: https://linkedin.com/in/a
  github_url: https://github.com/a
  website_url: https://a.dev
work_experience:
  - org: Acme Corp
    role: Engineer
    location: NYC
    start_date: "2020"
    end_date: Present
    bullets:
      - Did a thing
education: []
awards: []
publications: []
skills: []
"""


class TestExtractResumeSchema(unittest.TestCase):
    @patch("resume_manager.normalize.call_ollama", return_value=_VALID_YAML_RESPONSE)
    def test_parses_valid_yaml_response(self, mock_call):
        result = extract_resume_schema("raw text", model="qwen2.5:7b-instruct")
        self.assertEqual(result["contact"]["name"], "Aaron Scherf")
        self.assertEqual(result["work_experience"][0]["org"], "Acme Corp")

    @patch("resume_manager.normalize.call_ollama", return_value="```yaml\n" + _VALID_YAML_RESPONSE + "```")
    def test_strips_code_fence_before_parsing(self, mock_call):
        result = extract_resume_schema("raw text")
        self.assertEqual(result["contact"]["name"], "Aaron Scherf")

    @patch("resume_manager.normalize.call_ollama", return_value=None)
    def test_returns_none_when_ollama_call_fails(self, mock_call):
        self.assertIsNone(extract_resume_schema("raw text"))

    @patch("resume_manager.normalize.call_ollama", return_value="not: [valid: yaml: at all")
    def test_returns_none_on_invalid_yaml(self, mock_call):
        self.assertIsNone(extract_resume_schema("raw text"))


class TestVerifyExtraction(unittest.TestCase):
    def test_clean_extraction_has_no_problems(self):
        raw = (
            "Acme Corp\nEngineer\nNYC\n2020\nDid a thing\n"
            "Aaron Scherf\nUSA\na@example.com\n"
            "https://linkedin.com/in/a\nhttps://github.com/a\nhttps://a.dev"
        )
        parsed = {
            "contact": {
                "name": "Aaron Scherf", "location": "USA", "email": "a@example.com",
                "linkedin_url": "https://linkedin.com/in/a", "github_url": "https://github.com/a",
                "website_url": "https://a.dev",
            },
            "work_experience": [{
                "id": "acme-1", "org": "Acme Corp", "role": "Engineer", "location": "NYC",
                "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
            }],
            "education": [], "awards": [], "publications": [], "skills": [],
        }
        self.assertEqual(verify_extraction(parsed, raw), [])

    def test_untraceable_field_is_flagged(self):
        raw = "Acme Corp\nEngineer\nNYC\n2020"
        parsed = {
            "contact": {
                "name": "", "location": "", "email": "", "linkedin_url": "", "github_url": "", "website_url": "",
            },
            "work_experience": [{
                "id": "acme-1", "org": "Acme Corp", "role": "Engineer", "location": "Los Angeles",
                "start_date": "2020", "end_date": "Present", "bullets": [],
            }],
            "education": [], "awards": [], "publications": [], "skills": [],
        }
        problems = verify_extraction(parsed, raw)
        self.assertTrue(any("location" in p for p in problems))
