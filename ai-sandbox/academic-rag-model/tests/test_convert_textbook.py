import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# convert_textbook.py imports torch/marker at module scope for its GPU
# pipeline pieces, which aren't installed/needed to exercise its pure-logic
# functions locally -- stub out the marker submodules before import so this
# file can test those functions without a GPU or the marker package.
for _mod in ("marker", "marker.converters", "marker.converters.pdf", "marker.models", "marker.output"):
    sys.modules.setdefault(_mod, MagicMock())

from pypdf import PdfReader, PdfWriter

from textbook import convert_textbook as ct


def _blank_pdf_reader(num_pages):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return PdfReader(buf)


class TestLoadOrComputeBoundariesCorruptRunConfig(unittest.TestCase):
    # Issue #3: a corrupt/truncated run_config.json hit the same silent
    # except-pass as the old-format case, but never got the stale-chunk-
    # clearing treatment the old-format case does -- risking a duplicate-
    # content merge if the recomputed boundaries differ (the probe is
    # documented as potentially nondeterministic).

    def test_corrupt_run_config_clears_stale_chunks_before_recompute(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_dir = os.path.join(tmp, "marker_checkpoints", "book")
            chunks_dir = os.path.join(checkpoint_dir, "chunks")
            os.makedirs(chunks_dir)
            stale_chunk = os.path.join(chunks_dir, "00000_00010.md")
            with open(stale_chunk, "w") as f:
                f.write("stale content from an old boundary scheme")

            run_config_path = os.path.join(checkpoint_dir, "run_config.json")
            with open(run_config_path, "w") as f:
                f.write("{not valid json")  # corrupt/truncated

            with patch.object(ct, "compute_chunk_boundaries", return_value=([(0, 20)], 3, 20)):
                boundaries, folio_offset, folio_start_page = ct._load_or_compute_boundaries(
                    run_config_path, MagicMock(), MagicMock(), tmp, 20, 150, 20, 5, True,
                )

            self.assertEqual(boundaries, [(0, 20)])
            self.assertFalse(os.path.exists(stale_chunk), "stale chunk from the old scheme should be discarded")

    def test_missing_boundaries_key_still_clears_stale_chunks(self):
        # The pre-existing old-format-file behavior, confirmed unbroken by
        # the fix above.
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_dir = os.path.join(tmp, "marker_checkpoints", "book")
            chunks_dir = os.path.join(checkpoint_dir, "chunks")
            os.makedirs(chunks_dir)
            stale_chunk = os.path.join(chunks_dir, "00000_00010.md")
            with open(stale_chunk, "w") as f:
                f.write("stale")

            run_config_path = os.path.join(checkpoint_dir, "run_config.json")
            with open(run_config_path, "w") as f:
                json.dump({"chunk_size": 150}, f)  # old format, no "boundaries" key

            with patch.object(ct, "compute_chunk_boundaries", return_value=([(0, 20)], None, 20)):
                ct._load_or_compute_boundaries(
                    run_config_path, MagicMock(), MagicMock(), tmp, 20, 150, 20, 5, True,
                )

            self.assertFalse(os.path.exists(stale_chunk))

    def test_valid_run_config_is_used_without_recomputing(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_dir = os.path.join(tmp, "marker_checkpoints", "book")
            os.makedirs(checkpoint_dir)
            run_config_path = os.path.join(checkpoint_dir, "run_config.json")
            with open(run_config_path, "w") as f:
                json.dump({"boundaries": [[0, 10], [10, 20]], "folio_offset": 2, "folio_start_page": 10}, f)

            with patch.object(ct, "compute_chunk_boundaries") as mock_compute:
                boundaries, folio_offset, folio_start_page = ct._load_or_compute_boundaries(
                    run_config_path, MagicMock(), MagicMock(), tmp, 20, 150, 20, 5, True,
                )

            mock_compute.assert_not_called()
            self.assertEqual(boundaries, [(0, 10), (10, 20)])
            self.assertEqual(folio_offset, 2)

    def test_writes_run_config_atomically_no_leftover_tmp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            checkpoint_dir = os.path.join(tmp, "marker_checkpoints", "book")
            os.makedirs(checkpoint_dir)
            run_config_path = os.path.join(checkpoint_dir, "run_config.json")

            with patch.object(ct, "compute_chunk_boundaries", return_value=([(0, 20)], 3, 20)):
                ct._load_or_compute_boundaries(
                    run_config_path, MagicMock(), MagicMock(), tmp, 20, 150, 20, 5, True,
                )

            self.assertTrue(os.path.exists(run_config_path))
            with open(run_config_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["boundaries"], [[0, 20]])
            leftover_tmp = [f for f in os.listdir(checkpoint_dir) if f.endswith(".tmp")]
            self.assertEqual(leftover_tmp, [])


class TestProbeAndShiftBoundaryShiftCap(unittest.TestCase):
    # Issue #4a: `while shifted <= max_shift` permits max_shift + 1 shifts.

    def test_never_shifts_more_than_max_shift_times(self):
        reader = _blank_pdf_reader(30)
        converter = MagicMock(return_value="rendered")
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(ct, "text_from_rendered", return_value=("some text", None, None)), \
             patch.object(ct, "_page_looks_unterminated", return_value=True):
            end_page = ct.probe_and_shift_boundary(
                converter, reader, tmp, candidate_end_page=10, max_shift=3, hard_limit_page=25,
            )
        self.assertEqual(end_page, 13)  # exactly 3 shifts from 10, never 4


class TestComputeChunkBoundariesBootstrapCleanupAndTimeouts(unittest.TestCase):
    # Issue #4: _boundary_bootstrap_images is never cleaned up (accumulates
    # across a whole batch), and the bootstrap process_page_range call
    # hardcodes chunk_timeout_s=1800/page_timeout_s=240 instead of honoring
    # the user's --chunk-timeout/--page-timeout overrides.

    def _run(self, tmp, chunk_timeout_s=1800, page_timeout_s=240):
        reader = _blank_pdf_reader(30)
        converter = MagicMock()
        with patch.object(ct, "process_page_range", return_value=("front matter text", {}, False)) as mock_ppr, \
             patch.object(ct.chapter_index, "get_all_outline_entries", return_value=[]), \
             patch.object(ct.chapter_index, "parse_printed_toc", return_value=[]), \
             patch.object(ct.chapter_index, "bootstrap_chapter_index_from_front_matter", return_value=([], None)), \
             patch.object(ct.chapter_index, "pack_chapters_into_chunks", return_value=[(0, 30)]), \
             patch.object(ct.chapter_index, "resolve_probe_boundaries", return_value=[(0, 30)]):
            ct.compute_chunk_boundaries(
                converter, reader, tmp, 30, 150, 20, 5, True,
                chunk_timeout_s=chunk_timeout_s, page_timeout_s=page_timeout_s,
            )
        return mock_ppr

    def test_bootstrap_images_dir_is_cleaned_up_after_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run(tmp)
            images_dir = os.path.join(tmp, "marker_checkpoints", "_boundary_bootstrap_images")
            self.assertFalse(os.path.exists(images_dir), "bootstrap scratch images should not persist after use")

    def test_custom_timeouts_are_threaded_through_not_hardcoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            mock_ppr = self._run(tmp, chunk_timeout_s=99, page_timeout_s=17)
            _, kwargs = mock_ppr.call_args
            self.assertEqual(kwargs["chunk_timeout_s"], 99)
            self.assertEqual(kwargs["page_timeout_s"], 17)


if __name__ == "__main__":
    unittest.main()
