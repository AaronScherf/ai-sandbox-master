import os
import tempfile
from unittest.mock import patch

import pytest

from pipelines.convert_journal_articles import convert_journal_articles as cja
from pipelines.convert_journal_articles import oversize


def _pdf(root, rel, data=b"%PDF x"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path


def _eligible(root, paths, pages):
    with patch.object(cja, "_page_count", side_effect=lambda p: pages[os.path.basename(p)]):
        return cja._eligible_pdfs(paths, oversize.THRESHOLD, root)


def test_threshold_is_one_hundred_pages():
    assert oversize.THRESHOLD == 100 and cja._DEFAULT_MAX_PAGES == 100


def test_oversize_pdf_is_skipped_and_recorded_as_an_open_item(capsys):
    with tempfile.TemporaryDirectory() as root:
        paper = _pdf(root, "journal-articles/a/paper.pdf")
        book = _pdf(root, "journal-articles/a/book.pdf")
        kept = _eligible(root, [paper, book], {"paper.pdf": 30, "book.pdf": 250})
        assert kept == [paper]
        assert oversize.open_items(root) == {"journal-articles/a/book.pdf": {"pages": 250, "choice": None}}
        assert "OVERSIZE" in capsys.readouterr().out


def test_an_already_transcribed_long_pdf_is_not_flagged():
    with tempfile.TemporaryDirectory() as root:
        long = _pdf(root, "journal-articles/a/report.pdf")
        _pdf(root, "journal-articles/a/processed_outputs/report.md", b"text")
        assert _eligible(root, [long], {"report.pdf": 104}) == [long]
        assert oversize.open_items(root) == {}


def test_article_choice_lets_it_through_and_leave_skips_it_quietly(capsys):
    with tempfile.TemporaryDirectory() as root:
        a = _pdf(root, "journal-articles/a/review.pdf")
        b = _pdf(root, "journal-articles/a/book.pdf")
        pages = {"review.pdf": 205, "book.pdf": 300}
        _eligible(root, [a, b], pages)
        oversize.apply_decisions(root, {"journal-articles/a/review.pdf": "article", "journal-articles/a/book.pdf": "leave"})
        capsys.readouterr()
        assert _eligible(root, [a, b], pages) == [a]
        assert "OVERSIZE" not in capsys.readouterr().out
        assert oversize.open_items(root) == {}


def test_move_puts_the_pdf_and_sidecar_in_oversize_pdf_and_keeps_it_out_of_discovery():
    with tempfile.TemporaryDirectory() as root:
        _pdf(root, "journal-articles/a/book.pdf")
        _pdf(root, "journal-articles/a/book.meta.json", b"{}")
        out = oversize.apply_decisions(root, {"journal-articles/a/book.pdf": "move"})
        assert out == {"journal-articles/a/book.pdf": "moved"}
        base = os.path.join(root, "journal-articles", "oversize_PDF")
        assert os.path.exists(os.path.join(base, "book.pdf")) and os.path.exists(os.path.join(base, "book.meta.json"))
        assert not os.path.exists(os.path.join(root, "journal-articles", "a", "book.pdf"))
        assert cja.discover_pdf_files(os.path.join(root, "journal-articles")) == []


def test_move_refuses_to_overwrite_and_unknown_choice_changes_nothing():
    with tempfile.TemporaryDirectory() as root:
        _pdf(root, "journal-articles/a/book.pdf")
        _pdf(root, "journal-articles/oversize_PDF/book.pdf", b"other")
        out = oversize.apply_decisions(root, {"journal-articles/a/book.pdf": "move"})
        assert out["journal-articles/a/book.pdf"].startswith("refused")
        assert os.path.exists(os.path.join(root, "journal-articles", "a", "book.pdf"))
        with pytest.raises(ValueError):
            oversize.apply_decisions(root, {"journal-articles/a/book.pdf": "delete"})


def test_a_path_outside_the_corpus_is_refused_before_anything_moves():
    with tempfile.TemporaryDirectory() as root:
        _pdf(root, "journal-articles/a/book.pdf")
        for bad in ("../elsewhere/book.pdf", "book.pdf"):
            with pytest.raises(ValueError, match="not inside"):
                oversize.apply_decisions(root, {"journal-articles/a/book.pdf": "move", bad: "move"})
        assert os.path.exists(os.path.join(root, "journal-articles", "a", "book.pdf"))


def test_dry_run_does_not_write_the_oversize_ledger(capsys):
    with tempfile.TemporaryDirectory() as root:
        pdf = _pdf(root, "journal-articles/a/book.pdf")
        with patch.object(cja, "_page_count", return_value=300):
            assert cja._eligible_pdfs([pdf], oversize.THRESHOLD, None) == []
        assert oversize.load(root) == {}


def test_replication_packages_are_not_discovered_as_papers():
    with tempfile.TemporaryDirectory() as root:
        _pdf(root, "a/paper.pdf")
        _pdf(root, "a/17945_Data_and_Programs/replication_materials/README.pdf")
        assert [os.path.basename(p) for p in cja.discover_pdf_files(root)] == ["paper.pdf"]


def test_queue_lists_untranscribed_pdfs_by_state():
    from pipelines.convert_journal_articles import queue
    with tempfile.TemporaryDirectory() as root:
        arts = os.path.join(root, "journal-articles")
        paths = [_pdf(root, f"journal-articles/a/{n}.pdf") for n in ("done", "short", "mid", "book", "kept", "gone", "bad")]
        done = "".join(f"<!-- page {n} -->\nx\n" for n in range(1, 11)).encode()
        _pdf(root, "journal-articles/a/processed_outputs/done.md", done)
        pages = {"done": 10, "short": 5, "mid": 40, "book": 300, "kept": 205, "gone": 400, "bad": None}
        oversize.apply_decisions(root, {"journal-articles/a/kept.pdf": "article", "journal-articles/a/gone.pdf": "leave"})
        q = queue.build(arts, root, paths, lambda p: pages[os.path.splitext(os.path.basename(p))[0]])
        assert [r["path"] for r in q["ready"]] == ["a/short.pdf", "a/mid.pdf"]
        assert [r["path"] for r in q["ready_long"]] == ["a/kept.pdf"]
        assert [r["path"] for r in q["waiting"]] == ["a/book.pdf"]
        assert [r["path"] for r in q["unreadable"]] == ["a/bad.pdf"]
        text = queue.render(q)
        assert "2 PDFs, 45 pages" in text and "a/done.pdf" not in text


def test_queue_flags_a_transcript_that_is_missing_pages():
    from pipelines.convert_journal_articles import queue
    with tempfile.TemporaryDirectory() as root:
        arts = os.path.join(root, "journal-articles")
        paper = _pdf(root, "journal-articles/a/paper.pdf")
        _pdf(root, "journal-articles/a/processed_outputs/paper.md", b"<!-- page 1 -->\nx\n<!-- page 2 -->\ny")
        q = queue.build(arts, root, [paper], lambda p: 5)
        assert q["ready"] == [{"path": "a/paper.pdf", "pages": 5, "incomplete": "transcript has 2 of 5 pages"}]
        assert "transcript has 2 of 5 pages" in queue.render(q)
        assert queue.build(arts, root, [paper], lambda p: 2)["ready"] == []
