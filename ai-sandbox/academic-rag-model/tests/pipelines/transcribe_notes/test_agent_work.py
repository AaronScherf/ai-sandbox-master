# tests/pipelines/transcribe_notes/test_agent_work.py
import json
import os
import tempfile
import unittest
import unittest.mock

from pipelines.transcribe_notes.agent_driver import AgentPending
from pipelines.transcribe_notes.agent_work import (
    AgentDriver,
    ManifestEntry,
    agent_work_dir,
    doc_slug_for,
    doc_work_dir,
    dedupe_by_file_id,
    load_manifest,
    parse_task_card_output,
    render_task_card,
    render_worklist,
    save_manifest,
)


class TestLayout(unittest.TestCase):
    def test_agent_work_dir_is_under_hub_root_dot_agent_work(self):
        path = agent_work_dir("/hub", "run-1")
        self.assertEqual(path, os.path.join("/hub", ".agent_work", "run-1"))

    def test_doc_slug_combines_basename_and_file_id_prefix(self):
        slug = doc_slug_for("/hub/academic_resources/microecon/foo bar.pdf", "abcdef1234567890")
        self.assertTrue(slug.startswith("foo_bar"))
        self.assertIn("abcdef12", slug)
        self.assertNotIn(" ", slug)

    def test_doc_work_dir_nests_under_run(self):
        path = doc_work_dir("/hub", "run-1", "foo--abcdef12")
        self.assertEqual(path, os.path.join("/hub", ".agent_work", "run-1", "foo--abcdef12"))


class TestManifest(unittest.TestCase):
    def test_round_trips_entries(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            entries = [
                ManifestEntry(task_id="task-0001", tier="hybrid", pages=[1, 2, 3], status="pending", bounce_reason=None),
            ]
            save_manifest(doc_dir, entries)
            loaded = load_manifest(doc_dir)
            self.assertEqual(loaded, entries)

    def test_load_manifest_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            self.assertEqual(load_manifest(doc_dir), [])

    def test_load_manifest_malformed_json_raises_clear_error(self):
        # Final review I6: a hand-edited manifest with broken JSON must
        # raise a message naming the file, not a raw JSONDecodeError.
        with tempfile.TemporaryDirectory() as doc_dir:
            with open(os.path.join(doc_dir, "manifest.json"), "w", encoding="utf-8") as f:
                f.write("{not valid json")
            with self.assertRaises(ValueError) as ctx:
                load_manifest(doc_dir)
            self.assertIn("manifest.json", str(ctx.exception))

    def test_load_manifest_unexpected_schema_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            with open(os.path.join(doc_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump([{"task_id": "task-0001", "unexpected_field": "x"}], f)
            with self.assertRaises(ValueError) as ctx:
                load_manifest(doc_dir)
            self.assertIn("manifest.json", str(ctx.exception))

    def test_render_worklist_writes_human_readable_file(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            entries = [
                ManifestEntry(task_id="task-0001", tier="hybrid", pages=[1, 2, 3], status="submitted", bounce_reason=None),
                ManifestEntry(task_id="task-0002", tier="hybrid", pages=[4, 5], status="bounced", bounce_reason="missing page 5"),
            ]
            render_worklist(doc_dir, entries)
            with open(os.path.join(doc_dir, "worklist.md"), encoding="utf-8") as f:
                content = f.read()
            self.assertIn("task-0001", content)
            self.assertIn("submitted", content)
            self.assertIn("missing page 5", content)


class TestDedupe(unittest.TestCase):
    def test_duplicate_pdfs_collapse_to_one_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a.pdf")
            b = os.path.join(tmp, "b.pdf")
            c = os.path.join(tmp, "c.pdf")
            with open(a, "wb") as f:
                f.write(b"%PDF-1.4 same content")
            with open(b, "wb") as f:
                f.write(b"%PDF-1.4 same content")
            with open(c, "wb") as f:
                f.write(b"%PDF-1.4 different content")
            canonical, duplicates_of = dedupe_by_file_id([a, b, c])
            self.assertEqual(len(canonical), 2)
            self.assertIn(a, canonical)
            self.assertIn(c, canonical)
            self.assertEqual(duplicates_of[a], [b])


class TestTaskCard(unittest.TestCase):
    def test_render_then_parse_empty_agent_output(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            render_task_card(
                doc_dir, "task-0001", "hybrid", [1, 2],
                page_prompts={1: "prompt for page 1", 2: "prompt for page 2"},
                image_paths={1: "images/page-0001.png", 2: "images/page-0002.png"},
            )
            self.assertIsNone(parse_task_card_output(doc_dir, "task-0001"))

    def test_parse_returns_filled_agent_output(self):
        with tempfile.TemporaryDirectory() as doc_dir:
            render_task_card(
                doc_dir, "task-0001", "hybrid", [1, 2],
                page_prompts={1: "p1", 2: "p2"}, image_paths={1: "img1.png", 2: "img2.png"},
            )
            card_path = os.path.join(doc_dir, "task-0001.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            filled = content.replace(
                "## Agent output\n\n",
                "## Agent output\n\n--- PAGE 1 ---\nFirst page text\n\n--- PAGE 2 ---\nSecond page text\n",
            )
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(filled)
            output = parse_task_card_output(doc_dir, "task-0001")
            self.assertIn("First page text", output)


class TestAgentDriverBatch(unittest.TestCase):
    def test_transcribe_batch_writes_one_card_and_raises_pending(self):
        with tempfile.TemporaryDirectory() as hub:
            # compute_file_id reads the real file's bytes, so the PDF path
            # must exist on disk -- a fake nonexistent path (as the plan's
            # brief used) raises FileNotFoundError before AgentDriver ever
            # gets a chance to write a card.
            pdf_path = os.path.join(hub, "doc.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 fake content for file_id hashing")

            driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ):
                    driver.transcribe_batch(pdf_path, "gemini-3.1-flash-lite", [1, 2], "the batch prompt")
            doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].pages, [1, 2])
            self.assertEqual(entries[0].status, "pending")


class TestAgentDriverTier3(unittest.TestCase):
    def test_transcribe_page_stages_a_multi_page_card(self):
        with tempfile.TemporaryDirectory() as hub:
            pdf_path = os.path.join(hub, "doc.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 fake content for file_id hashing")

            driver = AgentDriver(hub, "run-1")
            with unittest.mock.patch(
                "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                return_value=b"fake-png-bytes",
            ), unittest.mock.patch(
                "pipelines.transcribe_notes.agent_work.extract_page_text", return_value="hint text",
            ):
                with self.assertRaises(AgentPending):
                    driver.transcribe_page(pdf_path, "gemini-3.6-flash", 1, "prompt for page 1", b"img1", 20)
            doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)
            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].pages[0], 1)
            self.assertGreater(len(entries[0].pages), 1)  # staged more than just page 1
            self.assertLessEqual(entries[0].pages[-1], 20)  # clamped at total_pages


class TestAgentDriverTaskIdCollision(unittest.TestCase):
    """Final review C2: a fresh AgentDriver instance (submit's auto-stage,
    or a re-collect with the same --run-id) must not restart task
    numbering from task-0001 and overwrite an existing card."""

    def test_new_driver_instance_seeds_task_counter_from_existing_manifest(self):
        with tempfile.TemporaryDirectory() as hub:
            pdf_path = os.path.join(hub, "doc.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 fake content for file_id hashing")

            first_driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ), unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.extract_page_text", return_value="hint text",
                ):
                    first_driver.transcribe_page(pdf_path, "gemini-3.6-flash", 1, "prompt for page 1", b"img1", 20)
            doc_dir = os.path.join(hub, ".agent_work", "run-1", first_driver.last_doc_slug)

            # Submit the first card so the next page's driver call is for a
            # genuinely new, uncovered page range.
            entries = load_manifest(doc_dir)
            entries[0].status = "submitted"
            save_manifest(doc_dir, entries)

            # A brand-new AgentDriver instance (as submit's auto-stage or a
            # fresh CLI --collect invocation would create) must continue
            # numbering from task-0002, not restart at task-0001.
            second_driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ), unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.extract_page_text", return_value="hint text",
                ):
                    second_driver.transcribe_page(pdf_path, "gemini-3.6-flash", 7, "prompt for page 7", b"img7", 20)

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0].task_id, "task-0001")
            self.assertEqual(entries[0].status, "submitted")
            self.assertEqual(entries[1].task_id, "task-0002")
            self.assertEqual(entries[1].pages[0], 7)

    def test_recollecting_a_still_pending_tier3_card_does_not_overwrite_it(self):
        with tempfile.TemporaryDirectory() as hub:
            pdf_path = os.path.join(hub, "doc.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 fake content for file_id hashing")

            driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ), unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.extract_page_text", return_value="hint text",
                ):
                    driver.transcribe_page(pdf_path, "gemini-3.6-flash", 1, "prompt for page 1", b"img1", 20)
            doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)

            # Agent starts filling the card (not yet submitted).
            entries = load_manifest(doc_dir)
            task_id = entries[0].task_id
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace("## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nIn progress...\n"))

            # A second collect run over the same still-pending card (fresh
            # AgentDriver, same page) must not create a duplicate card or
            # touch the agent's in-progress text.
            second_driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ), unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.extract_page_text", return_value="hint text",
                ):
                    second_driver.transcribe_page(pdf_path, "gemini-3.6-flash", 1, "prompt for page 1", b"img1", 20)

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)  # no duplicate card
            with open(card_path, encoding="utf-8") as f:
                self.assertIn("In progress...", f.read())  # agent's text survived

    def test_recollecting_a_still_pending_batch_card_does_not_duplicate_it(self):
        with tempfile.TemporaryDirectory() as hub:
            pdf_path = os.path.join(hub, "doc.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 fake content for file_id hashing")

            driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ):
                    driver.transcribe_batch(pdf_path, "gemini-3.1-flash-lite", [1, 2], "the batch prompt")
            doc_dir = os.path.join(hub, ".agent_work", "run-1", driver.last_doc_slug)

            second_driver = AgentDriver(hub, "run-1")
            with self.assertRaises(AgentPending):
                with unittest.mock.patch(
                    "pipelines.transcribe_notes.agent_work.render_page_to_image_bytes",
                    return_value=b"fake-png-bytes",
                ):
                    second_driver.transcribe_batch(pdf_path, "gemini-3.1-flash-lite", [1, 2], "the batch prompt")

            entries = load_manifest(doc_dir)
            self.assertEqual(len(entries), 1)  # no duplicate card for the same batch


if __name__ == "__main__":
    unittest.main()
