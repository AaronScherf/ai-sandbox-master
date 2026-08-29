import os
import tempfile
import unittest

from chunk_index import chunks_path, load_chunks, save_chunks


class TestChunkStorage(unittest.TestCase):
    def test_load_missing_shard_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_chunks(tmp, "math-camp"), [])

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            chunks = [{"chunk_id": "abc-000", "file_id": "abc", "text": "hello"}]
            save_chunks(tmp, "math-camp", chunks)
            self.assertEqual(load_chunks(tmp, "math-camp"), chunks)

    def test_chunks_path_lives_under_index_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = chunks_path(tmp, "math-camp")
            self.assertTrue(path.replace("\\", "/").endswith(".index/chunks/math-camp.json"))

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_chunks(tmp, "math-camp", [])
            self.assertTrue(os.path.isdir(os.path.join(tmp, ".index", "chunks")))


if __name__ == "__main__":
    unittest.main()
