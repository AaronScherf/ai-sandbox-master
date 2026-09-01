import unittest
from unittest.mock import MagicMock, patch

from journal_discovery.discovery import Work
from journal_discovery.zotero_sync import sync_to_zotero


def _work():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=["Jane Doe", "John Roe"],
        year=2024, abstract=None,
    )


class TestSyncToZotero(unittest.TestCase):
    @patch("journal_discovery.zotero_sync.zotero.Zotero")
    def test_creates_collection_when_missing(self, mock_zotero_cls):
        zot = MagicMock()
        mock_zotero_cls.return_value = zot
        zot.collections.return_value = []
        zot.create_collections.return_value = {"successful": {"0": {"key": "COLLKEY"}}}
        zot.item_template.return_value = {}
        zot.create_items.return_value = {"successful": {"0": {"key": "ITEMKEY"}}}

        sync_to_zotero(_work(), "/tmp/paper.pdf", "climate-change", "12345", "apikey")

        zot.create_collections.assert_called_once_with([{"name": "climate-change"}])
        created_item = zot.create_items.call_args[0][0][0]
        self.assertEqual(created_item["title"], "A Paper")
        self.assertEqual(created_item["DOI"], "10.1/abc")
        self.assertEqual(created_item["collections"], ["COLLKEY"])
        self.assertEqual(
            created_item["creators"],
            [{"creatorType": "author", "name": "Jane Doe"}, {"creatorType": "author", "name": "John Roe"}],
        )
        zot.attachment_simple.assert_called_once_with(["/tmp/paper.pdf"], "ITEMKEY")

    @patch("journal_discovery.zotero_sync.zotero.Zotero")
    def test_reuses_existing_collection(self, mock_zotero_cls):
        zot = MagicMock()
        mock_zotero_cls.return_value = zot
        zot.collections.return_value = [{"data": {"key": "EXISTING", "name": "climate-change"}}]
        zot.item_template.return_value = {}
        zot.create_items.return_value = {"successful": {"0": {"key": "ITEMKEY"}}}

        sync_to_zotero(_work(), "/tmp/paper.pdf", "climate-change", "12345", "apikey")

        zot.create_collections.assert_not_called()
        created_item = zot.create_items.call_args[0][0][0]
        self.assertEqual(created_item["collections"], ["EXISTING"])


if __name__ == "__main__":
    unittest.main()
