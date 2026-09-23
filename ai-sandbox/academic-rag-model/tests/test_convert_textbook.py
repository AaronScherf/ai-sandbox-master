import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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


class TestProcessPageRangeFallbackRatio(unittest.TestCase):
    # Real, repeatedly-confirmed incident this session: when the local
    # Marker/VLM inference server dies mid-run, every page in a chunk falls
    # back to raw PyPDF text extraction, producing a chunk 10-100x smaller
    # than its neighbors -- caught only by manually eyeballing chunk file
    # sizes after the fact. process_page_range now reports what fraction of
    # a chunk's pages took that fallback path, so callers can detect this
    # automatically instead.

    def test_ratio_reflects_fraction_of_pages_that_hit_pypdf_fallback(self):
        reader = _blank_pdf_reader(4)
        # Whole-chunk call fails immediately (forcing per-page recovery);
        # of the 4 individual pages, 2 also fail (raw PyPDF fallback) and 2
        # succeed via the per-page VLM retry.
        converter = MagicMock(side_effect=[
            RuntimeError("whole chunk failed"),
            RuntimeError("page 0 failed"),
            RuntimeError("page 1 failed"),
            "rendered-2",
            "rendered-3",
        ])
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(ct, "text_from_rendered", return_value=("page text", {}, {})), \
             patch.object(ct, "remap_page_markers", side_effect=lambda text, *a, **kw: text), \
             patch.object(ct, "remap_image_links", side_effect=lambda text, *a, **kw: text), \
             patch.object(ct, "tag_single_page", side_effect=lambda text, *a, **kw: text):
            images_dir = os.path.join(tmp, "images")
            os.makedirs(images_dir)
            chunk_text, chunk_meta, hit_exception, ratio = ct.process_page_range(
                converter, reader, tmp, 0, 4, images_dir,
                chunk_timeout_s=30, page_timeout_s=30, folio_offset=None, folio_start_page=4,
            )

        self.assertTrue(hit_exception)
        self.assertEqual(ratio, 0.5)

    def test_ratio_is_zero_when_whole_chunk_succeeds(self):
        reader = _blank_pdf_reader(3)
        converter = MagicMock(return_value="rendered")
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(ct, "text_from_rendered", return_value=("page text", {}, {})), \
             patch.object(ct, "remap_page_markers", side_effect=lambda text, *a, **kw: text), \
             patch.object(ct, "remap_image_links", side_effect=lambda text, *a, **kw: text):
            images_dir = os.path.join(tmp, "images")
            os.makedirs(images_dir)
            _, _, hit_exception, ratio = ct.process_page_range(
                converter, reader, tmp, 0, 3, images_dir,
                chunk_timeout_s=30, page_timeout_s=30, folio_offset=None, folio_start_page=3,
            )

        self.assertFalse(hit_exception)
        self.assertEqual(ratio, 0.0)


class TestChunkIsDegraded(unittest.TestCase):
    def test_majority_fallback_is_degraded(self):
        self.assertTrue(ct.chunk_is_degraded(0.75))

    def test_exactly_half_is_not_degraded(self):
        # A tight cluster of hard pages recovering via the normal per-page
        # fallback path is tolerated -- only a clear majority indicates the
        # inference server itself is dead.
        self.assertFalse(ct.chunk_is_degraded(0.5))

    def test_zero_is_not_degraded(self):
        self.assertFalse(ct.chunk_is_degraded(0.0))


class TestComputeChunkBoundariesBootstrapCleanupAndTimeouts(unittest.TestCase):
    # Issue #4: _boundary_bootstrap_images is never cleaned up (accumulates
    # across a whole batch), and the bootstrap process_page_range call
    # hardcodes chunk_timeout_s=1800/page_timeout_s=240 instead of honoring
    # the user's --chunk-timeout/--page-timeout overrides.

    def _run(self, tmp, chunk_timeout_s=1800, page_timeout_s=240):
        reader = _blank_pdf_reader(30)
        converter = MagicMock()
        with patch.object(ct, "process_page_range", return_value=("front matter text", {}, False, 0.0)) as mock_ppr, \
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


class TestFindExistingOutputByFileId(unittest.TestCase):
    # The index card check alone is unreliable in the actual deployment:
    # running on the GCP VM (Step 3.3), the source-indexer needs
    # GEMINI_API_KEY and a real local academic-hub checkout, neither of
    # which exist there, so it silently no-ops every time and no index card
    # is ever written to find. raw_output (GCS or local) is what's actually
    # durable in that environment -- this is the check keyed on that instead.

    def test_local_output_finds_matching_file_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = os.path.join(tmp, "Hansen_Econometrics_2022")
            os.makedirs(book_dir)
            metadata_path = os.path.join(book_dir, "Hansen_Econometrics_2022_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump({"source_pdf_file_id": "fid1"}, f)

            found = ct.find_existing_output_by_file_id(tmp, "fid1")
            self.assertEqual(found, book_dir)

    def test_local_output_no_match_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = os.path.join(tmp, "SomeOtherBook_2020")
            os.makedirs(book_dir)
            with open(os.path.join(book_dir, "SomeOtherBook_2020_metadata.json"), "w", encoding="utf-8") as f:
                json.dump({"source_pdf_file_id": "different-fid"}, f)

            found = ct.find_existing_output_by_file_id(tmp, "fid1")
            self.assertIsNone(found)

    def test_empty_local_output_dir_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = ct.find_existing_output_by_file_id(tmp, "fid1")
            self.assertIsNone(found)

    def test_gcs_output_finds_matching_file_id(self):
        list_result = MagicMock(returncode=0, stdout="gs://bucket/processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022_metadata.json\n")
        cat_result = MagicMock(returncode=0, stdout=json.dumps({"source_pdf_file_id": "fid1"}))
        with patch.object(ct.subprocess, "run", side_effect=[list_result, cat_result]):
            found = ct.find_existing_output_by_file_id("gs://bucket/processed_outputs", "fid1")
        self.assertEqual(found, "gs://bucket/processed_outputs/Hansen_Econometrics_2022")

    def test_gcs_output_no_uploads_yet_returns_none(self):
        list_result = MagicMock(returncode=1, stdout="", stderr="One or more URLs matched no objects.")
        with patch.object(ct.subprocess, "run", return_value=list_result):
            found = ct.find_existing_output_by_file_id("gs://bucket/processed_outputs", "fid1")
        self.assertIsNone(found)

    def test_gcs_output_non_matching_file_id_returns_none(self):
        list_result = MagicMock(returncode=0, stdout="gs://bucket/processed_outputs/Other_2020/Other_2020_metadata.json\n")
        cat_result = MagicMock(returncode=0, stdout=json.dumps({"source_pdf_file_id": "different-fid"}))
        with patch.object(ct.subprocess, "run", side_effect=[list_result, cat_result]):
            found = ct.find_existing_output_by_file_id("gs://bucket/processed_outputs", "fid1")
        self.assertIsNone(found)


class TestCleanupStaleRenamedOutput(unittest.TestCase):
    # Real, confirmed incident: two "UnknownAuthor_..." folders, from before
    # this pipeline had a filename-based naming tier, were left orphaned in
    # both the local download and the GCS bucket after later runs derived
    # better names ("Hansen_Econometrics_2022"-style) for the same two
    # books -- delete_existing_gcs_output() only ever replaces a prior
    # upload at the *exact* current folder name, so a rename between runs
    # left the old name behind forever instead of being cleaned up.

    def test_removes_local_output_under_a_different_stale_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale_dir = os.path.join(tmp, "UnknownAuthor_Econometrics_0000")
            os.makedirs(stale_dir)
            with open(os.path.join(stale_dir, "UnknownAuthor_Econometrics_0000_metadata.json"), "w", encoding="utf-8") as f:
                json.dump({"source_pdf_file_id": "fid1"}, f)

            ct.cleanup_stale_renamed_output(tmp, "fid1", "Hansen_Econometrics_2022", is_gcs_output=False)

            self.assertFalse(os.path.exists(stale_dir))

    def test_does_nothing_when_stale_name_matches_current_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            book_dir = os.path.join(tmp, "Hansen_Econometrics_2022")
            os.makedirs(book_dir)
            with open(os.path.join(book_dir, "Hansen_Econometrics_2022_metadata.json"), "w", encoding="utf-8") as f:
                json.dump({"source_pdf_file_id": "fid1"}, f)

            ct.cleanup_stale_renamed_output(tmp, "fid1", "Hansen_Econometrics_2022", is_gcs_output=False)

            self.assertTrue(os.path.exists(book_dir), "should not delete the current, correctly-named output")

    def test_does_nothing_when_no_prior_output_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Should not raise even though nothing is there yet.
            ct.cleanup_stale_renamed_output(tmp, "fid1", "Hansen_Econometrics_2022", is_gcs_output=False)

    def test_removes_gcs_output_under_a_different_stale_name(self):
        list_result = MagicMock(returncode=0, stdout="gs://bucket/processed_outputs/UnknownAuthor_Econometrics_0000/UnknownAuthor_Econometrics_0000_metadata.json\n")
        cat_result = MagicMock(returncode=0, stdout=json.dumps({"source_pdf_file_id": "fid1"}))
        rm_result = MagicMock(returncode=0)
        with patch.object(ct.subprocess, "run", side_effect=[list_result, cat_result, rm_result]) as mock_run:
            ct.cleanup_stale_renamed_output(
                "gs://bucket/processed_outputs", "fid1", "Hansen_Econometrics_2022", is_gcs_output=True,
            )
        rm_call = mock_run.call_args_list[-1]
        self.assertEqual(rm_call.args[0][:3], ["gcloud", "storage", "rm"])
        self.assertIn("gs://bucket/processed_outputs/UnknownAuthor_Econometrics_0000", rm_call.args[0])


class TestProcessOnePdfSkipsAlreadyConvertedBook(unittest.TestCase):
    # A batch interrupted partway through book 3 of 4, then rerun from the
    # top, used to redo books 1-2 from scratch even though they'd already
    # succeeded and uploaded -- checkpoint_dir is deleted on success (see
    # process_one_pdf's cleanup at the end of a run), so chunk-level resume
    # has nothing left to find for an already-finished book. This is the
    # whole-book skip added ahead of that, keyed on the index card that's
    # only ever written after a book's conversion actually succeeded.

    def test_skips_and_returns_early_when_index_card_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf = os.path.join(tmp, "some_book.pdf")
            with open(input_pdf, "wb") as f:
                f.write(b"%PDF-1.4 fake bytes, only ever hashed in this test, never parsed")

            fake_card = {"path": "processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.md"}
            with patch.object(ct, "find_card_by_file_id", return_value=("econ-101", fake_card)) as mock_find, \
                 patch.object(ct, "PdfReader") as mock_reader:
                result = ct.process_one_pdf(
                    converter=MagicMock(), raw_input=input_pdf, raw_output=tmp,
                    workspace=tmp, args=MagicMock(),
                )

            self.assertEqual(result, fake_card["path"])
            mock_reader.assert_not_called()
            mock_find.assert_called_once()

    def test_skips_via_output_dir_when_no_index_card_but_output_already_exists(self):
        # The realistic case on the GCP VM: the indexer never wrote a card
        # there (no GEMINI_API_KEY, no local academic-hub), but the book's
        # own output IS already sitting under raw_output from an earlier,
        # interrupted-later run of this same batch.
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf = os.path.join(tmp, "some_book.pdf")
            with open(input_pdf, "wb") as f:
                f.write(b"%PDF-1.4 fake bytes, only ever hashed in this test, never parsed")

            output_dir = os.path.join(tmp, "output")
            book_dir = os.path.join(output_dir, "Hansen_Econometrics_2022")
            os.makedirs(book_dir)
            file_id = ct.compute_file_id(input_pdf)
            with open(os.path.join(book_dir, "Hansen_Econometrics_2022_metadata.json"), "w", encoding="utf-8") as f:
                json.dump({"source_pdf_file_id": file_id}, f)

            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader") as mock_reader:
                result = ct.process_one_pdf(
                    converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                    workspace=tmp, args=MagicMock(),
                )

            self.assertEqual(result, book_dir)
            mock_reader.assert_not_called()

    def test_proceeds_normally_when_nothing_already_converted(self):
        # Not a full end-to-end run (that needs a real batch of mocks this
        # test doesn't set up) -- just confirms both skip checks are a no-op
        # when there's genuinely nothing to skip, i.e. PdfReader IS reached.
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf = os.path.join(tmp, "some_book.pdf")
            with open(input_pdf, "wb") as f:
                f.write(b"not a real pdf, just needs to exist and be hashable")

            output_dir = os.path.join(tmp, "output")
            os.makedirs(output_dir)

            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", side_effect=RuntimeError("reached PdfReader, as expected")):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=MagicMock(),
                    )


class TestProcessOnePdfAbortsOnDegradedChunk(unittest.TestCase):
    # The safety property behind the fix: process_one_pdf must never
    # checkpoint a chunk as done when process_page_range reports the local
    # inference server was effectively dead for it -- but a lone hard page
    # recovering through the normal per-page fallback (low ratio) must NOT
    # abort the run.

    def _setup(self, tmp):
        input_pdf = os.path.join(tmp, "some_book.pdf")
        with open(input_pdf, "wb") as f:
            f.write(b"not a real pdf, just needs to exist and be hashable")
        output_dir = os.path.join(tmp, "output")
        os.makedirs(output_dir)
        reader = _blank_pdf_reader(4)
        args = MagicMock(chunk_timeout=30, page_timeout=30)
        return input_pdf, output_dir, reader, args

    def test_aborts_before_writing_done_marker_when_chunk_is_degraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)

            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("mostly empty", {}, True, 0.75)):
                with self.assertRaises(SystemExit):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )

            done_marker = os.path.join(tmp, "marker_checkpoints", "some_book", "chunks", "00000_00004.done")
            self.assertFalse(os.path.exists(done_marker), "a degraded chunk must never be checkpointed as done")

    def test_does_not_abort_when_fallback_ratio_is_low(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)

            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("real content", {}, True, 0.25)), \
                 patch.object(ct.gc, "collect", side_effect=RuntimeError("reached post-checkpoint cleanup, as expected")):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )

            done_marker = os.path.join(tmp, "marker_checkpoints", "some_book", "chunks", "00000_00004.done")
            self.assertTrue(os.path.exists(done_marker), "a merely-recovered chunk should still be checkpointed")


class TestProcessOnePdfEmitsRamSizingMarkers(unittest.TestCase):
    def _setup(self, tmp):
        input_pdf = os.path.join(tmp, "some_book.pdf")
        with open(input_pdf, "wb") as f:
            f.write(b"not a real pdf, just needs to exist, be hashable, and be sized")
        output_dir = os.path.join(tmp, "output")
        os.makedirs(output_dir)
        reader = _blank_pdf_reader(4)
        args = MagicMock(chunk_timeout=30, page_timeout=30, llm_bib=False)
        return input_pdf, output_dir, reader, args

    def test_emits_start_marker_with_pages_and_file_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            expected_size = os.path.getsize(input_pdf)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", side_effect=RuntimeError("reached boundaries, as expected")), \
                 redirect_stdout(captured):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            output = captured.getvalue()
            self.assertIn(f"RAM_SIZING_START book=some_book pages=4 file_size_bytes={expected_size} ts=", output)

    def test_ram_sizing_start_marker_includes_cumulative_totals_across_books(self):
        # Reset module-level counters since they persist across tests in a pytest session.
        ct._cumulative_pages_this_batch = 0
        ct._cumulative_file_size_bytes_this_batch = 0

        with tempfile.TemporaryDirectory() as tmp:
            input_pdf_a, output_dir, reader, args = self._setup(tmp)
            input_pdf_b = os.path.join(tmp, "second_book.pdf")
            with open(input_pdf_b, "wb") as f:
                f.write(b"a second fake pdf, different size from the first one")
            size_a = os.path.getsize(input_pdf_a)
            size_b = os.path.getsize(input_pdf_b)

            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", side_effect=RuntimeError("reached boundaries, as expected")), \
                 redirect_stdout(captured):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf_a, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf_b, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            lines = [l for l in captured.getvalue().splitlines() if l.startswith("RAM_SIZING_START")]
            self.assertEqual(len(lines), 2)

            # First book: cumulative totals equal that book's own totals.
            self.assertIn(f"cumulative_pages_so_far=4", lines[0])
            self.assertIn(f"cumulative_file_size_bytes_so_far={size_a}", lines[0])

            # Second book: cumulative totals include both books.
            self.assertIn(f"cumulative_pages_so_far=8", lines[1])
            self.assertIn(f"cumulative_file_size_bytes_so_far={size_a + size_b}", lines[1])

            # New fields come AFTER ts=, not before it -- confirms the
            # existing field order/regex sequence wasn't disturbed.
            self.assertRegex(lines[0], r"file_size_bytes=\d+ ts=\d+ cumulative_pages_so_far=")

    def test_no_ram_sizing_marker_when_book_is_skipped_as_already_converted(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            fake_card = {"path": "processed_outputs/Hansen_Econometrics_2022/Hansen_Econometrics_2022.md"}
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=("econ-101", fake_card)), \
                 patch.object(ct, "PdfReader") as mock_reader, \
                 redirect_stdout(captured):
                ct.process_one_pdf(
                    converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                    workspace=tmp, args=args,
                )
            mock_reader.assert_not_called()
            self.assertNotIn("RAM_SIZING", captured.getvalue())

    def test_emits_end_marker_with_status_success_on_a_successful_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("# Some real content\n", {}, False, 0.0)), \
                 patch.object(ct, "get_gemini_client", return_value=None), \
                 patch.object(ct, "load_dotenv_override"), \
                 redirect_stdout(captured):
                ct.process_one_pdf(
                    converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                    workspace=tmp, args=args,
                )
            output = captured.getvalue()
            self.assertIn("RAM_SIZING_END book=some_book ts=", output)
            self.assertIn("status=success", output)

    def test_emits_end_marker_with_status_failed_on_an_unhandled_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("real content", {}, False, 0.0)), \
                 patch.object(ct.gc, "collect", side_effect=RuntimeError("reached post-checkpoint cleanup, as expected")), \
                 redirect_stdout(captured):
                with self.assertRaises(RuntimeError):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            output = captured.getvalue()
            self.assertIn("RAM_SIZING_END book=some_book ts=", output)
            self.assertIn("status=failed", output)

    def test_emits_end_marker_with_status_failed_when_a_chunk_is_degraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_pdf, output_dir, reader, args = self._setup(tmp)
            captured = io.StringIO()
            with patch.object(ct, "find_card_by_file_id", return_value=None), \
                 patch.object(ct, "PdfReader", return_value=reader), \
                 patch.object(ct, "_load_or_compute_boundaries", return_value=([(0, 4)], None, 4)), \
                 patch.object(ct, "process_page_range", return_value=("mostly empty", {}, True, 0.75)), \
                 redirect_stdout(captured):
                with self.assertRaises(SystemExit):
                    ct.process_one_pdf(
                        converter=MagicMock(), raw_input=input_pdf, raw_output=output_dir,
                        workspace=tmp, args=args,
                    )
            output = captured.getvalue()
            self.assertIn("RAM_SIZING_END book=some_book ts=", output)
            self.assertIn("status=failed", output)


if __name__ == "__main__":
    unittest.main()
