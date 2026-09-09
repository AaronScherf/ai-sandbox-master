"""
transcribe_excalidraw.py
Turns an Excalidraw handwritten-notes canvas (.excalidraw.md + its
plugin-auto-exported .png) into RAG-corpus markdown: chunk -> transcribe
-> assemble -> expand -> write. Replaces the OneNote capture workflow
(see docs/status/2026-08-24-notes-transcription-status.md's "2026-09-07"
section for why). Spec: docs/superpowers/specs/2026-09-09-excalidraw-notes-transcription-design.md.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image

from common.gemini_utils import call_with_retries
from common.ollama_utils import call_ollama
from indexer.index_card import (
    EXCALIDRAW_DOC_TYPES,
    compute_content_hash,
    compute_file_id,
    derive_course,
    reconcile_and_write,
)
from notes.excalidraw_chunking import chunk_image, resize_chunk_for_api
from notes.transcribe_notes import build_frontmatter, transcribe_page_via_gemini

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


def discover_excalidraw_files(notes_dir: str, file_filter: str | None = None) -> list[tuple[str, str]]:
    """Finds every `.excalidraw.md` directly under notes_dir with a
    matching `.excalidraw.png` sibling (the plugin's auto-export) --
    skips (with a warning, not an error) any .md whose PNG hasn't been
    written yet."""
    if not os.path.isdir(notes_dir):
        return []
    pairs = []
    for name in sorted(os.listdir(notes_dir)):
        if not name.lower().endswith(".excalidraw.md"):
            continue
        if file_filter is not None and name != file_filter:
            continue
        md_path = os.path.join(notes_dir, name)
        png_path = md_path[: -len(".md")] + ".png"
        if not os.path.exists(png_path):
            print(f"WARNING: {name} has no matching .png (auto-export may not have run yet) -- skipping.")
            continue
        pairs.append((md_path, png_path))
    return pairs


def build_chunk_transcription_prompt(accumulated_context: str, chunk_index: int, total_chunks: int) -> str:
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


def transcribe_chunks(client, model: str, chunk_bytes: list[bytes]) -> dict[str, str]:
    cache: dict[str, str] = {}
    total_chunks = len(chunk_bytes)
    for chunk_index, image_bytes in enumerate(chunk_bytes):
        accumulated_context = _accumulated_chunk_context(cache, chunk_index, window=_ACCUMULATION_WINDOW)
        prompt = build_chunk_transcription_prompt(accumulated_context, chunk_index, total_chunks)
        try:
            text = call_with_retries(lambda: transcribe_page_via_gemini(client, model, image_bytes, prompt))
            cache[str(chunk_index)] = text
        except Exception as err:
            print(f"WARNING: chunk {chunk_index + 1}/{total_chunks} failed after retries ({err}); skipping.")
    return cache


def build_expansion_prompt(raw_markdown: str, retrieved_passages: list[str] | None = None) -> str:
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
        f"{grounding_block}"
        f"Shorthand transcription:\n{raw_markdown}\n\n"
        "Respond with ONLY the expanded markdown -- no commentary, no code fence.\n"
    )


def expand_via_gemini(client, model: str, raw_markdown: str, retrieved_passages: list[str] | None = None) -> str:
    prompt = build_expansion_prompt(raw_markdown, retrieved_passages)
    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config={"temperature": 0, "thinking_config": {"thinking_level": "minimal"}},
    )
    return (response.text or "").strip()


def expand_via_ollama(
    raw_markdown: str, model: str = _EXPANSION_MODEL_OLLAMA, request_timeout: int = 300,
    retrieved_passages: list[str] | None = None,
) -> str | None:
    prompt = build_expansion_prompt(raw_markdown, retrieved_passages)
    result = call_ollama(prompt, model=model, request_timeout=request_timeout)
    if isinstance(result, str):
        return result.strip()
    return None  # unreachable server or timeout -- caller decides whether to fall back


def expand_transcription(
    client, raw_markdown: str, backend: str = "gemini", retrieved_passages: list[str] | None = None,
) -> tuple[str | None, dict]:
    """backend='gemini' (default) or 'ollama' (opt-in, matches
    VIZ_BACKEND/PROBLEMGEN_BACKEND's existing env-var pattern at the CLI
    layer -- see main()). Falls back to Gemini if Ollama is requested but
    unreachable, printing a warning, rather than failing the whole
    document."""
    grounded = bool(retrieved_passages)
    if backend == "ollama":
        text = expand_via_ollama(raw_markdown, retrieved_passages=retrieved_passages)
        if text is not None:
            return text, {"expansion_backend": "ollama", "expansion_model": _EXPANSION_MODEL_OLLAMA, "grounded": grounded}
        print("WARNING: Ollama expansion backend unreachable; falling back to Gemini.")
    text = expand_via_gemini(client, _EXPANSION_MODEL_GEMINI, raw_markdown, retrieved_passages)
    return text, {"expansion_backend": "gemini", "expansion_model": _EXPANSION_MODEL_GEMINI, "grounded": grounded}


def write_outputs(
    excalidraw_md_path: str, png_path: str, raw_markdown: str, expanded_markdown: str,
    transcription_model: str, expansion_meta: dict, num_chunks: int, academic_hub_root: str, client,
) -> tuple[str, str]:
    base_name = os.path.basename(excalidraw_md_path)[: -len(".excalidraw.md")]
    output_dir = os.path.join(os.path.dirname(excalidraw_md_path), "processed_outputs")
    os.makedirs(output_dir, exist_ok=True)

    common_meta = {
        "source_excalidraw": os.path.basename(excalidraw_md_path),
        "source_png": os.path.basename(png_path),
        "folder_category": "excalidraw_notes",
        "routing": "excalidraw_chunked",
        "chunks": num_chunks,
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
        course = derive_course(rel_source_path)
        reconcile_and_write(
            academic_hub_root, file_id=file_id, path=rel_rag_path, source_pdf_path=rel_source_path,
            course=course, folder_category="excalidraw_notes", content_sample=expanded_markdown,
            page_count=num_chunks, client=client, content_hash=compute_content_hash(rag_path),
            known_doc_types=EXCALIDRAW_DOC_TYPES,
        )
    except Exception as err:
        print(f"WARNING: source-indexer update failed for {rag_path} ({err}); "
              f"rerun `python -m indexer.index_search rebuild` later to catch it up.")

    return raw_path, rag_path


_TRANSCRIBE_MODEL = "gemini-3.6-flash"  # same tier as transcribe_notes.py's
                                         # _MODEL_HANDWRITING -- these are all
                                         # handwriting-heavy vision transcription


def process_excalidraw_note(
    excalidraw_md_path: str, png_path: str, client, model: str,
    expand_backend: str, academic_hub_root: str, use_grounding: bool = False, dry_run: bool = False,
) -> None:
    print(f"Processing {os.path.basename(excalidraw_md_path)}...")
    if dry_run:
        print("  (dry run -- would chunk, transcribe, expand, and write outputs)")
        return

    image = Image.open(png_path)
    chunks = chunk_image(image)
    print(f"  {len(chunks)} chunks")
    chunk_bytes = [resize_chunk_for_api(c) for c in chunks]

    cache = transcribe_chunks(client, model, chunk_bytes)
    raw_markdown = assemble_raw_markdown(cache, total_chunks=len(chunks))

    retrieved_passages = None
    if use_grounding:
        from indexer.index_search import search_passages
        course = derive_course(os.path.relpath(excalidraw_md_path, academic_hub_root).replace(os.sep, "/"))
        results = search_passages([academic_hub_root], query=raw_markdown[:500], client=client, course=course, top_k=3)
        retrieved_passages = [r.text for r in results] if results else None

    expanded_markdown, expansion_meta = expand_transcription(client, raw_markdown, expand_backend, retrieved_passages)

    write_outputs(
        excalidraw_md_path=excalidraw_md_path, png_path=png_path,
        raw_markdown=raw_markdown, expanded_markdown=expanded_markdown or "",
        transcription_model=model, expansion_meta=expansion_meta,
        num_chunks=len(chunks), academic_hub_root=academic_hub_root, client=client,
    )
    print(f"  wrote outputs to {os.path.dirname(excalidraw_md_path)}/processed_outputs/")


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
    parser.add_argument("--dry-run", action="store_true", help="List files that would be processed without calling any API.")
    args = parser.parse_args()

    from common.gemini_utils import get_gemini_client, load_dotenv_override
    load_dotenv_override()

    academic_hub_dir = Path(__file__).resolve().parent.parent.parent / "academic-hub"
    notes_dir = academic_hub_dir / args.notes_subdir
    pairs = discover_excalidraw_files(str(notes_dir), args.file)
    if not pairs:
        print(f"No .excalidraw.md/.png pairs found under {notes_dir}.")
        sys.exit(1)

    client = None
    if not args.dry_run:
        client = get_gemini_client()
        if client is None:
            sys.exit(1)

    for md_path, png_path in pairs:
        process_excalidraw_note(
            md_path, png_path, client, args.model, args.expand_backend,
            str(academic_hub_dir), use_grounding=args.grounding, dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
