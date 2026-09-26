import io
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from pypdf import PdfWriter

from textbook.split_chapters import (
    _locate_source_pdf,
    _manual_chapter_list_path,
    _slugify,
    discover_book_dirs,
    ensure_chapter_template,
    split_book,
    split_into_chapter_files,
)


def _fake_gemini_client(default_response=None, repair_response=None, classification_response=None):
    """
    A fake client that replies based on which prompt it received, not
    call order -- necessary since call_with_retries can call the same
    prompt multiple times, and table repair now always attempts first
    (see split_book), so a test enabling classification alone still
    needs repair's own attempt(s) to fail cleanly rather than
    mis-parsing a classification response as a repair one.
    """
    client = MagicMock()

    def side_effect(*args, **kwargs):
        contents = kwargs.get("contents", "")
        response = MagicMock()
        if "Reconstruct a clean" in contents and repair_response is not None:
            response.text = repair_response
        elif "Identify every real top-level chapter" in contents and classification_response is not None:
            response.text = classification_response
        else:
            response.text = default_response
        return response

    client.models.generate_content.side_effect = side_effect
    return client


_HAMMACK_STYLE_TOC = (
    "## **Contents**\n\n"
    "| 1. Sets                             |                         |                            | 3          |\n"
    "|-------------------------------------|-------------------------|----------------------------|------------|\n"
    "| 2. Logic                            |                         |                            | 34         |\n"
)

_CONFIDENT_BOOK_TEXT = (
    _HAMMACK_STYLE_TOC
    + "\n<!-- page 1 --><!-- folio 1 -->\n\nTitle page front matter.\n\n"
    + "<!-- page 4 --><!-- folio 3 -->\n\n# Sets\n\nChapter 1 body content.\n\n"
    + "<!-- page 35 --><!-- folio 34 -->\n\n# Logic\n\nChapter 2 body content.\n"
)

_UNCONFIDENT_BOOK_TEXT = (
    _HAMMACK_STYLE_TOC
    + "\n<!-- page 4 --><!-- folio 3 -->\n\n# Sets\n\nOnly one chapter's folio is ever reached.\n"
)


class TestSlugify(unittest.TestCase):
    def test_caps_length_at_a_word_boundary(self):
        # Real bug (Cameron): a chapter title garbled with its own nested
        # sub-TOC ("Hypothesis Tests 223 7.1 Introduction 223 7.2 Wald,
        # Likelihood Ratio, and Lagrange Multiplier Tests 224") produces a
        # 100+ char slug -- capped here rather than in the shared TOC
        # parser, since the file content is still correct either way.
        title = "Hypothesis Tests 223 7.1 Introduction 223 7.2 Wald, Likelihood Ratio, and Lagrange Multiplier Tests 224"
        slug = _slugify(title)
        self.assertLessEqual(len(slug), 60)
        self.assertFalse(slug.endswith("_"))

    def test_short_title_is_unaffected(self):
        self.assertEqual(_slugify("Basic Topology"), "basic_topology")


class TestSplitIntoChapterFiles(unittest.TestCase):
    def test_confident_book_splits_front_matter_and_each_chapter(self):
        files = split_into_chapter_files(_CONFIDENT_BOOK_TEXT)
        self.assertEqual(
            set(files.keys()), {"00_front_matter.rag.md", "01_sets.rag.md", "02_logic.rag.md"}
        )
        self.assertIn("Title page front matter", files["00_front_matter.rag.md"])
        self.assertNotIn("Chapter 2 body content", files["01_sets.rag.md"])
        self.assertIn("Chapter 1 body content", files["01_sets.rag.md"])
        self.assertIn("Chapter 2 body content", files["02_logic.rag.md"])

    def test_unconfident_book_returns_none(self):
        self.assertIsNone(split_into_chapter_files(_UNCONFIDENT_BOOK_TEXT))


def _book_dir(tmp, root_name, course="math-camp", book="Sample_Book_2020"):
    return os.path.join(tmp, root_name, course, "textbooks", "processed_outputs", book)


def _write_metadata(book_dir, book="Sample_Book_2020", source_pdf_filename=None, source_pdf_path=None):
    metadata = {}
    if source_pdf_filename:
        metadata["source_pdf_filename"] = source_pdf_filename
    if source_pdf_path:
        metadata["source_pdf_path"] = source_pdf_path
    with open(os.path.join(book_dir, f"{book}_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f)


def _write_pdf_with_outline(path, entries, num_pages=50):
    """entries: list of (title, page_index) for top-level outline items."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    for title, page_index in entries:
        writer.add_outline_item(title, page_index)
    with open(path, "wb") as f:
        writer.write(f)


class TestLocateSourcePdf(unittest.TestCase):
    def test_finds_pdf_alongside_the_textbooks_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            _write_metadata(resources_dir, source_pdf_filename="source.pdf")
            textbooks_dir = os.path.dirname(os.path.dirname(resources_dir))
            pdf_path = os.path.join(textbooks_dir, "source.pdf")
            open(pdf_path, "wb").close()

            self.assertEqual(_locate_source_pdf(resources_dir), pdf_path)

    def test_resolves_from_a_notes_side_book_dir_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            _write_metadata(resources_dir, source_pdf_filename="source.pdf")
            textbooks_dir = os.path.dirname(os.path.dirname(resources_dir))
            pdf_path = os.path.join(textbooks_dir, "source.pdf")
            open(pdf_path, "wb").close()

            notes_dir = _book_dir(tmp, "academic_notes")
            self.assertEqual(_locate_source_pdf(notes_dir), pdf_path)

    def test_returns_none_when_metadata_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            self.assertIsNone(_locate_source_pdf(resources_dir))

    def test_returns_none_when_source_pdf_filename_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            _write_metadata(resources_dir)
            self.assertIsNone(_locate_source_pdf(resources_dir))

    def test_returns_none_when_pdf_file_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            _write_metadata(resources_dir, source_pdf_filename="missing.pdf")
            self.assertIsNone(_locate_source_pdf(resources_dir))

    def test_falls_back_to_source_pdf_path_when_filename_missing(self):
        # Real case (Axler, Simon): metadata predates source_pdf_filename,
        # but source_pdf_path is still a real, hub-root-relative local
        # path for a book that was converted locally (not on a GCP VM).
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            textbooks_dir = os.path.dirname(os.path.dirname(resources_dir))
            pdf_path = os.path.join(textbooks_dir, "legacy_source.pdf")
            open(pdf_path, "wb").close()

            legacy_path = os.path.relpath(pdf_path, tmp).replace("\\", "/")
            _write_metadata(resources_dir, source_pdf_path=legacy_path)

            self.assertEqual(_locate_source_pdf(resources_dir), pdf_path)

    def test_ignores_a_gcp_temp_source_pdf_path(self):
        # Real case (Hansen): a GCP VM conversion's source_pdf_path is the
        # temp download's own path, never useful locally -- must not be
        # resolved even though nothing else is available to fall back to.
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            _write_metadata(
                resources_dir, source_pdf_path="../academic-rag-model/temp_gcs_input_book.pdf"
            )
            self.assertIsNone(_locate_source_pdf(resources_dir))


class TestSplitBook(unittest.TestCase):
    def test_confident_book_writes_chapters_and_moves_source_to_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_CONFIDENT_BOOK_TEXT)

            resources_dir = _book_dir(tmp, "academic_resources")
            status = split_book(resources_dir)

            self.assertIn("OK", status)
            chapters_dir = os.path.join(notes_dir, "chapters")
            self.assertEqual(
                set(os.listdir(chapters_dir)),
                {"00_front_matter.rag.md", "01_sets.rag.md", "02_logic.rag.md"},
            )
            self.assertFalse(os.path.exists(rag_path))  # moved out of academic_notes/
            moved_path = os.path.join(resources_dir, "Sample_Book_2020.rag.md")
            self.assertTrue(os.path.exists(moved_path))
            with open(moved_path, "r", encoding="utf-8") as f:
                self.assertEqual(f.read(), _CONFIDENT_BOOK_TEXT)

    def test_unconfident_book_is_skipped_and_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_UNCONFIDENT_BOOK_TEXT)

            resources_dir = _book_dir(tmp, "academic_resources")
            status = split_book(resources_dir)

            self.assertIn("SKIP", status)
            self.assertTrue(os.path.exists(rag_path))  # left in place
            self.assertFalse(os.path.exists(os.path.join(notes_dir, "chapters")))

    def test_dry_run_reports_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_CONFIDENT_BOOK_TEXT)

            resources_dir = _book_dir(tmp, "academic_resources")
            status = split_book(resources_dir, dry_run=True)

            self.assertIn("OK", status)
            self.assertTrue(os.path.exists(rag_path))  # nothing written or moved
            self.assertFalse(os.path.exists(os.path.join(notes_dir, "chapters")))

    def test_missing_rag_md_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            status = split_book(resources_dir)
            self.assertIn("SKIP", status)

    def test_falls_back_to_pdf_outline_when_folio_tags_are_missing(self):
        # Real case (Hansen): front-matter OCR never anchors a folio
        # offset, so no <!-- folio N --> tags exist anywhere in the body,
        # but the source PDF's own outline still gives exact chapter
        # page numbers.
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            no_folio_text = (
                _HAMMACK_STYLE_TOC
                + "\n<!-- page 4 -->\n\n# Sets\n\nChapter 1 body content.\n\n"
                + "<!-- page 35 -->\n\n# Logic\n\nChapter 2 body content.\n"
            )
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(no_folio_text)

            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            _write_metadata(resources_dir, source_pdf_filename="source.pdf")
            textbooks_dir = os.path.dirname(os.path.dirname(resources_dir))
            _write_pdf_with_outline(
                os.path.join(textbooks_dir, "source.pdf"), [("1. Sets", 4), ("2. Logic", 35)]
            )

            status = split_book(resources_dir)

            self.assertIn("OK", status)
            self.assertIn("PDF outline", status)
            chapters_dir = os.path.join(notes_dir, "chapters")
            self.assertEqual(
                set(os.listdir(chapters_dir)),
                {"00_front_matter.rag.md", "01_sets.rag.md", "02_logic.rag.md"},
            )
            self.assertFalse(os.path.exists(rag_path))
            self.assertTrue(os.path.exists(os.path.join(resources_dir, "Sample_Book_2020.rag.md")))

    def test_stays_skipped_when_neither_folio_tags_nor_a_usable_pdf_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            no_folio_text = (
                _HAMMACK_STYLE_TOC + "\n<!-- page 4 -->\n\n# Sets\n\nChapter 1 body content.\n"
            )
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(no_folio_text)
            # No metadata.json at all -- no PDF to fall back to.

            resources_dir = _book_dir(tmp, "academic_resources")
            status = split_book(resources_dir)

            self.assertIn("SKIP", status)
            self.assertTrue(os.path.exists(rag_path))

    def test_falls_back_to_a_filled_in_manual_template_as_a_last_resort(self):
        # Real case (Simon): no folio tags, and the PDF has zero outline
        # entries -- a human-filled "Title | Page" template is the only
        # remaining source of chapter boundaries.
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            no_folio_text = (
                _HAMMACK_STYLE_TOC
                + "\n<!-- page 4 -->\n\n# Sets\n\nChapter 1 body content.\n\n"
                + "<!-- page 35 -->\n\n# Logic\n\nChapter 2 body content.\n"
            )
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(no_folio_text)

            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            # No metadata.json -- no PDF outline path available either.
            with open(_manual_chapter_list_path(resources_dir), "w", encoding="utf-8") as f:
                f.write("Sets | 4\nLogic | 35\n")

            status = split_book(resources_dir)

            self.assertIn("OK", status)
            self.assertIn("manual", status)
            chapters_dir = os.path.join(notes_dir, "chapters")
            self.assertEqual(
                set(os.listdir(chapters_dir)),
                {"00_front_matter.rag.md", "01_sets.rag.md", "02_logic.rag.md"},
            )


_NO_FOLIO_BUT_TOC_PARSES = (
    _HAMMACK_STYLE_TOC
    + "\n<!-- page 4 -->\n\n# Sets\n\nChapter 1 body content.\n\n"
    + "<!-- page 35 -->\n\n# Logic\n\nChapter 2 body content.\n"
)

_UNPARSEABLE_TOC_TEXT = (
    "Just some plain front matter prose with no chapter listing at all.\n\n"
    "<!-- page 4 -->\n\n# Sets\n\nChapter 1 body content.\n\n"
    "<!-- page 35 -->\n\n# Logic\n\nChapter 2 body content.\n"
)

_CLASSIFICATION_RESPONSE = '[{"title": "Sets", "page": 4}, {"title": "Logic", "page": 35}]'

_TABLE_REPAIR_RESPONSE = json.dumps({
    "toc_start_marker": "Just some plain front matter prose",
    "toc_end_marker": "no chapter listing at all.",
    "repaired_table_markdown": "# Contents\n\n| Clean | Table |",
})

# Matches _HAMMACK_STYLE_TOC (the TOC block inside _NO_FOLIO_BUT_TOC_PARSES).
_HAMMACK_TABLE_REPAIR_RESPONSE = json.dumps({
    "toc_start_marker": "## **Contents**",
    "toc_end_marker": "| 2. Logic                            |                         |                            | 34         |",
    "repaired_table_markdown": "# Contents\n\n| Clean | Table |",
})


class TestSplitBookGeminiRepair(unittest.TestCase):
    def test_uses_gemini_classification_when_everything_else_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            with open(os.path.join(notes_dir, "Sample_Book_2020.rag.md"), "w", encoding="utf-8") as f:
                f.write(_NO_FOLIO_BUT_TOC_PARSES)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)

            client = _fake_gemini_client(
                repair_response=_HAMMACK_TABLE_REPAIR_RESPONSE, classification_response=_CLASSIFICATION_RESPONSE
            )
            status = split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            self.assertIn("OK", status)
            self.assertIn("Gemini", status)
            self.assertEqual(client.models.generate_content.call_count, 2)  # repair, then classification
            template_path = _manual_chapter_list_path(resources_dir)
            with open(template_path, encoding="utf-8") as f:
                template_content = f.read()
            self.assertIn("AI-generated", template_content)
            self.assertIn("Sets | 4", template_content)
            chapters_dir = os.path.join(notes_dir, "chapters")
            self.assertEqual(
                set(os.listdir(chapters_dir)),
                {"00_front_matter.rag.md", "01_sets.rag.md", "02_logic.rag.md"},
            )

    def test_does_not_overwrite_a_template_with_real_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            with open(os.path.join(notes_dir, "Sample_Book_2020.rag.md"), "w", encoding="utf-8") as f:
                f.write(_NO_FOLIO_BUT_TOC_PARSES)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            with open(_manual_chapter_list_path(resources_dir), "w", encoding="utf-8") as f:
                f.write("Sets | 4\nLogic | 35\n")

            client = _fake_gemini_client(repair_response=_HAMMACK_TABLE_REPAIR_RESPONSE)
            status = split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            self.assertIn("OK", status)
            self.assertIn("manual", status)
            self.assertEqual(client.models.generate_content.call_count, 1)  # repair only, classification skipped
            with open(_manual_chapter_list_path(resources_dir), encoding="utf-8") as f:
                self.assertEqual(f.read(), "Sets | 4\nLogic | 35\n")  # untouched

    def test_overwrites_a_blank_scaffold_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            with open(os.path.join(notes_dir, "Sample_Book_2020.rag.md"), "w", encoding="utf-8") as f:
                f.write(_NO_FOLIO_BUT_TOC_PARSES)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            with open(_manual_chapter_list_path(resources_dir), "w", encoding="utf-8") as f:
                f.write("# just a blank scaffold, no chapters filled in yet\n")

            client = _fake_gemini_client(
                repair_response=_HAMMACK_TABLE_REPAIR_RESPONSE, classification_response=_CLASSIFICATION_RESPONSE
            )
            status = split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            self.assertIn("OK", status)
            self.assertIn("Gemini", status)
            self.assertEqual(client.models.generate_content.call_count, 2)  # repair, then classification

    def test_attempts_table_repair_even_when_the_toc_partially_parses(self):
        # Real bug (Simon): the TOC parsed to 27 correct entries (with
        # real folio numbers!) -- reason was "no folio tags found in the
        # body", not "no parseable table of contents". A narrower trigger
        # gated on that one exact reason string skipped repair entirely,
        # even though the same rendered table is just as unusable to a
        # human reader. Repair now fires whenever folio tags, PDF
        # outline, and manual template have all failed to produce a
        # split, regardless of the specific reason -- table repair and
        # chapter classification are independent jobs, and both apply
        # here.
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_NO_FOLIO_BUT_TOC_PARSES)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)

            client = _fake_gemini_client(
                repair_response=_HAMMACK_TABLE_REPAIR_RESPONSE, classification_response=_CLASSIFICATION_RESPONSE
            )
            split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            self.assertEqual(client.models.generate_content.call_count, 2)
            self.assertTrue(os.path.exists(os.path.join(resources_dir, "Sample_Book_2020.rag.md.bak")))

    def test_repairs_the_toc_table_when_it_is_confirmed_unparseable(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_UNPARSEABLE_TOC_TEXT)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)

            client = _fake_gemini_client("placeholder")
            client.models.generate_content.side_effect = [
                MagicMock(text=_TABLE_REPAIR_RESPONSE),  # table repair, tried first
                MagicMock(text=_CLASSIFICATION_RESPONSE),  # classification, tried second
            ]

            status = split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            self.assertIn("OK", status)
            self.assertEqual(client.models.generate_content.call_count, 2)

            backup_path = os.path.join(resources_dir, "Sample_Book_2020.rag.md.bak")
            self.assertTrue(os.path.exists(backup_path))
            with open(backup_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), _UNPARSEABLE_TOC_TEXT)

            # The book split successfully and moved to resources -- the
            # repaired TOC table should be present in its front matter.
            moved_path = os.path.join(resources_dir, "Sample_Book_2020.rag.md")
            with open(os.path.join(notes_dir, "chapters", "00_front_matter.rag.md"), encoding="utf-8") as f:
                self.assertIn("Clean | Table", f.read())
            self.assertTrue(os.path.exists(moved_path))

    def test_repairs_toc_table_even_when_an_existing_manual_template_already_splits_it(self):
        # Real bug (Hayashi): a book can already have a real, filled-in
        # manual chapter_titles.txt that makes result.confident True on
        # its own -- table repair must still run when the printed TOC
        # itself is confirmed broken, since it exists to fix the file as
        # a standalone artifact, independent of whether splitting already
        # succeeded some other way. Classification, unlike table repair,
        # correctly stays skipped here (nothing left for it to do).
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_UNPARSEABLE_TOC_TEXT)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            with open(_manual_chapter_list_path(resources_dir), "w", encoding="utf-8") as f:
                f.write("Sets | 4\nLogic | 35\n")

            client = _fake_gemini_client(_TABLE_REPAIR_RESPONSE)
            status = split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            self.assertIn("OK", status)
            self.assertIn("manual", status)
            client.models.generate_content.assert_called_once()  # table repair only
            self.assertTrue(os.path.exists(os.path.join(resources_dir, "Sample_Book_2020.rag.md.bak")))

    def test_skips_table_repair_when_a_backup_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            rag_path = os.path.join(notes_dir, "Sample_Book_2020.rag.md")
            with open(rag_path, "w", encoding="utf-8") as f:
                f.write(_UNPARSEABLE_TOC_TEXT)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            with open(os.path.join(resources_dir, "Sample_Book_2020.rag.md.bak"), "w", encoding="utf-8") as f:
                f.write("already repaired once")

            client = _fake_gemini_client(_CLASSIFICATION_RESPONSE)
            split_book(resources_dir, gemini_client=client, gemini_model="test-model")

            client.models.generate_content.assert_called_once()  # classification only, no repair retry

    def test_gemini_repair_never_attempted_during_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes_dir = _book_dir(tmp, "academic_notes")
            os.makedirs(notes_dir)
            with open(os.path.join(notes_dir, "Sample_Book_2020.rag.md"), "w", encoding="utf-8") as f:
                f.write(_UNPARSEABLE_TOC_TEXT)
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)

            client = _fake_gemini_client(_CLASSIFICATION_RESPONSE)
            status = split_book(resources_dir, dry_run=True, gemini_client=client, gemini_model="test-model")

            self.assertIn("SKIP", status)
            client.models.generate_content.assert_not_called()


class TestEnsureChapterTemplate(unittest.TestCase):
    def test_creates_template_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            status = ensure_chapter_template(resources_dir)
            self.assertIn("created", status)
            template_path = _manual_chapter_list_path(resources_dir)
            self.assertTrue(os.path.exists(template_path))
            with open(template_path, encoding="utf-8") as f:
                self.assertIn("Sample_Book_2020", f.read())

    def test_does_not_overwrite_an_existing_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            resources_dir = _book_dir(tmp, "academic_resources")
            os.makedirs(resources_dir)
            template_path = _manual_chapter_list_path(resources_dir)
            with open(template_path, "w", encoding="utf-8") as f:
                f.write("Sets | 4\nLogic | 35\n")

            status = ensure_chapter_template(resources_dir)

            self.assertIn("already exists", status)
            with open(template_path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "Sets | 4\nLogic | 35\n")


class TestDiscoverBookDirs(unittest.TestCase):
    def test_finds_only_books_with_a_rag_md_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            has_rag = _book_dir(tmp, "academic_notes", book="Has_Rag_2020")
            os.makedirs(has_rag)
            with open(os.path.join(has_rag, "Has_Rag_2020.rag.md"), "w", encoding="utf-8") as f:
                f.write("content")

            no_rag = _book_dir(tmp, "academic_notes", book="No_Rag_2021")
            os.makedirs(no_rag)

            processed_outputs_dir = os.path.dirname(has_rag)
            dirs = discover_book_dirs(processed_outputs_dir)
            self.assertEqual([os.path.basename(d) for d in dirs], ["Has_Rag_2020"])


if __name__ == "__main__":
    unittest.main()
