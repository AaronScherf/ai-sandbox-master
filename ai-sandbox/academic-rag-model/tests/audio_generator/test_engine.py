import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from audio_generator.engine import synthesize_speech


class TestSynthesizeSpeech(unittest.TestCase):
    @patch("audio_generator.engine.AudioSegment")
    @patch("audio_generator.engine._synthesize_piper_wav")
    def test_piper_engine_receives_the_given_text(self, mock_piper, mock_audio_segment):
        mock_audio_segment.from_wav.return_value = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.mp3")
            synthesize_speech("hello world", output_path, engine="piper")
        mock_piper.assert_called_once()
        self.assertEqual(mock_piper.call_args[0][0], "hello world")

    @patch("audio_generator.engine.AudioSegment")
    @patch("audio_generator.engine._synthesize_kokoro_wav")
    def test_kokoro_engine_receives_the_given_text(self, mock_kokoro, mock_audio_segment):
        mock_audio_segment.from_wav.return_value = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.mp3")
            synthesize_speech("hello world", output_path, engine="kokoro")
        mock_kokoro.assert_called_once()
        self.assertEqual(mock_kokoro.call_args[0][0], "hello world")

    def test_unknown_engine_raises_before_synthesizing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                synthesize_speech("hello", os.path.join(tmp, "out.mp3"), engine="not-a-real-engine")

    @patch("audio_generator.engine.AudioSegment")
    @patch("audio_generator.engine._synthesize_piper_wav")
    def test_exports_mp3_at_the_given_path(self, mock_piper, mock_audio_segment):
        exported_paths = []
        mock_audio_segment.from_wav.return_value.export.side_effect = (
            lambda path, **kw: exported_paths.append(path)
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "out.mp3")
            synthesize_speech("hello", output_path, engine="piper")
        self.assertEqual(exported_paths, [output_path])
