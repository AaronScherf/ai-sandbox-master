import unittest
from unittest.mock import patch

from common.ollama_utils import OLLAMA_TIMEOUT
from video_notes.synthesize import build_synthesis_prompt, synthesize_group_note
from video_notes.transcribe import TranscriptSegment
from video_notes.youtube_metadata import VideoMetadata


def _video(video_id, title, url):
    return VideoMetadata(
        video_id=video_id, url=url, title=title, channel_id="UC1", playlist_id=None,
        playlist_title=None, playlist_index=None, upload_date="20260101", duration=100.0,
    )


class TestBuildSynthesisPrompt(unittest.TestCase):
    def test_single_video_uses_its_own_title_as_label(self):
        videos_by_id = {"A": _video("A", "Intro to Eigenvalues", "https://youtube.com/watch?v=A")}
        transcripts_by_id = {"A": [TranscriptSegment(75.0, 80.0, "an eigenvalue is")]}
        prompt = build_synthesis_prompt("Intro to Eigenvalues", ["A"], videos_by_id, transcripts_by_id)
        self.assertIn("[Intro to Eigenvalues @ 01:15](https://youtube.com/watch?v=A&t=75s):", prompt)

    def test_multi_video_group_labels_lectures_in_order(self):
        videos_by_id = {
            "A": _video("A", "Real Analysis 1", "https://youtube.com/watch?v=A"),
            "B": _video("B", "Real Analysis 2", "https://youtube.com/watch?v=B"),
        }
        transcripts_by_id = {
            "A": [TranscriptSegment(0.0, 1.0, "first")],
            "B": [TranscriptSegment(65.0, 70.0, "second")],
        }
        prompt = build_synthesis_prompt("Real Analysis", ["A", "B"], videos_by_id, transcripts_by_id)
        self.assertIn("[Lecture 1 @ 00:00](https://youtube.com/watch?v=A&t=0s): first", prompt)
        self.assertIn("[Lecture 2 @ 01:05](https://youtube.com/watch?v=B&t=65s): second", prompt)


class TestSynthesizeGroupNote(unittest.TestCase):
    @patch("video_notes.synthesize.call_ollama")
    def test_returns_model_output_on_success(self, mock_call):
        mock_call.return_value = "# Notes\n..."
        self.assertEqual(synthesize_group_note("prompt", model="qwen2.5:7b-instruct"), "# Notes\n...")

    @patch("video_notes.synthesize.call_ollama", return_value=None)
    def test_returns_none_when_ollama_unreachable(self, mock_call):
        self.assertIsNone(synthesize_group_note("prompt"))

    @patch("video_notes.synthesize.call_ollama", return_value=OLLAMA_TIMEOUT)
    def test_returns_none_on_timeout(self, mock_call):
        self.assertIsNone(synthesize_group_note("prompt"))
