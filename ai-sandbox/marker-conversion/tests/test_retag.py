import unittest
from unittest.mock import MagicMock

from retag import build_clusters, fuzzy_match_tag, discover_tags


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


if __name__ == "__main__":
    unittest.main()
