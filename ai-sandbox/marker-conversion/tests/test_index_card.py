import os
import tempfile
import unittest
from unittest.mock import MagicMock

from index_card import (
    compute_file_id,
    derive_course,
    load_courses,
    load_shard,
    save_courses,
    save_shard,
    cosine_similarity,
    generate_index_card,
    make_failure_card,
    recompute_course_entry,
)


def _fake_client(doc_type="textbook", has_solutions=False, level="introductory"):
    client = MagicMock()
    gen_response = MagicMock()
    gen_response.text = (
        '{"title": "Linear Algebra Done Right", "doc_type": "%s", '
        '"summary": "Covers vector spaces and eigenvalues.", '
        '"level": "%s", "has_solutions": %s}'
        % (doc_type, level, str(has_solutions).lower())
    )
    client.models.generate_content.return_value = gen_response

    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1, 0.2, 0.3]
    embed_response.embeddings = [embedding]
    client.models.embed_content.return_value = embed_response
    return client


class TestComputeFileId(unittest.TestCase):
    def test_same_bytes_produce_same_id_regardless_of_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "nested", "b.pdf")
            os.makedirs(os.path.dirname(b))
            for p in (a, b):
                with open(p, "wb") as f:
                    f.write(b"%PDF-1.4 fake content for hashing")
            self.assertEqual(compute_file_id(a), compute_file_id(b))

    def test_different_bytes_produce_different_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "b.pdf")
            with open(a, "wb") as f:
                f.write(b"content one")
            with open(b, "wb") as f:
                f.write(b"content two")
            self.assertNotEqual(compute_file_id(a), compute_file_id(b))

    def test_id_is_a_short_hex_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "a.pdf")
            with open(p, "wb") as f:
                f.write(b"x")
            file_id = compute_file_id(p)
            self.assertEqual(len(file_id), 16)
            int(file_id, 16)  # raises ValueError if not valid hex


class TestDeriveCourse(unittest.TestCase):
    def test_notes_path(self):
        self.assertEqual(
            derive_course("academic_notes/math-camp/ta_notes/foo.pdf"), "math-camp"
        )

    def test_resources_path(self):
        self.assertEqual(
            derive_course("academic_resources/econ-101/textbooks-and-papers/bar.pdf"),
            "econ-101",
        )

    def test_handles_backslashes(self):
        self.assertEqual(
            derive_course(r"academic_notes\math-camp\handwritten_notes\x.pdf"), "math-camp"
        )

    def test_raises_on_too_short_path(self):
        with self.assertRaises(ValueError):
            derive_course("just_a_file.pdf")


class TestShardIO(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_shard(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards = [{"file_id": "abc", "path": "x.md"}]
            save_shard(tmp, "math-camp", cards)
            self.assertEqual(load_shard(tmp, "math-camp"), cards)

    def test_load_missing_courses_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_courses(tmp), {})

    def test_save_then_load_courses_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            courses = {"math-camp": {"course": "math-camp", "file_count": 1}}
            save_courses(tmp, courses)
            self.assertEqual(load_courses(tmp), courses)


class TestCosineSimilarity(unittest.TestCase):
    def test_identical_vectors_score_one(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0, places=6)

    def test_orthogonal_vectors_score_zero(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0, places=6)

    def test_not_sensitive_to_magnitude(self):
        # Confirmed live against the real API that gemini-embedding-001
        # does NOT return unit-normalized vectors -- this is the case that
        # would silently break if cosine_similarity assumed unit length.
        a = [1.0, 1.0]
        b = [50.0, 50.0]
        self.assertAlmostEqual(cosine_similarity(a, b), 1.0, places=6)

    def test_empty_vector_scores_zero_not_a_crash(self):
        self.assertEqual(cosine_similarity([], [1.0, 2.0]), 0.0)


class TestRecomputeCourseEntry(unittest.TestCase):
    def test_computes_centroid_and_file_count_from_shard_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "topics": ["linear-algebra"]},
                {"file_id": "b", "embedding": [0.0, 1.0], "topics": ["linear-algebra", "real-analysis"]},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["file_count"], 2)
            self.assertEqual(courses["math-camp"]["embedding"], [0.5, 0.5])
            self.assertIn("linear-algebra", courses["math-camp"]["predominant_topics"])

    def test_title_is_a_readable_form_of_the_course_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0], "topics": []}])
            recompute_course_entry(tmp, "math-camp")
            self.assertEqual(load_courses(tmp)["math-camp"]["title"], "Math Camp")

    def test_excludes_orphaned_cards_from_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [1.0, 0.0], "topics": [], "orphaned": True},
                {"file_id": "b", "embedding": [0.0, 1.0], "topics": []},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["file_count"], 1)
            self.assertEqual(courses["math-camp"]["embedding"], [0.0, 1.0])

    def test_removes_course_entry_when_shard_becomes_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [{"file_id": "a", "embedding": [1.0], "topics": []}])
            recompute_course_entry(tmp, "math-camp")
            save_shard(tmp, "math-camp", [])
            recompute_course_entry(tmp, "math-camp")
            self.assertNotIn("math-camp", load_courses(tmp))

    def test_cards_missing_topics_are_missing_from_the_embedding_but_not_a_crash(self):
        # needs_indexing cards (Task 2) have embedding: [] -- must not
        # poison the centroid computation.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "math-camp", [
                {"file_id": "a", "embedding": [], "topics": [], "needs_indexing": True},
                {"file_id": "b", "embedding": [1.0, 0.0], "topics": []},
            ])
            recompute_course_entry(tmp, "math-camp")
            courses = load_courses(tmp)
            self.assertEqual(courses["math-camp"]["embedding"], [1.0, 0.0])
            self.assertEqual(courses["math-camp"]["file_count"], 2)


class TestGenerateIndexCard(unittest.TestCase):
    def test_builds_a_complete_card_from_llm_and_embedding_responses(self):
        client = _fake_client()
        card = generate_index_card(
            file_id="abc123",
            path="academic_resources/math-camp/textbooks-and-papers/processed_outputs/Axler/Axler.md",
            source_pdf_path="academic_resources/math-camp/textbooks-and-papers/Axler.pdf",
            course="math-camp",
            folder_category="textbooks-and-papers",
            content_sample="Chapter 1: Vector Spaces...",
            page_count=404,
            client=client,
        )
        self.assertEqual(card["file_id"], "abc123")
        self.assertEqual(card["title"], "Linear Algebra Done Right")
        self.assertEqual(card["doc_type"], "textbook")
        self.assertEqual(card["summary"], "Covers vector spaces and eigenvalues.")
        self.assertEqual(card["level"], "introductory")
        self.assertFalse(card["has_solutions"])
        self.assertEqual(card["page_count"], 404)
        self.assertEqual(card["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(card["embedding_model"], "gemini-embedding-001:768")
        self.assertEqual(card["topics"], [])
        self.assertFalse(card["needs_indexing"])
        self.assertIsNone(card["rag_md_path"])
        self.assertNotIn("orphaned", card)

    def test_falls_back_to_folder_category_when_llm_doc_type_is_unrecognized(self):
        client = _fake_client(doc_type="something_weird")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["doc_type"], "ta_notes")

    def test_falls_back_to_introductory_when_llm_level_is_unrecognized(self):
        client = _fake_client(level="expert-plus")
        card = generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="text", page_count=10, client=client,
        )
        self.assertEqual(card["level"], "introductory")

    def test_embeds_title_and_summary_not_raw_content(self):
        client = _fake_client()
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="ta_notes", content_sample="a" * 50000, page_count=10, client=client,
        )
        embed_call = client.models.embed_content.call_args
        self.assertIn("Linear Algebra Done Right", embed_call.kwargs["contents"])
        self.assertIn("Covers vector spaces", embed_call.kwargs["contents"])
        self.assertNotIn("a" * 50000, embed_call.kwargs["contents"])

    def test_prompt_mentions_folder_category_as_a_hint_not_a_verdict(self):
        client = _fake_client()
        generate_index_card(
            file_id="x", path="p.md", source_pdf_path="p.pdf", course="math-camp",
            folder_category="problem_sets", content_sample="text", page_count=10, client=client,
        )
        prompt = client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("problem_sets", prompt)


class TestMakeFailureCard(unittest.TestCase):
    def test_minimal_card_carries_enough_to_be_reconciled_later(self):
        card = make_failure_card(
            file_id="abc123", path="p.md", source_pdf_path="p.pdf",
            course="math-camp", folder_category="ta_notes",
        )
        self.assertEqual(card["file_id"], "abc123")
        self.assertEqual(card["path"], "p.md")
        self.assertEqual(card["source_pdf_path"], "p.pdf")
        self.assertEqual(card["course"], "math-camp")
        self.assertEqual(card["doc_type"], "ta_notes")
        self.assertTrue(card["needs_indexing"])
        self.assertEqual(card["embedding"], [])


if __name__ == "__main__":
    unittest.main()
