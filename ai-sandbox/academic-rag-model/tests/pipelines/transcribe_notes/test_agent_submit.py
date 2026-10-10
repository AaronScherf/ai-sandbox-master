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

    def test_duplicate_page_text_bounces(self):
        # Final review I7: a copy-paste mistake (same text pasted into two
        # pages of the same card) must bounce, not be published as if
        # both pages were transcribed correctly.
        duplicated_text = "This is a long enough transcribed passage to not be a coincidence."
        output = f"--- PAGE 1 ---\n{duplicated_text}\n\n--- PAGE 2 ---\n{duplicated_text}\n"
        result = validate_card_output(output, expected_pages=[1, 2], tier="tier3")
        self.assertIsNotNone(result.bounce_reason)
        self.assertIn("duplicate", result.bounce_reason)

    def test_short_identical_pages_do_not_bounce_as_duplicates(self):
        # A short, genuinely repeated phrase (e.g. a bare page number or a
        # one-word heading) is not evidence of a copy-paste mistake.
        output = "--- PAGE 1 ---\n(continued)\n\n--- PAGE 2 ---\n(continued)\n"
        result = validate_card_output(output, expected_pages=[1, 2], tier="tier3")
        self.assertIsNone(result.bounce_reason)


def _write_minimal_tier3_pdf(path: str, pages: int = 2) -> None:
    import pymupdf

    doc = pymupdf.open()
    for _ in range(pages):
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


class TestSubmitDocMultiCardTier3(unittest.TestCase):
    """Final review C1: submitting the first card of a multi-card tier-3
    document must not finalize the write (partial .md, paid classification
    call) and report "complete" -- it must auto-stage the next card and
    report incomplete, exactly as the spec's BLOCKING #2 requires."""

    def _fill_card(self, doc_dir: str, task_id: str, pages: list[int]) -> None:
        card_path = os.path.join(doc_dir, f"{task_id}.md")
        with open(card_path, encoding="utf-8") as f:
            content = f.read()
        body = "\n\n".join(f"--- PAGE {p} ---\nText for page {p}." for p in pages) + "\n"
        with open(card_path, "w", encoding="utf-8") as f:
            f.write(content.replace("## Agent output\n\n", f"## Agent output\n\n{body}"))

    def test_submitting_first_card_of_multi_card_doc_does_not_finalize(self):
        with tempfile.TemporaryDirectory() as hub:
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            pdf_path = os.path.join(notes_dir, "doc.pdf")
            _write_minimal_tier3_pdf(pdf_path, pages=8)  # 2 tier-3 cards: 1-6, 7-8

            driver = AgentDriver(hub, "run-1")
            from pipelines.transcribe_notes.transcribe_notes import process_pdf
            process_pdf(pdf_path, None, None, hub, driver=driver, collect_mode=True)
            doc_slug = driver.last_doc_slug
            doc_dir = os.path.join(hub, ".agent_work", "run-1", doc_slug)

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)  # only the first card staged so far
            self.assertEqual(entries[0].pages, [1, 2, 3, 4, 5, 6])
            self._fill_card(doc_dir, entries[0].task_id, entries[0].pages)

            status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)

            # Must NOT report complete, and must NOT have written a
            # partial .md file -- it must instead auto-stage card 2.
            self.assertNotEqual(status, "complete")
            md_path = os.path.join(notes_dir, "processed_outputs", "doc.md")
            self.assertFalse(os.path.exists(md_path), "a partial .md was written for an incomplete document")

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 2)  # card 2 auto-staged
            self.assertEqual(entries[1].pages, [7, 8])

            # Finish the document: fill and submit card 2.
            self._fill_card(doc_dir, entries[1].task_id, entries[1].pages)
            final_status = submit_doc(hub, hub, "run-1", doc_slug, pdf_path, MagicMock(), None)
            self.assertEqual(final_status, "complete")
            self.assertTrue(os.path.exists(md_path))
            with open(md_path, encoding="utf-8") as f:
                written = f.read()
            for page in range(1, 9):
                self.assertIn(f"Text for page {page}.", written)


class TestSubmitDocForceVision(unittest.TestCase):
    """Final review I5: --force-vision used at collect time must be
    preserved through submit's rerun, or the rerun routes a clean,
    reliably-paginated document to tier-1 local extraction and discards
    the agent's transcription."""

    def test_force_vision_is_preserved_through_submits_rerun(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = os.path.join(tmp, "notes", "hw.pdf")
            os.makedirs(os.path.dirname(pdf_path))
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 mock")

            mock_reader = MagicMock()
            mock_reader.pages = [MagicMock()]
            mock_reader.metadata = {"/Producer": "pdfTeX"}

            with patch("pypdf.PdfReader", return_value=mock_reader):
                with patch("pipelines.transcribe_notes.transcribe_notes.has_reliable_pagination", return_value=True):
                    with patch("pipelines.transcribe_notes.transcribe_notes.extract_all_page_texts", return_value=["clean text"]):
                        with patch("pipelines.transcribe_notes.transcribe_notes.page_looks_defective", return_value=False):
                            with patch(
                                "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                                return_value=b"fake-png-bytes",
                            ):
                                from pipelines.transcribe_notes.transcribe_notes import process_pdf

                                driver = AgentDriver(tmp, "run-1")
                                process_pdf(pdf_path, None, None, tmp, force_vision=True, driver=driver, collect_mode=True)
                            doc_slug = driver.last_doc_slug
                            doc_dir = os.path.join(tmp, ".agent_work", "run-1", doc_slug)
                            entries = load_manifest(doc_dir)
                            self.assertEqual(len(entries), 1)
                            card_path = os.path.join(doc_dir, f"{entries[0].task_id}.md")
                            with open(card_path, encoding="utf-8") as f:
                                content = f.read()
                            with open(card_path, "w", encoding="utf-8") as f:
                                f.write(content.replace(
                                    "## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nAgent text.\n",
                                ))

                            with patch("pipelines.transcribe_notes.transcribe_notes._write_markdown_and_index") as mock_write:
                                with patch(
                                    "pipelines.transcribe_notes.agent_submit.extract_page_text", return_value="hint",
                                ):
                                    status = submit_doc(
                                        tmp, tmp, "run-1", doc_slug, pdf_path, MagicMock(), None, force_vision=True,
                                    )
                            self.assertEqual(status, "complete")
                            mock_write.assert_called_once()
                            frontmatter = mock_write.call_args[0][1]
                            # Must still be the batch tier force_vision routed it to at
                            # collect time, not tier-1 local extraction (which would
                            # silently discard the agent's transcribed text).
                            self.assertIn("routing: gemini_batched", frontmatter)


if __name__ == "__main__":
    unittest.main()
