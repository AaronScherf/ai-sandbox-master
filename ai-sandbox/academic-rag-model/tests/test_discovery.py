import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import (
    Work,
    doi_url,
    iter_author_works,
    iter_citing_works,
    iter_topic_works,
    reconstruct_abstract,
    resolve_author_id,
    resolve_work_by_doi,
    resolve_works,
)


def _openalex_work(title="Untitled", doi="https://doi.org/10.1/abc", arxiv_url=None, work_type="article",
                    concepts=None):
    return {
        "id": "https://openalex.org/W1",
        "doi": doi,
        "title": title,
        "type": work_type,
        "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Jane Doe"}}],
        "abstract_inverted_index": {"Climate": [0], "displacement": [1]},
        "concepts": concepts if concepts is not None else [
            {"display_name": "Climate change", "score": 0.9, "level": 2},
            {"display_name": "Economics", "score": 0.4, "level": 0},
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
        # "Economics" (level 0) sorts ahead of "Climate change" (level 2,
        # higher score) -- see test_prefers_level_zero_concept_for_ordering.
        self.assertEqual(work.concepts, ["Economics", "Climate change"])
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

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_prefers_level_zero_concept_for_ordering(self, mock_fetch):
        # Confirmed live 2026-09-02: OpenAlex's top-scored concept is
        # often a narrow, homonym-prone level-2 concept (e.g. "GRASP" the
        # algorithm for a paper just using the word "grasp") even when a
        # sensible, broad level-0 field ("Computer science") is also
        # present, just scored lower. Folder routing uses concepts[0], so
        # a level-0 concept should win when one exists, regardless of
        # score ranking among the narrower ones.
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(concepts=[
                {"display_name": "GRASP", "score": 0.93, "level": 2},
                {"display_name": "Work (physics)", "score": 0.61, "level": 2},
                {"display_name": "Sociology", "score": 0.41, "level": 0},
                {"display_name": "Computer science", "score": 0.37, "level": 0},
            ])]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual(works[0].concepts[0], "Sociology")

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_falls_back_to_top_score_without_any_level_zero_concept(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(concepts=[
                {"display_name": "Transformative learning", "score": 0.74, "level": 2},
                {"display_name": "Psychological resilience", "score": 0.61, "level": 2},
            ])]}),
            _response({"results": []}),
        ]
        works = list(iter_author_works("https://openalex.org/A1", "me@example.com", batch_size=25))
        self.assertEqual(works[0].concepts[0], "Transformative learning")


class TestDoiUrl(unittest.TestCase):
    def test_builds_doi_dot_org_url(self):
        work = Work(openalex_id="W1", doi="10.1/abc", title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(doi_url(work), "https://doi.org/10.1/abc")

    def test_falls_back_to_openalex_id_without_doi(self):
        work = Work(openalex_id="https://openalex.org/W1", doi=None, title="T", authors=[], year=2024, abstract=None)
        self.assertEqual(doi_url(work), "https://openalex.org/W1")


class TestResolveWorkByDoi(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_returns_parsed_work(self, mock_fetch):
        mock_fetch.return_value = _response(_openalex_work(doi="https://doi.org/10.1/abc"))
        work = resolve_work_by_doi("10.1/abc", "me@example.com")
        self.assertIsInstance(work, Work)
        self.assertEqual(work.doi, "10.1/abc")

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_none_on_non_200(self, mock_fetch):
        mock_fetch.return_value = _response({}, status_code=404)
        self.assertIsNone(resolve_work_by_doi("10.1/unknown", "me@example.com"))

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_none_on_fetch_error(self, mock_fetch):
        from journal_discovery.http_utils import FetchError
        mock_fetch.side_effect = FetchError("not found")
        self.assertIsNone(resolve_work_by_doi("10.1/unknown", "me@example.com"))


class TestIterCitingWorks(unittest.TestCase):
    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_pages_until_empty(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work()]}),
            _response({"results": []}),
        ]
        works = list(iter_citing_works("https://openalex.org/W1", "me@example.com", batch_size=25))
        self.assertEqual(len(works), 1)

    @patch("journal_discovery.discovery.fetch_with_retries")
    def test_excludes_dataset_type_works(self, mock_fetch):
        mock_fetch.side_effect = [
            _response({"results": [_openalex_work(work_type="dataset")]}),
            _response({"results": []}),
        ]
        works = list(iter_citing_works("https://openalex.org/W1", "me@example.com", batch_size=25))
        self.assertEqual(works, [])


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
