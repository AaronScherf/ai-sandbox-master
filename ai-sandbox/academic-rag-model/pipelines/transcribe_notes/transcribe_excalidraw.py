"""
transcribe_excalidraw.py
Turns an Excalidraw handwritten-notes canvas (.excalidraw.md + its
plugin-auto-exported .png or .svg) into RAG-corpus markdown: chunk -> transcribe
-> assemble -> expand -> write. Replaces the OneNote capture workflow
(see docs/status/2026-08-24-notes-transcription-status.md's "2026-09-07"
section for why). Spec: docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from core.env.academic_hub_paths import resolve_output_dir, to_resources_root
from core.env.frontmatter import parse_frontmatter
from core.env.gemini_utils import call_with_retries
from core.env.ollama_utils import call_ollama
from core.indexer.index_card import (
    EXCALIDRAW_DOC_TYPES,
    compute_content_hash,
    compute_file_id,
    derive_course,
    reconcile_and_write,
)
from core.indexer.related import link_subsets
from pipelines.transcribe_notes.excalidraw_chunking import chunk_image, load_canvas_image, resize_chunk_for_api
from pipelines.transcribe_notes.transcribe_notes import build_frontmatter, transcribe_page_via_gemini

_EXPANSION_MODEL_GEMINI = "gemini-3.1-flash-lite"  # text-only reasoning task, matches
                                                     # problem_gen's/viz's own default tier
_EXPANSION_MODEL_OLLAMA = "qwen2.5:7b-instruct"     # general-purpose, not qwen2-math --
                                                     # expansion spans math AND econ notes,
                                                     # same reasoning video_notes used for
                                                     # its own synthesis model choice

_ACCUMULATION_WINDOW = 3  # same value as transcribe_notes.py's Tier 3 -- see that
                          # module's _ACCUMULATION_WINDOW docstring for why a
                          # trailing window (not full-document accumulation) is used


def _accumulated_chunk_context(cache: dict, chunk_index: int, window: int) -> str:
    """0-based equivalent of transcribe_notes.py's build_accumulated_context.
    Not reused directly: that function assumes 1-based page numbers (its
    start-page floor is hardcoded to 1), which silently drops chunk 0's
    context when called with 0-based chunk indices -- caught by a real
    failing test (test_transcribe_chunks_passes_accumulated_context_from_prior_chunks),
    not assumed in advance. Same trailing-window behavior, just 0-based."""
    start = max(0, chunk_index - window)
    parts = []
    for i in range(start, chunk_index):
        text = cache.get(str(i))
        if text:
            parts.append(f"--- Chunk {i + 1} ---\n{text}")
    return "\n\n".join(parts)


_EXPORT_EXTENSIONS = (".png", ".svg")  # the plugin's auto-export format is a
                                       # vault-wide setting that switched from
                                       # PNG to SVG partway through this corpus
                                       # (2026-09-09), so synced files span both


def discover_excalidraw_files(notes_dir: str, file_filter: str | None = None) -> list[tuple[str, str]]:
    """Finds every `.excalidraw.md` directly under notes_dir with a
    matching `.excalidraw.png` or `.excalidraw.svg` sibling (the plugin's
    auto-export) -- checked locally first, then in the mirrored
    academic_resources/ location (the post-migration case; see
    docs/superpowers/specs/2026-09-21-source-asset-relocation-design.md).
    Skips (with a warning, not an error) any .md with no image found in
    either location."""
    if not os.path.isdir(notes_dir):
        return []
    pairs = []
    for name in sorted(os.listdir(notes_dir)):
        if not name.lower().endswith(".excalidraw.md"):
            continue
        if file_filter is not None and name != file_filter:
            continue
        md_path = os.path.join(notes_dir, name)
        stem = md_path[: -len(".md")]
        image_path = next((stem + ext for ext in _EXPORT_EXTENSIONS if os.path.exists(stem + ext)), None)
        if image_path is None:
            try:
                mirrored_stem = to_resources_root(stem)
            except ValueError:
                mirrored_stem = None
            if mirrored_stem is not None:
                image_path = next(
                    (mirrored_stem + ext for ext in _EXPORT_EXTENSIONS if os.path.exists(mirrored_stem + ext)),
                    None,
                )
        if image_path is None:
            print(f"WARNING: {name} has no matching .png/.svg (auto-export may not have run yet) -- skipping.")
            continue
        pairs.append((md_path, image_path))
    return pairs


_EMBEDDED_IMAGE_RE = re.compile(r"\[\[[^\]]*\.(?:png|jpe?g|gif|webp|svg|pdf)[^\]]*\]\]", re.IGNORECASE)

_QUESTION_TAG = "[Question]"

_QUESTION_INSTRUCTION = (
    "Handwritten sidebar questions, margin notes, or any region marked with a question mark are "
    "OPEN QUESTIONS about their surrounding content. Transcribe each one in place, prefixed with "
    f"the literal tag {_QUESTION_TAG} (e.g. `{_QUESTION_TAG} why does this need completeness?`). "
    "Do NOT answer them -- a later step resolves them.\n\n"
)

_SLIDE_TRANSCRIPTION_INSTRUCTION = (
    "This canvas also contains typeset lecture slides (embedded images) placed side by side with "
    "the handwriting; the handwriting annotates and responds to the slides next to it. Transcribe "
    "slide text verbatim (keeping bullets, theorem/proof structure, and math as LaTeX) under a "
    "`**[Slide]**` label, and the handwriting under a `**[Handwritten]**` label, keeping each "
    "handwritten passage adjacent to the slide it sits beside. Read by column, then top to "
    "bottom, so slide and handwriting order stays coherent.\n\n"
)

_SLIDE_EXPANSION_INSTRUCTION = (
    "The transcription mixes typeset lecture slides (`**[Slide]**`) with the student's handwriting "
    "(`**[Handwritten]**`) written beside them. Treat slide content as the authoritative source "
    "and keep it as slide content (do not rephrase it as the student's own words); weave the "
    "handwritten annotations in as the student's commentary on the slide they sit beside.\n\n"
)

def _question_expansion_instruction(source_text: str) -> str:
    """Only mentioned when the input actually contains a tag: telling the
    model to "preserve every [Question] tag" when there are none made it
    invent them at sentence ends (observed on a real note: 0 tags in, 13 out),
    which would feed false positives to the question-resolving step."""
    if _QUESTION_TAG not in source_text:
        return ""
    return (
        f"Keep every existing `{_QUESTION_TAG}` tag exactly, attached to the content it concerns, and "
        "do not answer or remove it. Do not add any new tags.\n\n"
    )


def has_embedded_images(excalidraw_md_path: str, image_path: str) -> bool:
    """True when the canvas has embedded images (e.g. pasted lecture slides)
    alongside the handwriting. Primary signal: the scene file's plaintext
    `## Embedded Files` section lists an image (cheap, and present even
    though the drawing itself is compressed). Fallback for an SVG export:
    `<image` elements in the rendered file -- what the vision model will
    actually see, and robust to a scene file the plugin saved without
    that section. A PNG export is never scanned (binary)."""
    try:
        with open(excalidraw_md_path, encoding="utf-8") as f:
            scene = f.read()
    except OSError:
        scene = ""
    match = re.search(r"^## Embedded Files\s*$(.*?)(?=^%%|^## |\Z)", scene, re.MULTILINE | re.DOTALL)
    if match and _EMBEDDED_IMAGE_RE.search(match.group(1)):
        return True
    if image_path.lower().endswith(".svg"):
        try:
            with open(image_path, encoding="utf-8") as f:
                return "<image" in f.read()
        except OSError:
            return False
    return False


def build_chunk_transcription_prompt(
    accumulated_context: str, chunk_index: int, total_chunks: int, has_slides: bool = False,
) -> str:
    context_block = (
        f"Already-transcribed content from earlier chunks of this same canvas, for continuity "
        f"(a chunk boundary can split a derivation or sentence mid-thought):\n{accumulated_context}\n\n"
        if accumulated_context else ""
    )
    return (
        f"This is chunk {chunk_index + 1} of {total_chunks} from a single tall, continuous "
        "handwritten-notes canvas (an Excalidraw drawing, cropped at a whitespace gap -- not a "
        "page boundary). Transcribe everything on this chunk into clean markdown: preserve "
        "problem/part numbering, mathematical notation (LaTeX-style, e.g. $...$ or $$...$$), "
        "and reading order. Keep this transcription terse and faithful to the shorthand as "
        "written -- do not expand abbreviations or add explanation; that happens in a later "
        "pass.\n\n"
        f"{_SLIDE_TRANSCRIPTION_INSTRUCTION if has_slides else ''}"
        f"{_QUESTION_INSTRUCTION}"
        f"{context_block}"
        "Respond with ONLY the transcribed markdown for THIS chunk -- no commentary, no code "
        "fence, no repetition of earlier chunks' content.\n"
    )


def assemble_raw_markdown(cache: dict, total_chunks: int) -> str:
    parts = []
    for chunk_index in range(total_chunks):
        text = cache.get(str(chunk_index))
        if text is None:
            continue
        parts.append(f"<!-- chunk {chunk_index + 1} -->\n\n{text}")
    return "\n\n".join(parts)


def transcribe_chunks(client, model: str, chunk_bytes: list[bytes], has_slides: bool = False) -> dict[str, str]:
    cache: dict[str, str] = {}
    total_chunks = len(chunk_bytes)
    for chunk_index, image_bytes in enumerate(chunk_bytes):
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks, has_slides)
        try:
            text = call_with_retries(lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt))
            cache[str(chunk_index)] = text
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache


def build_expansion_prompt(
    raw_markdown: str, retrieved_passages: list[str] | None = None, has_slides: bool = False,
) -> str:
    grounding_block = ""
    if retrieved_passages:
        joined = "\n\n".join(retrieved_passages)
        grounding_block = (
            "Relevant passages from the course's own textbook material, for grounding and "
            f"terminology consistency (cite/connect to these where genuinely relevant, don't "
            f"force a connection that isn't there):\n{joined}\n\n"
        )
    return (
        "The following is a terse, shorthand transcription of a student's handwritten math/"
        "economics lecture notes -- LaTeX-heavy, abbreviated, written for the student's own "
        "quick reference, not for someone else to read. Rewrite it into a cohesive, "
        "self-contained prose explanation: expand abbreviations, spell out the reasoning "
        "between steps, and preserve every piece of mathematical content (do not drop or "
        "simplify any equation) while making it directly understandable to someone who "
        "wasn't in the room. Keep LaTeX notation ($...$, $$...$$) for all math.\n\n"
        f"{_SLIDE_EXPANSION_INSTRUCTION if has_slides else ''}"
        f"{_question_expansion_instruction(raw_markdown)}"
        f"{grounding_block}"
        f"Shorthand transcription:\n{raw_markdown}\n\n"
        "Respond with ONLY the expanded markdown -- no commentary, no code fence.\n"
    )


def expand_via_gemini(
    client, model: str, raw_markdown: str, retrieved_passages: list[str] | None = None, has_slides: bool = False,
) -> str:
    prompt = build_expansion_prompt(raw_markdown, retrieved_passages, has_slides)
    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
    )
    return (response.text or "").strip()


def expand_via_ollama(
    raw_markdown: str, model: str = _EXPANSION_MODEL_OLLAMA, request_timeout: int = 300,
    retrieved_passages: list[str] | None = None, has_slides: bool = False,
) -> str | None:
    prompt = build_expansion_prompt(raw_markdown, retrieved_passages, has_slides)
    result = call_ollama(prompt, model=model, request_timeout=request_timeout)
    if isinstance(result, str):
        return result.strip()
    return None  # unreachable server or timeout -- caller decides whether to fall back


_SEGMENT_LABEL_RE = re.compile(r"^\*\*\[(Slide|Handwritten)\]\*\*[ \t]*$", re.MULTILINE)
_CHUNK_MARKER_RE = re.compile(r"^<!-- chunk \d+ -->[ \t]*$", re.MULTILINE)
_SLIDE_CONTEXT_CHARS = 3000  # per neighboring slide, keeps each handwriting call small


def split_labeled_segments(raw_markdown: str) -> list[tuple[str, str]]:
    """Splits a slide-aware raw transcript into ordered (label, text) blocks,
    label being 'Slide' or 'Handwritten'. Chunk markers are dropped (a block
    can straddle a chunk boundary; they are transcription bookkeeping, not
    content). Text before the first label is treated as handwriting -- the
    safe default, since handwriting is the part that gets rewritten and the
    fallback on any failure is to keep it verbatim."""
    text = _CHUNK_MARKER_RE.sub("", raw_markdown)
    matches = list(_SEGMENT_LABEL_RE.finditer(text))
    pieces: list[tuple[str, str]] = []
    first_start = matches[0].start() if matches else len(text)
    if text[:first_start].strip():
        pieces.append(("Handwritten", text[:first_start].strip()))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            pieces.append((m.group(1), body))
    return pieces


def build_handwriting_expansion_prompt(
    handwriting: str, adjacent_slides: list[str], retrieved_passages: list[str] | None = None,
) -> str:
    slide_block = ""
    if adjacent_slides:
        joined = "\n\n---\n\n".join(slide[:_SLIDE_CONTEXT_CHARS] for slide in adjacent_slides)
        slide_block = (
            "The lecture slide content this handwriting sits beside (context only -- do NOT repeat or "
            f"rewrite it; it is reproduced separately, verbatim):\n{joined}\n\n"
        )
    grounding_block = ""
    if retrieved_passages:
        grounding_block = (
            "Relevant passages from the course's own textbook material, for terminology consistency "
            "(connect only where genuinely relevant):\n" + "\n\n".join(retrieved_passages) + "\n\n"
        )
    return (
        "The following is a terse, shorthand transcription of a student's handwritten annotations "
        "written beside lecture slides -- abbreviated, written for the student's own quick reference. "
        "Rewrite ONLY this handwriting into cohesive, self-contained prose: expand abbreviations, "
        "spell out the reasoning between steps, and preserve every piece of mathematical content (do "
        "not drop or simplify any equation). Keep LaTeX notation ($...$, $$...$$) for all math.\n\n"
        f"{_question_expansion_instruction(handwriting)}"
        f"{slide_block}{grounding_block}"
        f"Handwriting transcription:\n{handwriting}\n\n"
        "Respond with ONLY the expanded markdown for this handwriting -- no commentary, no code fence.\n"
    )


def expand_with_verbatim_slides(
    raw_markdown: str, generate, retrieved_passages: list[str] | None = None,
) -> str:
    """Rebuilds a slide-aware transcript for the RAG corpus with slide text
    kept byte-for-byte: only the handwriting blocks go through `generate`
    (a prompt -> text callable), each given its neighboring slide(s) as
    context. A whole-document rewrite was observed to silently summarize
    slides away (14 -> 1 display equations on a real note) despite being
    told to preserve every equation, so slides never pass through the
    model. A handwriting block whose generation fails or comes back empty
    is kept as its raw transcription -- terse but lossless."""
    segments = split_labeled_segments(raw_markdown)
    out: list[str] = []
    for i, (label, text) in enumerate(segments):
        if label == "Slide":
            out.append(f"**[Slide]**\n{text}")
            continue
        neighbors = [
            segments[j][1] for j in (i - 1, i + 1)
            if 0 <= j < len(segments) and segments[j][0] == "Slide"
        ]
        prompt = build_handwriting_expansion_prompt(text, neighbors, retrieved_passages)
        try:
            expanded = (generate(prompt) or "").strip()
        except Exception as err:
            print(f"WARNING: handwriting expansion failed ({err}); keeping the raw transcription for that block.")
            expanded = ""
        if not expanded:
            expanded = text
        out.append(f"**[Notes]**\n{expanded}")
    return "\n\n".join(out)


def _expand_slide_note(client, raw_markdown: str, backend: str, retrieved_passages) -> tuple[str, dict]:
    state = {"backend": backend}

    def generate(prompt: str) -> str:
        if state["backend"] == "ollama":
            result = call_ollama(prompt, model=_EXPANSION_MODEL_OLLAMA, request_timeout=300)
            if isinstance(result, str):
                return result
            print("WARNING: Ollama expansion backend unreachable; falling back to Gemini.")
            state["backend"] = "gemini"
        response = client.models.generate_content(
            model=_EXPANSION_MODEL_GEMINI, contents=[prompt],
            config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
        )
        return response.text or ""

    text = expand_with_verbatim_slides(raw_markdown, generate, retrieved_passages)
    model = _EXPANSION_MODEL_OLLAMA if state["backend"] == "ollama" else _EXPANSION_MODEL_GEMINI
    return text, {
        "expansion_backend": state["backend"], "expansion_model": model,
        "grounded": bool(retrieved_passages), "slides_verbatim": True,
    }


def expand_transcription(
    client, raw_markdown: str, backend: str = "gemini", retrieved_passages: list[str] | None = None,
    has_slides: bool = False,
) -> tuple[str | None, dict]:
    """backend='gemini' (default) or 'ollama' (opt-in, matches
    VIZ_BACKEND/PROBLEMGEN_BACKEND's existing env-var pattern at the CLI
    layer -- see main()). Falls back to Gemini if Ollama is requested but
    unreachable, printing a warning, rather than failing the whole
    document."""
    grounded = bool(retrieved_passages)
    if has_slides:
        return _expand_slide_note(client, raw_markdown, backend, retrieved_passages)
    if backend == "ollama":
        text = expand_via_ollama(raw_markdown, retrieved_passages=retrieved_passages, has_slides=has_slides)
        if text is not None:
            return text, {"expansion_backend": "ollama", "expansion_model": _EXPANSION_MODEL_OLLAMA, "grounded": grounded}
        print("WARNING: Ollama expansion backend unreachable; falling back to Gemini.")
    text = expand_via_gemini(client, _EXPANSION_MODEL_GEMINI, raw_markdown, retrieved_passages, has_slides)
    return text, {"expansion_backend": "gemini", "expansion_model": _EXPANSION_MODEL_GEMINI, "grounded": grounded}


def write_outputs(
    excalidraw_md_path: str, image_path: str, raw_markdown: str, expanded_markdown: str,
    transcription_model: str, expansion_meta: dict, num_chunks: int, academic_hub_root: str, client, has_slides: bool = False,
) -> tuple[str, str]:
    base_name = os.path.basename(excalidraw_md_path)[: -len(".excalidraw.md")]
    output_dir = resolve_output_dir(excalidraw_md_path)
    os.makedirs(output_dir, exist_ok=True)

    common_meta = {
        "source_excalidraw": os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/"),
        "source_image": os.path.relpath(image_path, academic_hub_root).replace(os.sep, "/"),
        "folder_category": "excalidraw_notes",
        "routing": "excalidraw_chunked",
        "chunks": num_chunks,
        "embedded_slides": has_slides,
        "model": transcription_model,
        "tags": [],
    }

    raw_path = os.path.join(output_dir, f"{base_name}.excalidraw.md")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(build_frontmatter(common_meta) + raw_markdown)

    rag_meta = dict(common_meta)
    rag_meta.update(expansion_meta)
    rag_path = os.path.join(output_dir, f"{base_name}.excalidraw.rag.md")
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(build_frontmatter(rag_meta) + expanded_markdown)

    try:
        file_id = compute_file_id(excalidraw_md_path)
        rel_rag_path = os.path.relpath(rag_path, academic_hub_root).replace(os.sep, "/")
        rel_source_path = os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/")
        rel_image_path = os.path.relpath(image_path, academic_hub_root).replace(os.sep, "/")
        course = derive_course(rel_source_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_rag_path, source_pdf_path=rel_source_path,
            course=course, folder_category="excalidraw_notes", content_sample=expanded_markdown,
            page_count=num_chunks, client=client, content_hash=compute_content_hash(rag_path),
            known_doc_types=EXCALIDRAW_DOC_TYPES, source_asset_path=rel_image_path,
        )
        link_subsets(academic_hub_root, course)
    except Exception as err:
        print(f"WARNING: source-indexer update failed for {rag_path} ({err}); "
              f"rerun `python -m core.indexer.index_search rebuild` later to catch it up.")

    return raw_path, rag_path


_TRANSCRIBE_MODEL = "gemini-3.6-flash"  # same tier as transcribe_notes.py's
                                         # _MODEL_HANDWRITING -- these are all
                                         # handwriting-heavy vision transcription


def _retrieve_grounding(
    excalidraw_md_path: str, raw_markdown: str, client, academic_hub_root: str, use_grounding: bool,
) -> list[str] | None:
    if not use_grounding:
        return None
    from core.indexer.index_search import search_passages
    course = derive_course(os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/"))
    results = search_passages([academic_hub_root], query=raw_markdown[:500], client=client, course=course, top_k=3)
    return [r.text for r in results] if results else None


def reexpand_excalidraw_note(
    excalidraw_md_path: str, image_path: str, client, expand_backend: str,
    academic_hub_root: str, use_grounding: bool = False,
) -> bool:
    """Regenerates only the expanded `.rag.md` (and its index card) from the
    already-saved raw transcript -- no vision calls, so it is cheap to rerun
    after an expansion-prompt change. The raw file's frontmatter supplies the
    original transcription model, chunk count, and slide flag. Returns False
    (writing nothing) if there is no raw transcript to expand."""
    base_name = os.path.basename(excalidraw_md_path)[: -len(".excalidraw.md")]
    raw_path = os.path.join(resolve_output_dir(excalidraw_md_path), f"{base_name}.excalidraw.md")
    print(f"Re-expanding {os.path.basename(excalidraw_md_path)}...")
    if not os.path.exists(raw_path):
        print(f"ERROR: no raw transcript at {raw_path}; run the full transcription first.")
        return False
    with open(raw_path, encoding="utf-8") as f:
        meta, raw_markdown = parse_frontmatter(f.read())
    has_slides = meta.get("embedded_slides", "false").strip().lower() == "true"
    retrieved_passages = _retrieve_grounding(
        excalidraw_md_path, raw_markdown, client, academic_hub_root, use_grounding,
    )
    expanded_markdown, expansion_meta = expand_transcription(
        client, raw_markdown, expand_backend, retrieved_passages, has_slides=has_slides,
    )
    write_outputs(
        excalidraw_md_path=excalidraw_md_path, image_path=image_path,
        raw_markdown=raw_markdown, expanded_markdown=expanded_markdown or "",
        transcription_model=meta.get("model", _TRANSCRIBE_MODEL), expansion_meta=expansion_meta,
        num_chunks=int(meta.get("chunks", "0") or 0), academic_hub_root=academic_hub_root,
        client=client, has_slides=has_slides,
    )
    print(f"  re-wrote {base_name}.excalidraw.rag.md")
    return True


def process_excalidraw_note(
    excalidraw_md_path: str, image_path: str, client, model: str,
    expand_backend: str, academic_hub_root: str, use_grounding: bool = False, dry_run: bool = False,
) -> bool:
    """Returns True when the note was written (or on a dry run), False when it was
    aborted because a chunk failed transcription -- a truncated transcript is
    never written or indexed, since it would look finished to search and to the
    router's output check."""
    print(f"Processing {os.path.basename(excalidraw_md_path)}...")
    if dry_run:
        print("  (dry run -- would chunk, transcribe, expand, and write outputs)")
        return True

    has_slides = has_embedded_images(excalidraw_md_path, image_path)
    if has_slides:
        print("  embedded slide images detected -- using slide-aware prompts")
    image = load_canvas_image(image_path)
    chunks = chunk_image(image)
    print(f"  {len(chunks)} chunks")
    chunk_bytes = [resize_chunk_for_api(c) for c in chunks]

    cache = transcribe_chunks(client, model, chunk_bytes, has_slides=has_slides)
    missing = [i + 1 for i in range(len(chunks)) if str(i) not in cache]
    if missing:
        print(f"ERROR: {os.path.basename(excalidraw_md_path)}: chunk {', '.join(map(str, missing))} of "
              f"{len(chunks)} failed transcription -- not writing or indexing a truncated transcript; rerun later.")
        return False
    raw_markdown = assemble_raw_markdown(cache, total_chunks=len(chunks))

    retrieved_passages = _retrieve_grounding(
        excalidraw_md_path, raw_markdown, client, academic_hub_root, use_grounding,
    )

    expanded_markdown, expansion_meta = expand_transcription(client, raw_markdown, expand_backend, retrieved_passages, has_slides=has_slides)

    write_outputs(
        excalidraw_md_path=excalidraw_md_path, image_path=image_path,
        raw_markdown=raw_markdown, expanded_markdown=expanded_markdown or "",
        transcription_model=model, expansion_meta=expansion_meta,
        num_chunks=len(chunks), academic_hub_root=academic_hub_root, client=client, has_slides=has_slides,
    )
    print(f"  wrote outputs to {resolve_output_dir(excalidraw_md_path)}/")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe and expand Excalidraw handwritten-notes canvases into markdown."
    )
    parser.add_argument(
        "--notes-subdir", required=True,
        help="Path, relative to the academic-hub/ folder next to this project, e.g. "
             "'academic_notes/math_methods/lecture_notes'.",
    )
    parser.add_argument("--file", default=None, help="Only process this one .excalidraw.md filename.")
    parser.add_argument("--model", default=_TRANSCRIBE_MODEL, help=f"Gemini vision model. Default: {_TRANSCRIBE_MODEL}.")
    parser.add_argument(
        "--expand-backend", default="gemini", choices=("gemini", "ollama"),
        help="Expansion backend (default: gemini). 'ollama' falls back to Gemini if unreachable.",
    )
    parser.add_argument("--grounding", action="store_true", help="Retrieve textbook passages to ground the expansion.")
    parser.add_argument(
        "--reexpand", action="store_true",
        help="Skip transcription: regenerate only the expanded .rag.md from each note's saved raw transcript.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List files that would be processed without calling any API.")
    args = parser.parse_args()

    from core.env.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent.parent / "academic-hub"
    notes_dir = academic_hub_dir / args.notes_subdir
    pairs = discover_excalidraw_files(str(notes_dir), args.file)
    if not pairs:
        print(f"No .excalidraw.md/.png or .excalidraw.md/.svg pairs found under {notes_dir}.")
        sys.exit(1)

    client = None
    if not args.dry_run:
        client = get_gemini_client()
        if client is None:
            sys.exit(1)

    for md_path, image_path in pairs:
        if args.reexpand:
            if not args.dry_run:
                reexpand_excalidraw_note(
                    md_path, image_path, client, args.expand_backend, str(academic_hub_dir), use_grounding=args.grounding,
                )
            else:
                print(f"Re-expanding {os.path.basename(md_path)}... (dry run)")
            continue
        process_excalidraw_note(
            md_path, image_path, client, args.model, args.expand_backend,
            str(academic_hub_dir), use_grounding=args.grounding, dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
