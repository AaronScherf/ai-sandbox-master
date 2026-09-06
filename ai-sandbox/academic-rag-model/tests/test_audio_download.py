import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.audio_download import delete_audio, download_audio


class TestDownloadAudio(unittest.TestCase):
    @patch("video_notes.audio_download.yt_dlp.YoutubeDL")
    def test_returns_expected_mp3_path_and_invokes_download(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl
        with tempfile.TemporaryDirectory() as tmp:
            result = download_audio("AAAA111", "https://youtube.com/watch?v=AAAA111", tmp)
            expected = os.path.join(tmp, ".cache", "audio", "AAAA111.mp3")
            self.assertEqual(result, expected)
            mock_ydl.download.assert_called_once_with(["https://youtube.com/watch?v=AAAA111"])


class TestDeleteAudio(unittest.TestCase):
    def test_deletes_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.mp3")
            with open(path, "w", encoding="utf-8") as f:
                f.write("fake audio")
            delete_audio(path)
            self.assertFalse(os.path.exists(path))

    def test_missing_file_is_a_no_op(self):
        delete_audio(os.path.join(tempfile.gettempdir(), "definitely-does-not-exist.mp3"))  # must not raise
