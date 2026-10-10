# tests/pipelines/transcribe_notes/test_agent_submit.py
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from pipelines.transcribe_notes.agent_submit import submit_doc, validate_card_output
from pipelines.transcribe_notes.agent_work import AgentDriver, load_manifest


class TestValidateCardOutput(unittest.TestCase):
    def _good_output(self, pages):
        return "\n\n".join(f"--- PAGE {p} ---\nSome transcribed text for page {p}." for p in pages)

    def test_all_pages_present_passes(self):
        result = validate_card_output(self._good_output([1, 2]), expected_pages=[1, 2], tier="batch")
        self.assertIsNone(result.bounce_reason)
        self.assertEqual(set(result.pages), {1, 2})

    def test_missing_page_bounces(self):
        result = validate_card_output(self._good_output([1]), expected_pages=[1, 2], tier="batch")
        self.assertIsNotNone(result.bounce_reason)
        self.assertIn("2", result.bounce_reason)

    def test_empty_page_bounces(self):
        output = "--- PAGE 1 ---\nSome text.\n\n--- PAGE 2 ---\n\n"
        result = validate_card_output(output, expected_pages=[1, 2], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_unclosed_code_fence_bounces(self):
        output = "--- PAGE 1 ---\n```\nsome code with no closing fence"
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_unbalanced_display_math_bounces(self):
        output = "--- PAGE 1 ---\nSome text with $$x^2 unclosed."
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_single_dollar_currency_does_not_bounce(self):
        output = "--- PAGE 1 ---\nThe price is $5 and the fee is $10."
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNone(result.bounce_reason)

    def test_repetition_loop_bounces(self):
        output = "--- PAGE 1 ---\n" + (". . . " * 60)
        result = validate_card_output(output, expected_pages=[1], tier="batch")
        self.assertIsNotNone(result.bounce_reason)

    def test_short_output_warns_not_bounces_for_tier2(self):
        output = "--- PAGE 1 ---\nshort"
        result = validate_card_output(
            output, expected_pages=[1], tier="batch", local_text_hints={1: "a" * 500},
        )
        self.assertIsNone(result.bounce_reason)
        self.assertTrue(result.warnings)

    def test_short_output_does_not_warn_for_tier3(self):
        output = "--- PAGE 1 ---\nshort"
        result = validate_card_output(
            output, expected_pages=[1], tier="tier3", local_text_hints={1: "a" * 500},
        )
        self.assertIsNone(result.bounce_reason)
        self.assertEqual(result.warnings, [])


def _write_minimal_tier3_pdf(path: str) -> None:
    import pymupdf

    doc = pymupdf.open()
    for _ in range(2):
        page = doc.new_page()
        page.insert_text((72, 72), "handwritten-looking content")
    doc.save(path)
    doc.close()


class TestSubmitDoc(unittest.TestCase):
    def test_incomplete_when_a_card_is_still_pending(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)

            # collect first, to get a real card + manifest on disk
            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertTrue(status.startswith("incomplete"))

    def test_complete_writes_cache_and_reruns_process_pdf(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)  # 2 pages, both fit in one tier-3 card (batch size 6)

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)
            task_id = entries[0].task_id
            # Fill the card as the agent would.
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            filled = content.replace(
                "## Agent output\n\n",
                "## Agent output\n\n--- PAGE 1 ---\nFirst page text.\n\n--- PAGE 2 ---\nSecond page text.\n",
            )
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(filled)

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(status, "complete")

            # resolve_output_dir() puts output in a processed_outputs/
            # sibling, not next to the source PDF directly.
            md_path = os.path.join(notes_dir, "processed_outputs", "doc.md")
            self.assertTrue(os.path.exists(md_path))
            with open(md_path, encoding="utf-8") as f:
                written = f.read()
            self.assertIn("driver: agent", written)
            self.assertIn("First page text.", written)

    def test_already_complete_is_idempotent(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
            entries = load_manifest(doc_dir)
            task_id = entries[0].task_id
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace(
                    "## Agent output\n\n",
                    "## Agent output\n\n--- PAGE 1 ---\nFirst.\n\n--- PAGE 2 ---\nSecond.\n",
                ))

            first = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(first, "complete")
            second = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(second, "already complete")

    def test_bounced_card_is_marked_and_not_written_to_cache(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path)

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)
            entries = load_manifest(doc_dir)
            task_id = entries[0].task_id
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            # Only page 1 filled -- page 2 missing -> must bounce.
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace("## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nFirst.\n"))

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertTrue(status.startswith("incomplete"))
            entries = load_manifest(doc_dir)
            self.assertEqual(entries[0].status, "bounced")
            self.assertIn("missing", entries[0].bounce_reason)


if __name__ == "__main__":
    unittest.main()
