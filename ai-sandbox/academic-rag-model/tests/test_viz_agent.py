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
            with patch("viz.viz_agent.match_template", return_value=None):
                result = generate_visualization("unmatched concept", academic_hub_root=tmp)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
