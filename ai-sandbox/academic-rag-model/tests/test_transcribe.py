import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.transcribe import TranscriptSegment, load_transcript, save_transcript, transcribe_audio


class TestTranscribeAudio(unittest.TestCase):
    @patch("faster_whisper.WhisperModel")
    def test_converts_whisper_segments_to_transcript_segments(self, mock_model_cls):
        fake_segment = MagicMock(start=1.5, end=3.0, text=" hello world ")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([fake_segment], MagicMock())
        mock_model_cls.return_value = mock_model

        result = transcribe_audio("fake.mp3", model_size="small", device="cpu", compute_type="int8")

        self.assertEqual(result, [TranscriptSegment(start=1.5, end=3.0, text="hello world")])
        mock_model_cls.assert_called_once_with("small", device="cpu", compute_type="int8")


class TestTranscriptRoundTrip(unittest.TestCase):
    def test_save_then_load_preserves_segments(self):
        segments = [TranscriptSegment(start=0.0, end=1.0, text="a"), TranscriptSegment(start=1.0, end=2.5, text="b")]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "AAAA111.json")
            save_transcript(path, segments)
            self.assertEqual(load_transcript(path), segments)
