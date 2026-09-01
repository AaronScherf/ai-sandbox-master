"""
zotero_sync.py
Optional Zotero push per spec S1/S3: find-or-create a collection matching
the topic folder, push the item's bibliographic metadata, attach the
fetched PDF. A failure here is always caught and logged by the caller
(discover.py) -- it must never discard or block a PDF that's already
safely on disk (spec S6).
"""
from __future__ import annotations

from pyzotero import zotero

from journal_discovery.discovery import Work


def _get_or_create_collection(zot, name: str) -> str:
    for collection in zot.collections():
        if collection["data"]["name"] == name:
            return collection["data"]["key"]
    created = zot.create_collections([{"name": name}])
    return created["successful"]["0"]["key"]


def sync_to_zotero(
    work: Work, pdf_path, topic_folder: str, library_id: str, api_key: str, library_type: str = "user"
) -> None:
    zot = zotero.Zotero(library_id, library_type, api_key)
    collection_key = _get_or_create_collection(zot, topic_folder)

    item = zot.item_template("journalArticle")
    item["title"] = work.title
    item["date"] = str(work.year or "")
    item["DOI"] = work.doi or ""
    item["creators"] = [{"creatorType": "author", "name": name} for name in work.authors]
    item["collections"] = [collection_key]

    created = zot.create_items([item])
    item_key = created["successful"]["0"]["key"]
    zot.attachment_simple([str(pdf_path)], item_key)
