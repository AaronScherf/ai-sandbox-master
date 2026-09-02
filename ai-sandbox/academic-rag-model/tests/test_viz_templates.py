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


from viz.templates import spectral_decomposition


class TestSpectralDecompositionTemplate(unittest.TestCase):
    def test_render_returns_four_traces(self):
        fig = spectral_decomposition.render()
        self.assertEqual(len(fig.data), 4)  # 2 eigenvectors x (original + transformed)

    def test_template_metadata(self):
        self.assertIn("spectral decomposition", spectral_decomposition.TEMPLATE.keywords)
        self.assertIs(spectral_decomposition.TEMPLATE.render, spectral_decomposition.render)

    def test_registered_in_global_registry(self):
        from viz.templates import TEMPLATE_REGISTRY
        self.assertIn(spectral_decomposition.TEMPLATE, TEMPLATE_REGISTRY)

    def test_matches_via_full_registry(self):
        from viz.templates import match_template
        self.assertIs(match_template("teach me about spectral decomposition"), spectral_decomposition.TEMPLATE)


if __name__ == "__main__":
    unittest.main()
