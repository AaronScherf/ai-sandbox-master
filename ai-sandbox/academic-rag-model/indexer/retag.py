"""
retag.py
Corpus-wide, two-phase tag mining for the academic-hub source indexer
(spec §5): discovery (propose candidate tags holistically, validate each
against real card embeddings before minting) and assignment (apply any
tag in the vocabulary to any matching file, independently -- no
cluster-membership restriction, which is what makes this genuinely
many-to-many instead of one-tag-per-file).

Discovery originally built a similarity graph and took connected
components as candidate clusters -- tested live against the real corpus
and rejected (spec §5.2): connected components are transitive, so any
document bridging two subjects merges their clusters into one, and no
similarity threshold swept (0.78-0.90) produced a clean subject split --
just one giant blob, a cluster grouped by document format instead of
subject, or nothing. Discovery now asks once, holistically, instead of
inferring indirectly from a similarity graph.

Deliberately separate from index_card.py (per-file generation) and
index_search.py (query-time search/rebuild) -- tag mining looks at the
whole corpus at once, on its own explicit schedule, never per-file.
"""
from __future__ import annotations

import json
import os
import re

from rapidfuzz import fuzz
from google.genai import types

from common.gemini_utils import call_with_retries
from indexer.index_card import (
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

TAG_ASSIGNMENT_THRESHOLD = 0.65  # confirmed live: an anchor's similarity to
# individual founding documents (0.65-0.76) runs measurably lower than to
# their centroid (0.82) -- this is the low end of that observed range,
# used identically at discovery-time validation and assignment (spec §5.2).
MIN_TAG_CLUSTER_SIZE = 3
TAG_FUZZY_MATCH_THRESHOLD = 85  # rapidfuzz token_sort_ratio, 0-100


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


_TAG_DISCOVERY_PROMPT = """You are analyzing a personal study corpus to propose canonical subject \
tags. Below is the title and summary of every document currently in the corpus.

Propose a set of tags that would meaningfully partition this content by subject -- broad enough \
that each tag plausibly covers several documents, specific enough to be useful for finding \
material on a topic (e.g. "linear-algebra" and "real-analysis" as separate tags, not one tag \
for both, and not one tag per individual document).

Respond with ONLY a JSON object with exactly one key, "tags": a list of objects, each with \
"tag" (a short, kebab-case tag name) and "definition" (one sentence defining what it means, \
for use as its own semantic anchor).

{documents}"""


def _propose_candidate_tags(cards: list[dict], client) -> list[tuple[str, str]]:
    """One holistic LLM call over every card's title+summary -- proposes
    candidate subject tags directly, rather than reactively naming
    whatever a similarity graph happened to produce (spec §5.2)."""
    documents = "\n\n".join(f"- {c.get('title', '')}: {c.get('summary', '')}" for c in cards)
    prompt = _TAG_DISCOVERY_PROMPT.format(documents=documents)
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
    candidates = []
    for entry in parsed.get("tags") or []:
        tag = str(entry.get("tag") or "").strip().lower().replace(" ", "-")
        definition = str(entry.get("definition") or "").strip()
        if tag:
            candidates.append((tag, definition))
    return candidates


def _embed_tag(tag: str, definition: str, client) -> list[float]:
    """The tag's semantic anchor -- an embedding of its own name+definition,
    not the mean of whichever cards happened to inspire it (spec §5.1): a
    stable meaning that doesn't drift with whichever documents proposed
    it, and gets related terms (eigenvalues near eigenvectors) for free."""
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=f"{tag}: {definition}",
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY),
    )
    return list(response.embeddings[0].values)


def discover_tags(
    all_cards: list[tuple[str, dict]], known_tags: list[dict], client,
    threshold: float = TAG_ASSIGNMENT_THRESHOLD, min_matches: int = MIN_TAG_CLUSTER_SIZE,
) -> tuple[list[dict], dict]:
    """Phase 1 (spec §5.2): proposes candidate tags holistically (one call
    over the whole corpus), then empirically validates each candidate
    against real card embeddings before minting -- only kept if at least
    `min_matches` cards actually match its anchor above `threshold`. A
    candidate the LLM proposed but that doesn't correspond to enough real
    content gets rejected, not minted on the LLM's say-so alone. Pure
    function -- does not read or write any files, does not mutate
    `known_tags` in place. Returns (updated_known_tags, stats); the
    caller (retag()) is responsible for persisting."""
    stats = {"candidates_proposed": 0, "tags_minted": 0, "tags_reused": 0, "candidates_rejected": 0}
    if not all_cards:
        return list(known_tags), stats

    cards_only = [c for _, c in all_cards]
    candidates = _propose_candidate_tags(cards_only, client)
    stats["candidates_proposed"] = len(candidates)

    updated_tags = list(known_tags)
    for proposed_tag, definition in candidates:
        existing = fuzzy_match_tag(proposed_tag, updated_tags)
        if existing is not None:
            stats["tags_reused"] += 1
            continue

        anchor = _embed_tag(proposed_tag, definition, client)
        match_count = sum(
            1 for c in cards_only if cosine_similarity(anchor, c["embedding"]) > threshold
        )
        if match_count < min_matches:
            stats["candidates_rejected"] += 1
            continue

        updated_tags.append({"tag": proposed_tag, "embedding": anchor})
        stats["tags_minted"] += 1

    return updated_tags, stats


def assign_tags(
    academic_hub_root: str, all_cards: list[tuple[str, dict]], known_tags: list[dict],
    threshold: float = TAG_ASSIGNMENT_THRESHOLD, dry_run: bool = False,
) -> dict:
    """Phase 2 (spec §5.3): for every card, independently checks every tag
    anchor and replaces the card's tags list with this run's fresh
    result. Many-to-many by construction -- no cluster-membership
    restriction at all, which is the actual fix for one-tag-per-file.

    Excludes fallback-origin tags (spec §5.4): a fallback tag's anchor is
    a generic paraphrase of one specific document, never validated
    against the corpus the way discover_tags' >=min_matches bar requires
    -- confirmed live to drift above threshold against unrelated cards
    in a small, topically-homogeneous corpus (a "syllabus" fallback tag
    scored 0.73 against an unrelated Linear Algebra card). A fallback
    tag only ever describes the one card it was minted for."""
    stats = {"cards_tagged": 0, "tag_assignments": 0}
    by_course: dict[str, dict[str, list[str]]] = {}

    for course, card in all_cards:
        matched = [
            entry["tag"] for entry in known_tags
            if entry.get("origin") != "fallback"
            and cosine_similarity(card["embedding"], entry["embedding"]) > threshold
        ]
        if matched:
            stats["cards_tagged"] += 1
            stats["tag_assignments"] += len(matched)
        by_course.setdefault(course, {})[card["file_id"]] = matched

    # `preview` is always populated (not just under dry_run) -- retag()
    # uses it directly, in-memory, to see this run's fresh tags for the
    # minimum-coverage pass (spec §5.4) without a stale disk re-read,
    # which would be wrong specifically in dry_run mode (nothing written
    # yet) and wasteful otherwise.
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

    return stats | {"preview": by_course}


_FALLBACK_TAG_PROMPT = """This document has no matching tags in the corpus's shared tag \
vocabulary -- likely because it's a unique document type in this corpus (e.g. the only \
syllabus), or its subject area doesn't have enough other documents yet to justify a shared tag.

Propose ONE short, useful, kebab-case tag that specifically describes THIS document -- e.g. \
"syllabus" for a course syllabus, even though nothing else in the corpus needs that tag yet.

Respond with ONLY a JSON object with exactly two keys:
"tag" (a short, kebab-case tag name),
"definition" (one sentence defining what it means, for use as its own semantic anchor).

Title: {title}
Summary: {summary}"""


def _propose_fallback_tag(card: dict, client) -> tuple[str, str]:
    prompt = _FALLBACK_TAG_PROMPT.format(title=card.get("title", ""), summary=card.get("summary", ""))
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


def ensure_minimum_coverage(
    academic_hub_root: str, all_cards: list[tuple[str, dict]], known_tags: list[dict], client,
    dry_run: bool = False,
) -> tuple[list[dict], dict]:
    """Safety net (spec §5.4): after discovery+assignment, any card still
    without a tag gets one from a per-file proposal -- an untagged file
    is worse than a single-file tag like "syllabus" that will never
    clear §5.2's corpus-wide minting bar and isn't meant to. Deliberately
    skips the similarity check entirely when assigning: the anchor was
    derived to describe this exact card, so requiring it to also clear a
    threshold against that same card would reintroduce the anchor-vs-
    document gap §5.2 already had to fix. Newly-minted fallback tags are
    marked origin="fallback" so a later assign_tags() run never reuses
    them against a different card (see assign_tags docstring)."""
    stats = {"fallback_tags_minted": 0, "fallback_tags_reused": 0, "cards_covered": 0}
    updated_tags = list(known_tags)
    by_course: dict[str, dict[str, str]] = {}

    for course, card in all_cards:
        if card.get("tags"):
            continue
        proposed_tag, definition = _propose_fallback_tag(card, client)
        existing = fuzzy_match_tag(proposed_tag, updated_tags)
        if existing is not None:
            tag_name = existing["tag"]
            stats["fallback_tags_reused"] += 1
        else:
            anchor = _embed_tag(proposed_tag, definition, client)
            updated_tags.append({"tag": proposed_tag, "embedding": anchor, "origin": "fallback"})
            tag_name = proposed_tag
            stats["fallback_tags_minted"] += 1
        by_course.setdefault(course, {})[card["file_id"]] = tag_name
        stats["cards_covered"] += 1

    if dry_run or not by_course:
        return updated_tags, stats

    for course, file_tag_map in by_course.items():
        cards = load_shard(academic_hub_root, course)
        changed = False
        for c in cards:
            fid = c.get("file_id")
            if fid in file_tag_map:
                c["tags"] = [file_tag_map[fid]]
                changed = True
        if changed:
            save_shard(academic_hub_root, course, cards)
            recompute_course_entry(academic_hub_root, course)

    return updated_tags, stats


_FRONTMATTER_RE = re.compile(r"\A(---\n.*?\n---\n)", re.DOTALL)
_TAGS_LINE_RE = re.compile(r"(?m)^tags:.*$")


def write_tags_to_frontmatter(academic_hub_root: str) -> dict:
    """Patches each card's own .md file frontmatter `tags:` line in place
    with its current tags from the index (spec §5.5), so a reader of the
    raw file sees real tags without needing to consult the index. Reads
    tags fresh from each shard on disk rather than trusting any
    in-memory card state a caller might pass in, since by the time this
    runs (end of a real retag()) the shards are the source of truth and
    the only thing guaranteed to be fully up to date. Pure local file
    I/O -- no LLM or embedding calls, so this is cheap even at this
    corpus's current file count.

    A card whose .md has no leading `---...---` frontmatter block (predates
    frontmatter support entirely, or is a textbook's .rag.md, which never
    had one) is skipped rather than having a block invented -- this isn't
    the place to guess at source_pdf/routing/model metadata this function
    doesn't have."""
    stats = {"frontmatter_updated": 0, "skipped_no_frontmatter": 0}
    for course in list_courses(academic_hub_root):
        for card in load_shard(academic_hub_root, course):
            if card.get("orphaned") or not card.get("path"):
                continue
            md_path = os.path.join(academic_hub_root, card["path"])
            if not os.path.exists(md_path):
                continue

            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            match = _FRONTMATTER_RE.match(content)
            if not match or not _TAGS_LINE_RE.search(match.group(1)):
                stats["skipped_no_frontmatter"] += 1
                continue

            rendered = "[" + ", ".join(card.get("tags") or []) + "]"
            new_frontmatter = _TAGS_LINE_RE.sub(f"tags: {rendered}", match.group(1), count=1)
            if new_frontmatter == match.group(1):
                continue

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(new_frontmatter + content[match.end():])
            stats["frontmatter_updated"] += 1
    return stats


def _load_all_cards(academic_hub_root: str) -> list[tuple[str, dict]]:
    """(course, card) for every non-orphaned, embedded card across all
    shards -- what discovery, assignment, and minimum-coverage all
    operate over."""
    result = []
    for course in list_courses(academic_hub_root):
        for card in load_shard(academic_hub_root, course):
            if card.get("orphaned") or card.get("needs_indexing") or not card.get("embedding"):
                continue
            result.append((course, card))
    return result


def retag(
    academic_hub_root: str, client, dry_run: bool = False,
    assignment_threshold: float = TAG_ASSIGNMENT_THRESHOLD,
    min_matches: int = MIN_TAG_CLUSTER_SIZE,
) -> dict:
    all_cards = _load_all_cards(academic_hub_root)
    known_tags = load_tags(academic_hub_root)

    updated_tags, discovery_stats = discover_tags(
        all_cards, known_tags, client, threshold=assignment_threshold, min_matches=min_matches,
    )
    assignment_stats = assign_tags(
        academic_hub_root, all_cards, updated_tags, threshold=assignment_threshold, dry_run=dry_run,
    )

    # Reflect this run's fresh assignment onto the in-memory cards before
    # the minimum-coverage pass decides which are still untagged --
    # reading back from disk here would be stale in dry_run mode
    # (nothing written yet).
    preview = assignment_stats["preview"]
    for course, card in all_cards:
        card["tags"] = preview.get(course, {}).get(card["file_id"], [])

    updated_tags, coverage_stats = ensure_minimum_coverage(
        academic_hub_root, all_cards, updated_tags, client, dry_run=dry_run,
    )

    frontmatter_stats = {}
    if not dry_run:
        save_tags(academic_hub_root, updated_tags)
        frontmatter_stats = write_tags_to_frontmatter(academic_hub_root)

    return discovery_stats | assignment_stats | coverage_stats | frontmatter_stats
