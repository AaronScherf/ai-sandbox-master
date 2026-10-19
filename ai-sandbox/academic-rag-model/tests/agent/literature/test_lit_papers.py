import os
import tempfile
import unittest

from agent.literature.papers import eligible_papers
from lit_helpers import make_index


class TestEligiblePapers(unittest.TestCase):
    def test_a_converted_journal_paper_is_eligible_and_carries_identity(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, card_extra={"openalex_id": "https://openalex.org/W9", "doi": "10.1/x",
                                         "publication_year": 2021,
                                         "openalex_topics": [{"id": "https://openalex.org/T1"}]})
            papers, skipped = eligible_papers(root)
        self.assertEqual(skipped, {})
        self.assertEqual(len(papers), 1)
        p = papers[0]
        self.assertEqual(p.file_id, "0123456789abcdef")
        self.assertEqual(p.identity["title"], "Cash transfers in Somalia")
        self.assertEqual(p.identity["doi"], "10.1/x")
        self.assertEqual(p.identity["publication_year"], 2021)
        self.assertEqual(p.identity["openalex_topics"], [{"id": "https://openalex.org/T1"}])

    def test_other_document_types_are_ignored_without_a_skip_reason(self):
        with tempfile.TemporaryDirectory() as root:
            make_index(root, card_extra={"doc_type": "lecture_notes"})
            self.assertEqual(eligible_papers(root), ([], {}))

    def test_unusable_papers_are_skipped_with_a_reason_and_never_raise(self):
        cases = {
            "needs indexing": dict(card_extra={"needs_indexing": True}),
            "no transcript file": dict(write_md=False),
            "no page markers": dict(md_text="plain text with no markers"),
            "invalid file_id": dict(file_id="../x"),
        }
        for needle, kwargs in cases.items():
            with self.subTest(needle=needle), tempfile.TemporaryDirectory() as root:
                make_index(root, **kwargs)
                papers, skipped = eligible_papers(root)
                self.assertEqual(papers, [])
                self.assertEqual(len(skipped), 1)
                self.assertIn(needle, next(iter(skipped.values())))

    def test_an_empty_index_is_fine(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(eligible_papers(root), ([], {}))


if __name__ == "__main__":
    unittest.main()
