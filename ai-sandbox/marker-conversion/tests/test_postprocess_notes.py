import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

import postprocessing.postprocess_notes as pn

# Issue #11: two of its three sub-items ("never exercised across multiple
# --root directories in one invocation" and "the pattern-review threshold
# has never actually fired in any real run") turn out to already be
# unit-tested at the function level (discover_markdown_files,
# documents_needing_review) -- what was genuinely missing is coverage of
# main() itself, the CLI orchestration layer that ties discovery,
# per-document processing, and the corpus-wide pattern aggregation
# together. This file is the first test coverage for postprocess_notes.py
# at all. The network/local-model boundary (find_candidates_for_page,
# repair_page_individually, get_gemini_client) is mocked; everything else
# -- frontmatter parsing, page splitting, cross-reference pooling,
# grouping, threshold logic -- runs for real.


def _write_md(path, frontmatter_lines, pages):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    header = "\n".join(["---"] + frontmatter_lines + ["---"]) + "\n\n"
    # split_pages_by_tag's _PAGE_TAG_RE requires a blank line after the tag.
    body = "".join(f"<!-- page {page_num} -->\n\n{text}\n\n" for page_num, text in pages.items())
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + body)


class TestMainMultiRootAndPatternReview(unittest.TestCase):
    def test_targets_from_both_roots_processed_and_threshold_fires_correctly(self):
        with tempfile.TemporaryDirectory() as root1, tempfile.TemporaryDirectory() as root2:
            target_a = os.path.join(root1, "problem_sets", "processed_outputs", "target_a.md")
            _write_md(
                target_a,
                ["routing: local", "total_pages: 5"],
                {i: f"Page {i} text mentioning Omega." for i in range(1, 6)},
            )
            # Not a correction target (routing is already model-verified) --
            # included only so its content is available as cross-reference
            # material, proving root2's files really do enter the shared
            # reference pool, not just get discovered.
            other = os.path.join(root2, "ta_notes", "processed_outputs", "other.md")
            _write_md(
                other,
                ["routing: gemini_batched", "total_pages: 1"],
                {1: "Reference text mentioning Omega for cross-checking."},
            )

            argv = ["postprocess_notes.py", "--root", root1, "--root", root2]

            with patch.object(sys, "argv", argv), \
                 patch.object(pn, "load_dotenv_override"), \
                 patch.object(pn, "get_gemini_client", return_value=MagicMock()), \
                 patch.object(pn, "find_source_pdf", return_value="/fake/target_a.pdf"), \
                 patch.object(pn, "find_candidates_for_page",
                               return_value=[{"text": "Omega", "source": "causal_then_masked"}]), \
                 patch.object(pn, "repair_page_individually",
                               side_effect=RuntimeError("simulated verification failure")), \
                 patch.object(pn, "search_reference_documents", wraps=pn.search_reference_documents) as mock_search:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    pn.main()

            output = buf.getvalue()

            # Multi-root discovery + processing reached the target in root1.
            # (other.md is also nominally a "target" -- it has a routing
            # field -- but gemini_batched has zero eligible pages, so it's
            # processed and immediately no-ops; both get listed as
            # "processing", which is correct, not a bug.)
            self.assertIn("[target_a.md] processing", output)
            self.assertIn("[other.md] processing", output)

            # The pattern-review threshold (5 identical-signature findings,
            # all from target_a's 5 pages failing verification the same
            # way) fires and reports the right document.
            self.assertIn("Documents with a consistent low-confidence pattern", output)
            self.assertIn("target_a.md", output.split("consistent low-confidence pattern")[1])

            # other.md was never a target (routing is already fully
            # verified), so it must not appear as a flagged document.
            review_section = output.split("consistent low-confidence pattern")[1]
            self.assertNotIn("other.md", review_section)

            # The cross-reference pool passed into search really does span
            # both roots -- not just target_a's own file.
            self.assertTrue(mock_search.call_args_list, "search_reference_documents was never called")
            reference_texts_seen = mock_search.call_args_list[0].args[1]
            self.assertIn(target_a, reference_texts_seen)
            self.assertIn(other, reference_texts_seen)

    def test_single_root_with_no_pattern_reports_none_needed(self):
        # Below-threshold control case: a target whose candidates all
        # verify successfully (no exception) never enters `unresolved` at
        # all, so the threshold correctly never fires.
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "problem_sets", "processed_outputs", "clean.md")
            _write_md(target, ["routing: local", "total_pages: 2"], {1: "Page one.", 2: "Page two."})

            argv = ["postprocess_notes.py", "--root", root]

            with patch.object(sys, "argv", argv), \
                 patch.object(pn, "load_dotenv_override"), \
                 patch.object(pn, "get_gemini_client", return_value=MagicMock()), \
                 patch.object(pn, "find_source_pdf", return_value="/fake/clean.pdf"), \
                 patch.object(pn, "find_candidates_for_page", return_value=[]):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    pn.main()

            self.assertIn("No documents crossed the pattern-review threshold.", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
