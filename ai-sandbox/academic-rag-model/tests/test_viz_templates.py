import unittest
from unittest.mock import patch

from viz.templates import Template, match_template


def _fake_template(name="Fake", keywords=("fake concept", "fake alias")):
    return Template(name=name, keywords=list(keywords), render=lambda: "figure")


class TestMatchTemplate(unittest.TestCase):
    def test_matches_exact_keyword(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIs(match_template("fake concept"), template)

    def test_matches_keyword_as_substring_case_insensitively(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIs(match_template("Teach me about Fake Concept please"), template)

    def test_matches_alias_keyword(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIs(match_template("what is a fake alias"), template)

    def test_no_match_returns_none(self):
        template = _fake_template()
        with patch("viz.templates.TEMPLATE_REGISTRY", [template]):
            self.assertIsNone(match_template("totally unrelated topic"))

    def test_empty_registry_returns_none(self):
        with patch("viz.templates.TEMPLATE_REGISTRY", []):
            self.assertIsNone(match_template("anything"))


if __name__ == "__main__":
    unittest.main()
