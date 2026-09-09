import os
import tempfile
import unittest

from resume_manager.render import render_resume_pdf


class TestRenderResumePdf(unittest.TestCase):
    def test_writes_a_non_empty_pdf(self):
        markdown_text = (
            "# Aaron Scherf\n\n## Experience\n\n"
            "### Acme Corp — Engineer (2020 – Present)\n\n- Did a thing\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(markdown_text, output_path)

            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))
