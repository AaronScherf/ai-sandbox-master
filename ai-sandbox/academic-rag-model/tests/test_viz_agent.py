import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from viz.templates import Template
from viz.viz_agent import VizResult, generate_visualization


def _fake_template(fig, keywords=("fake concept",)):
    return Template(name="Fake", keywords=list(keywords), render=lambda: fig)


class TestGenerateVisualizationTemplatePath(unittest.TestCase):
    def test_template_match_writes_html_and_returns_result(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                result = generate_visualization("fake concept", academic_hub_root=tmp, course="math-camp")
        fake_fig.write_html.assert_called_once()
        self.assertEqual(result.source, "template")
        self.assertEqual(result.title, "Fake")
        self.assertTrue(result.html_path.startswith(os.path.join(tmp, ".viz", "math-camp")))
        self.assertTrue(result.html_path.endswith(".html"))

    def test_write_html_called_with_inline_plotlyjs(self):
        fake_fig = MagicMock()
        template = _fake_template(fake_fig)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("viz.viz_agent.match_template", return_value=template):
                generate_visualization("fake concept", academic_hub_root=tmp)
        _, kwargs = fake_fig.write_html.call_args
        self.assertEqual(kwargs["include_plotlyjs"], "inline")

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


class TestGenerateVisualizationFallbackPath(unittest.TestCase):
    def test_no_template_match_falls_back_to_llm(self):
        fake_result = VizResult(html_path="/x/y.html", title="unknown concept", source="llm_fallback")
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


if __name__ == "__main__":
    unittest.main()
