"""
related.py
Links a handwriting-only Excalidraw lecture note (the "subset") to its
"with slides" counterpart (the "superset") on the subset's index card, so
default search can return just the superset. Detection: same course and
folder, same YYYY-MM-DD in the filename, the superset's raw transcript
flagged embedded_slides: true and the subset's not -- then confirmed by
word-3-gram containment of the subset's handwriting inside the superset's
[Handwritten] blocks (whole-card embeddings were measured and cannot
separate true pairs from different lectures on the same topic).

Spec: docs/superpowers/specs/indexer/2026-10-03-subset-note-linking-design.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass

from core.env.corpus_write_lock import CorpusWriteLockError, corpus_write_lock
from core.env.excalidraw_text import CHUNK_MARKER_RE as _CHUNK_MARKER_RE, SEGMENT_LABEL_RE as _LABEL_RE
from core.env.frontmatter import parse_frontmatter
from core.indexer.index_card import list_courses, load_shard, save_shard

CONTAINMENT_THRESHOLD = 0.3
_NGRAM = 3

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TOKEN_RE = re.compile(r"[A-Za-z]{3,}|\\[A-Za-z]+")
_RAG_SUFFIX = ".excalidraw.rag.md"


def raw_transcript_path(card_path: str) -> str | None:
    if not card_path.endswith(_RAG_SUFFIX):
        return None
    return card_path[: -len(_RAG_SUFFIX)] + ".excalidraw.md"


def lecture_date(card_path: str) -> str | None:
    match = _DATE_RE.search(os.path.basename(card_path))
    return match.group(0) if match else None


def read_raw(academic_hub_root: str, card: dict) -> tuple[dict, str] | None:
    rel = raw_transcript_path(card.get("path", ""))
    if rel is None:
        return None
    full = os.path.join(academic_hub_root, *rel.split("/"))
    if not os.path.exists(full):
        return None
    with open(full, encoding="utf-8") as f:
        return parse_frontmatter(f.read())


def handwriting_text(meta: dict, body: str) -> str:
    text = _CHUNK_MARKER_RE.sub("", body)
    if meta.get("embedded_slides", "").strip().lower() != "true":
        return text
    parts = _LABEL_RE.split(text)  # [pre, label, body, label, body, ...]
    return "\n".join(parts[i + 1] for i in range(1, len(parts) - 1, 2) if parts[i] == "Handwritten")


def _ngrams(text: str) -> set[tuple[str, ...]]:
    words = _TOKEN_RE.findall(text.lower())
    return {tuple(words[i : i + _NGRAM]) for i in range(len(words) - _NGRAM + 1)}


def containment(subset_text: str, superset_text: str) -> float:
    sub = _ngrams(subset_text)
    if not sub:
        return 0.0
    return len(sub & _ngrams(superset_text)) / len(sub)


@dataclass(frozen=True)
class Link:
    subset_id: str
    superset_id: str
    score: float
    forced: bool = False


def overrides_path(academic_hub_root: str) -> str:
    # In a subdirectory, not a direct child of .index/: list_courses() and
    # _flag_or_prune_orphans() treat every top-level .index/*.json as a course
    # shard (same reason duplicate_check.py keeps its files in .index/duplicates/).
    return os.path.join(academic_hub_root, ".index", "links", "overrides.json")


def load_overrides(academic_hub_root: str) -> dict:
    path = overrides_path(academic_hub_root)
    if not os.path.exists(path):
        return {"force": [], "block": []}
    # A bad file is an error, not "no overrides": silently dropping a `block`
    # entry would create links the user explicitly forbade.
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as err:
        raise ValueError(f"cannot read {path} ({err}); fix or remove the file") from err
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object with optional 'force'/'block' lists")
    return {"force": data.get("force", []), "block": data.get("block", [])}


def _is_excalidraw(card: dict) -> bool:
    return card.get("doc_type") == "excalidraw_notes"


def _score(academic_hub_root: str, sub_card: dict, sup_card: dict) -> float | None:
    """Containment of sub's handwriting in sup's, or None if either raw
    transcript is missing or the slides-flag direction is wrong."""
    sub_raw = read_raw(academic_hub_root, sub_card)
    sup_raw = read_raw(academic_hub_root, sup_card)
    if sub_raw is None or sup_raw is None:
        return None
    sub_slides = sub_raw[0].get("embedded_slides", "").strip().lower() == "true"
    sup_slides = sup_raw[0].get("embedded_slides", "").strip().lower() == "true"
    if sub_slides or not sup_slides:
        return None
    return containment(handwriting_text(*sub_raw), handwriting_text(*sup_raw))


def _compute_links(academic_hub_root: str, cards: list[dict], overrides: dict) -> list[Link]:
    by_id = {c["file_id"]: c for c in cards}
    blocked = set(overrides["block"])
    forced = {f["subset"]: f["superset"] for f in overrides["force"] if "subset" in f and "superset" in f}
    excalidraw = [c for c in cards if _is_excalidraw(c)]

    links: dict[str, Link] = {}
    for sub in excalidraw:
        sub_id = sub["file_id"]
        if sub_id in blocked:
            continue
        if sub_id in forced:
            sup_id = forced[sub_id]
            if sup_id in by_id and sup_id != sub_id:
                score = _score(academic_hub_root, sub, by_id[sup_id])
                links[sub_id] = Link(sub_id, sup_id, round(score or 0.0, 4), forced=True)
            continue
        sub_date = lecture_date(sub["path"])
        if sub_date is None:
            continue
        best: Link | None = None
        for sup in excalidraw:
            if sup["file_id"] == sub_id or lecture_date(sup["path"]) != sub_date:
                continue
            if os.path.dirname(sup["path"]) != os.path.dirname(sub["path"]):
                continue
            score = _score(academic_hub_root, sub, sup)
            if score is None or score < CONTAINMENT_THRESHOLD:
                continue
            if best is None or score > best.score:
                best = Link(sub_id, sup["file_id"], round(score, 4))
        if best is not None:
            links[sub_id] = best

    # One level only: drop any link whose superset is itself a linked subset.
    return sorted((l for l in links.values() if l.superset_id not in links), key=lambda l: l.subset_id)


def link_subsets(academic_hub_root: str, course: str, dry_run: bool = False) -> list[Link]:
    """Computes and records subset links for one course shard. Idempotent:
    the shard is rewritten only when a card's link fields actually change.
    Also clears links that no longer qualify (superset gone, now blocked,
    text changed)."""
    cards = load_shard(academic_hub_root, course)
    links = _compute_links(academic_hub_root, cards, load_overrides(academic_hub_root))
    if dry_run:
        return links
    desired = {l.subset_id: l for l in links}
    changed = False
    for card in cards:
        link = desired.get(card["file_id"])
        if link is not None:
            if card.get("subset_of") != link.superset_id or card.get("subset_link_score") != link.score:
                card["subset_of"] = link.superset_id
                card["subset_link_score"] = link.score
                changed = True
        elif "subset_of" in card or "subset_link_score" in card:
            card.pop("subset_of", None)
            card.pop("subset_link_score", None)
            changed = True
    if changed:
        save_shard(academic_hub_root, course, cards)
    return links


_DEFAULT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Link handwriting-only Excalidraw notes to their with-slides supersets.")
    parser.add_argument("--root", default=_DEFAULT_ROOT, help="Corpus root (academic-hub).")
    parser.add_argument("--course", default=None, help="Only this course (default: all).")
    parser.add_argument("--dry-run", action="store_true", help="Print links without writing them.")
    args = parser.parse_args(argv)
    try:
        def run() -> None:
            for course in [args.course] if args.course else list_courses(args.root):
                for link in link_subsets(args.root, course, dry_run=args.dry_run):
                    tag = " (forced)" if link.forced else ""
                    print(f"[{course}] {link.subset_id} -> {link.superset_id}  containment={link.score:.2f}{tag}")

        if args.dry_run:
            run()
        else:
            # Standalone subset linking writes the course index shard.
            with corpus_write_lock([args.root], "index subset links"):
                run()
    except (ValueError, CorpusWriteLockError) as err:
        raise SystemExit(f"ERROR: {err}")


if __name__ == "__main__":
    main()
