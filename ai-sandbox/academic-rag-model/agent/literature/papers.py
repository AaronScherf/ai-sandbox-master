"""Which converted papers can be extracted, and the identity each carries from its index card."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.indexer.index_card import list_courses, load_shard

from .store import check_file_id
from .transcript import split_pages

_IDENTITY_KEYS = ("openalex_id", "doi", "publication_year", "openalex_topics")


@dataclass(frozen=True)
class Paper:
    file_id: str
    path: str
    title: str
    identity: dict


def eligible_papers(index_root: str) -> tuple[list[Paper], dict[str, str]]:
    """Journal papers whose transcript exists and has page markers, plus a file_id -> reason map for the rest."""
    papers: list[Paper] = []
    skipped: dict[str, str] = {}
    for course in list_courses(index_root):
        for card in load_shard(index_root, course):
            if card.get("doc_type") != "journal_article":
                continue
            fid = str(card.get("file_id") or "")
            try:
                check_file_id(fid)
            except ValueError:
                skipped[fid or "(no file_id)"] = "invalid file_id on the index card"
                continue
            if card.get("needs_indexing") or card.get("orphaned"):
                skipped[fid] = "card needs indexing or is orphaned; convert and index the paper first"
                continue
            rel = card.get("path") or ""
            md = Path(index_root) / rel
            if not rel or not md.is_file():
                skipped[fid] = "no transcript file"
                continue
            if not split_pages(md.read_text(encoding="utf-8")):
                skipped[fid] = "transcript has no page markers"
                continue
            identity = {"file_id": fid, "title": card.get("title") or ""}
            identity.update({k: card[k] for k in _IDENTITY_KEYS if card.get(k) is not None})
            papers.append(Paper(fid, rel, identity["title"], identity))
    return papers, skipped
