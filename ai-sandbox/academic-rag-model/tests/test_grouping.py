import unittest

from video_notes.grouping import group_videos, slugify
from video_notes.youtube_metadata import VideoMetadata


def _video(video_id, title, playlist_id=None, playlist_title=None, playlist_index=None,
           channel_id="UC1", upload_date="20260101"):
    return VideoMetadata(
        video_id=video_id, url=f"https://youtube.com/watch?v={video_id}", title=title,
        channel_id=channel_id, playlist_id=playlist_id, playlist_title=playlist_title,
        playlist_index=playlist_index, upload_date=upload_date, duration=100.0,
    )


class TestSlugify(unittest.TestCase):
    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify("Real Analysis Lectures!"), "real-analysis-lectures")

    def test_empty_input_falls_back_to_untitled(self):
        self.assertEqual(slugify("   "), "untitled")


class TestGroupVideosPlaylistDefault(unittest.TestCase):
    def test_playlist_with_no_numbered_titles_becomes_one_group(self):
        videos = [
            _video("A", "Introduction to Real Analysis", playlist_id="PL1", playlist_title="Real Analysis", playlist_index=1),
            _video("B", "Continuity and Limits", playlist_id="PL1", playlist_title="Real Analysis", playlist_index=2),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "playlist")
        self.assertEqual(groups[0].member_video_ids, ["A", "B"])


class TestGroupVideosTitleSeriesSubdivision(unittest.TestCase):
    def test_playlist_with_two_distinct_lecture_series_subdivides(self):
        videos = [
            _video("A", "Unit 1: Sets, Lecture 1", playlist_id="PL1", playlist_index=1),
            _video("B", "Unit 1: Sets, Lecture 2", playlist_id="PL1", playlist_index=2),
            _video("C", "Unit 2: Metric Spaces, Lecture 1", playlist_id="PL1", playlist_index=3),
            _video("D", "Unit 2: Metric Spaces, Lecture 2", playlist_id="PL1", playlist_index=4),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 2)
        member_sets = sorted(tuple(g.member_video_ids) for g in groups)
        self.assertEqual(member_sets, [("A", "B"), ("C", "D")])
        self.assertTrue(all(g.tier == "title_series" for g in groups))

    def test_a_single_multi_member_stem_is_not_real_subdivision(self):
        # Only one distinct series detected (plus one non-matching
        # video) -- not "2+ distinct series", so the whole playlist
        # stays one group instead of splitting off the numbered videos.
        videos = [
            _video("A", "Real Analysis, Lecture 1", playlist_id="PL1", playlist_index=1),
            _video("B", "Real Analysis, Lecture 2", playlist_id="PL1", playlist_index=2),
            _video("C", "Course Introduction", playlist_id="PL1", playlist_index=3),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "playlist")
        self.assertEqual(set(groups[0].member_video_ids), {"A", "B", "C"})


class TestGroupVideosNoPlaylistScope(unittest.TestCase):
    def test_non_playlisted_videos_with_no_series_pattern_become_singletons(self):
        videos = [
            _video("A", "A Talk About Eigenvalues", channel_id="UC1"),
            _video("B", "A Different Talk", channel_id="UC1"),
        ]
        groups = group_videos(videos)
        self.assertEqual({g.tier for g in groups}, {"singleton"})
        self.assertEqual(len(groups), 2)

    def test_non_playlisted_videos_with_series_pattern_still_group(self):
        videos = [
            _video("A", "Econometrics Lecture 1", channel_id="UC1"),
            _video("B", "Econometrics Lecture 2", channel_id="UC1"),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].tier, "title_series")


class TestGroupVideosScopeIsolation(unittest.TestCase):
    def test_same_title_pattern_in_different_playlists_never_merges(self):
        videos = [
            _video("A", "Lecture 1", playlist_id="PL1", playlist_index=1),
            _video("B", "Lecture 2", playlist_id="PL1", playlist_index=2),
            _video("C", "Lecture 1", playlist_id="PL2", playlist_index=1),
            _video("D", "Lecture 2", playlist_id="PL2", playlist_index=2),
        ]
        groups = group_videos(videos)
        self.assertEqual(len(groups), 2)
        member_sets = sorted(tuple(g.member_video_ids) for g in groups)
        self.assertEqual(member_sets, [("A", "B"), ("C", "D")])
