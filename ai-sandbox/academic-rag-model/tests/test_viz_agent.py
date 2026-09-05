import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

from viz.templates import Template
from viz.viz_agent import VizResult, generate_visualization, _slugify


def _fake_template(fig, keywords=("fake concept",)):
    return Template(name="Fake", keywords=list(keywords), render=lambda: fig)


class TestGenerateVisualizationTemplatePath(unittest.TestCase):
    def test_template_match_writes_html_and_returns_result(self):
        fake_fig = MagicMock()
        fake_fig.to_html.return_value = "<div>fake plot</div>"
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp, course="math-camp")
        fake_fig.to_html.assert_called_once()
        self.assertEqual(result.source, "template")
        self.assertEqual(result.title, "Fake")
        self.assertEqual(result.fragment_html, "<div>fake plot</div>")
        self.assertTrue(result.html_path.startswith(os.path.join(tmp, ".viz", "math-camp")))
        self.assertTrue(result.html_path.endswith(".html"))

    def test_to_html_called_with_inline_plotlyjs_and_fragment_mode(self):
        fake_fig = MagicMock()
        fake_fig.to_html.return_value = "<div>fake plot</div>"
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                generate_visualization("fake concept", academic_hub_root=tmp)
        _, kwargs = fake_fig.to_html.call_args
        self.assertEqual(kwargs["include_plotlyjs"], "inline")
        self.assertFalse(kwargs["full_html"])

    def test_output_file_is_wrapped_but_fragment_html_is_not(self):
        fake_fig = MagicMock()
        fake_fig.to_html.return_value = "<div>fake plot</div>"
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp)
            with open(result.html_path, "r", encoding="utf-8") as f:
                written = f.read()
        self.assertIn("<html>", written)
        self.assertIn("<div>fake plot</div>", written)
        self.assertNotIn("<html>", result.fragment_html)

    def test_course_none_uses_uncategorized_folder(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp, course=None)
        self.assertIn("uncategorized", result.html_path)

    def test_slug_derived_from_concept(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig, keywords=("spectral decomposition",))
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("Spectral Decomposition!", academic_hub_root=tmp)
        self.assertTrue(os.path.basename(result.html_path).startswith("spectral-decomposition"))

    def test_no_template_match_returns_none_for_now(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=None):
                result = generate_visualization("unmatched concept", academic_hub_root=tmp)
        self.assertIsNone(result)

    def test_slug_is_capped_at_a_bounded_length(self):
        long_concept = "why does the sequence eventually converge to a finite limit " * 5
        self.assertLessEqual(len(_slugify(long_concept)), 80)

    def test_very_long_concept_through_template_path_returns_none_instead_of_raising(self):
        """Reproduces the original bug end-to-end: a long question
        (~260+ characters) through the template-match path used to
        overflow Windows's per-component filename length limit inside
        fig.write_html(), raising an uncaught OSError that would
        otherwise destroy an already-paid-for Gemini answer. Uses a REAL
        go.Figure() (not a MagicMock) so write_html() actually touches
        the filesystem. This exercises the length cap alone (the
        176-char concept below produces an 80-char capped slug, well
        under any filename limit)."""
        long_concept = (
            "why does the sequence defined by the following complicated recursive "
            "relation involving nested summations and alternating signs eventually "
            "converge to a finite limit as n approaches infinity"
        )
        self.assertGreater(len(long_concept), 150)
        real_template = Template(name="Fake", keywords=[long_concept.lower()], render=lambda: go.Figure())
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=real_template):
                result = generate_visualization(long_concept, academic_hub_root=tmp)
        self.assertIsNotNone(result)
        self.assertEqual(result.source, "template")

    def test_template_render_or_write_failure_is_isolated_and_returns_none(self):
        """Isolates the error-handling half of the fix from the length
        cap: even with an already-short, already-capped slug, a
        filesystem-level failure inside the template-match branch
        (os.makedirs / template.render() / fig.write_html()) must be
        caught and surfaced as None, not propagate and destroy an
        already-paid-for answer. Forces the same OSError the original
        bug hit by patching _slugify to return an over-long slug
        directly, bypassing the cap so the try/except is what's under
        test here, not the cap."""
        real_template = Template(name="Fake", keywords=["fake concept"], render=lambda: go.Figure())
        overlong_slug = "x" * 300
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=real_template), \
                 patch("viz.viz_agent._slugify", return_value=overlong_slug):
                result = generate_visualization("fake concept", academic_hub_root=tmp)
        self.assertIsNone(result)


class TestGenerateVisualizationFallbackPath(unittest.TestCase):
    def test_no_template_match_falls_back_to_llm(self):
        fake_result = VizResult(
            html_path="/x/y.html", title="unknown concept", source="llm_fallback",
            fragment_html="<div>x</div>",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=fake_result) as mock_llm:
                result = generate_visualization("unknown concept", context="ctx", academic_hub_root=tmp, course="math-camp")
        mock_llm.assert_called_once()
        args, kwargs = mock_llm.call_args
        self.assertEqual(args[0], "unknown concept")
        self.assertEqual(args[1], "ctx")
        self.assertEqual(result, fake_result)

    def test_fallback_receives_the_same_output_path_the_template_path_would_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=None) as mock_llm:
                generate_visualization("unknown concept", academic_hub_root=tmp, course="math-camp")
        args, kwargs = mock_llm.call_args
        output_path = args[2]
        self.assertTrue(output_path.startswith(os.path.join(tmp, ".viz", "math-camp")))

    def test_fallback_failure_propagates_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=None), \
                 patch("viz.llm_fallback.generate_via_llm", return_value=None):
                result = generate_visualization("unknown concept", academic_hub_root=tmp)
        self.assertIsNone(result)


class TestWrapFragment(unittest.TestCase):
    def test_wraps_fragment_in_minimal_html_shell(self):
        from viz.viz_agent import _wrap_fragment
        wrapped = _wrap_fragment("<div>plot</div>")
        self.assertIn("<html>", wrapped)
        self.assertIn("<div>plot</div>", wrapped)


if __name__ == "__main__":
    unittest.main()
