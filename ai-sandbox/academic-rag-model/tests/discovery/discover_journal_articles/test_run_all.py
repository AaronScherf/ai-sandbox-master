import argparse
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import discovery.discover_journal_articles.run_all as run_all

M = "discovery.discover_journal_articles.run_all"
CJA = "pipelines.convert_journal_articles.convert_journal_articles"


def _args(**overrides):
    defaults = dict(
        faculty=["Jane Doe"], topic=[], relevance_prompt="climate", relevance_threshold=0.5,
        batch_size=25, max_results=100, max_examined=300, pace_per_hour=25.0, zotero=False,
        time_budget_seconds=None, driver="agent", model=None, max_pages=150, run_id=None,
        dry_run=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _pdf(root, rel="economics/a.pdf"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4 mock " + rel.encode())
    return path


def _run_argv(argv):
    with patch.object(sys, "argv", ["run_all"] + argv):
        run_all.main()


class TestRunPipeline(unittest.TestCase):
    def test_zero_fetched_skips_conversion_and_indexing_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(f"{M}.discover_run", return_value={
                "fetched": 0, "needs_manual": 0, "fetched_paths": [],
            }) as disc, patch(f"{M}._collect") as collect, patch(f"{M}._convert_via_api") as api:
                counts = run_all.run_pipeline(_args(articles_dir=tmp, index_root=tmp))
            disc.assert_called_once()
            collect.assert_not_called()
            api.assert_not_called()
            self.assertEqual(counts["converted"], 0)
            self.assertEqual(counts["collected"], 0)

    def test_fetched_papers_are_staged_for_agent_driver_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            with patch(f"{M}.discover_run", return_value={
                "fetched": 1, "needs_manual": 0, "fetched_paths": [pdf],
            }), patch(f"{CJA}._page_count", return_value=5), patch(f"{M}._collect") as collect:
                counts = run_all.run_pipeline(_args(articles_dir=tmp, index_root=tmp))
            collect.assert_called_once()
            staged_paths = collect.call_args.args[0]
            self.assertEqual(staged_paths, [pdf])
            self.assertEqual(counts["collected"], 1)
            self.assertIsNotNone(counts["collect_run_id"])

    def test_fetched_papers_are_converted_immediately_with_api_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            with patch(f"{M}.discover_run", return_value={
                "fetched": 1, "needs_manual": 0, "fetched_paths": [pdf],
            }), patch(f"{CJA}._page_count", return_value=5), \
                    patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.process_pdf") as proc, patch(f"{M}.attach_identity") as attach:
                counts = run_all.run_pipeline(_args(articles_dir=tmp, index_root=tmp, driver="api"))
            proc.assert_called_once()
            attach.assert_called_once_with(pdf, tmp)
            self.assertEqual(counts["converted"], 1)

    def test_oversized_fetched_paper_is_never_converted(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            with patch(f"{M}.discover_run", return_value={
                "fetched": 1, "needs_manual": 0, "fetched_paths": [pdf],
            }), patch(f"{CJA}._page_count", return_value=400), \
                    patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.process_pdf") as proc:
                counts = run_all.run_pipeline(_args(articles_dir=tmp, index_root=tmp, driver="api"))
            proc.assert_not_called()
            self.assertEqual(counts["converted"], 0)

    def test_one_conversion_failure_does_not_stop_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = _pdf(tmp, "economics/a.pdf")
            b = _pdf(tmp, "economics/b.pdf")
            seen = []

            def fake_process(pdf_path, *a_, **kw):
                seen.append(pdf_path)
                if pdf_path == a:
                    raise RuntimeError("corrupt pdf")

            with patch(f"{M}.discover_run", return_value={
                "fetched": 2, "needs_manual": 0, "fetched_paths": [a, b],
            }), patch(f"{CJA}._page_count", return_value=5), \
                    patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.process_pdf", side_effect=fake_process), \
                    patch(f"{M}.attach_identity") as attach, patch("builtins.print") as out:
                counts = run_all.run_pipeline(_args(articles_dir=tmp, index_root=tmp, driver="api"))
            self.assertEqual(sorted(seen), sorted([a, b]))
            self.assertEqual(attach.call_count, 1)
            self.assertEqual(counts["converted"], 1)
            self.assertTrue(any("error" in " ".join(map(str, c.args)).lower() for c in out.call_args_list))

    def test_needs_manual_is_reported_not_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(f"{M}.discover_run", return_value={
                "fetched": 0, "needs_manual": 3, "fetched_paths": [],
            }), patch("builtins.print") as out:
                counts = run_all.run_pipeline(_args(articles_dir=tmp, index_root=tmp))
            self.assertEqual(counts["needs_manual"], 3)


class TestMainCLI(unittest.TestCase):
    def test_dry_run_never_calls_discovery_and_previews_existing_pdfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            env = {"OPENALEX_CONTACT_EMAIL": "me@example.com"}
            with patch(f"{M}.load_dotenv_override"), patch.dict(os.environ, env), \
                    patch(f"{M}.discover_run") as disc, patch(f"{CJA}._page_count", return_value=5), \
                    patch(f"{M}.process_pdf") as proc:
                _run_argv([
                    "--faculty", "Jane Doe", "--relevance-prompt", "climate",
                    "--articles-dir", tmp, "--index-root", tmp, "--dry-run",
                ])
            disc.assert_not_called()
            self.assertTrue(proc.call_args.kwargs["dry_run"])
            self.assertEqual(proc.call_args.args[0], pdf)

    def test_missing_openalex_email_exits_before_any_api_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(f"{M}.load_dotenv_override"), patch.dict(os.environ, {}, clear=True), \
                    patch(f"{M}.discover_run") as disc:
                with self.assertRaises(SystemExit):
                    _run_argv([
                        "--faculty", "Jane Doe", "--relevance-prompt", "climate",
                        "--articles-dir", tmp, "--index-root", tmp,
                    ])
            disc.assert_not_called()

    def test_requires_relevance_prompt_and_a_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"OPENALEX_CONTACT_EMAIL": "me@example.com"}
            with patch(f"{M}.load_dotenv_override"), patch.dict(os.environ, env), \
                    patch(f"{M}.discover_run") as disc:
                with self.assertRaises(SystemExit):
                    _run_argv(["--articles-dir", tmp, "--index-root", tmp])
            disc.assert_not_called()

    def test_full_run_wires_discovery_into_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            env = {"OPENALEX_CONTACT_EMAIL": "me@example.com"}
            with patch(f"{M}.load_dotenv_override"), patch.dict(os.environ, env), \
                    patch(f"{M}.discover_run", return_value={
                        "fetched": 1, "needs_manual": 0, "fetched_paths": [pdf],
                    }) as disc, patch(f"{CJA}._page_count", return_value=5), patch(f"{M}._collect") as collect:
                _run_argv([
                    "--faculty", "Jane Doe", "--relevance-prompt", "climate",
                    "--articles-dir", tmp, "--index-root", tmp,
                ])
            disc.assert_called_once()
            collect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
