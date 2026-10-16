import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

TN = "pipelines.transcribe_notes.transcribe_notes"


class TestCheckMathNotationPassthrough(unittest.TestCase):
    def _run(self, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "econ", "paper.pdf")
            os.makedirs(os.path.dirname(pdf))
            with open(pdf, "wb") as f:
                f.write(b"%PDF-1.4 mock")
            reader = MagicMock()
            reader.pages = [MagicMock()]
            reader.metadata = {"/Producer": "Apache FOP"}
            seen = []

            def fake_defective(text, check_math_notation=True):
                seen.append(check_math_notation)
                return False

            with patch("pypdf.PdfReader", return_value=reader), \
                    patch(f"{TN}.has_reliable_pagination", return_value=True), \
                    patch(f"{TN}.extract_all_page_texts", return_value=["Fit is R2 = 0.43."]), \
                    patch(f"{TN}.page_looks_defective", side_effect=fake_defective), \
                    patch(f"{TN}._write_markdown_and_index"):
                from pipelines.transcribe_notes.transcribe_notes import process_pdf
                process_pdf(pdf, None, None, tmp, **kw)
            return seen

    def test_default_keeps_math_notation_check(self):
        self.assertEqual(self._run(), [True])

    def test_false_is_forwarded_to_the_defect_check(self):
        self.assertEqual(self._run(check_math_notation=False), [False])


if __name__ == "__main__":
    unittest.main()
