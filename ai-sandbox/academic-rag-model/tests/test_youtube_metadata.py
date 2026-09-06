import unittest
from unittest.mock import MagicMock, patch

from video_notes.youtube_metadata import VideoMetadata, fetch_playlist_metadata, fetch_video_metadata

_FAKE_VIDEO_INFO = {
    "id": "AAAA111", "title": "Lecture 3: Convexity", "channel_id": "UC123",
    "playlist_id": "PL999", "playlist_title": "Math Camp 2026",
    "playlist_index": 3, "upload_date": "20260101", "duration": 3600.0,
}


class TestFetchVideoMetadata(unittest.TestCase):
    @patch("video_notes.youtube_metadata.yt_dlp.YoutubeDL")
    def test_extracts_fields_from_yt_dlp_info(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = _FAKE_VIDEO_INFO
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        result = fetch_video_metadata("https://youtube.com/watch?v=AAAA111")

        self.assertEqual(result, VideoMetadata(
            video_id="AAAA111", url="https://youtube.com/watch?v=AAAA111",
            title="Lecture 3: Convexity", channel_id="UC123",
            playlist_id="PL999", playlist_title="Math Camp 2026",
            playlist_index=3, upload_date="20260101", duration=3600.0,
        ))

    @patch("video_notes.youtube_metadata.yt_dlp.YoutubeDL")
    def test_missing_playlist_fields_default_to_none(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"id": "BBBB222", "title": "Standalone video", "channel_id": "UC456"}
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        result = fetch_video_metadata("https://youtube.com/watch?v=BBBB222")

        self.assertIsNone(result.playlist_id)
        self.assertIsNone(result.duration)


class TestFetchPlaylistMetadata(unittest.TestCase):
    @patch("video_notes.youtube_metadata.yt_dlp.YoutubeDL")
    def test_returns_one_video_metadata_per_entry(self, mock_ydl_cls):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {"id": "AAAA111", "title": "Lecture 1", "channel_id": "UC123", "playlist_id": "PL999",
                 "playlist_title": "Math Camp 2026", "playlist_index": 1, "upload_date": "20260101", "duration": 100.0},
                {"id": "BBBB222", "title": "Lecture 2", "channel_id": "UC123", "playlist_id": "PL999",
                 "playlist_title": "Math Camp 2026", "playlist_index": 2, "upload_date": "20260102", "duration": 200.0},
            ]
        }
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl

        results = fetch_playlist_metadata("https://youtube.com/playlist?list=PL999")

        self.assertEqual([r.video_id for r in results], ["AAAA111", "BBBB222"])
        self.assertTrue(all(r.playlist_id == "PL999" for r in results))
        self.assertEqual(results[0].url, "https://www.youtube.com/watch?v=AAAA111")
