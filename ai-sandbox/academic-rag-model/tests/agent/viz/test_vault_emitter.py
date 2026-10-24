import os
import tempfile
import unittest

from agent.viz.vault_emitter import VaultAsset, emit_from_viz_result, emit_vault_asset
from agent.viz.viz_agent import VizResult


_FRAGMENT = (
    '<div style="height:100%; width:100%;">'
    '<script charset="utf-8" src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>'
    '<div id="plot-abc"></div>'
    "<script>Plotly.newPlot('plot-abc', [], {});</script>"
    "</div>"
)


class TestEmitVaultAssetWritesBarePartial(unittest.TestCase):
    def test_written_file_matches_fragment_exactly_no_wrapping(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
                slug="testing-trinity",
            )
            with open(asset.div_path, "r", encoding="utf-8") as f:
                written = f.read()
        self.assertEqual(written, _FRAGMENT)

    def test_no_full_document_boilerplate_in_written_file_or_fragment(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
                slug="testing-trinity",
            )
            with open(asset.div_path, "r", encoding="utf-8") as f:
                written = f.read()
        for boilerplate in ("<!DOCTYPE", "<html", "<head", "<body"):
            self.assertNotIn(boilerplate, written)


class TestSlugToFilenameConvention(unittest.TestCase):
    def test_asset_written_under_assets_subdir_with_div_suffix(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
                slug="testing-trinity",
            )
        expected = os.path.join(
            hub_root, "academic_notes", "econometrics", "summaries", "assets", "testing-trinity_div.html"
        )
        self.assertEqual(asset.div_path, expected)

    def test_creates_assets_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/microecon/summaries",
                slug="indifference-curves",
            )
            self.assertTrue(os.path.isfile(asset.div_path))


class TestVaultRelativePath(unittest.TestCase):
    def test_relative_path_is_posix_style_and_hub_rooted(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
                slug="testing-trinity",
            )
        self.assertEqual(
            asset.vault_relative_path,
            "academic_notes/econometrics/summaries/assets/testing-trinity_div.html",
        )
        self.assertNotIn("\\", asset.vault_relative_path)


class TestDataviewSnippetShape(unittest.TestCase):
    def setUp(self):
        self.hub_root_ctx = tempfile.TemporaryDirectory()
        self.hub_root = self.hub_root_ctx.name
        self.asset = emit_vault_asset(
            fragment_html=_FRAGMENT,
            academic_hub_root=self.hub_root,
            note_dir="academic_notes/econometrics/summaries",
            slug="testing-trinity",
        )

    def tearDown(self):
        self.hub_root_ctx.cleanup()

    def test_snippet_is_a_dataviewjs_fenced_block(self):
        self.assertTrue(self.asset.dataview_snippet.startswith("```dataviewjs\n"))
        self.assertTrue(self.asset.dataview_snippet.rstrip().endswith("```"))

    def test_snippet_references_the_emitted_assets_vault_relative_path(self):
        self.assertIn(f'"{self.asset.vault_relative_path}"', self.asset.dataview_snippet)

    def test_snippet_checks_asset_existence_before_reading(self):
        self.assertIn("app.vault.adapter.exists(path)", self.asset.dataview_snippet)
        self.assertIn("app.vault.adapter.read(path)", self.asset.dataview_snippet)

    def test_snippet_sets_explicit_pixel_height_on_container(self):
        self.assertIn("height: 360px", self.asset.dataview_snippet)

    def test_snippet_forces_injected_script_tags_to_execute(self):
        self.assertIn("querySelectorAll(\"script\")", self.asset.dataview_snippet)
        self.assertIn("createElement(\"script\")", self.asset.dataview_snippet)
        self.assertIn("replaceChild(newScript, oldScript)", self.asset.dataview_snippet)

    def test_snippet_sets_innerHTML_from_the_read_payload(self):
        self.assertIn("container.innerHTML = rawHtml", self.asset.dataview_snippet)

    def test_custom_height_px_reflected_in_snippet(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
                slug="testing-trinity",
                height_px=480,
            )
        self.assertIn("height: 480px", asset.dataview_snippet)
        self.assertNotIn("height: 360px", asset.dataview_snippet)


class TestVaultAssetDataclass(unittest.TestCase):
    def test_fields_present(self):
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_vault_asset(
                fragment_html=_FRAGMENT,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
                slug="testing-trinity",
            )
        self.assertIsInstance(asset, VaultAsset)
        self.assertEqual(asset.slug, "testing-trinity")
        self.assertTrue(os.path.isabs(asset.div_path))


class TestEmitFromVizResult(unittest.TestCase):
    def test_derives_slug_from_title_and_writes_fragment(self):
        viz_result = VizResult(
            html_path="/irrelevant/x.html",
            title="Testing Trinity!",
            source="template",
            fragment_html=_FRAGMENT,
        )
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_from_viz_result(
                viz_result,
                academic_hub_root=hub_root,
                note_dir="academic_notes/econometrics/summaries",
            )
            self.assertEqual(asset.slug, "testing-trinity")
            with open(asset.div_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), _FRAGMENT)

    def test_passes_through_custom_height_px(self):
        viz_result = VizResult(
            html_path="/irrelevant/x.html", title="Solow Growth", source="template", fragment_html=_FRAGMENT,
        )
        with tempfile.TemporaryDirectory() as hub_root:
            asset = emit_from_viz_result(
                viz_result,
                academic_hub_root=hub_root,
                note_dir="academic_notes/macro/summaries",
                height_px=500,
            )
        self.assertIn("height: 500px", asset.dataview_snippet)


if __name__ == "__main__":
    unittest.main()
