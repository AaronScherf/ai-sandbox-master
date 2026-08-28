import tempfile
import unittest
from unittest.mock import MagicMock

from index_card import load_shard, load_tags, save_shard
from retag import assign_tags, build_clusters, discover_tags, fuzzy_match_tag, retag


class TestBuildClusters(unittest.TestCase):
    def test_two_disjoint_similar_groups_become_two_clusters(self):
        embeddings = [
            [1.0, 0.0], [0.99, 0.01], [0.98, 0.02],   # group A -- mutually similar
            [0.0, 1.0], [0.01, 0.99], [0.02, 0.98],   # group B -- mutually similar, unlike A
        ]
        clusters = build_clusters(embeddings, threshold=0.9)
        self.assertEqual(len(clusters), 2)
        sizes = sorted(len(c) for c in clusters)
        self.assertEqual(sizes, [3, 3])

    def test_dissimilar_singletons_stay_separate(self):
        embeddings = [[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]]
        clusters = build_clusters(embeddings, threshold=0.9)
        self.assertEqual(len(clusters), 3)

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(build_clusters([], threshold=0.9), [])

    def test_transitive_bridge_merges_into_one_component(self):
        # A-B similar, B-C similar, A-C NOT similar -- still one component,
        # because connected components are transitive. This is exactly the
        # failure mode spec §5 motivates splitting discovery from
        # assignment over: a file bridging two topics merges their
        # clusters rather than getting two tags.
        embeddings = [[1.0, 0.0], [0.7, 0.7], [0.0, 1.0]]
        clusters = build_clusters(embeddings, threshold=0.5)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(sorted(clusters[0]), [0, 1, 2])


class TestFuzzyMatchTag(unittest.TestCase):
    def test_exact_match_reused(self):
        known = [{"tag": "linear-algebra", "embedding": [1.0]}]
        result = fuzzy_match_tag("linear-algebra", known)
        self.assertEqual(result["tag"], "linear-algebra")

    def test_close_variant_reused(self):
        known = [{"tag": "linear-algebra", "embedding": [1.0]}]
        result = fuzzy_match_tag("Linear Algebra", known)
        self.assertEqual(result["tag"], "linear-algebra")

    def test_unrelated_tag_not_matched(self):
        known = [{"tag": "linear-algebra", "embedding": [1.0]}]
        result = fuzzy_match_tag("real-analysis", known)
        self.assertIsNone(result)

    def test_empty_vocabulary_never_matches(self):
        self.assertIsNone(fuzzy_match_tag("anything", []))


def _fake_naming_client(tag="linear-algebra", definition="Linear algebra: vector spaces and linear maps."):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = '{"tag": "%s", "definition": "%s"}' % (tag, definition)
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.5, 0.5]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestDiscoverTags(unittest.TestCase):
    def _cards(self, n, embedding):
        return [
            ("math-camp", {"file_id": f"f{i}", "title": f"T{i}", "summary": f"S{i}", "embedding": embedding})
            for i in range(n)
        ]

    def test_no_cards_mints_nothing(self):
        updated, stats = discover_tags([], [], client=MagicMock())
        self.assertEqual(updated, [])
        self.assertEqual(stats["clusters_found"], 0)
        self.assertEqual(stats["tags_minted"], 0)

    def test_cluster_below_min_size_mints_nothing(self):
        cards = self._cards(2, [1.0, 0.0])  # below default MIN_TAG_CLUSTER_SIZE=3
        client = _fake_naming_client()
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(stats["tags_minted"], 0)
        self.assertEqual(updated, [])
        client.models.generate_content.assert_not_called()

    def test_qualifying_cluster_mints_a_new_tag_with_anchor_embedding(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_naming_client(tag="linear-algebra")
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(stats["clusters_found"], 1)
        self.assertEqual(stats["tags_minted"], 1)
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["tag"], "linear-algebra")
        self.assertEqual(updated[0]["embedding"], [0.5, 0.5])

    def test_qualifying_cluster_matching_existing_vocabulary_reuses_not_mints(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_naming_client(tag="Linear Algebra")  # fuzzy-matches existing
        known = [{"tag": "linear-algebra", "embedding": [0.9, 0.1]}]
        updated, stats = discover_tags(cards, known, client)
        self.assertEqual(stats["tags_minted"], 0)
        self.assertEqual(stats["tags_reused"], 1)
        self.assertEqual(updated, known)  # unchanged -- no new embedding call needed
        client.models.embed_content.assert_not_called()

    def test_two_disjoint_qualifying_clusters_mint_two_tags(self):
        cards_a = self._cards(3, [1.0, 0.0])
        cards_b = [
            ("math-camp", {"file_id": f"g{i}", "title": f"T{i}", "summary": f"S{i}", "embedding": [0.0, 1.0]})
            for i in range(3)
        ]
        client = MagicMock()
        responses = [
            '{"tag": "linear-algebra", "definition": "d1"}',
            '{"tag": "real-analysis", "definition": "d2"}',
        ]
        gen_response = MagicMock()
        gen_response.text = responses[0]
        embed_response = MagicMock()
        embedding = MagicMock()
        embedding.values = [0.5, 0.5]
        embed_response.embeddings = [embedding]

        def _side_effect(*args, **kwargs):
            gen_response.text = responses.pop(0)
            return gen_response

        client.models.generate_content.side_effect = _side_effect
        client.models.embed_content.return_value = embed_response

        updated, stats = discover_tags(cards_a + cards_b, [], client)
        self.assertEqual(stats["clusters_found"], 2)
        self.assertEqual(stats["tags_minted"], 2)
        self.assertEqual(sorted(t["tag"] for t in updated), ["linear-algebra", "real-analysis"])


class TestAssignTags(unittest.TestCase):
    def test_card_matching_one_tag_gets_tagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["linear-algebra"])

    def test_card_matching_multiple_tags_gets_all_of_them(self):
        # The actual fix for one-tag-per-file: a card similar to two
        # unrelated tag anchors gets both, with no cluster-membership
        # restriction at all (spec §5.3).
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [0.7, 0.7], "tags": []}])
            known = [
                {"tag": "linear-algebra", "embedding": [1.0, 0.0]},
                {"tag": "probability", "embedding": [0.0, 1.0]},
            ]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [0.7, 0.7]})]
            assign_tags(tmp, all_cards, known, threshold=0.5)
            self.assertEqual(
                sorted(load_shard(tmp, "math-camp")[0]["tags"]), ["linear-algebra", "probability"],
            )

    def test_card_matching_no_tags_gets_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": ["stale"]}])
            known = [{"tag": "real-analysis", "embedding": [0.0, 1.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], [])

    def test_tags_are_replaced_not_appended(self):
        # spec §5.3: a card's tags list is fully replaced each run, not
        # accumulated -- this is what makes tags non-permanent.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "tags": ["old-unrelated-tag"]},
            ])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["linear-algebra"])

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            stats = assign_tags(tmp, all_cards, known, dry_run=True)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], [])  # unchanged
            self.assertIn("preview", stats)
            self.assertEqual(stats["preview"]["math-camp"]["a"], ["linear-algebra"])


class TestRetag(unittest.TestCase):
    def test_end_to_end_mints_and_assigns(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [
                {"file_id": f"f{i}", "title": f"T{i}", "summary": f"S{i}",
                 "embedding": [1.0, 0.0], "tags": []}
                for i in range(3)
            ]
            save_shard(tmp, "math-camp", cards)
            client = _fake_naming_client(tag="linear-algebra")

            # assignment_threshold lowered to match this test's mock anchor
            # embedding ([0.5, 0.5], cosine similarity ~0.71 with the cards'
            # [1.0, 0.0]) -- the default (0.78) is calibrated for real
            # embeddings, not this synthetic fixture.
            stats = retag(tmp, client, assignment_threshold=0.5)

            self.assertEqual(stats["tags_minted"], 1)
            self.assertEqual(stats["cards_tagged"], 3)
            tags_on_disk = load_tags(tmp)
            self.assertEqual(len(tags_on_disk), 1)
            self.assertEqual(tags_on_disk[0]["tag"], "linear-algebra")
            for card in load_shard(tmp, "math-camp"):
                self.assertEqual(card["tags"], ["linear-algebra"])

    def test_dry_run_mints_nothing_persisted_and_writes_no_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [
                {"file_id": f"f{i}", "title": f"T{i}", "summary": f"S{i}",
                 "embedding": [1.0, 0.0], "tags": []}
                for i in range(3)
            ]
            save_shard(tmp, "math-camp", cards)
            client = _fake_naming_client(tag="linear-algebra")

            stats = retag(tmp, client, dry_run=True)

            self.assertEqual(stats["tags_minted"], 1)  # discovery still ran/reported
            self.assertEqual(load_tags(tmp), [])        # but nothing persisted
            for card in load_shard(tmp, "math-camp"):
                self.assertEqual(card["tags"], [])       # cards untouched


if __name__ == "__main__":
    unittest.main()
