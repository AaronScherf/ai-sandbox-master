import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from journal_discovery.access import AccessResult
from journal_discovery.discovery import Work
from journal_discovery.relevance import ScoredWork
from journal_discovery.snowball import confirm, iter_seed_openalex_ids, iter_snowball_candidates, propose


def _work(idx, doi=None, openalex_id=None):
    return Work(
        openalex_id=openalex_id or f"https://openalex.org/W{idx}", doi=doi, title=f"Paper {idx}",
        authors=[], year=2024, abstract="x",
    )


class TestIterSeedOpenalexIds(unittest.TestCase):
    @patch("journal_discovery.snowball.resolve_work_by_doi")
    def test_yields_pairs_for_fetched_and_downloaded_entries(self, mock_resolve):
        manifest = {
            "10.1/fetched": {"status": "fetched"},
            "10.1/downloaded": {"status": "downloaded"},
            "10.1/manual": {"status": "needs_manual"},
        }
        mock_resolve.side_effect = lambda doi, mailto: _work(1, doi=doi, openalex_id=f"https://openalex.org/{doi}")

        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com"))

        self.assertEqual(
            sorted(pairs),
            sorted([
                ("10.1/fetched", "https://openalex.org/10.1/fetched"),
                ("10.1/downloaded", "https://openalex.org/10.1/downloaded"),
            ]),
        )

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    def test_skips_seed_that_fails_to_resolve(self, mock_resolve):
        manifest = {"10.1/broken": {"status": "fetched"}}
        mock_resolve.return_value = None

        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com"))

        self.assertEqual(pairs, [])

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    def test_seed_doi_override_bypasses_manifest_scan(self, mock_resolve):
        manifest = {"10.1/ignored": {"status": "fetched"}}
        mock_resolve.return_value = _work(1, doi="10.1/explicit", openalex_id="https://openalex.org/W1")

        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com", seed_dois=["10.1/explicit"]))

        self.assertEqual(pairs, [("10.1/explicit", "https://openalex.org/W1")])

    def test_non_doi_manifest_key_used_directly_as_openalex_id(self):
        manifest = {"https://openalex.org/W9": {"status": "fetched"}}
        pairs = list(iter_seed_openalex_ids(manifest, "me@example.com"))
        self.assertEqual(pairs, [("https://openalex.org/W9", "https://openalex.org/W9")])


class TestIterSnowballCandidates(unittest.TestCase):
    @patch("journal_discovery.snowball.iter_citing_works")
    @patch("journal_discovery.snowball.iter_seed_openalex_ids")
    def test_chains_seeds_and_populates_seed_map(self, mock_seeds, mock_citing):
        mock_seeds.return_value = iter([("10.1/seed-a", "OA-A"), ("10.1/seed-b", "OA-B")])
        mock_citing.side_effect = lambda openalex_id, mailto, batch_size: iter(
            [_work(1, doi="10.1/citer-a")] if openalex_id == "OA-A" else [_work(2, doi="10.1/citer-b")]
        )
        manifest = {}
        counts = {"already_seen": 0}
        seed_map = {}

        candidates = list(iter_snowball_candidates(manifest, "me@example.com", 25, counts, seed_map))

        self.assertEqual(sorted(w.doi for w in candidates), ["10.1/citer-a", "10.1/citer-b"])
        self.assertEqual(seed_map["10.1/citer-a"], "10.1/seed-a")
        self.assertEqual(seed_map["10.1/citer-b"], "10.1/seed-b")

    @patch("journal_discovery.snowball.iter_citing_works")
    @patch("journal_discovery.snowball.iter_seed_openalex_ids")
    def test_already_seen_candidates_filtered_and_counted(self, mock_seeds, mock_citing):
        mock_seeds.return_value = iter([("10.1/seed-a", "OA-A")])
        mock_citing.return_value = iter([_work(1, doi="10.1/already-seen")])
        manifest = {"10.1/already-seen": {"status": "fetched"}}
        counts = {"already_seen": 0}
        seed_map = {}

        candidates = list(iter_snowball_candidates(manifest, "me@example.com", 25, counts, seed_map))

        self.assertEqual(candidates, [])
        self.assertEqual(counts["already_seen"], 1)
        self.assertNotIn("10.1/already-seen", seed_map)


def _propose_args(**overrides):
    defaults = dict(
        relevance_prompt="climate", relevance_threshold=0.5, batch_size=25,
        max_results=50, max_examined=200, seed_doi=[],
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestPropose(unittest.TestCase):
    @patch("journal_discovery.snowball.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.snowball.iter_snowball_candidates")
    @patch("journal_discovery.snowball.select_relevant_works")
    def test_records_scored_candidates_as_proposed(self, mock_select, mock_candidates, mock_load_model):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1, doi="10.1/citer")
            mock_candidates.return_value = iter([work])
            mock_select.return_value = [ScoredWork(work=work, score=0.75)]

            counts = propose(_propose_args(articles_dir=tmp, mailto="me@example.com"))

            self.assertEqual(counts["proposed"], 1)

            from journal_discovery.manifest import load_manifest, manifest_path
            manifest = load_manifest(manifest_path(tmp))
            entry = manifest["10.1/citer"]
            self.assertEqual(entry["status"], "proposed")
            self.assertEqual(entry["relevance_score"], 0.75)
            self.assertEqual(entry["scored_from"], "abstract")
            self.assertEqual(entry["title"], "Paper 1")
            self.assertIn("folder", entry)

    @patch("journal_discovery.snowball.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.snowball.iter_snowball_candidates")
    @patch("journal_discovery.snowball.select_relevant_works")
    def test_writes_worklist(self, mock_select, mock_candidates, mock_load_model):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1, doi="10.1/citer")
            mock_candidates.return_value = iter([work])
            mock_select.return_value = [ScoredWork(work=work, score=0.75)]

            propose(_propose_args(articles_dir=tmp, mailto="me@example.com"))

            worklist = Path(tmp) / "snowball_candidates.md"
            self.assertTrue(worklist.exists())
            self.assertIn("Paper 1", worklist.read_text(encoding="utf-8"))

    @patch("journal_discovery.snowball.load_relevance_model", return_value=MagicMock())
    @patch("journal_discovery.snowball.iter_snowball_candidates")
    @patch("journal_discovery.snowball.select_relevant_works")
    def test_records_cites_seed_from_seed_map(self, mock_select, mock_candidates, mock_load_model):
        with tempfile.TemporaryDirectory() as tmp:
            work = _work(1, doi="10.1/citer")

            def fake_candidates(manifest, mailto, batch_size, counts, seed_map, seed_dois=None):
                # Not a generator: a generator's body wouldn't run until
                # something iterates it, and the mocked select_relevant_works
                # below never does that (it returns a canned result without
                # touching its argument) -- so the seed_map write has to
                # happen eagerly, on call, to be visible to the assertion.
                seed_map["10.1/citer"] = "10.1/seed-paper"
                return iter([work])

            mock_candidates.side_effect = fake_candidates
            mock_select.return_value = [ScoredWork(work=work, score=0.75)]

            propose(_propose_args(articles_dir=tmp, mailto="me@example.com"))

            from journal_discovery.manifest import load_manifest, manifest_path
            manifest = load_manifest(manifest_path(tmp))
            self.assertEqual(manifest["10.1/citer"]["cites_seed"], "10.1/seed-paper")


def _confirm_args(**overrides):
    defaults = dict(pace_per_hour=25.0, core_api_key=None)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestConfirm(unittest.TestCase):
    @patch("journal_discovery.snowball.resolve_work_by_doi")
    @patch("journal_discovery.snowball.resolve_full_text")
    def test_fetches_checked_proposed_entry(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome
            from journal_discovery.worklist import write_snowball_candidates_worklist

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/citer", "proposed", folder="business", metadata={
                "title": "A Candidate", "doi_url": "https://doi.org/10.1/citer", "relevance_score": 0.7,
            })
            save_manifest(path, manifest)
            worklist_path = write_snowball_candidates_worklist(manifest, tmp)
            worklist_path.write_text(
                worklist_path.read_text(encoding="utf-8").replace("- [ ] [A Candidate]", "- [x] [A Candidate]"),
                encoding="utf-8",
            )

            mock_resolve_by_doi.return_value = _work(1, doi="10.1/citer")
            mock_resolve_full_text.return_value = AccessResult(status="fetched", content=b"%PDF-1.4", tier="open_access")

            counts = confirm(_confirm_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["confirmed"], 1)
            self.assertEqual(counts["fetched"], 1)

            manifest = load_manifest(path)
            self.assertEqual(manifest["10.1/citer"]["status"], "fetched")
            pdfs = list((Path(tmp) / "business").glob("*.pdf"))
            self.assertEqual(len(pdfs), 1)

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    @patch("journal_discovery.snowball.resolve_full_text")
    def test_unchecked_proposed_entry_left_untouched(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome
            from journal_discovery.worklist import write_snowball_candidates_worklist

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/citer", "proposed", folder="business", metadata={
                "title": "A Candidate", "doi_url": "https://doi.org/10.1/citer",
            })
            save_manifest(path, manifest)
            write_snowball_candidates_worklist(manifest, tmp)  # left unchecked

            counts = confirm(_confirm_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["confirmed"], 0)
            mock_resolve_full_text.assert_not_called()
            manifest = load_manifest(path)
            self.assertEqual(manifest["10.1/citer"]["status"], "proposed")

    @patch("journal_discovery.snowball.resolve_work_by_doi")
    @patch("journal_discovery.snowball.resolve_full_text")
    def test_confirmed_but_unfetchable_lands_in_needs_manual_worklist(self, mock_resolve_full_text, mock_resolve_by_doi):
        with tempfile.TemporaryDirectory() as tmp:
            from journal_discovery.manifest import manifest_path, load_manifest, save_manifest, record_outcome
            from journal_discovery.worklist import write_snowball_candidates_worklist

            path = manifest_path(tmp)
            manifest = load_manifest(path)
            record_outcome(manifest, "10.1/citer", "proposed", folder="business", metadata={
                "title": "A Candidate", "doi_url": "https://doi.org/10.1/citer",
            })
            save_manifest(path, manifest)
            worklist_path = write_snowball_candidates_worklist(manifest, tmp)
            worklist_path.write_text(
                worklist_path.read_text(encoding="utf-8").replace("- [ ] [A Candidate]", "- [x] [A Candidate]"),
                encoding="utf-8",
            )

            mock_resolve_by_doi.return_value = _work(1, doi="10.1/citer")
            mock_resolve_full_text.return_value = AccessResult(status="needs_manual")

            counts = confirm(_confirm_args(articles_dir=tmp, mailto="me@example.com", ezproxy_cookie=None))

            self.assertEqual(counts["needs_manual"], 1)
            needs_manual_content = (Path(tmp) / "needs_manual_downloads.md").read_text(encoding="utf-8")
            self.assertIn("A Candidate", needs_manual_content)


if __name__ == "__main__":
    unittest.main()
