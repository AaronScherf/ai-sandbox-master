import json
import tempfile
import unittest
from pathlib import Path

from journal_discovery.discovery import Work
from journal_discovery.metadata_sidecar import sidecar_path, write_sidecar


def _work():
    return Work(
        openalex_id="W1", doi="10.1/abc", title="A Paper", authors=["Jane Doe"],
        year=2024, abstract="...", concepts=["Climate change"], page_count=12,
    )


class TestSidecarPath(unittest.TestCase):
    def test_replaces_pdf_extension(self):
        self.assertEqual(sidecar_path(Path("/x/paper.pdf")), Path("/x/paper.meta.json"))


class TestWriteSidecar(unittest.TestCase):
    def test_writes_expected_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "paper.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")

            write_sidecar(pdf_path, _work(), relevance_score=0.82, source_tier="open_access")

            data = json.loads((Path(tmp) / "paper.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(data["title"], "A Paper")
            self.assertEqual(data["authors"], ["Jane Doe"])
            self.assertEqual(data["year"], 2024)
            self.assertEqual(data["doi"], "10.1/abc")
            self.assertEqual(data["concepts"], ["Climate change"])
            self.assertEqual(data["source_tier"], "open_access")
            self.assertEqual(data["relevance_score"], 0.82)
            self.assertEqual(data["page_count"], 12)

    def test_null_relevance_score_for_unscored_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "paper.pdf"
            write_sidecar(pdf_path, _work(), relevance_score=None, source_tier="ezproxy")
            data = json.loads((Path(tmp) / "paper.meta.json").read_text(encoding="utf-8"))
            self.assertIsNone(data["relevance_score"])


if __name__ == "__main__":
    unittest.main()
