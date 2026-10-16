import inspect
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from pipelines.transcribe_notes.agent_submit import submit_doc
from pipelines.transcribe_notes.agent_work import AgentDriver, load_manifest

JOURNAL = frozenset({"journal_article"})


class TestSubmitForwardsCollectTimeSettings(unittest.TestCase):
    def test_final_rerun_gets_known_doc_types_and_check_math_notation(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "econ", "paper.pdf")
            os.makedirs(os.path.dirname(pdf))
            with open(pdf, "wb") as f:
                f.write(b"%PDF-1.4 mock")
            reader = MagicMock()
            reader.pages = [MagicMock()]
            reader.metadata = {"/Producer": "pdfTeX"}
            tn = "pipelines.transcribe_notes.transcribe_notes"
            with patch("pypdf.PdfReader", return_value=reader), \
                    patch(f"{tn}.has_reliable_pagination", return_value=True), \
                    patch(f"{tn}.extract_all_page_texts", return_value=["x"]), \
                    patch(f"{tn}.page_looks_defective", return_value=False), \
                    patch("pipelines.transcribe_notes.agent_work.render_page_to_image_bytes", return_value=b"png"):
                from pipelines.transcribe_notes.transcribe_notes import process_pdf
                driver = AgentDriver(tmp, "run-1")
                process_pdf(pdf, None, None, tmp, force_vision=True, driver=driver, collect_mode=True,
                            known_doc_types=JOURNAL, check_math_notation=False)
                slug = driver.last_doc_slug
                doc_dir = os.path.join(tmp, ".agent_work", "run-1", slug)
                card = os.path.join(doc_dir, f"{load_manifest(doc_dir)[0].task_id}.md")
                with open(card, encoding="utf-8") as f:
                    text = f.read()
                with open(card, "w", encoding="utf-8") as f:
                    f.write(text.replace("## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nAgent text.\n"))
                with patch("pipelines.transcribe_notes.agent_submit.process_pdf") as rerun, \
                        patch("pipelines.transcribe_notes.agent_submit.extract_page_text", return_value="hint"):
                    submit_doc(tmp, tmp, "run-1", slug, pdf, MagicMock(), None, force_vision=True,
                               known_doc_types=JOURNAL, check_math_notation=False)
            kwargs = rerun.call_args.kwargs
            self.assertEqual(kwargs["known_doc_types"], JOURNAL)
            self.assertIs(kwargs["check_math_notation"], False)

    def test_signature_defaults_preserve_existing_callers(self):
        sig = inspect.signature(submit_doc).parameters
        self.assertIsNone(sig["known_doc_types"].default)
        self.assertIs(sig["check_math_notation"].default, True)


if __name__ == "__main__":
    unittest.main()
