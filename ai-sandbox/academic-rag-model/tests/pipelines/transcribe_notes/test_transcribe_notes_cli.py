# tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
import os
import subprocess
import sys
import tempfile
import unittest


def _write_minimal_pdf(path: str) -> None:
    # A single-page PDF with no embedded text layer and no reliable-
    # pagination metadata -- routes to tier 3, which is enough to prove
    # --collect writes a task card without touching the network.
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "handwritten-looking content")
    doc.save(path)
    doc.close()


class TestCollectCLI(unittest.TestCase):
    def test_collect_runs_with_no_api_key_and_writes_a_task_card(self):
        with tempfile.TemporaryDirectory() as hub:
            # --notes-subdir is resolved directly under the hub root
            # (academic_hub_dir / args.notes_subdir, no implicit
            # "academic_notes/" prefix -- see the README's own
            # --notes-subdir academic_notes/math-camp/problem_sets
            # example), so the PDF and the --notes-subdir value must
            # agree on the full relative path.
            notes_dir = os.path.join(hub, "academic_notes", "course", "ta_notes")
            os.makedirs(notes_dir)
            _write_minimal_pdf(os.path.join(notes_dir, "sample.pdf"))

            env = dict(os.environ)
            env.pop("GEMINI_API_KEY", None)
            env.pop("PAID_GEMINI_KEY", None)
            result = subprocess.run(
                [
                    sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                    "--notes-subdir", "academic_notes/course/ta_notes", "--driver", "agent", "--collect",
                    "--run-id", "test-run",
                ],
                # __file__ is tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py --
                # 4 dirname() calls walk up to academic-rag-model/ (3 lands one level
                # short, at tests/, where the pipelines package isn't importable).
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),

                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub},  # see Step 3 note on how main() resolves this in tests
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            card = os.path.join(hub, ".agent_work", "test-run")
            self.assertTrue(os.path.isdir(card), f"no run directory written; stdout={result.stdout}")


if __name__ == "__main__":
    unittest.main()
