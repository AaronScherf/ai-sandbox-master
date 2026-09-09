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


from common.ollama_utils import OLLAMA_TIMEOUT
from notes.transcribe_excalidraw import expand_transcription, expand_via_ollama


def test_expand_via_ollama_returns_response_text():
    with patch("notes.transcribe_excalidraw.call_ollama", return_value="Expanded via Ollama."):
        result = expand_via_ollama("shorthand", model="qwen2.5:7b-instruct")
    assert result == "Expanded via Ollama."


def test_expand_via_ollama_returns_none_on_timeout():
    with patch("notes.transcribe_excalidraw.call_ollama", return_value=OLLAMA_TIMEOUT):
        result = expand_via_ollama("shorthand", model="qwen2.5:7b-instruct")
    assert result is None


def test_expand_transcription_gemini_backend():
    with patch("notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="gemini")
    assert text == "Gemini prose"
    assert meta["expansion_backend"] == "gemini"
    assert meta["grounded"] is False


def test_expand_transcription_ollama_backend_success():
    with patch("notes.transcribe_excalidraw.expand_via_ollama", return_value="Ollama prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="ollama")
    assert text == "Ollama prose"
    assert meta["expansion_backend"] == "ollama"


def test_expand_transcription_ollama_falls_back_to_gemini_when_unreachable():
    with patch("notes.transcribe_excalidraw.expand_via_ollama", return_value=None), \
         patch("notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini fallback prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="ollama")
    assert text == "Gemini fallback prose"
    assert meta["expansion_backend"] == "gemini"


def test_expand_transcription_marks_grounded_when_passages_given():
    with patch("notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini prose"):
        _text, meta = expand_transcription(
            client=object(), raw_markdown="shorthand", backend="gemini",
            retrieved_passages=["some textbook passage"],
        )
    assert meta["grounded"] is True


from notes.transcribe_excalidraw import write_outputs


def test_write_outputs_creates_both_files_with_frontmatter(tmp_path):
    course_dir = tmp_path / "academic-hub" / "academic_notes" / "math_methods" / "lecture_notes"
    course_dir.mkdir(parents=True)
    md_path = course_dir / "Drawing 2026-09-08.excalidraw.md"
    png_path = course_dir / "Drawing 2026-09-08.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")

    with patch("notes.transcribe_excalidraw.reconcile_and_write") as mock_reconcile:
        raw_path, rag_path = write_outputs(
            excalidraw_md_path=str(md_path), png_path=str(png_path),
            raw_markdown="raw shorthand text", expanded_markdown="expanded prose text",
            transcription_model="gemini-3.6-flash",
            expansion_meta={"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False},
            num_chunks=3, academic_hub_root=str(tmp_path / "academic-hub"), client=object(),
        )

    assert os.path.basename(raw_path) == "Drawing 2026-09-08.excalidraw.md"
    assert os.path.basename(rag_path) == "Drawing 2026-09-08.excalidraw.rag.md"
    assert os.path.dirname(raw_path).endswith("processed_outputs")

    raw_content = open(raw_path, encoding="utf-8").read()
    assert "routing: excalidraw_chunked" in raw_content
    assert "raw shorthand text" in raw_content

    rag_content = open(rag_path, encoding="utf-8").read()
    assert "expansion_backend: gemini" in rag_content
    assert "expanded prose text" in rag_content

    mock_reconcile.assert_called_once()  # only the .rag.md gets indexed


from notes.transcribe_excalidraw import process_excalidraw_note


def test_process_excalidraw_note_dry_run_does_not_call_apis(tmp_path):
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")

    with patch("notes.transcribe_excalidraw.transcribe_chunks") as mock_transcribe, \
         patch("notes.transcribe_excalidraw.expand_transcription") as mock_expand:
        process_excalidraw_note(
            str(md_path), str(png_path), client=None, model="gemini-3.6-flash",
            expand_backend="gemini", academic_hub_root=str(tmp_path), dry_run=True,
        )

    mock_transcribe.assert_not_called()
    mock_expand.assert_not_called()


def test_process_excalidraw_note_runs_full_pipeline(tmp_path):
    from PIL import Image
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(png_path)

    with patch("notes.transcribe_excalidraw.chunk_image", return_value=["chunk_image_1", "chunk_image_2"]), \
         patch("notes.transcribe_excalidraw.resize_chunk_for_api", side_effect=[b"bytes1", b"bytes2"]), \
         patch("notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "raw text 0", "1": "raw text 1"}), \
         patch("notes.transcribe_excalidraw.expand_transcription", return_value=("expanded text", {"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False})), \
         patch("notes.transcribe_excalidraw.write_outputs", return_value=("raw.md", "raw.rag.md")) as mock_write:
        process_excalidraw_note(
            str(md_path), str(png_path), client=object(), model="gemini-3.6-flash",
            expand_backend="gemini", academic_hub_root=str(tmp_path), dry_run=False,
        )

    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args.kwargs
    assert call_kwargs["raw_markdown"] == "<!-- chunk 1 -->\n\nraw text 0\n\n<!-- chunk 2 -->\n\nraw text 1"
    assert call_kwargs["expanded_markdown"] == "expanded text"
    assert call_kwargs["num_chunks"] == 2
