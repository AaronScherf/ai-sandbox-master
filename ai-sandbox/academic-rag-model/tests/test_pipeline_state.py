import tempfile
import unittest

from video_notes.pipeline_state import (
    compute_member_content_hash, load_group_states, load_video_states,
    save_group_states, save_video_state,
)
from video_notes.transcribe import TranscriptSegment


class TestVideoState(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_video_state(tmp, "math-camp", "AAAA111", stage="transcribed", url="https://x")
            states = load_video_states(tmp, "math-camp")
            self.assertEqual(states["AAAA111"]["stage"], "transcribed")

    def test_repeated_saves_merge_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_video_state(tmp, "math-camp", "AAAA111", url="https://x")
            save_video_state(tmp, "math-camp", "AAAA111", stage="transcribed")
            states = load_video_states(tmp, "math-camp")
            self.assertEqual(states["AAAA111"]["url"], "https://x")
            self.assertEqual(states["AAAA111"]["stage"], "transcribed")

    def test_missing_state_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_video_states(tmp, "math-camp"), {})


class TestGroupState(unittest.TestCase):
    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_group_states(tmp, "math-camp", {"g_0001": {"slug": "real-analysis"}})
            self.assertEqual(load_group_states(tmp, "math-camp"), {"g_0001": {"slug": "real-analysis"}})


class TestComputeMemberContentHash(unittest.TestCase):
    def test_member_order_does_not_affect_the_hash(self):
        transcripts = {"A": [TranscriptSegment(0.0, 1.0, "hello")], "B": [TranscriptSegment(0.0, 1.0, "world")]}
        self.assertEqual(
            compute_member_content_hash(["A", "B"], transcripts),
            compute_member_content_hash(["B", "A"], transcripts),
        )

    def test_changed_transcript_text_changes_the_hash(self):
        transcripts_a = {"A": [TranscriptSegment(0.0, 1.0, "hello")]}
        transcripts_b = {"A": [TranscriptSegment(0.0, 1.0, "hello there")]}
        self.assertNotEqual(
            compute_member_content_hash(["A"], transcripts_a),
            compute_member_content_hash(["A"], transcripts_b),
        )
