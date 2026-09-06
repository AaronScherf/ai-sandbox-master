"""
grouping.py
Fully automatic grouping of a course's videos into logical lecture
series -- no manual per-batch config (spec §4). Tried in order, per
playlist/channel scope: playlist-as-one-group (the default, unless
real title-series subdivision is detected), title-series subdivision,
then content-clustering fallback (added by Task 7), then singleton.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from video_notes.youtube_metadata import VideoMetadata

_SERIES_PATTERN = re.compile(r"(?i)\b(?:lecture|lec|part|week)\.?\s*#?\s*(\d+)\b")
_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Group:
    group_id: str
    member_video_ids: list[str]
    slug: str
    tier: str  # "playlist" | "title_series" | "content_cluster" | "singleton"


def slugify(text: str) -> str:
    slug = _SLUG_STRIP_RE.sub("-", text.strip().lower()).strip("-")
    return slug or "untitled"


def _title_stem(title: str) -> str | None:
    """Strips a `Lecture N` / `Part N` / `Week N` marker and returns the
    remaining text as the series stem, or None if no such marker is
    present (spec §4 tier 2)."""
    match = _SERIES_PATTERN.search(title)
    if not match:
        return None
    stem = title[:match.start()] + title[match.end():]
    stem = re.sub(r"[\s:,\-]+", " ", stem).strip().lower()
    return stem or None


def _scope_key(video: VideoMetadata) -> tuple:
    """Playlist membership scopes videos together; a video with no
    playlist is scoped by channel instead, so tier-3 clustering (Task 7)
    never compares videos across unrelated channels (spec §4)."""
    if video.playlist_id:
        return ("playlist", video.playlist_id)
    return ("channel", video.channel_id)


def _bucket_by_scope(videos: list[VideoMetadata]) -> dict[tuple, list[VideoMetadata]]:
    scopes: dict[tuple, list[VideoMetadata]] = {}
    for video in videos:
        scopes.setdefault(_scope_key(video), []).append(video)
    return scopes


def _subdivide_by_title_series(
    videos: list[VideoMetadata],
) -> tuple[dict[str, list[VideoMetadata]], list[VideoMetadata]]:
    """Returns (real_stems, unmatched): real_stems holds only stems with
    2+ members (a genuine subdivision signal); everything else --
    no-pattern titles and one-off stems with a single member -- is
    returned as unmatched, for tier 3 / singleton to handle."""
    buckets: dict[str, list[VideoMetadata]] = {}
    unmatched: list[VideoMetadata] = []
    for video in videos:
        stem = _title_stem(video.title)
        if stem is None:
            unmatched.append(video)
        else:
            buckets.setdefault(stem, []).append(video)

    real_stems = {stem: members for stem, members in buckets.items() if len(members) >= 2}
    for stem, members in buckets.items():
        if len(members) < 2:
            unmatched.extend(members)
    return real_stems, unmatched


def _order_members(videos: list[VideoMetadata]) -> list[VideoMetadata]:
    return sorted(
        videos,
        key=lambda v: (v.playlist_index if v.playlist_index is not None else 10**9, v.upload_date or ""),
    )


def _make_group(group_id: str, members: list[VideoMetadata], slug_source: str, tier: str) -> Group:
    ordered = _order_members(members)
    return Group(group_id=group_id, member_video_ids=[v.video_id for v in ordered], slug=slugify(slug_source), tier=tier)


def group_videos(
    videos: list[VideoMetadata], embeddings: dict[str, list[float] | None] | None = None,
    similarity_threshold: float = 0.75,
) -> list[Group]:
    groups: list[Group] = []
    counter = 0

    for scope_key, scope_videos in _bucket_by_scope(videos).items():
        is_playlist_scope = scope_key[0] == "playlist"
        real_stems, unmatched = _subdivide_by_title_series(scope_videos)

        if is_playlist_scope and len(real_stems) < 2:
            # No genuine subdivision signal -- trust the playlist itself
            # as one group (the common case: a coherent lecture series
            # whose titles aren't necessarily numbered). This is the
            # whole-playlist default for playlists that DON'T have
            # subgroups, while the branch below subdivides the ones
            # that do.
            counter += 1
            slug_source = scope_videos[0].playlist_title or scope_videos[0].title
            groups.append(_make_group(f"g_{counter:04d}", scope_videos, slug_source, "playlist"))
            continue

        for stem, members in real_stems.items():
            counter += 1
            groups.append(_make_group(f"g_{counter:04d}", members, stem, "title_series"))

        for video in unmatched:
            # Tier 3 (content clustering) is added by Task 7; until
            # then every leftover becomes its own singleton group.
            counter += 1
            groups.append(_make_group(f"g_{counter:04d}", [video], video.title, "singleton"))

    return groups
