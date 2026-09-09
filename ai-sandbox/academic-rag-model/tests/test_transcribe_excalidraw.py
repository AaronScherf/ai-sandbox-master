import os

from notes.transcribe_excalidraw import discover_excalidraw_files


def test_discover_excalidraw_files_pairs_md_and_png(tmp_path):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing A.excalidraw.png").write_bytes(b"fake-png")
    (tmp_path / "Drawing B.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing B.excalidraw.png").write_bytes(b"fake-png")

    pairs = discover_excalidraw_files(str(tmp_path))

    assert pairs == [
        (str(tmp_path / "Drawing A.excalidraw.md"), str(tmp_path / "Drawing A.excalidraw.png")),
        (str(tmp_path / "Drawing B.excalidraw.md"), str(tmp_path / "Drawing B.excalidraw.png")),
    ]


def test_discover_excalidraw_files_skips_md_with_no_png(tmp_path, capsys):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    # no matching PNG

    pairs = discover_excalidraw_files(str(tmp_path))

    assert pairs == []
    assert "no matching .png" in capsys.readouterr().out.lower()


def test_discover_excalidraw_files_respects_file_filter(tmp_path):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing A.excalidraw.png").write_bytes(b"fake-png")
    (tmp_path / "Drawing B.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing B.excalidraw.png").write_bytes(b"fake-png")

    pairs = discover_excalidraw_files(str(tmp_path), file_filter="Drawing A.excalidraw.md")

    assert len(pairs) == 1
    assert pairs[0][0].endswith("Drawing A.excalidraw.md")


def test_discover_excalidraw_files_missing_dir_returns_empty():
    assert discover_excalidraw_files("/no/such/dir") == []
