import tempfile
import unittest

from agent.literature.backfill_years import backfill_years, cards_missing_year
from core.indexer.index_card import load_shard
from discovery.discover_journal_articles.discovery import Work
from lit_helpers import make_index


def _work(year):
    return Work(openalex_id="https://openalex.org/W1", doi="10.1/x", title="T", authors=[], year=year, abstract=None)


class TestCardsMissingYear(unittest.TestCase):
    def test_finds_journal_articles_with_no_publication_year(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, file_id="0000000000000001", card_extra={"doi": "10.1/x"})
            make_index(root, file_id="0000000000000002", card_extra={"publication_year": 2020})
            cards = cards_missing_year(root)
        self.assertEqual([c["file_id"] for c in cards], ["0000000000000001"])

    def test_non_journal_cards_are_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, card_extra={"doc_type": "lecture_notes"})
            self.assertEqual(cards_missing_year(root), [])


class TestBackfillYears(unittest.TestCase):
    def test_resolves_year_by_doi_and_writes_it_to_the_card(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, file_id="0000000000000001", card_extra={"doi": "10.1/x"})
            outcomes = backfill_years(root, "me@example.com",
                                       resolve_doi=lambda doi, mailto: _work(2018),
                                       resolve_openalex=lambda oid, mailto: None)
            cards = load_shard(root, "economics")
        self.assertEqual(outcomes, {"0000000000000001": "backfilled"})
        self.assertEqual(cards[0]["publication_year"], 2018)

    def test_falls_back_to_openalex_id_when_there_is_no_doi(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, file_id="0000000000000001", card_extra={"openalex_id": "https://openalex.org/W1"})
            outcomes = backfill_years(root, "me@example.com",
                                       resolve_doi=lambda doi, mailto: None,
                                       resolve_openalex=lambda oid, mailto: _work(2019))
            cards = load_shard(root, "economics")
        self.assertEqual(outcomes, {"0000000000000001": "backfilled"})
        self.assertEqual(cards[0]["publication_year"], 2019)

    def test_doi_lookup_with_no_year_falls_back_to_openalex_id(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, file_id="0000000000000001",
                       card_extra={"doi": "10.1/x", "openalex_id": "https://openalex.org/W1"})
            outcomes = backfill_years(root, "me@example.com",
                                       resolve_doi=lambda doi, mailto: _work(None),
                                       resolve_openalex=lambda oid, mailto: _work(2021))
            cards = load_shard(root, "economics")
        self.assertEqual(outcomes, {"0000000000000001": "backfilled"})
        self.assertEqual(cards[0]["publication_year"], 2021)

    def test_card_with_no_identifier_is_reported_not_resolved(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, file_id="0000000000000001")
            outcomes = backfill_years(root, "me@example.com",
                                       resolve_doi=lambda doi, mailto: None,
                                       resolve_openalex=lambda oid, mailto: None)
            cards = load_shard(root, "economics")
        self.assertEqual(outcomes, {"0000000000000001": "no identifier"})
        self.assertNotIn("publication_year", cards[0])

    def test_openalex_lookup_that_finds_nothing_is_reported(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, file_id="0000000000000001", card_extra={"doi": "10.1/x"})
            outcomes = backfill_years(root, "me@example.com",
                                       resolve_doi=lambda doi, mailto: None,
                                       resolve_openalex=lambda oid, mailto: None)
        self.assertEqual(outcomes, {"0000000000000001": "not found in OpenAlex"})

    def test_an_empty_index_backfills_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(backfill_years(root, "me@example.com"), {})


if __name__ == "__main__":
    unittest.main()
