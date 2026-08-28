"""
retag.py
Corpus-wide, two-phase tag mining for the academic-hub source indexer
(spec §5): discovery (mint new tags, conservatively, via connected
components over the corpus's card embeddings) and assignment (apply any
tag in the vocabulary to any matching file, independently -- no
cluster-membership restriction, which is what makes this genuinely
many-to-many instead of one-tag-per-file; see spec §5 for why plain
connected-components alone actively merges clusters for any file that
bridges two subjects, rather than just under-tagging it).

Deliberately separate from index_card.py (per-file generation) and
index_search.py (query-time search/rebuild) -- tag mining looks at the
whole corpus at once, on its own explicit schedule, never per-file.
"""
from __future__ import annotations

import json

from rapidfuzz import fuzz
from google.genai import types

from gemini_utils import call_with_retries
from index_card import (
    EMBEDDING_DIMENSIONALITY,
    EMBEDDING_MODEL,
    GENERATION_MODEL,
    cosine_similarity,
    list_courses,
    load_shard,
    load_tags,
    recompute_course_entry,
    save_shard,
    save_tags,
)

CLUSTER_SIMILARITY_THRESHOLD = 0.78
TAG_ASSIGNMENT_THRESHOLD = 0.78
MIN_TAG_CLUSTER_SIZE = 3
TAG_FUZZY_MATCH_THRESHOLD = 85  # rapidfuzz token_sort_ratio, 0-100


def build_clusters(embeddings: list[list[float]], threshold: float) -> list[list[int]]:
    """Connected components over a similarity graph -- index i adjacent to
    j if cosine_similarity(embeddings[i], embeddings[j]) > threshold."""
    n = len(embeddings)
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if cosine_similarity(embeddings[i], embeddings[j]) > threshold:
                adjacency[i].append(j)
                adjacency[j].append(i)

    visited = [False] * n
    clusters: list[list[int]] = []
    for start in range(n):
        if visited[start]:
            continue
        stack = [start]
        visited[start] = True
        component = []
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        clusters.append(component)
    return clusters


def fuzzy_match_tag(proposed: str, known_tags: list[dict]) -> dict | None:
    """Returns the existing tag entry whose name is closest to `proposed`
    (rapidfuzz token_sort_ratio), if that score is >= TAG_FUZZY_MATCH_THRESHOLD
    -- None means `proposed` is genuinely new, not a near-duplicate of
    something already in the vocabulary (spec §5.2)."""
    slug = proposed.strip().lower().replace(" ", "-")
    best_entry = None
    best_score = 0.0
    for entry in known_tags:
        score = fuzz.token_sort_ratio(slug, entry["tag"])
        if score > best_score:
            best_score = score
            best_entry = entry
    if best_entry is not None and best_score >= TAG_FUZZY_MATCH_THRESHOLD:
        return best_entry
    return None


_TAG_NAMING_PROMPT = """You are naming a topic tag shared by {n} related documents from a personal \
study corpus. Below is each document's title and summary.

Respond with ONLY a JSON object with exactly two keys:
"tag" (a short, kebab-case tag name, e.g. "linear-algebra" or "real-analysis"),
"definition" (one sentence defining what this tag means, for use as its own semantic anchor).

{documents}"""


def _name_cluster(cards: list[dict], client) -> tuple[str, str]:
    documents = "\n\n".join(f"- {c.get('title', '')}: {c.get('summary', '')}" for c in cards)
    prompt = _TAG_NAMING_PROMPT.format(n=len(cards), documents=documents)
    response = call_with_retries(lambda: client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0,
            "thinking_config": {"thinking_level": "minimal"},
        },
    ))
    parsed = json.loads(response.text)
    tag = str(parsed.get("tag") or "").strip().lower().replace(" ", "-")
    definition = str(parsed.get("definition") or "").strip()
    return tag, definition


def _embed_tag(tag: str, definition: str, client) -> list[float]:
    """The tag's semantic anchor -- an embedding of its own name+definition,
    not the mean of whichever cards happened to found it (spec §5.1): a
    stable meaning that doesn't drift with the founding cluster, and gets
    related terms (eigenvalues near eigenvectors) for free."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=f"{tag}: {definition}",
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def discover_tags(
    all_cards: list[tuple[str, dict]], known_tags: list[dict], client,
    threshold: float = CLUSTER_SIMILARITY_THRESHOLD, min_cluster_size: int = MIN_TAG_CLUSTER_SIZE,
) -> tuple[list[dict], dict]:
    """Phase 1 (spec §5.2): mints new tags from qualifying clusters,
    conservatively. Pure function -- does not read or write any files,
    does not mutate `known_tags` in place. Returns (updated_known_tags,
    stats); the caller (retag()) is responsible for persisting."""
    stats = {"clusters_found": 0, "tags_minted": 0, "tags_reused": 0}
    if not all_cards:
        return list(known_tags), stats

    cards_only = [c for _, c in all_cards]
    embeddings = [c["embedding"] for c in cards_only]
    clusters = build_clusters(embeddings, threshold)

    updated_tags = list(known_tags)
    for cluster_indices in clusters:
        if len(cluster_indices) < min_cluster_size:
            continue
        stats["clusters_found"] += 1
        cluster_cards = [cards_only[i] for i in cluster_indices]

        proposed_tag, definition = _name_cluster(cluster_cards, client)
        existing = fuzzy_match_tag(proposed_tag, updated_tags)
        if existing is not None:
            stats["tags_reused"] += 1
            continue

        embedding = _embed_tag(proposed_tag, definition, client)
        updated_tags.append({"tag": proposed_tag, "embedding": embedding})
        stats["tags_minted"] += 1

    return updated_tags, stats


def assign_tags(
    academic_hub_root: str, all_cards: list[tuple[str, dict]], known_tags: list[dict],
    threshold: float = TAG_ASSIGNMENT_THRESHOLD, dry_run: bool = False,
) -> dict:
    """Phase 2 (spec §5.3): for every card, independently checks every tag
    anchor and replaces the card's tags list with this run's fresh
    result. Many-to-many by construction -- no cluster-membership
    restriction at all, which is the actual fix for one-tag-per-file."""
    stats = {"cards_tagged": 0, "tag_assignments": 0}
    by_course: dict[str, dict[str, list[str]]] = {}

    for course, card in all_cards:
        matched = [
            entry["tag"] for entry in known_tags
            if cosine_similarity(card["embedding"], entry["embedding"]) > threshold
        ]
        if matched:
            stats["cards_tagged"] += 1
            stats["tag_assignments"] += len(matched)
        by_course.setdefault(course, {})[card["file_id"]] = matched

    if dry_run:
        return stats | {"preview": by_course}

    for course, file_tag_map in by_course.items():
        cards = load_shard(academic_hub_root, course)
        changed = False
        for card in cards:
            fid = card.get("file_id")
            if fid in file_tag_map and card.get("tags") != file_tag_map[fid]:
                card["tags"] = file_tag_map[fid]
                changed = True
        if changed:
            save_shard(academic_hub_root, course, cards)
            recompute_course_entry(academic_hub_root, course)

    return stats


def _load_all_cards(academic_hub_root: str) -> list[tuple[str, dict]]:
    """(course, card) for every non-orphaned, embedded card across all
    shards -- what both discovery and assignment operate over."""
    result = []
    for course in list_courses(academic_hub_root):
        for card in load_shard(academic_hub_root, course):
            if card.get("orphaned") or card.get("needs_indexing") or not card.get("embedding"):
                continue
            result.append((course, card))
    return result


def retag(
    academic_hub_root: str, client, dry_run: bool = False,
    cluster_threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
    assignment_threshold: float = TAG_ASSIGNMENT_THRESHOLD,
    min_cluster_size: int = MIN_TAG_CLUSTER_SIZE,
) -> dict:
    all_cards = _load_all_cards(academic_hub_root)
    known_tags = load_tags(academic_hub_root)

    updated_tags, discovery_stats = discover_tags(
        all_cards, known_tags, client, threshold=cluster_threshold, min_cluster_size=min_cluster_size,
    )
    assignment_stats = assign_tags(
        academic_hub_root, all_cards, updated_tags, threshold=assignment_threshold, dry_run=dry_run,
    )

    if not dry_run:
        save_tags(academic_hub_root, updated_tags)

    return discovery_stats | assignment_stats
