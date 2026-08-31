import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from indexer.index_card import load_shard, load_tags, save_shard
from indexer.retag import (
    assign_tags, discover_tags, ensure_minimum_coverage, fuzzy_match_tag, retag,
    write_tags_to_frontmatter,
)


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


def _fake_discovery_client(candidates=None, anchor_embedding=None):
    """candidates: list of (tag, definition) tuples the holistic proposal
    call returns. anchor_embedding: what embed_content returns for every
    tag anchor requested (same value for all, unless overridden per-test
    with a side_effect)."""
    if candidates is None:
        candidates = [("linear-algebra", "Linear algebra: vector spaces and linear maps.")]
    if anchor_embedding is None:
        anchor_embedding = [1.0, 0.0]

    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = json.dumps({
        "tags": [{"tag": tag, "definition": definition} for tag, definition in candidates]
    })
    client.models.generate_content.return_value = gen_response

    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = anchor_embedding
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestDiscoverTags(unittest.TestCase):
    def _cards(self, n, embedding, prefix="f"):
        return [
            ("math-camp", {"file_id": f"{prefix}{i}", "title": f"T{i}", "summary": f"S{i}", "embedding": embedding})
            for i in range(n)
        ]

    def test_no_cards_proposes_nothing(self):
        updated, stats = discover_tags([], [], client=MagicMock())
        self.assertEqual(updated, [])
        self.assertEqual(stats["candidates_proposed"], 0)
        self.assertEqual(stats["tags_minted"], 0)

    def test_candidate_with_enough_real_matches_is_minted(self):
        # 3 cards, all embedding [1.0, 0.0] -- the proposed anchor is the
        # same vector, so cosine similarity is 1.0, comfortably above the
        # default TAG_ASSIGNMENT_THRESHOLD (0.65).
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_discovery_client(
            candidates=[("linear-algebra", "d")], anchor_embedding=[1.0, 0.0],
        )
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(stats["candidates_proposed"], 1)
        self.assertEqual(stats["tags_minted"], 1)
        self.assertEqual(stats["candidates_rejected"], 0)
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["tag"], "linear-algebra")
        self.assertEqual(updated[0]["embedding"], [1.0, 0.0])

    def test_candidate_with_too_few_real_matches_is_rejected_not_minted(self):
        # The LLM proposed a tag, but its anchor doesn't actually match
        # enough real cards (min_matches=3 by default) -- must not be
        # minted just on the LLM's say-so. Anchor [0.0, 1.0] is
        # orthogonal (similarity 0.0) to the cards' [1.0, 0.0].
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_discovery_client(
            candidates=[("unrelated-tag", "d")], anchor_embedding=[0.0, 1.0],
        )
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(stats["tags_minted"], 0)
        self.assertEqual(stats["candidates_rejected"], 1)
        self.assertEqual(updated, [])

    def test_candidate_matching_existing_vocabulary_reuses_not_mints(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_discovery_client(candidates=[("Linear Algebra", "d")])  # fuzzy-matches existing
        known = [{"tag": "linear-algebra", "embedding": [0.9, 0.1]}]
        updated, stats = discover_tags(cards, known, client)
        self.assertEqual(stats["tags_minted"], 0)
        self.assertEqual(stats["tags_reused"], 1)
        self.assertEqual(updated, known)  # unchanged -- no new embedding call needed
        client.models.embed_content.assert_not_called()

    def test_multiple_candidates_from_one_holistic_call(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_discovery_client(
            candidates=[("linear-algebra", "d1"), ("real-analysis", "d2")],
            anchor_embedding=[1.0, 0.0],  # both anchors match these cards for this test
        )
        updated, stats = discover_tags(cards, [], client)
        self.assertEqual(client.models.generate_content.call_count, 1)  # one holistic call, not one per tag
        self.assertEqual(stats["candidates_proposed"], 2)
        self.assertEqual(stats["tags_minted"], 2)
        self.assertEqual(sorted(t["tag"] for t in updated), ["linear-algebra", "real-analysis"])

    def test_proposal_uses_every_cards_title_and_summary_at_once(self):
        cards = self._cards(3, [1.0, 0.0])
        client = _fake_discovery_client()
        discover_tags(cards, [], client)
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        for i in range(3):
            self.assertIn(f"T{i}", prompt)
            self.assertIn(f"S{i}", prompt)


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

    def test_fallback_origin_tags_are_never_assigned_to_other_cards(self):
        # A fallback tag (spec §5.4) was minted to describe ONE specific
        # document -- its anchor is a generic paraphrase of that single
        # card's title+summary, so in a small, topically-homogeneous
        # corpus it can drift above TAG_ASSIGNMENT_THRESHOLD against
        # unrelated cards too (confirmed live: a "syllabus" fallback tag
        # scored 0.73 against an unrelated Linear Algebra card). Fallback
        # tags must never leak onto a different document via assign_tags,
        # no matter how similar -- that's what distinguishes them from
        # tags that cleared discover_tags' corpus-wide validation.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            known = [{"tag": "syllabus", "embedding": [1.0, 0.0], "origin": "fallback"}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            assign_tags(tmp, all_cards, known)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], [])

    def test_preview_is_returned_even_when_not_dry_run(self):
        # retag() (spec §5.4) needs this run's fresh per-card tags
        # in-memory, without a disk re-read that would be stale in
        # dry_run mode -- so preview is always populated, not just under
        # dry_run.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            known = [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}]
            all_cards = [("math-camp", {"file_id": "a", "embedding": [1.0, 0.0]})]
            stats = assign_tags(tmp, all_cards, known)
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
            client = _fake_discovery_client(
                candidates=[("linear-algebra", "d")], anchor_embedding=[1.0, 0.0],
            )

            stats = retag(tmp, client)

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
            client = _fake_discovery_client(
                candidates=[("linear-algebra", "d")], anchor_embedding=[1.0, 0.0],
            )

            stats = retag(tmp, client, dry_run=True)

            self.assertEqual(stats["tags_minted"], 1)  # discovery still ran/reported
            self.assertEqual(load_tags(tmp), [])        # but nothing persisted
            for card in load_shard(tmp, "math-camp"):
                self.assertEqual(card["tags"], [])       # cards untouched


def _fake_fallback_client(tag="syllabus", definition="A course syllabus."):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = json.dumps({"tag": tag, "definition": definition})
    client.models.generate_content.return_value = gen_response
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.3, 0.3]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestEnsureMinimumCoverage(unittest.TestCase):
    def test_untagged_card_gets_a_new_fallback_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [9.0, 9.0], "tags": []}])
            all_cards = [("math-camp", {"file_id": "a", "title": "Summer Camp", "summary": "Overview.", "tags": []})]
            client = _fake_fallback_client(tag="syllabus")

            updated_tags, stats = ensure_minimum_coverage(tmp, all_cards, [], client)

            self.assertEqual(stats["fallback_tags_minted"], 1)
            self.assertEqual(stats["cards_covered"], 1)
            self.assertEqual([t["tag"] for t in updated_tags], ["syllabus"])
            self.assertEqual(updated_tags[0]["origin"], "fallback")
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["syllabus"])

    def test_assigned_regardless_of_anchor_similarity_to_the_card(self):
        # The anchor was derived to describe THIS card specifically --
        # requiring it to also clear a similarity threshold against the
        # same card would reintroduce the exact anchor-vs-document gap
        # §5.2 already had to fix (spec §5.4). The card's embedding
        # ([-5.0, 0.001]) and the fake anchor ([0.3, 0.3], from
        # _fake_fallback_client) point in near-opposite directions
        # (negative cosine similarity) -- deliberately, to prove the tag
        # still gets assigned even though a similarity check would fail.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [-5.0, 0.001], "tags": []}])
            all_cards = [("math-camp", {"file_id": "a", "title": "T", "summary": "S", "tags": []})]
            client = _fake_fallback_client(tag="syllabus")
            ensure_minimum_coverage(tmp, all_cards, [], client)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["syllabus"])

    def test_already_tagged_cards_are_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": ["linear-algebra"]}])
            all_cards = [("math-camp", {"file_id": "a", "title": "T", "summary": "S", "tags": ["linear-algebra"]})]
            client = MagicMock()
            _, stats = ensure_minimum_coverage(tmp, all_cards, [{"tag": "linear-algebra", "embedding": [1.0, 0.0]}], client)
            self.assertEqual(stats["cards_covered"], 0)
            client.models.generate_content.assert_not_called()
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], ["linear-algebra"])

    def test_two_untagged_cards_proposing_the_same_fallback_converge_on_one_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "tags": []},
                {"file_id": "b", "embedding": [0.0, 1.0], "tags": []},
            ])
            all_cards = [
                ("math-camp", {"file_id": "a", "title": "T1", "summary": "S1", "tags": []}),
                ("math-camp", {"file_id": "b", "title": "T2", "summary": "S2", "tags": []}),
            ]
            client = _fake_fallback_client(tag="syllabus")  # both proposals return the same tag
            updated_tags, stats = ensure_minimum_coverage(tmp, all_cards, [], client)
            self.assertEqual(stats["fallback_tags_minted"], 1)
            self.assertEqual(stats["fallback_tags_reused"], 1)
            self.assertEqual(len(updated_tags), 1)
            cards = {c["file_id"]: c for c in load_shard(tmp, "math-camp")}
            self.assertEqual(cards["a"]["tags"], ["syllabus"])
            self.assertEqual(cards["b"]["tags"], ["syllabus"])

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0, 0.0], "tags": []}])
            all_cards = [("math-camp", {"file_id": "a", "title": "T", "summary": "S", "tags": []})]
            client = _fake_fallback_client(tag="syllabus")
            _, stats = ensure_minimum_coverage(tmp, all_cards, [], client, dry_run=True)
            self.assertEqual(stats["fallback_tags_minted"], 1)
            self.assertEqual(load_shard(tmp, "math-camp")[0]["tags"], [])  # unchanged
            self.assertEqual(load_tags(tmp), [])  # unchanged


def _write_md(tmp, rel_path, content):
    full_path = os.path.join(tmp, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


class TestWriteTagsToFrontmatter(unittest.TestCase):
    def test_patches_the_tags_line_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_md(
                tmp, "notes/a.md",
                "---\nsource_pdf: a.pdf\nrouting: hybrid\ntags: []\n---\n\nBody content.\n",
            )
            save_shard(tmp, "math-camp", [{"file_id": "a", "path": "notes/a.md",
                                            "tags": ["linear-algebra", "real-analysis"]}])
            stats = write_tags_to_frontmatter(tmp)
            self.assertEqual(stats["frontmatter_updated"], 1)
            with open(md_path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("tags: [linear-algebra, real-analysis]", content)
            self.assertIn("source_pdf: a.pdf", content)  # other frontmatter fields untouched
            self.assertIn("routing: hybrid", content)
            self.assertIn("Body content.", content)  # body untouched

    def test_empty_tags_list_renders_as_empty_brackets(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_md(tmp, "notes/a.md", "---\ntags: []\n---\n\nBody.\n")
            save_shard(tmp, "math-camp", [{"file_id": "a", "path": "notes/a.md", "tags": []}])
            write_tags_to_frontmatter(tmp)
            with open(md_path, encoding="utf-8") as f:
                self.assertIn("tags: []", f.read())

    def test_file_with_no_frontmatter_is_skipped_not_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_md(tmp, "notes/a.md", "<!-- page 1 -->\n\nNo frontmatter here.\n")
            save_shard(tmp, "math-camp", [{"file_id": "a", "path": "notes/a.md", "tags": ["linear-algebra"]}])
            stats = write_tags_to_frontmatter(tmp)
            self.assertEqual(stats["skipped_no_frontmatter"], 1)
            self.assertEqual(stats["frontmatter_updated"], 0)
            with open(md_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "<!-- page 1 -->\n\nNo frontmatter here.\n")

    def test_already_up_to_date_file_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            md_path = _write_md(tmp, "notes/a.md", "---\ntags: [linear-algebra]\n---\n\nBody.\n")
            save_shard(tmp, "math-camp", [{"file_id": "a", "path": "notes/a.md", "tags": ["linear-algebra"]}])
            mtime_before = os.path.getmtime(md_path)
            stats = write_tags_to_frontmatter(tmp)
            self.assertEqual(stats["frontmatter_updated"], 0)
            self.assertEqual(os.path.getmtime(md_path), mtime_before)

    def test_orphaned_card_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "path": "notes/a.md",
                                            "tags": ["linear-algebra"], "orphaned": True}])
            stats = write_tags_to_frontmatter(tmp)
            self.assertEqual(stats["frontmatter_updated"], 0)
            self.assertEqual(stats["skipped_no_frontmatter"], 0)

    def test_missing_md_file_is_skipped_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "path": "notes/does-not-exist.md",
                                            "tags": ["linear-algebra"]}])
            stats = write_tags_to_frontmatter(tmp)  # must not raise
            self.assertEqual(stats["frontmatter_updated"], 0)


if __name__ == "__main__":
    unittest.main()
