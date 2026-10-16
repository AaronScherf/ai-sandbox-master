import tempfile
import unittest

from core.indexer.index_card import IDENTITY_FIELDS, find_card_by_file_id, load_shard, save_shard, set_card_fields


def _seed(root, file_id="f1", course="economics"):
    save_shard(root, course, [{"file_id": file_id, "path": "a.md", "course": course, "summary": "keep me"}])


class TestSetCardFields(unittest.TestCase):
    def test_sets_identity_and_leaves_everything_else(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            self.assertTrue(set_card_fields(root, "f1", {"openalex_id": "https://openalex.org/W1", "doi": "10.1/x"}))
            card = find_card_by_file_id(root, "f1")[1]
            self.assertEqual(card["openalex_id"], "https://openalex.org/W1")
            self.assertEqual(card["summary"], "keep me")
            self.assertEqual(card["path"], "a.md")

    def test_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            set_card_fields(root, "f1", {"doi": "10.1/x"})
            first = load_shard(root, "economics")
            set_card_fields(root, "f1", {"doi": "10.1/x"})
            self.assertEqual(load_shard(root, "economics"), first)

    def test_missing_card_returns_false(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(set_card_fields(root, "nope", {"doi": "10.1/x"}))

    def test_non_identity_keys_are_refused(self):
        with tempfile.TemporaryDirectory() as root:
            _seed(root)
            with self.assertRaises(ValueError):
                set_card_fields(root, "f1", {"path": "evil.md"})
            self.assertEqual(find_card_by_file_id(root, "f1")[1]["path"], "a.md")

    def test_identity_field_set_is_the_documented_one(self):
        self.assertEqual(IDENTITY_FIELDS, {"openalex_id", "doi", "openalex_topics", "publication_year"})


if __name__ == "__main__":
    unittest.main()
