import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import Work
from journal_discovery.snowball import iter_seed_openalex_ids, iter_snowball_candidates


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


if __name__ == "__main__":
    unittest.main()
