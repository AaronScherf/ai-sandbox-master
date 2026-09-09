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


from notes.transcribe_excalidraw import assemble_raw_markdown, build_chunk_transcription_prompt


def test_build_chunk_transcription_prompt_mentions_chunk_position():
    prompt = build_chunk_transcription_prompt("", chunk_index=0, total_chunks=5)
    assert "chunk 1 of 5" in prompt.lower()


def test_build_chunk_transcription_prompt_includes_accumulated_context():
    prompt = build_chunk_transcription_prompt("--- Chunk 1 ---\nEarlier text", chunk_index=1, total_chunks=5)
    assert "Earlier text" in prompt
    assert "continuity" in prompt.lower()


def test_build_chunk_transcription_prompt_omits_context_block_when_empty():
    prompt = build_chunk_transcription_prompt("", chunk_index=0, total_chunks=1)
    assert "already-transcribed" not in prompt.lower()


def test_assemble_raw_markdown_joins_chunks_in_order():
    cache = {"0": "first chunk text", "1": "second chunk text"}
    result = assemble_raw_markdown(cache, total_chunks=2)
    assert result == "<!-- chunk 1 -->\n\nfirst chunk text\n\n<!-- chunk 2 -->\n\nsecond chunk text"


def test_assemble_raw_markdown_skips_missing_chunks():
    cache = {"0": "first chunk text"}  # chunk 1 never transcribed (failed)
    result = assemble_raw_markdown(cache, total_chunks=2)
    assert result == "<!-- chunk 1 -->\n\nfirst chunk text"
