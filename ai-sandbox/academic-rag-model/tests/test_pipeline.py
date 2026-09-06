import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from video_notes.grouping import Group
from video_notes.pipeline import _read_urls_file, run_pipeline
from video_notes.transcribe import TranscriptSegment
from video_notes.youtube_metadata import VideoMetadata


def _video(video_id, title="Lecture 1"):
    return VideoMetadata(
        video_id=video_id, url=f"https://youtube.com/watch?v={video_id}", title=title,
        channel_id="UC1", playlist_id=None, playlist_title=None, playlist_index=None,
        upload_date="20260101", duration=100.0,
    )


class TestRunPipeline(unittest.TestCase):
    @patch("video_notes.pipeline.index_group_note")
    @patch("video_notes.pipeline.write_group_note")
    @patch("video_notes.pipeline.synthesize_group_note")
    @patch("video_notes.pipeline.embed_transcripts", return_value={})
    @patch("video_notes.pipeline.group_videos")
    @patch("video_notes.pipeline.transcribe_audio")
    @patch("video_notes.pipeline.download_audio", return_value="/tmp/A.mp3")
    @patch("video_notes.pipeline.delete_audio")
    @patch("video_notes.pipeline.fetch_video_metadata")
    def test_synthesizes_and_indexes_a_new_group(
        self, mock_fetch, mock_delete, mock_download, mock_transcribe,
        mock_group, mock_embed, mock_synthesize, mock_write, mock_index,
    ):
        mock_fetch.return_value = _video("A")
        mock_transcribe.return_value = [TranscriptSegment(0.0, 1.0, "hello")]
        mock_group.return_value = [Group(group_id="g_0001", member_video_ids=["A"], slug="lecture-1", tier="singleton")]
        mock_synthesize.return_value = "# Notes"
        mock_write.return_value = ("academic_notes/math-camp/lecture-notes/lecture-1.md",
                                    "academic_notes/math-camp/lecture-notes/lecture-1.meta.json")

        with tempfile.TemporaryDirectory() as video_notes_root:
            summary = run_pipeline(
                course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock(),
            )

        self.assertEqual(summary["groups_synthesized"], 1)
        self.assertEqual(summary["videos_transcribed"], 1)
        mock_index.assert_called_once()

    @patch("video_notes.pipeline.group_videos", return_value=[])
    @patch("video_notes.pipeline.embed_transcripts", return_value={})
    @patch("video_notes.pipeline.download_audio", side_effect=RuntimeError("network down"))
    @patch("video_notes.pipeline.fetch_video_metadata")
    def test_a_failed_video_is_recorded_and_does_not_raise(self, mock_fetch, mock_download, mock_embed, mock_group):
        mock_fetch.return_value = _video("A")
        with tempfile.TemporaryDirectory() as video_notes_root:
            summary = run_pipeline(
                course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock(),
            )
        self.assertEqual(summary["videos_failed"], 1)
        self.assertEqual(summary["videos_transcribed"], 0)

    @patch("video_notes.pipeline.index_group_note")
    @patch("video_notes.pipeline.write_group_note")
    @patch("video_notes.pipeline.synthesize_group_note")
    @patch("video_notes.pipeline.embed_transcripts", return_value={})
    @patch("video_notes.pipeline.group_videos")
    @patch("video_notes.pipeline.transcribe_audio")
    @patch("video_notes.pipeline.download_audio", return_value="/tmp/A.mp3")
    @patch("video_notes.pipeline.delete_audio")
    @patch("video_notes.pipeline.fetch_video_metadata")
    def test_unchanged_group_is_not_resynthesized_on_second_run(
        self, mock_fetch, mock_delete, mock_download, mock_transcribe,
        mock_group, mock_embed, mock_synthesize, mock_write, mock_index,
    ):
        mock_fetch.return_value = _video("A")
        mock_transcribe.return_value = [TranscriptSegment(0.0, 1.0, "hello")]
        mock_group.return_value = [Group(group_id="g_0001", member_video_ids=["A"], slug="lecture-1", tier="singleton")]
        mock_synthesize.return_value = "# Notes"
        mock_write.return_value = ("academic_notes/math-camp/lecture-notes/lecture-1.md",
                                    "academic_notes/math-camp/lecture-notes/lecture-1.meta.json")

        with tempfile.TemporaryDirectory() as video_notes_root:
            run_pipeline(course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                          academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock())
            summary = run_pipeline(course="math-camp", urls=["https://youtube.com/watch?v=A"], playlists=[],
                                    academic_hub_root="/fake/hub", video_notes_root=video_notes_root, client=MagicMock())

        self.assertEqual(summary["groups_unchanged"], 1)
        self.assertEqual(summary["groups_synthesized"], 0)
        mock_synthesize.assert_called_once()
        mock_download.assert_called_once()


class TestReadUrlsFile(unittest.TestCase):
    def test_reads_one_video_url_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "urls.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("https://youtube.com/watch?v=AAA\nhttps://youtube.com/watch?v=BBB\n")
            video_urls, playlist_urls = _read_urls_file(path)
            self.assertEqual(video_urls, ["https://youtube.com/watch?v=AAA", "https://youtube.com/watch?v=BBB"])
            self.assertEqual(playlist_urls, [])

    def test_skips_blank_lines_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "urls.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# a comment\n\nhttps://youtube.com/watch?v=AAA\n   \n# another\n")
            video_urls, playlist_urls = _read_urls_file(path)
            self.assertEqual(video_urls, ["https://youtube.com/watch?v=AAA"])
            self.assertEqual(playlist_urls, [])

    def test_strips_surrounding_whitespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "urls.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("  https://youtube.com/watch?v=AAA  \n")
            video_urls, _ = _read_urls_file(path)
            self.assertEqual(video_urls, ["https://youtube.com/watch?v=AAA"])

    def test_routes_playlist_links_separately_from_video_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "urls.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    "https://youtube.com/watch?v=AAA\n"
                    "https://youtube.com/playlist?list=PL123\n"
                    "https://www.youtube.com/watch?v=BBB\n"
                )
            video_urls, playlist_urls = _read_urls_file(path)
            self.assertEqual(video_urls, ["https://youtube.com/watch?v=AAA", "https://www.youtube.com/watch?v=BBB"])
            self.assertEqual(playlist_urls, ["https://youtube.com/playlist?list=PL123"])

    def test_a_video_url_with_a_list_param_is_still_treated_as_a_video(self):
        # watch?v=...&list=... is a video played from within a playlist,
        # not a playlist link itself -- stays routed as a single video,
        # same as --urls already treats such a URL.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "urls.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("https://youtube.com/watch?v=AAA&list=PL123\n")
            video_urls, playlist_urls = _read_urls_file(path)
            self.assertEqual(video_urls, ["https://youtube.com/watch?v=AAA&list=PL123"])
            self.assertEqual(playlist_urls, [])
