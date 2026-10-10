# tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py
import json
import os
import subprocess
import sys
import tempfile
import unittest

# __file__ is tests/pipelines/transcribe_notes/test_transcribe_notes_cli.py --
# 4 dirname() calls walk up to academic-rag-model/ (3 lands one level short,
# at tests/, where the pipelines package isn't importable as a subprocess cwd).
_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


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
                cwd=_PACKAGE_ROOT,
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub},  # see Step 3 note on how main() resolves this in tests
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            card = os.path.join(hub, ".agent_work", "test-run")
            self.assertTrue(os.path.isdir(card), f"no run directory written; stdout={result.stdout}")


class TestSubmitAndBootstrapCLI(unittest.TestCase):
    def test_bootstrap_prints_contract_text(self):
        with tempfile.TemporaryDirectory() as hub:
            env = dict(os.environ)
            result = subprocess.run(
                [sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                 "--notes-subdir", "x", "--bootstrap", "test-run"],
                cwd=_PACKAGE_ROOT,
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Agent output", result.stdout)
            self.assertIn("submit", result.stdout)

    def test_collect_then_submit_end_to_end_with_no_network(self):
        with tempfile.TemporaryDirectory() as hub:
            # --submit acquires corpus_write_lock, which resolves repository
            # identity via `git rev-parse --show-toplevel` -- a bare tempdir
            # (not inside any git repo) makes that fail. academic-hub/ is
            # always a real git repo in production use, so this test needs
            # one too.
            subprocess.run(["git", "init", "--quiet"], cwd=hub, check=True)
            # corpus_write_lock resolves academic_hub_dir / "academic_notes"
            # with strict=True -- it must exist on disk even though this
            # test's PDF lives directly under notes/, not academic_notes/.
            os.makedirs(os.path.join(hub, "academic_notes"))
            notes_dir = os.path.join(hub, "notes")
            os.makedirs(notes_dir)
            _write_minimal_pdf(os.path.join(notes_dir, "doc.pdf"))
            env = dict(os.environ)
            env.pop("GEMINI_API_KEY", None)
            env.pop("PAID_GEMINI_KEY", None)

            collect = subprocess.run(
                [sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                 "--notes-subdir", "notes", "--driver", "agent", "--collect", "--run-id", "e2e"],
                cwd=_PACKAGE_ROOT,
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub}, capture_output=True, text=True,
            )
            self.assertEqual(collect.returncode, 0, msg=collect.stderr)

            run_dir = os.path.join(hub, ".agent_work", "e2e")
            doc_slug = os.listdir(run_dir)[0]
            doc_dir = os.path.join(run_dir, doc_slug)
            manifest_path = os.path.join(doc_dir, "manifest.json")
            with open(manifest_path, encoding="utf-8") as f:
                entries = json.load(f)
            self.assertEqual(len(entries), 1)
            task_id = entries[0]["task_id"]
            card_path = os.path.join(doc_dir, f"{task_id}.md")
            with open(card_path, encoding="utf-8") as f:
                content = f.read()
            with open(card_path, "w", encoding="utf-8") as f:
                f.write(content.replace(
                    "## Agent output\n\n", "## Agent output\n\n--- PAGE 1 ---\nTranscribed text.\n",
                ))

            submit = subprocess.run(
                [sys.executable, "-m", "pipelines.transcribe_notes.transcribe_notes",
                 "--notes-subdir", "notes", "--submit", "e2e"],
                cwd=_PACKAGE_ROOT,
                env={**env, "ACADEMIC_HUB_ROOT_OVERRIDE": hub}, capture_output=True, text=True,
            )
            self.assertEqual(submit.returncode, 0, msg=submit.stderr)
            md_path = os.path.join(notes_dir, "processed_outputs", "doc.md")
            self.assertTrue(os.path.exists(md_path), f"stdout={submit.stdout}")
            with open(md_path, encoding="utf-8") as f:
                written = f.read()
            self.assertIn("Transcribed text.", written)
            self.assertIn("driver: agent", written)


if __name__ == "__main__":
    unittest.main()
