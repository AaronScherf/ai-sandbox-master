import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pipelines.convert_journal_articles.convert_journal_articles as cja

M = "pipelines.convert_journal_articles.convert_journal_articles"


def _pdf(root, rel="economics/a.pdf"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4 mock " + rel.encode())
    return path


def _run(argv):
    with patch.object(sys, "argv", ["convert_journal_articles"] + argv):
        cja.main()


class TestDriverFlags(unittest.TestCase):
    def test_bare_run_does_not_spend_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5):
                with self.assertRaises(SystemExit) as ctx:
                    _run(["--articles-dir", tmp, "--index-root", tmp])
            self.assertNotEqual(ctx.exception.code, 0)
            client.assert_not_called()
            proc.assert_not_called()

    def test_collect_uses_agent_driver_collect_mode_and_journal_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--collect", "--run-id", "r1"])
            client.assert_not_called()
            kw = proc.call_args.kwargs
            self.assertTrue(kw["collect_mode"])
            self.assertEqual(kw["known_doc_types"], cja._JOURNAL_DOC_TYPES)
            self.assertIs(kw["check_math_notation"], False)
            self.assertEqual(type(kw["driver"]).__name__, "AgentDriver")
            self.assertEqual(kw["driver"].hub_root, tmp)

    def test_api_driver_keeps_the_existing_client_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()) as client, \
                    patch(f"{M}.process_pdf") as proc, patch(f"{M}._page_count", return_value=5), \
                    patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--driver", "api"])
            client.assert_called_once()
            self.assertIs(proc.call_args.kwargs["check_math_notation"], False)
            self.assertNotIn("driver", proc.call_args.kwargs)

    def test_dry_run_needs_no_driver_flag_and_no_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--dry-run"])
            client.assert_not_called()
            self.assertTrue(proc.call_args.kwargs["dry_run"])

    def test_oversize_paper_is_never_staged(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.process_pdf") as proc, patch(f"{M}._page_count", return_value=400):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--collect", "--run-id", "r1"])
            proc.assert_not_called()

    def test_bootstrap_prints_contract_without_touching_anything(self):
        with patch(f"{M}.process_pdf") as proc, patch(f"{M}.discover_pdf_files") as disc:
            _run(["--bootstrap", "r9"])
        proc.assert_not_called()
        disc.assert_not_called()
        self.assertIn("r9", cja._bootstrap_text("r9"))


class TestSubmit(unittest.TestCase):
    def _slug(self, path):
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_work import doc_slug_for
        return doc_slug_for(path, compute_file_id(path))

    def test_submit_forwards_collect_time_settings_and_fallback_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1", self._slug(pdf)))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.submit_doc", return_value="incomplete: 1 card(s) still pending/bounced") as sub, \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1", "--allow-api-fallback"])
            first, second = sub.call_args_list
            self.assertFalse(first.kwargs["allow_api_fallback"])
            self.assertTrue(second.kwargs["allow_api_fallback"])
            self.assertEqual(first.kwargs["known_doc_types"], cja._JOURNAL_DOC_TYPES)
            self.assertIs(first.kwargs["check_math_notation"], False)

    def test_card_less_paper_is_finished_locally_with_a_null_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}.submit_doc") as sub, \
                    patch(f"{M}.process_pdf") as proc, patch(f"{M}._page_count", return_value=5), \
                    patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            sub.assert_not_called()
            self.assertEqual(type(proc.call_args.kwargs["driver"]).__name__, "NullDriver")

    def test_card_less_paper_that_needs_the_agent_is_reported_not_crashed(self):
        from pipelines.transcribe_notes.agent_driver import NullDriverFired
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                    patch(f"{M}.process_pdf", side_effect=NullDriverFired("x")), \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"), \
                    patch("builtins.print") as out:
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            self.assertTrue(any("--collect" in " ".join(map(str, c.args)) for c in out.call_args_list))

    def test_already_converted_paper_is_not_touched_by_the_local_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            out_dir = os.path.join(os.path.dirname(pdf), "processed_outputs")
            os.makedirs(out_dir)
            with open(os.path.join(out_dir, "a.md"), "w", encoding="utf-8") as f:
                f.write("done")
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}.process_pdf") as proc, \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            proc.assert_not_called()

    def test_unknown_run_id_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pdf(tmp)
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}._page_count", return_value=5):
                with self.assertRaises(SystemExit):
                    _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "nope"])


class TestIdentityWiring(unittest.TestCase):
    def _slug(self, path):
        from core.indexer.index_card import compute_file_id
        from pipelines.transcribe_notes.agent_work import doc_slug_for
        return doc_slug_for(path, compute_file_id(path))

    def test_backfill_stamps_each_eligible_paper_and_needs_no_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = _pdf(tmp, "economics/a.pdf")
            b = _pdf(tmp, "economics/b.pdf")
            with patch(f"{M}.get_gemini_client") as client, patch(f"{M}.attach_identity", return_value=True) as attach, \
                    patch(f"{M}._page_count", return_value=5), patch(f"{M}.corpus_write_lock"), \
                    patch(f"{M}.process_pdf") as proc:
                _run(["--articles-dir", tmp, "--index-root", tmp, "--backfill-identity"])
            client.assert_not_called()
            proc.assert_not_called()
            self.assertEqual(sorted(c.args[0] for c in attach.call_args_list), sorted([a, b]))

    def test_submit_stamps_only_completed_papers(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            os.makedirs(os.path.join(tmp, ".agent_work", "r1", self._slug(pdf)))
            for status, expected_calls in (("complete", 1), ("incomplete: 1 card(s) still pending/bounced", 0)):
                with patch(f"{M}.get_gemini_client", return_value=MagicMock()), \
                        patch(f"{M}.submit_doc", return_value=status), \
                        patch(f"{M}.attach_identity") as attach, patch(f"{M}._page_count", return_value=5), \
                        patch(f"{M}.corpus_write_lock"):
                    _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
                self.assertEqual(attach.call_count, expected_calls, status)

    def test_api_loop_stamps_after_each_paper(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = _pdf(tmp)
            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}.process_pdf"), \
                    patch(f"{M}.attach_identity") as attach, patch(f"{M}._page_count", return_value=5):
                _run(["--articles-dir", tmp, "--index-root", tmp, "--driver", "api"])
            attach.assert_called_once_with(pdf, tmp)


class TestLocalFinishIsolation(unittest.TestCase):
    def test_one_unreadable_paper_does_not_stop_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = _pdf(tmp, "economics/a.pdf")
            b = _pdf(tmp, "economics/b.pdf")
            os.makedirs(os.path.join(tmp, ".agent_work", "r1"))
            seen = []

            def fake_process(pdf_path, *args, **kwargs):
                seen.append(pdf_path)
                if pdf_path == a:
                    raise RuntimeError("corrupt pdf")

            with patch(f"{M}.get_gemini_client", return_value=MagicMock()), patch(f"{M}.process_pdf", side_effect=fake_process), \
                    patch(f"{M}.attach_identity"), patch(f"{M}._page_count", return_value=5), \
                    patch(f"{M}.corpus_write_lock"), patch("builtins.print") as out:
                _run(["--articles-dir", tmp, "--index-root", tmp, "--submit", "r1"])
            self.assertEqual(sorted(seen), sorted([a, b]))
            self.assertTrue(any("error" in " ".join(map(str, c.args)) for c in out.call_args_list))


if __name__ == "__main__":
    unittest.main()
