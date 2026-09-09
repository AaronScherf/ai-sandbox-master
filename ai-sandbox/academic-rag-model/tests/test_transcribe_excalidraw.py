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


from unittest.mock import patch

from notes.transcribe_excalidraw import transcribe_chunks


def test_transcribe_chunks_builds_cache_keyed_by_index():
    with patch("notes.transcribe_excalidraw.transcribe_page_via_gemini") as mock_transcribe:
        mock_transcribe.side_effect = ["first chunk text", "second chunk text"]
        cache = transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"])
    assert cache == {"0": "first chunk text", "1": "second chunk text"}


def test_transcribe_chunks_passes_accumulated_context_from_prior_chunks():
    captured_prompts = []

    def fake_transcribe(client, model, image_bytes, prompt):
        captured_prompts.append(prompt)
        return f"text for chunk with prompt len {len(prompt)}"

    with patch("notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake_transcribe):
        transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"])

    # second call's prompt must include the first chunk's already-transcribed text
    assert "text for chunk with prompt len" in captured_prompts[1]


def test_transcribe_chunks_skips_a_chunk_that_fails_after_retries():
    def fake_transcribe(client, model, image_bytes, prompt):
        if image_bytes == b"img1":
            raise ValueError("simulated repetition-loop failure")
        return "ok text"

    with patch("notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake_transcribe):
        with patch("notes.transcribe_excalidraw.call_with_retries", side_effect=lambda fn: fn()):
            cache = transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1", b"img2"])

    assert cache == {"0": "ok text", "2": "ok text"}


from notes.transcribe_excalidraw import build_expansion_prompt, expand_via_gemini


def test_build_expansion_prompt_includes_raw_text():
    prompt = build_expansion_prompt("$$x + y = z$$")
    assert "$$x + y = z$$" in prompt
    assert "cohesive" in prompt.lower() or "prose" in prompt.lower()


def test_build_expansion_prompt_includes_retrieved_passages_when_given():
    prompt = build_expansion_prompt("shorthand notes", retrieved_passages=["Textbook passage about norms."])
    assert "Textbook passage about norms." in prompt


def test_build_expansion_prompt_omits_grounding_block_when_none():
    prompt = build_expansion_prompt("shorthand notes", retrieved_passages=None)
    assert "textbook" not in prompt.lower()


def test_expand_via_gemini_returns_response_text():
    class FakeResponse:
        text = "Expanded prose explaining the shorthand."
        usage_metadata = None

    class FakeModels:
        def generate_content(self, model, contents, config):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    result = expand_via_gemini(FakeClient(), model="gemini-3.1-flash-lite", raw_markdown="shorthand")
    assert result == "Expanded prose explaining the shorthand."
