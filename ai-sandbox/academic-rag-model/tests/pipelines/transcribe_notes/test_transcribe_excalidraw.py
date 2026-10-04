import os

from pipelines.transcribe_notes.transcribe_excalidraw import discover_excalidraw_files


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


def test_discover_excalidraw_files_falls_back_to_the_mirrored_resources_directory(tmp_path):
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Drawing.excalidraw.md").write_text("---\n---\n")
    # no local image sibling -- it's already been migrated

    resources_dir = tmp_path / "academic_resources" / "econometrics" / "lecture_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "Drawing.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_excalidraw_files(str(notes_dir))

    assert len(pairs) == 1
    assert pairs[0][1] == str(resources_dir / "Drawing.excalidraw.svg")


def test_discover_excalidraw_files_prefers_local_image_over_mirrored_one(tmp_path):
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Drawing.excalidraw.md").write_text("---\n---\n")
    (notes_dir / "Drawing.excalidraw.svg").write_text("<svg>local</svg>")

    resources_dir = tmp_path / "academic_resources" / "econometrics" / "lecture_notes"
    resources_dir.mkdir(parents=True)
    (resources_dir / "Drawing.excalidraw.svg").write_text("<svg>mirrored</svg>")

    pairs = discover_excalidraw_files(str(notes_dir))

    assert pairs[0][1] == str(notes_dir / "Drawing.excalidraw.svg")


def test_discover_excalidraw_files_still_skips_when_no_image_anywhere(tmp_path, capsys):
    notes_dir = tmp_path / "academic_notes" / "econometrics" / "lecture_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "Drawing.excalidraw.md").write_text("---\n---\n")

    pairs = discover_excalidraw_files(str(notes_dir))

    assert pairs == []
    assert "no matching .png/.svg" in capsys.readouterr().out.lower()


def test_discover_excalidraw_files_pairs_md_and_svg(tmp_path):
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing A.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_excalidraw_files(str(tmp_path))

    assert pairs == [
        (str(tmp_path / "Drawing A.excalidraw.md"), str(tmp_path / "Drawing A.excalidraw.svg")),
    ]


def test_discover_excalidraw_files_prefers_png_when_both_exist(tmp_path):
    # The plugin writes one auto-export per file, so this shouldn't happen
    # in practice, but a deterministic preference is safer than relying on
    # directory listing order.
    (tmp_path / "Drawing A.excalidraw.md").write_text("---\n---\n")
    (tmp_path / "Drawing A.excalidraw.png").write_bytes(b"fake-png")
    (tmp_path / "Drawing A.excalidraw.svg").write_text("<svg></svg>")

    pairs = discover_excalidraw_files(str(tmp_path))

    assert pairs[0][1].endswith(".png")


from pipelines.transcribe_notes.transcribe_excalidraw import assemble_raw_markdown, build_chunk_transcription_prompt


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

from pipelines.transcribe_notes.transcribe_excalidraw import transcribe_chunks


def test_transcribe_chunks_builds_cache_keyed_by_index():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini") as mock_transcribe:
        mock_transcribe.side_effect = ["first chunk text", "second chunk text"]
        cache = transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"])
    assert cache == {"0": "first chunk text", "1": "second chunk text"}


def test_transcribe_chunks_passes_accumulated_context_from_prior_chunks():
    captured_prompts = []

    def fake_transcribe(client, model, image_bytes, prompt):
        captured_prompts.append(prompt)
        return f"text for chunk with prompt len {len(prompt)}"

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake_transcribe):
        transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1"])

    # second call's prompt must include the first chunk's already-transcribed text
    assert "text for chunk with prompt len" in captured_prompts[1]


def test_transcribe_chunks_skips_a_chunk_that_fails_after_retries():
    def fake_transcribe(client, model, image_bytes, prompt):
        if image_bytes == b"img1":
            raise ValueError("simulated repetition-loop failure")
        return "ok text"

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake_transcribe):
        with patch("pipelines.transcribe_notes.transcribe_excalidraw.call_with_retries", side_effect=lambda fn: fn()):
            cache = transcribe_chunks(client=object(), model="gemini-3.6-flash", chunk_bytes=[b"img0", b"img1", b"img2"])

    assert cache == {"0": "ok text", "2": "ok text"}


from pipelines.transcribe_notes.transcribe_excalidraw import build_expansion_prompt, expand_via_gemini


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


from core.env.ollama_utils import OLLAMA_TIMEOUT
from pipelines.transcribe_notes.transcribe_excalidraw import expand_transcription, expand_via_ollama


def test_expand_via_ollama_returns_response_text():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.call_ollama", return_value="Expanded via Ollama."):
        result = expand_via_ollama("shorthand", model="qwen2.5:7b-instruct")
    assert result == "Expanded via Ollama."


def test_expand_via_ollama_returns_none_on_timeout():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.call_ollama", return_value=OLLAMA_TIMEOUT):
        result = expand_via_ollama("shorthand", model="qwen2.5:7b-instruct")
    assert result is None


def test_expand_transcription_gemini_backend():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="gemini")
    assert text == "Gemini prose"
    assert meta["expansion_backend"] == "gemini"
    assert meta["grounded"] is False


def test_expand_transcription_ollama_backend_success():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_via_ollama", return_value="Ollama prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="ollama")
    assert text == "Ollama prose"
    assert meta["expansion_backend"] == "ollama"


def test_expand_transcription_ollama_falls_back_to_gemini_when_unreachable():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_via_ollama", return_value=None), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini fallback prose"):
        text, meta = expand_transcription(client=object(), raw_markdown="shorthand", backend="ollama")
    assert text == "Gemini fallback prose"
    assert meta["expansion_backend"] == "gemini"


def test_expand_transcription_marks_grounded_when_passages_given():
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_via_gemini", return_value="Gemini prose"):
        _text, meta = expand_transcription(
            client=object(), raw_markdown="shorthand", backend="gemini",
            retrieved_passages=["some textbook passage"],
        )
    assert meta["grounded"] is True


from pipelines.transcribe_notes.transcribe_excalidraw import write_outputs


def test_write_outputs_creates_both_files_with_frontmatter(tmp_path):
    course_dir = tmp_path / "academic-hub" / "academic_notes" / "math_methods" / "lecture_notes"
    course_dir.mkdir(parents=True)
    md_path = course_dir / "Drawing 2026-09-08.excalidraw.md"
    png_path = course_dir / "Drawing 2026-09-08.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write") as mock_reconcile:
        raw_path, rag_path = write_outputs(
            excalidraw_md_path=str(md_path), image_path=str(png_path),
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
    assert "source_image: academic_notes/math_methods/lecture_notes/Drawing 2026-09-08.excalidraw.png" in raw_content

    rag_content = open(rag_path, encoding="utf-8").read()
    assert "expansion_backend: gemini" in rag_content
    assert "expanded prose text" in rag_content

    mock_reconcile.assert_called_once()  # only the .rag.md gets indexed


def test_write_outputs_records_svg_source_filename(tmp_path):
    # source_image must reflect whichever export format was actually used --
    # mislabeling an SVG source as a PNG would be misleading metadata, not
    # just a cosmetic gap.
    course_dir = tmp_path / "academic-hub" / "academic_notes" / "econometrics" / "lecture_notes"
    course_dir.mkdir(parents=True)
    md_path = course_dir / "Econometrics 2026-09-09.excalidraw.md"
    svg_path = course_dir / "Econometrics 2026-09-09.excalidraw.svg"
    md_path.write_text("---\n---\n")
    svg_path.write_text("<svg></svg>")

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"):
        raw_path, _rag_path = write_outputs(
            excalidraw_md_path=str(md_path), image_path=str(svg_path),
            raw_markdown="raw text", expanded_markdown="expanded text",
            transcription_model="gemini-3.6-flash",
            expansion_meta={"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False},
            num_chunks=1, academic_hub_root=str(tmp_path / "academic-hub"), client=object(),
        )

    raw_content = open(raw_path, encoding="utf-8").read()
    assert "source_image: academic_notes/econometrics/lecture_notes/Econometrics 2026-09-09.excalidraw.svg" in raw_content


from pipelines.transcribe_notes.transcribe_excalidraw import process_excalidraw_note


def test_process_excalidraw_note_dry_run_does_not_call_apis(tmp_path):
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks") as mock_transcribe, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription") as mock_expand:
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

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", return_value=["chunk_image_1", "chunk_image_2"]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", side_effect=[b"bytes1", b"bytes2"]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "raw text 0", "1": "raw text 1"}), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("expanded text", {"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False})), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs", return_value=("raw.md", "raw.rag.md")) as mock_write:
        process_excalidraw_note(
            str(md_path), str(png_path), client=object(), model="gemini-3.6-flash",
            expand_backend="gemini", academic_hub_root=str(tmp_path), dry_run=False,
        )

    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args.kwargs
    assert call_kwargs["raw_markdown"] == "<!-- chunk 1 -->\n\nraw text 0\n\n<!-- chunk 2 -->\n\nraw text 1"
    assert call_kwargs["expanded_markdown"] == "expanded text"
    assert call_kwargs["num_chunks"] == 2


def test_process_excalidraw_note_runs_full_pipeline_from_an_svg_source(tmp_path):
    # Real SVG rasterization runs unmocked here -- the point of the test is
    # that an .svg source reaches chunking at all, which it couldn't when
    # the canvas was opened straight through PIL (no native SVG decoder).
    md_path = tmp_path / "Econometrics.excalidraw.md"
    svg_path = tmp_path / "Econometrics.excalidraw.svg"
    md_path.write_text("---\n---\n")
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<rect width="100" height="100" fill="#ffffff"/>'
        '<rect x="10" y="10" width="20" height="20" fill="#1e1e1e"/>'
        "</svg>"
    )

    captured_images = []

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", side_effect=lambda im, *a, **k: captured_images.append(im) or ["chunk_1"]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", return_value=b"bytes1"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "raw text 0"}), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("expanded text", {"expansion_backend": "gemini", "expansion_model": "gemini-3.1-flash-lite", "grounded": False})), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs", return_value=("raw.md", "raw.rag.md")) as mock_write:
        process_excalidraw_note(
            str(md_path), str(svg_path), client=object(), model="gemini-3.6-flash",
            expand_backend="gemini", academic_hub_root=str(tmp_path), dry_run=False,
        )

    assert captured_images[0].size == (100, 100)  # rasterized, not passed through as a path
    assert mock_write.call_args.kwargs["image_path"] == str(svg_path)


from pipelines.transcribe_notes.transcribe_excalidraw import has_embedded_images


def test_has_embedded_images_true_when_scene_lists_embedded_png(tmp_path):
    md = tmp_path / "A.excalidraw.md"
    md.write_text("# Excalidraw Data\n\n## Text Elements\n## Embedded Files\nabc123: [[Pasted Image 1.png]]\n\n%%\n## Drawing\n")
    svg = tmp_path / "A.excalidraw.svg"
    svg.write_text("<svg></svg>")
    assert has_embedded_images(str(md), str(svg)) is True


def test_has_embedded_images_false_for_handwriting_only_scene(tmp_path):
    md = tmp_path / "A.excalidraw.md"
    md.write_text("# Excalidraw Data\n\n## Text Elements\n%%\n## Drawing\n```compressed-json\nN4Kg\n```\n%%\n")
    svg = tmp_path / "A.excalidraw.svg"
    svg.write_text('<svg><path d="M0 0"/></svg>')
    assert has_embedded_images(str(md), str(svg)) is False


def test_has_embedded_images_ignores_non_image_embedded_files(tmp_path):
    md = tmp_path / "A.excalidraw.md"
    md.write_text("## Embedded Files\nabc: [[Some Note.md]]\n\n%%\n")
    svg = tmp_path / "A.excalidraw.svg"
    svg.write_text("<svg></svg>")
    assert has_embedded_images(str(md), str(svg)) is False


def test_has_embedded_images_falls_back_to_svg_image_elements(tmp_path):
    md = tmp_path / "A.excalidraw.md"
    md.write_text("---\n---\n")  # scene gives no signal
    svg = tmp_path / "A.excalidraw.svg"
    svg.write_text('<svg><defs><symbol id="i"><image href="data:image/png;base64,AAAA"/></symbol></defs></svg>')
    assert has_embedded_images(str(md), str(svg)) is True


def test_has_embedded_images_png_export_relies_on_scene_only(tmp_path):
    md = tmp_path / "A.excalidraw.md"
    md.write_text("---\n---\n")
    png = tmp_path / "A.excalidraw.png"
    png.write_bytes(b"\x89PNG<image")  # must not be scanned as text
    assert has_embedded_images(str(md), str(png)) is False


def test_transcription_prompt_flags_open_questions_always():
    for has_slides in (False, True):
        prompt = build_chunk_transcription_prompt("", 0, 1, has_slides=has_slides)
        assert "[Question]" in prompt


def test_transcription_prompt_slide_block_only_when_has_slides():
    plain = build_chunk_transcription_prompt("", 0, 1)
    slides = build_chunk_transcription_prompt("", 0, 1, has_slides=True)
    assert "slide" not in plain.lower()
    assert "slide" in slides.lower()
    assert "side by side" in slides.lower()


def test_expansion_prompt_preserves_question_tags_only_when_input_has_them():
    for has_slides in (False, True):
        with_tag = build_expansion_prompt("notes [Question] why?", has_slides=has_slides)
        assert "[Question]" in with_tag and "Do not add" in with_tag
        # no tag in -> no mention of the tag at all (it primed the model to invent them)
        assert "[Question]" not in build_expansion_prompt("notes", has_slides=has_slides)


def test_handwriting_prompt_mentions_question_tag_only_when_present():
    assert "Do not add" in build_handwriting_expansion_prompt("a [Question] b", [], None)
    assert "[Question]" not in build_handwriting_expansion_prompt("a b", [], None)


def test_expansion_prompt_slide_block_only_when_has_slides():
    assert "slide" not in build_expansion_prompt("notes").lower()
    assert "slide" in build_expansion_prompt("notes", has_slides=True).lower()


def test_transcribe_chunks_forwards_has_slides_to_prompt():
    captured = []

    def fake(client, model, image_bytes, prompt):
        captured.append(prompt)
        return "t"

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_page_via_gemini", side_effect=fake):
        transcribe_chunks(client=object(), model="m", chunk_bytes=[b"a"], has_slides=True)
    assert "slide" in captured[0].lower()


def test_process_excalidraw_note_detects_slides_and_threads_flag(tmp_path):
    md_path = tmp_path / "S.excalidraw.md"
    svg_path = tmp_path / "S.excalidraw.svg"
    md_path.write_text("## Embedded Files\nabc: [[x.png]]\n\n%%\n")
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="#fff"/></svg>'
    )
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", return_value=["c"]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", return_value=b"b"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "raw"}) as mock_t, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("exp", {})) as mock_e, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs", return_value=("r", "r2")) as mock_w:
        process_excalidraw_note(
            str(md_path), str(svg_path), client=object(), model="m",
            expand_backend="gemini", academic_hub_root=str(tmp_path),
        )
    assert mock_t.call_args.kwargs["has_slides"] is True
    assert mock_e.call_args.kwargs["has_slides"] is True
    assert mock_w.call_args.kwargs["has_slides"] is True


def test_process_excalidraw_note_aborts_without_writing_when_a_chunk_failed(tmp_path, capsys):
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"x")

    with patch("pipelines.transcribe_notes.transcribe_excalidraw.load_canvas_image", return_value=object()), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", return_value=["c1", "c2", "c3"]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", return_value=b"b"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "a", "2": "c"}), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription") as mock_expand, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs") as mock_write:
        result = process_excalidraw_note(
            str(md_path), str(png_path), client=object(), model="m",
            expand_backend="gemini", academic_hub_root=str(tmp_path),
        )

    assert result is False
    mock_expand.assert_not_called()
    mock_write.assert_not_called()
    assert "chunk 2" in capsys.readouterr().out


def test_process_excalidraw_note_returns_true_on_success(tmp_path):
    md_path = tmp_path / "Drawing.excalidraw.md"
    png_path = tmp_path / "Drawing.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"x")
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.load_canvas_image", return_value=object()), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.chunk_image", return_value=["c1"]), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.resize_chunk_for_api", return_value=b"b"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks", return_value={"0": "a"}), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("e", {})), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs", return_value=("r", "r2")):
        assert process_excalidraw_note(
            str(md_path), str(png_path), client=object(), model="m",
            expand_backend="gemini", academic_hub_root=str(tmp_path),
        ) is True


from pipelines.transcribe_notes.transcribe_excalidraw import (
    build_handwriting_expansion_prompt,
    expand_with_verbatim_slides,
    split_labeled_segments,
)

_RAW = (
    "<!-- chunk 1 -->\n\n**[Handwritten]**\nnote a $x$\n\n**[Slide]**\n* Slide one\n$$u(x) \\geq u(y)$$\n\n"
    "<!-- chunk 2 -->\n\n**[Handwritten]**\nnote b\n[Question] why?\n\n**[Slide]**\n* Slide two\n"
)


def test_split_labeled_segments_orders_labels_and_strips_chunk_markers():
    segments = split_labeled_segments(_RAW)
    assert [label for label, _ in segments] == ["Handwritten", "Slide", "Handwritten", "Slide"]
    assert all("<!-- chunk" not in text for _, text in segments)
    assert segments[1][1] == "* Slide one\n$$u(x) \\geq u(y)$$"


def test_split_labeled_segments_treats_leading_unlabeled_text_as_handwritten():
    segments = split_labeled_segments("stray words\n\n**[Slide]**\n* s\n")
    assert segments[0] == ("Handwritten", "stray words")


def test_handwriting_prompt_includes_adjacent_slides():
    prompt = build_handwriting_expansion_prompt("note a", ["* Slide one"], None)
    assert "note a" in prompt and "* Slide one" in prompt


def test_expand_with_verbatim_slides_keeps_slide_text_exactly_and_expands_handwriting():
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return "EXPANDED"

    out = expand_with_verbatim_slides(_RAW, generate)
    assert "* Slide one\n$$u(x) \\geq u(y)$$" in out
    assert "* Slide two" in out
    assert out.count("EXPANDED") == 2
    assert "note a" not in out  # replaced by the expansion
    assert len(calls) == 2  # slides are never sent to the model for rewriting
    assert out.index("EXPANDED") < out.index("* Slide one") < out.rindex("EXPANDED") < out.index("* Slide two")


def test_expand_with_verbatim_slides_falls_back_to_raw_handwriting_when_generation_fails(capsys):
    def generate(prompt):
        raise RuntimeError("boom")

    out = expand_with_verbatim_slides(_RAW, generate)
    assert "note a $x$" in out and "[Question] why?" in out
    assert "* Slide one" in out
    assert "WARNING" in capsys.readouterr().out


def test_expand_with_verbatim_slides_falls_back_when_generation_returns_empty():
    out = expand_with_verbatim_slides(_RAW, lambda p: "  ")
    assert "note b" in out


def test_expand_transcription_uses_verbatim_slide_path_when_has_slides():
    class FakeResponse:
        text = "PROSE"

    class FakeModels:
        def generate_content(self, model, contents, config):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    text, meta = expand_transcription(FakeClient(), _RAW, "gemini", has_slides=True)
    assert "* Slide one" in text and "PROSE" in text
    assert meta["slides_verbatim"] is True


def test_expand_transcription_without_slides_is_unchanged():
    class FakeResponse:
        text = "WHOLE DOC PROSE"

    class FakeModels:
        def generate_content(self, model, contents, config):
            return FakeResponse()

    class FakeClient:
        models = FakeModels()

    text, meta = expand_transcription(FakeClient(), "terse notes", "gemini")
    assert text == "WHOLE DOC PROSE"
    assert "slides_verbatim" not in meta


from core.env.academic_hub_paths import resolve_output_dir
from pipelines.transcribe_notes.transcribe_excalidraw import reexpand_excalidraw_note


def _seed_raw(tmp_path, frontmatter, body):
    md_path = tmp_path / "Lecture.excalidraw.md"
    svg_path = tmp_path / "Lecture.excalidraw.svg"
    md_path.write_text("---\n---\n")
    svg_path.write_text("<svg/>")
    out_dir = resolve_output_dir(str(md_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "Lecture.excalidraw.md"), "w", encoding="utf-8") as f:
        f.write(frontmatter + body)
    return str(md_path), str(svg_path)


def test_reexpand_rebuilds_rag_from_saved_raw_without_transcribing(tmp_path):
    md, svg = _seed_raw(
        tmp_path, "---\nchunks: 3\nembedded_slides: true\nmodel: gemini-3.6-flash\n---\n\n", "RAW BODY",
    )
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.transcribe_chunks") as mock_t, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("new rag", {"expansion_backend": "gemini"})) as mock_e, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs", return_value=("r", "r2")) as mock_w:
        ok = reexpand_excalidraw_note(md, svg, client=object(), expand_backend="gemini", academic_hub_root=str(tmp_path))
    assert ok is True
    mock_t.assert_not_called()
    assert mock_e.call_args.args[1] == "RAW BODY"
    assert mock_e.call_args.kwargs["has_slides"] is True
    kw = mock_w.call_args.kwargs
    assert kw["raw_markdown"] == "RAW BODY" and kw["expanded_markdown"] == "new rag"
    assert kw["num_chunks"] == 3 and kw["transcription_model"] == "gemini-3.6-flash" and kw["has_slides"] is True


def test_reexpand_handwriting_only_note_uses_whole_document_path(tmp_path):
    md, svg = _seed_raw(tmp_path, "---\nchunks: 1\nmodel: m\n---\n\n", "terse")
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.expand_transcription", return_value=("x", {})) as mock_e, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs", return_value=("r", "r2")):
        reexpand_excalidraw_note(md, svg, client=object(), expand_backend="gemini", academic_hub_root=str(tmp_path))
    assert mock_e.call_args.kwargs["has_slides"] is False


def test_reexpand_returns_false_when_no_raw_transcript_exists(tmp_path, capsys):
    md_path = tmp_path / "Missing.excalidraw.md"
    md_path.write_text("---\n---\n")
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.write_outputs") as mock_w:
        ok = reexpand_excalidraw_note(str(md_path), str(tmp_path / "x.svg"), client=object(), expand_backend="gemini", academic_hub_root=str(tmp_path))
    assert ok is False
    mock_w.assert_not_called()
    assert "ERROR" in capsys.readouterr().out


def _write_outputs_kwargs(tmp_path):
    course_dir = tmp_path / "academic-hub" / "academic_notes" / "math_methods" / "lecture_notes"
    course_dir.mkdir(parents=True)
    md_path = course_dir / "Drawing 2026-09-08.excalidraw.md"
    png_path = course_dir / "Drawing 2026-09-08.excalidraw.png"
    md_path.write_text("---\n---\n")
    png_path.write_bytes(b"fake-png")
    return dict(
        excalidraw_md_path=str(md_path), image_path=str(png_path),
        raw_markdown="raw", expanded_markdown="expanded", transcription_model="m",
        expansion_meta={}, num_chunks=1, academic_hub_root=str(tmp_path / "academic-hub"), client=object(),
    )


def test_write_outputs_links_subsets_for_the_notes_course(tmp_path):
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets") as mock_link:
        write_outputs(**kwargs)
    mock_link.assert_called_once_with(kwargs["academic_hub_root"], "math_methods")


def test_write_outputs_survives_a_linking_failure(tmp_path, capsys):
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets", side_effect=RuntimeError("boom")):
        raw_path, rag_path = write_outputs(**kwargs)
    assert os.path.exists(rag_path)
    assert "WARNING" in capsys.readouterr().out


def test_write_outputs_reapplies_markers_from_an_existing_sidecar(tmp_path):
    from core.env.academic_hub_paths import resolve_output_dir
    from core.indexer.questions import Entry, find_tags, sidecar_path_for, write_sidecar

    kwargs = _write_outputs_kwargs(tmp_path)
    kwargs["raw_markdown"] = "**[Handwritten]**\n[Question] why not reflexivity?\n"
    kwargs["expanded_markdown"] = "Prose. [Question] why not reflexivity?\n"
    out_dir = resolve_output_dir(kwargs["excalidraw_md_path"])
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "Drawing 2026-09-08.excalidraw.md")
    tag = find_tags(kwargs["raw_markdown"])[0]
    write_sidecar(sidecar_path_for(raw_path), {"questions": "1"}, [Entry(
        qid=tag.qid, question=tag.text, grounded=True, model="m", resolved_at="t", answer="A", sources=["s"],
    )])
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write"), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets"):
        _raw, rag_path = write_outputs(**kwargs)
    text = open(rag_path, encoding="utf-8").read()
    assert f"[Question: answered -> Drawing 2026-09-08.excalidraw.questions.md#{tag.qid}] why not reflexivity?" in text


def test_write_outputs_applies_markers_before_indexing(tmp_path):
    order = []
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.apply_markers", side_effect=lambda *a: order.append("markers")), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write", side_effect=lambda *a, **k: order.append("index")), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets"):
        write_outputs(**kwargs)
    assert order == ["markers", "index"]


def test_write_outputs_survives_a_marker_failure_and_still_indexes(tmp_path, capsys):
    kwargs = _write_outputs_kwargs(tmp_path)
    with patch("pipelines.transcribe_notes.transcribe_excalidraw.apply_markers", side_effect=RuntimeError("boom")), \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.reconcile_and_write") as mock_index, \
         patch("pipelines.transcribe_notes.transcribe_excalidraw.link_subsets"):
        _raw, rag_path = write_outputs(**kwargs)
    assert os.path.exists(rag_path)
    mock_index.assert_called_once()
    assert "WARNING" in capsys.readouterr().out
