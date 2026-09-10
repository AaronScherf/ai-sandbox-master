import unittest

from resume_manager.llm_yaml import parse_llm_yaml


class TestParseLlmYaml(unittest.TestCase):
    def test_parses_plain_yaml(self):
        self.assertEqual(parse_llm_yaml("name: Aaron\nrole: Engineer"), {"name": "Aaron", "role": "Engineer"})

    def test_strips_code_fence(self):
        self.assertEqual(parse_llm_yaml("```yaml\nname: Aaron\n```"), {"name": "Aaron"})

    def test_returns_none_on_unrecoverable_invalid_yaml(self):
        self.assertIsNone(parse_llm_yaml("not: [valid: yaml: at all"))

    def test_bare_dash_placeholder_is_quoted_not_a_parse_failure(self):
        # Real, confirmed pattern from a live Ollama response (2026-09-09):
        # the model wrote "location: -" meaning "no value", which raw
        # yaml.safe_load rejects ("sequence entries are not allowed
        # here") because a bare "-" at that position is a sequence-item
        # marker, not a scalar. Sanitized rather than treated as an
        # unrecoverable failure -- retrying the whole slow CPU-only
        # Ollama call for a one-token placeholder is wasteful.
        text = "org: Acme\nlocation: -\nrole: Engineer"
        result = parse_llm_yaml(text)
        self.assertEqual(result, {"org": "Acme", "location": "-", "role": "Engineer"})

    def test_bare_dash_placeholder_inside_nested_mapping(self):
        text = "work_experience:\n  - org: Acme\n    location: -\n    role: Engineer"
        result = parse_llm_yaml(text)
        self.assertEqual(result["work_experience"][0]["location"], "-")

    def test_real_multi_field_response_with_dash_placeholders_parses(self):
        # The exact shape of the real failing response, trimmed to the
        # fields that triggered it.
        text = (
            "contact:\n"
            "  name: Aaron Scherf\n"
            "  location: -\n"
            "  email: -\n"
            "publications:\n"
            "  - title: A Paper\n"
            "    link: -\n"
        )
        result = parse_llm_yaml(text)
        self.assertEqual(result["contact"]["location"], "-")
        self.assertEqual(result["publications"][0]["link"], "-")
