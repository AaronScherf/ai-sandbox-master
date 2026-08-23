#!/usr/bin/env python3
"""
describe_images.py
Runs locally (no GCP VM needed) against textbooks already converted by
convert_textbook.py. For each image in a book's markdown, asks a Gemini
model whether the image is meaningful academic content worth describing
(skipping decorative/non-informational images), and writes a derived
"<book>.rag.md" file with descriptions inserted directly beneath each
kept image's link -- the original "<book>.md" is never modified.

Everything except the actual Gemini network call and the CLI driver is
pure-Python and independently unit-tested (test_describe_images.py) --
no torch/marker/pypdf dependency, matching chapter_index.py/page_markers.py.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_IMAGE_REF_RE = re.compile(r"!\[\]\((pg_(\d+)_[^)]+)\)")
_TAG_ONLY_RE = re.compile(r"^(?:\s*<!--.*?-->\s*)+$")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


@dataclass
class ImageRef:
    filename: str
    physical_page: int
    start: int
    end: int


def find_image_references(text: str) -> list[ImageRef]:
    """
    Locates every image link Marker's output produces after the
    remap_image_links fix (convert_textbook.py) -- "![](pg_{page}_...)".
    Links without that prefix (e.g. output converted before the fix
    shipped) can't be page-attributed and are skipped rather than
    crashing the parser.
    """
    refs = []
    for m in _IMAGE_REF_RE.finditer(text):
        refs.append(ImageRef(
            filename=m.group(1),
            physical_page=int(m.group(2)),
            start=m.start(),
            end=m.end(),
        ))
    return refs


def filter_front_matter(refs: list[ImageRef], front_matter_end: int | None) -> list[ImageRef]:
    """
    Drops images on or before the book's last front-matter physical page
    (cover art, publisher logos, title-page decoration) -- a free filter,
    no LLM call needed. front_matter_end is boundaries[0][1] from
    run_config.json (see load_front_matter_end); None if unavailable
    means "keep everything, let the per-image LLM call judge instead."
    """
    if front_matter_end is None:
        return list(refs)
    return [r for r in refs if r.physical_page > front_matter_end]


def _paragraphs(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text)
    return [b.strip() for b in blocks if b.strip() and not _TAG_ONLY_RE.match(b.strip())]


def extract_paragraph_context(
    text: str, ref: ImageRef, paragraphs_before: int = 1, paragraphs_after: int = 1
) -> tuple[str, str]:
    """
    Grabs the prose paragraph(s) immediately surrounding an image
    reference, skipping over <!-- page/folio --> tag lines so they don't
    get treated as prose context.
    """
    before_paragraphs = _paragraphs(text[:ref.start])
    after_paragraphs = _paragraphs(text[ref.end:])
    before = "\n\n".join(before_paragraphs[-paragraphs_before:]) if paragraphs_before > 0 else ""
    after = "\n\n".join(after_paragraphs[:paragraphs_after]) if paragraphs_after > 0 else ""
    return before, after


def nearest_preceding_heading(text: str, position: int) -> str | None:
    """Cheap chapter/section-name hint for the prompt: the nearest # heading above the image."""
    heading = None
    for m in _HEADING_RE.finditer(text, 0, position):
        heading = m.group(1).strip()
    return heading


def build_description_prompt(context_before: str, context_after: str, heading: str | None) -> str:
    heading_line = f"Chapter/section: {heading}\n\n" if heading else ""
    context_block = ""
    if context_before:
        context_block += f"Text immediately before the image:\n{context_before}\n\n"
    if context_after:
        context_block += f"Text immediately after the image:\n{context_after}\n\n"
    return (
        "You are helping convert a textbook into a study-friendly RAG-ready markdown file. "
        "An image extracted from the book is attached. Decide whether it is meaningful "
        "academic content -- a diagram, chart, plot, graph, geometric figure, table, or "
        "photo relevant to the surrounding material -- that a student would benefit from "
        "having described in text form. Decorative content (stock photos, publisher logos, "
        "cover art, blank or near-blank scan artifacts, ornamental borders) should be "
        "skipped.\n\n"
        f"{heading_line}{context_block}"
        "Respond with ONLY a JSON object with exactly these keys: "
        '"skip" (boolean) and "description" (a string; empty if skip is true, otherwise a '
        "clear, self-contained plain-text description of the image's content -- accurate "
        "enough that a reader who cannot see the image understands what it shows).\n"
    )


def parse_description_response(response_text: str) -> dict:
    default = {"skip": True, "description": ""}
    try:
        parsed = json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        return default
    if not isinstance(parsed, dict):
        return default
    skip = parsed.get("skip")
    description = parsed.get("description")
    if not isinstance(skip, bool) or not isinstance(description, str):
        return default
    return {"skip": skip, "description": description}


def load_description_cache(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_description_cache(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_front_matter_end(book_dir: str) -> int | None:
    """
    Reads the front-matter/chapter-1 boundary that convert_textbook.py
    already computed, from run_config.json (copied into the book's
    output folder alongside the .md/images/ so this never needs VM or
    PDF access). Returns None if unavailable -- filter_front_matter then
    keeps everything and leaves the judgment call to the per-image LLM
    call instead.
    """
    run_config_path = os.path.join(book_dir, "run_config.json")
    if not os.path.exists(run_config_path):
        return None
    try:
        with open(run_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        boundaries = data.get("boundaries")
        if boundaries:
            return int(boundaries[0][1])
    except (json.JSONDecodeError, OSError, ValueError, TypeError, IndexError):
        pass
    return None


def build_rag_markdown(text: str, results: dict) -> str:
    """
    Builds the derived .rag.md text: a description blockquote is
    inserted directly beneath each described image's link; skipped or
    not-yet-processed images are left completely untouched. Strictly
    additive -- never edits or removes anything from the source text.
    """
    refs = find_image_references(text)
    for ref in sorted(refs, key=lambda r: r.start, reverse=True):
        result = results.get(ref.filename)
        if not result or result.get("skip", True):
            continue
        description = result.get("description", "")
        if not description:
            continue
        insertion = f"\n\n> **Image description:** {description}"
        text = text[:ref.end] + insertion + text[ref.end:]
    return text


def discover_book_dirs(processed_outputs_dir: str, book_filter: str | None = None) -> list[str]:
    if not os.path.isdir(processed_outputs_dir):
        return []
    dirs = []
    for name in sorted(os.listdir(processed_outputs_dir)):
        full = os.path.join(processed_outputs_dir, name)
        if os.path.isdir(full) and os.path.exists(os.path.join(full, f"{name}.md")):
            if book_filter is None or name == book_filter:
                dirs.append(full)
    return dirs


def describe_image_via_gemini(client, model: str, image_path: str, prompt: str) -> dict:
    """Only function in this module that touches the network -- not unit-tested locally."""
    from google.genai import types

    mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response = client.models.generate_content(
        model=model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config={
            "response_mime_type": "application/json",
            "temperature": 0,
            "thinking_config": {"thinking_budget": 0},
        },
    )
    return parse_description_response(response.text)


def _call_with_retries(fn, retries: int = 3, backoff_seconds: float = 5.0):
    last_err: Exception = RuntimeError("no attempts were made")
    for attempt in range(retries):
        try:
            return fn()
        except Exception as err:
            last_err = err
            if attempt < retries - 1:
                wait = backoff_seconds * (attempt + 1)
                print(f"WARNING: Gemini call failed (attempt {attempt + 1}/{retries}): {err}. Retrying in {wait:.0f}s.")
                time.sleep(wait)
    raise last_err


def process_book(
    book_dir: str,
    client,
    model: str,
    paragraphs_before: int = 1,
    paragraphs_after: int = 1,
    dry_run: bool = False,
) -> None:
    folder_name = os.path.basename(book_dir)
    md_path = os.path.join(book_dir, f"{folder_name}.md")
    images_dir = os.path.join(book_dir, "images")
    cache_path = os.path.join(book_dir, f"{folder_name}_image_descriptions.json")
    rag_path = os.path.join(book_dir, f"{folder_name}.rag.md")

    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    front_matter_end = load_front_matter_end(book_dir)
    refs = filter_front_matter(find_image_references(text), front_matter_end)

    print(f"[{folder_name}] {len(refs)} candidate image(s) past front matter "
          f"(front_matter_end={front_matter_end}).")

    cache = load_description_cache(cache_path)

    if dry_run:
        for ref in refs:
            status = "cached" if ref.filename in cache else "would call Gemini"
            print(f"  page {ref.physical_page}: {ref.filename} ({status})")
        return

    for i, ref in enumerate(refs, 1):
        if ref.filename in cache:
            continue

        image_path = os.path.join(images_dir, ref.filename)
        if not os.path.exists(image_path):
            print(f"  WARNING: {ref.filename} referenced in markdown but missing from images/; skipping.")
            cache[ref.filename] = {"skip": True, "description": ""}
            save_description_cache(cache_path, cache)
            continue

        before, after = extract_paragraph_context(text, ref, paragraphs_before, paragraphs_after)
        heading = nearest_preceding_heading(text, ref.start)
        prompt = build_description_prompt(before, after, heading)

        try:
            result = _call_with_retries(
                lambda: describe_image_via_gemini(client, model, image_path, prompt)
            )
        except Exception as err:
            print(f"  WARNING: giving up on {ref.filename} after retries ({err}); leaving unprocessed for a future rerun.")
            continue

        cache[ref.filename] = result
        save_description_cache(cache_path, cache)
        tag = "described" if not result["skip"] else "skipped (decorative)"
        print(f"  [{i}/{len(refs)}] page {ref.physical_page}: {ref.filename} -- {tag}")

    rag_text = build_rag_markdown(text, cache)
    with open(rag_path, "w", encoding="utf-8") as f:
        f.write(rag_text)
    print(f"[{folder_name}] wrote {rag_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Describe images in already-converted textbook markdown for RAG use. "
                    "Runs locally -- no GCP VM needed."
    )
    parser.add_argument(
        "--textbook-subdir", required=True,
        help="Path, relative to the academic-hub/ folder next to this project, "
             "containing processed_outputs/ (same value as gcp_instructions.md Step 0.2).",
    )
    parser.add_argument("--book", default=None, help="Only process this one book folder name (default: every book found).")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--context-paragraphs-before", type=int, default=1)
    parser.add_argument("--context-paragraphs-after", type=int, default=1)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List which images would be processed (and which are already cached) without calling the API.",
    )
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
    except ImportError:
        print("WARNING: python-dotenv not installed (pip install python-dotenv); "
              "relying on GEMINI_API_KEY already being set in the environment.")

    academic_hub_dir = Path(__file__).resolve().parent.parent / "academic-hub"
    processed_outputs_dir = academic_hub_dir / args.textbook_subdir / "processed_outputs"
    book_dirs = discover_book_dirs(str(processed_outputs_dir), args.book)
    if not book_dirs:
        print(f"No book folders with a matching .md file found under {processed_outputs_dir}.")
        sys.exit(1)

    client = None
    if not args.dry_run:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not set (checked the environment and ../.env). "
                  "Get a key at aistudio.google.com/apikey and add it to ai-sandbox/.env.")
            sys.exit(1)
        try:
            from google import genai
        except ImportError:
            print("ERROR: google-genai is not installed. Run: pip install google-genai")
            sys.exit(1)
        client = genai.Client(api_key=api_key)

    for book_dir in book_dirs:
        process_book(
            book_dir, client, args.model,
            args.context_paragraphs_before, args.context_paragraphs_after,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
