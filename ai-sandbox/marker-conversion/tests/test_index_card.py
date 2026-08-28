import os
import tempfile
import unittest

from index_card import (
    compute_file_id,
    derive_course,
    load_courses,
    load_shard,
    save_courses,
    save_shard,
    cosine_similarity,
)


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


if __name__ == "__main__":
    unittest.main()
