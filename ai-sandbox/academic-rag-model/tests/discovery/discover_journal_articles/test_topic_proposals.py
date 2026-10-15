import json
import tempfile
import unittest
from pathlib import Path

from discovery.discover_journal_articles.topic_proposals import (
    build_proposals_ledger,
    proposals_ledger_path,
    topics_fingerprint,
    write_proposals_ledger,
)
from discovery.discover_journal_articles.discovery import Topic


def _write_sidecar(folder_dir: Path, stem: str, title: str, topics: list[dict]) -> None:
    folder_dir.mkdir(parents=True, exist_ok=True)
    (folder_dir / f"{stem}.meta.json").write_text(json.dumps({"title": title, "topics": topics}), encoding="utf-8")


class TestTopicsFingerprint(unittest.TestCase):
    def test_same_topics_same_fingerprint_regardless_of_order(self):
        a = [Topic(id="T1", display_name="X", score=0.5), Topic(id="T2", display_name="Y", score=0.9)]
        b = [Topic(id="T2", display_name="Y", score=0.9), Topic(id="T1", display_name="X", score=0.5)]
        self.assertEqual(topics_fingerprint(a), topics_fingerprint(b))

    def test_different_scores_different_fingerprint(self):
        a = [Topic(id="T1", display_name="X", score=0.5)]
        b = [Topic(id="T1", display_name="X", score=0.6)]
        self.assertNotEqual(topics_fingerprint(a), topics_fingerprint(b))


class TestBuildProposalsLedger(unittest.TestCase):
    def test_builds_one_entry_per_paper_with_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(
                articles_dir / "business", "10-1-abc", "Carbon Farming",
                [{"id": "T1", "display_name": "Business", "score": 0.39},
                 {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9}],
            )
            manifest = {"10.1/abc": {"status": "fetched", "folder": "business"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["key"], "10.1/abc")
            self.assertEqual(entry["title"], "Carbon Farming")
            self.assertEqual(entry["current_folder"], "business")
            self.assertEqual(entry["candidates"][0]["folder"], "soil-carbon-and-nitrogen-dynamics")
            self.assertFalse(entry["stale"])

    def test_skips_a_paper_with_no_stored_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(articles_dir / "misc", "10-1-def", "Not Backfilled Yet", [])
            manifest = {"10.1/def": {"status": "fetched", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_skips_an_entry_whose_sidecar_no_longer_exists_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            manifest = {"10.1/ghost": {"status": "fetched", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_counts_skipped_entries_when_a_counts_dict_is_passed(self):
        # Confirmed real (code review finding, 2026-10-15): skipped
        # entries (no folder, no sidecar on disk, or an empty topics
        # list) vanished silently -- there was no way to tell "47
        # entries, all skipped" apart from "47 entries, all classified".
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(articles_dir / "misc", "10-1-empty-topics", "No Topics Yet", [])
            manifest = {
                "10.1/no-sidecar": {"status": "fetched", "folder": "misc"},
                "10.1/empty-topics": {"status": "fetched", "folder": "misc"},
                "10.1/no-folder": {"status": "fetched", "folder": None},
                "10.1/needs-manual": {"status": "needs_manual", "folder": "misc"},
            }
            counts = {
                "skipped_not_active": 0, "skipped_no_folder": 0,
                "skipped_no_sidecar": 0, "skipped_no_topics": 0,
            }

            entries = build_proposals_ledger(manifest, articles_dir, counts=counts)

            self.assertEqual(entries, [])
            self.assertEqual(counts["skipped_not_active"], 1)
            self.assertEqual(counts["skipped_no_folder"], 1)
            self.assertEqual(counts["skipped_no_sidecar"], 1)
            self.assertEqual(counts["skipped_no_topics"], 1)

    def test_skips_a_needs_manual_entry_with_no_pdf_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            manifest = {"10.1/pending": {"status": "needs_manual", "folder": "misc"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertEqual(entries, [])

    def test_marks_stale_when_manifest_fingerprint_differs_from_current_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            topics_data = [{"id": "T1", "display_name": "Business", "score": 0.39}]
            _write_sidecar(articles_dir / "business", "10-1-abc", "Carbon Farming", topics_data)
            manifest = {"10.1/abc": {"status": "fetched", "folder": "business", "topic_decision_fingerprint": "stale-value"}}

            entries = build_proposals_ledger(manifest, articles_dir)

            self.assertTrue(entries[0]["stale"])


class TestWriteProposalsLedger(unittest.TestCase):
    def test_writes_ledger_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            articles_dir = Path(tmp)
            _write_sidecar(
                articles_dir / "misc", "10-1-abc", "A Paper",
                [{"id": "T1", "display_name": "Economics", "score": 0.8}],
            )
            manifest = {"10.1/abc": {"status": "fetched", "folder": "misc"}}

            path = write_proposals_ledger(manifest, articles_dir)

            self.assertEqual(path, proposals_ledger_path(articles_dir))
            entries = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)


from discovery.discover_journal_articles.manifest import load_manifest, manifest_path, record_outcome, save_manifest
from discovery.discover_journal_articles.topic_proposals import parse_resolve_arg, resolve_folder_proposal


class TestParseResolveArg(unittest.TestCase):
    def test_splits_on_the_last_colon(self):
        # Confirmed real (code review finding, 2026-10-15): an OpenAlex-id
        # manifest key is itself a URL containing colons
        # ("https://openalex.org/W123"). partition(":") split on the
        # FIRST colon, turning the key into "https" and raising KeyError
        # downstream. rpartition splits on the LAST colon instead.
        key, folder = parse_resolve_arg("https://openalex.org/W123:climate-change")
        self.assertEqual(key, "https://openalex.org/W123")
        self.assertEqual(folder, "climate-change")

    def test_splits_a_bare_doi_key(self):
        key, folder = parse_resolve_arg("10.1/abc:economics")
        self.assertEqual(key, "10.1/abc")
        self.assertEqual(folder, "economics")


class TestResolveFolderProposal(unittest.TestCase):
    def _setup(self, tmp, topics_data):
        articles_dir = Path(tmp)
        _write_sidecar(articles_dir / "business", "10-1-abc", "Carbon Farming", topics_data)
        (articles_dir / "business" / "10-1-abc.pdf").write_bytes(b"%PDF-1.4")
        manifest = {"10.1/abc": {"status": "fetched", "folder": "business"}}
        return articles_dir, manifest

    def test_moves_pdf_and_sidecar_when_chosen_folder_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "soil-carbon-and-nitrogen-dynamics")

            new_dir = articles_dir / "soil-carbon-and-nitrogen-dynamics"
            self.assertTrue((new_dir / "10-1-abc.pdf").exists())
            self.assertTrue((new_dir / "10-1-abc.meta.json").exists())
            self.assertFalse((articles_dir / "business" / "10-1-abc.pdf").exists())
            self.assertEqual(manifest["10.1/abc"]["folder"], "soil-carbon-and-nitrogen-dynamics")

    def test_keeping_current_folder_still_writes_tags_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "business")

            sidecar = json.loads((articles_dir / "business" / "10-1-abc.meta.json").read_text(encoding="utf-8"))
            self.assertIn("soil-carbon-and-nitrogen-dynamics", sidecar["tags"])
            self.assertIn("topic_decision_fingerprint", manifest["10.1/abc"])

    def test_tags_exclude_topics_below_the_relevance_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Negligible Side Topic", "score": 0.05},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "business")

            sidecar = json.loads((articles_dir / "business" / "10-1-abc.meta.json").read_text(encoding="utf-8"))
            self.assertNotIn("negligible-side-topic", sidecar["tags"])

    def test_raises_key_error_for_an_unknown_manifest_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                resolve_folder_proposal({}, tmp, "10.1/missing", "misc")

    def test_resumes_cleanly_after_a_partial_move_left_the_pdf_moved_but_not_the_sidecar(self):
        # Confirmed real (code review finding, 2026-10-15): if a crash (or
        # another process holding a file open on Windows) interrupts the
        # apply step between moving the PDF and moving the sidecar, a
        # retry of the same --resolve call must finish the job instead of
        # raising FileNotFoundError on the already-moved PDF.
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [
                {"id": "T1", "display_name": "Business", "score": 0.39},
                {"id": "T2", "display_name": "Soil Carbon and Nitrogen Dynamics", "score": 0.9},
            ]
            articles_dir, manifest = self._setup(tmp, topics_data)
            new_dir = articles_dir / "soil-carbon-and-nitrogen-dynamics"
            new_dir.mkdir(parents=True)
            (articles_dir / "business" / "10-1-abc.pdf").replace(new_dir / "10-1-abc.pdf")

            resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "soil-carbon-and-nitrogen-dynamics")

            self.assertTrue((new_dir / "10-1-abc.pdf").exists())
            self.assertTrue((new_dir / "10-1-abc.meta.json").exists())
            self.assertFalse((articles_dir / "business" / "10-1-abc.meta.json").exists())
            self.assertEqual(manifest["10.1/abc"]["folder"], "soil-carbon-and-nitrogen-dynamics")

    def test_rejects_an_empty_chosen_folder(self):
        # Confirmed real (code review finding, 2026-10-15): a bare
        # `--resolve KEY` with no colon parsed to folder="" and the PDF/
        # sidecar were silently moved into the articles root with
        # manifest["folder"] == "". Must be rejected instead.
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [{"id": "T1", "display_name": "Business", "score": 0.39}]
            articles_dir, manifest = self._setup(tmp, topics_data)

            with self.assertRaises(ValueError):
                resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "")

    def test_rejects_an_unsanitized_chosen_folder(self):
        # Free-text folder choices (spec B.4 allows a custom folder) must
        # still come out sanitized -- "Climate Change" or "../x" would
        # otherwise create an unsanitized or path-escaping directory.
        with tempfile.TemporaryDirectory() as tmp:
            topics_data = [{"id": "T1", "display_name": "Business", "score": 0.39}]
            articles_dir, manifest = self._setup(tmp, topics_data)

            with self.assertRaises(ValueError):
                resolve_folder_proposal(manifest, articles_dir, "10.1/abc", "Climate Change")


class TestRejectHelpText(unittest.TestCase):
    def test_reject_help_text_does_not_claim_nothing_else_changes(self):
        # Confirmed real (code review finding, 2026-10-15): --reject's
        # help text said "without changing anything else", but
        # resolve_folder_proposal() always rewrites the sidecar's tags
        # (correct per spec B.5) -- the help text was just inaccurate.
        import contextlib
        import io
        from unittest.mock import patch

        from discovery.discover_journal_articles.topic_proposals import main

        buf = io.StringIO()
        with patch("sys.argv", ["topic_proposals.py", "--help"]), self.assertRaises(SystemExit):
            with contextlib.redirect_stdout(buf):
                main()

        self.assertNotIn("without changing anything else", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
