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


import math

from viz.templates import gradient_descent, distributions, convergence


class TestGradientDescentTemplate(unittest.TestCase):
    def test_render_returns_two_traces(self):
        fig = gradient_descent.render()
        self.assertEqual(len(fig.data), 2)  # contour surface + descent path

    def test_template_metadata(self):
        self.assertIn("gradient descent", gradient_descent.TEMPLATE.keywords)


class TestDistributionsTemplate(unittest.TestCase):
    def test_render_returns_two_traces(self):
        fig = distributions.render()
        self.assertEqual(len(fig.data), 2)  # binomial bars + normal curve

    def test_binomial_pmf_sums_to_one(self):
        _, pmf = distributions._binomial_pmf(n=40, p=0.5)
        self.assertAlmostEqual(sum(pmf), 1.0, places=6)

    def test_template_metadata(self):
        self.assertIn("central limit theorem", distributions.TEMPLATE.keywords)


class TestConvergenceTemplate(unittest.TestCase):
    def test_render_returns_two_traces(self):
        fig = convergence.render()
        self.assertEqual(len(fig.data), 2)  # partial sums + limit line

    def test_template_metadata(self):
        self.assertIn("series convergence", convergence.TEMPLATE.keywords)
        # The bare, over-broad "convergence"/"divergence" keywords were
        # removed (see TestConvergenceTemplateNearMisses below) -- neither
        # should reappear as a standalone keyword.
        self.assertNotIn("convergence", convergence.TEMPLATE.keywords)
        self.assertNotIn("divergence", convergence.TEMPLATE.keywords)

    def test_genuine_match_via_full_registry(self):
        from viz.templates import match_template
        self.assertIs(match_template("explain series convergence"), convergence.TEMPLATE)
        self.assertIs(match_template("does this series converge?"), convergence.TEMPLATE)
        self.assertIs(match_template("what is an alternating series"), convergence.TEMPLATE)


class TestConvergenceTemplateNearMisses(unittest.TestCase):
    """Near-miss tests against the REAL, full TEMPLATE_REGISTRY (no
    mocking) -- these four phrasings are all real over-matches the
    original bare "convergence"/"divergence" keywords caused, verified
    against this exact registry. None of them are about the alternating
    harmonic series, so none should fire the convergence template."""

    def test_convergence_in_distribution_does_not_match_series_convergence(self):
        from viz.templates import match_template
        result = match_template("what is convergence in distribution?")
        self.assertIsNot(result, convergence.TEMPLATE)

    def test_convergence_in_probability_does_not_match_series_convergence(self):
        from viz.templates import match_template
        result = match_template("explain convergence in probability")
        self.assertIsNot(result, convergence.TEMPLATE)

    def test_em_algorithm_convergence_does_not_match_series_convergence(self):
        from viz.templates import match_template
        result = match_template("does the EM algorithm converge? discuss its convergence")
        self.assertIsNot(result, convergence.TEMPLATE)

    def test_divergence_theorem_does_not_match_series_convergence(self):
        from viz.templates import match_template
        result = match_template("explain the divergence theorem")
        self.assertIsNot(result, convergence.TEMPLATE)


class TestAllTemplatesRegistered(unittest.TestCase):
    def test_registry_has_four_templates(self):
        from viz.templates import TEMPLATE_REGISTRY
        self.assertEqual(len(TEMPLATE_REGISTRY), 4)


if __name__ == "__main__":
    unittest.main()
