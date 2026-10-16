import json
import os
import tempfile
import unittest

from core.indexer.index_card import compute_file_id, find_card_by_file_id, save_shard
from pipelines.convert_journal_articles.identity import attach_identity, identity_fields

SIDECAR = {
    "title": "T", "authors": ["A"], "year": 2021, "doi": "10.1/x", "openalex_id": "https://openalex.org/W9",
    "concepts": ["Economics"], "topics": [{"id": "https://openalex.org/T1", "display_name": "Aid", "score": 0.9}],
    "source_tier": "oa", "relevance_score": 0.5, "page_count": 12,
}


def _paper(root, sidecar=None, raw=None):
    pdf = os.path.join(root, "economics", "a.pdf")
    os.makedirs(os.path.dirname(pdf))
    with open(pdf, "wb") as f:
        f.write(b"%PDF-1.4 mock")
    side = os.path.join(root, "economics", "a.meta.json")
    if sidecar is not None:
        with open(side, "w", encoding="utf-8") as f:
            json.dump(sidecar, f)
    if raw is not None:
        with open(side, "w", encoding="utf-8") as f:
            f.write(raw)
    return pdf


class TestIdentityFields(unittest.TestCase):
    def test_maps_sidecar_to_card_fields(self):
        with tempfile.TemporaryDirectory() as root:
            f = identity_fields(_paper(root, SIDECAR))
        self.assertEqual(f["openalex_id"], "https://openalex.org/W9")
        self.assertEqual(f["doi"], "10.1/x")
        self.assertEqual(f["publication_year"], 2021)
        self.assertEqual(f["openalex_topics"], [{"id": "https://openalex.org/T1", "display_name": "Aid", "score": 0.9}])

    def test_missing_sidecar_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(identity_fields(_paper(root)))

    def test_corrupt_sidecar_is_none_not_a_crash(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(identity_fields(_paper(root, raw="{not json")))

    def test_non_object_sidecar_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(identity_fields(_paper(root, raw="[1, 2]")))

    def test_partial_sidecar_drops_absent_keys(self):
        with tempfile.TemporaryDirectory() as root:
            f = identity_fields(_paper(root, {"title": "T", "openalex_id": "https://openalex.org/W9", "doi": None}))
        self.assertEqual(f, {"openalex_id": "https://openalex.org/W9"})

    def test_sidecar_name_matches_discovery(self):
        from discovery.discover_journal_articles.metadata_sidecar import sidecar_path
        from pipelines.convert_journal_articles.identity import _sidecar
        self.assertEqual(_sidecar("x/a.pdf"), sidecar_path("x/a.pdf"))


class TestAttachIdentity(unittest.TestCase):
    def test_stamps_the_card_for_this_pdf(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = _paper(root, SIDECAR)
            fid = compute_file_id(pdf)
            save_shard(root, "economics", [{"file_id": fid, "path": "economics/a.md", "course": "economics"}])
            self.assertTrue(attach_identity(pdf, root))
            self.assertEqual(find_card_by_file_id(root, fid)[1]["doi"], "10.1/x")

    def test_no_card_yet_is_false(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(attach_identity(_paper(root, SIDECAR), root))

    def test_no_sidecar_is_false_and_card_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            pdf = _paper(root)
            fid = compute_file_id(pdf)
            save_shard(root, "economics", [{"file_id": fid, "path": "p.md", "course": "economics"}])
            self.assertFalse(attach_identity(pdf, root))
            self.assertNotIn("doi", find_card_by_file_id(root, fid)[1])


if __name__ == "__main__":
    unittest.main()
