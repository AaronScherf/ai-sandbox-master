import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import (
    Work,
    iter_author_works,
    iter_topic_works,
    reconstruct_abstract,
    resolve_author_id,
    resolve_works,
)


def _openalex_work(title="Untitled", doi="https://doi.org/10.1/abc", arxiv_url=None, work_type="article"):
    return {
        "id": "https://openalex.org/W1",
        "doi": doi,
        "title": title,
        "type": work_type,
        "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "abstract_inverted_index": {"Climate": [0], "displacement": [1]},
        "concepts": [
            {"display_name": "Climate change", "score": 0.9},
            {"display_name": "Economics", "score": 0.4},
        ],
        "open_access": {"is_oa": True, "oa_url": "https://example.com/paper.pdf"},
        "locations": [{"landing_page_url": arxiv_url}] if arxiv_url else [],
    }


def _response(json_data, status_code=200):
    response = MagicMock(status_code=status_code)
    response.json.return_value = json_data
    return response


class TestReconstructAbstract(unittest.TestCase):
    def test_reorders_by_position(self):
        result = reconstruct_abstract({"displacement": [1], "Climate": [0]})
        self.assertEqual(result, "Climate displacement")

    def test_none_when_missing(self):
        self.assertIsNone(reconstruct_abstract(None))
        self.assertIsNone(reconstruct_abstract({}))


class TestResolveAuthorId(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_returns_ror_filtered_match(self, mock_fetch):
        mock_fetch.return_value = _response({"results": [{"id": "https://openalex.org/A1"}]})
        result = resolve_author_id("Jane Doe", "me@example.com")
        self.assertEqual(result, "https://openalex.org/A1")
        self.assertEqual(mock_fetch.call_count, 1)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_falls_back_when_ror_filter_finds_nothing(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": []}),
            _response({"results": [{"id": "https://openalex.org/A2"}]}),
        ]
        result = resolve_author_id("Jane Doe", "me@example.com")
        self.assertEqual(result, "https://openalex.org/A2")
        self.assertEqual(mock_fetch.call_count, 2)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_none_when_nothing_matches_at_all(self, mock_fetch):
        mock_fetch.return_value = _response({"results": []})
        self.assertIsNone(resolve_author_id("Nobody", "me@example.com"))


class TestIterAuthorWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_pages_until_empty_and_parses_fields(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual(len(works), 1)
        work = works[0]
        self.assertIsInstance(work, Work)
        self.assertEqual(work.doi, "10.1/abc")
        self.assertEqual(work.title, "Untitled")
        self.assertEqual(work.authors, ["Jane Doe"])
        self.assertEqual(work.abstract, "Climate displacement")
        self.assertEqual(work.concepts, ["Climate change", "Economics"])
        self.assertTrue(work.is_oa)
        self.assertEqual(work.oa_url, "https://example.com/paper.pdf")
        self.assertIsNone(work.arxiv_id)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_extracts_arxiv_id(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(arxiv_url="https://arxiv.org/abs/2401.12345")]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual(works[0].arxiv_id, "2401.12345")

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_excludes_dataset_type_works(self, mock_fetch):
        # Confirmed live 2026-09-02: an author's OpenAlex works list
        # includes RCT trial registrations and replication-data records
        # (type="dataset") alongside real papers -- these can never have
        # a fetchable PDF and shouldn't burn a candidate slot.
        mock_fetch.side_effect = [
            _response({"results": [
                _openalex_work(doi="https://doi.org/10.1/real-paper", work_type="article"),
                _openalex_work(doi="https://doi.org/10.1/rct-registration", work_type="dataset"),
            ]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual([w.doi for w in works], ["10.1/real-paper"])


class TestIterTopicWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_pages_until_empty(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_topic_works("climate displacement", "me@example.com", batch_size=25))
        self.assertEqual(len(works), 1)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_excludes_dataset_type_works(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(work_type="dataset")]}),
            _response({"results": []}),
        ]
        works = list(iter_topic_works("climate displacement", "me@example.com", batch_size=25))
        self.assertEqual(works, [])


class TestResolveWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.iter_topic_works")
    @patch("journal_discovery.discovery.iter_author_works")
    @patch("journal_discovery.discovery.resolve_author_id")
    def test_chains_faculty_then_topic_queries(self, mock_resolve_author, mock_iter_author, mock_iter_topic):
        mock_resolve_author.return_value = "https://openalex.org/A1"
        mock_iter_author.return_value = iter([Work(
            openalex_id="W1", doi="10.1/a", title="A", authors=[], year=2024, abstract="x",
            concepts=[], oa_url=None, is_oa=False, arxiv_id=None, page_count=None,
        )])
        mock_iter_topic.return_value = iter([Work(
            openalex_id="W2", doi="10.1/b", title="B", authors=[], year=2024, abstract="y",
            concepts=[], oa_url=None, is_oa=False, arxiv_id=None, page_count=None,
        )])

        results = list(resolve_works(["Jane Doe"], ["climate"], "me@example.com", batch_size=25))

        self.assertEqual([w.openalex_id for w in results], ["W1", "W2"])

    @patch("journal_discovery.discovery.iter_author_works")
    @patch("journal_discovery.discovery.resolve_author_id")
    def test_skips_unresolvable_faculty(self, mock_resolve_author, mock_iter_author):
        mock_resolve_author.return_value = None

        results = list(resolve_works(["Nobody"], [], "me@example.com", batch_size=25))

        self.assertEqual(results, [])
        mock_iter_author.assert_not_called()


if __name__ == "__main__":
    unittest.main()
