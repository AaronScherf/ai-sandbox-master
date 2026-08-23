#!/usr/bin/env python3
"""
convert_textbook.py
Extracts textbook-length PDFs into structured Markdown using Marker.
Optimized for GCP Compute Engine VMs with native Google Cloud Storage (GCS) pipeline integration.

Batching: accepts one or more input PDFs. Marker's vision models are loaded
exactly once per invocation and reused across every book in the batch, so
running N books in one call costs one model load instead of N.

Checkpointing: each page-range chunk is written to disk (text + images + a
".done" marker) as soon as it finishes. Rerunning on the same source PDF
skips chunks that already completed, so a crash, OOM, or preemption only
costs you the chunk(s) in flight -- not the whole document. This also means
Spot VM preemption mid-batch only costs the in-flight chunk of the in-flight
book; already-finished books and already-finished chunks of the current book
are untouched on resume.
"""

import os

# Must be set before marker/surya are imported below -- surya reads this at
# module-load time to decide whether its VLM inference server (a Docker
# container on GPU machines) tears itself down on exit or stays running.
# Leaving it running means a *later invocation of this script, within the
# same VM session*, attaches to the already-running server instead of
# re-pulling the container image and re-loading model weights from scratch.
# This does NOT help the very first run after a fresh VM boot (or after
# `gcloud compute instances stop`, which kills the container regardless) --
# only back-to-back reruns on a VM you're keeping up between them.
os.environ.setdefault("SURYA_INFERENCE_KEEP_ALIVE", "1")

import argparse
import glob
import sys
import gc
import re
import json
import signal
import time
import shutil
import torch
import subprocess
from contextlib import contextmanager
from pypdf import PdfReader, PdfWriter
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from page_markers import remap_image_links, remap_page_markers, tag_single_page
import chapter_index

def clean_stale_state():
    # Purge stale surya lock files
    lock_files = glob.glob('/root/.cache/datalab/surya/*.lock')
    for lock_file in lock_files:
        try:
            os.remove(lock_file)
        except OSError:
            pass

clean_stale_state()


class StepTimeoutError(Exception):
    """Raised when a single Marker conversion call runs past its wall-clock budget."""


@contextmanager
def time_limit(seconds, description):
    """
    Best-effort wall-clock guard around a single Marker conversion call, so a
    hang on one malformed page (as opposed to a clean exception, which the
    existing try/except fallback chain already handles) can't pin the whole
    billed -- possibly Spot, possibly about to be preempted anyway -- VM
    indefinitely.

    Uses SIGALRM rather than a subprocess-based hard kill: a subprocess
    would need its own model load per attempt, which defeats the entire
    point of keeping Marker's models warm across chunks and across books in
    a batch. The tradeoff is that this is a *soft* timeout, not a hard
    guarantee -- signal delivery is deferred if execution is inside a C
    extension that never yields back to the Python interpreter. In practice
    CUDA kernel launches and synchronization calls yield periodically, so
    this catches real hangs; it just doesn't bound them to the second.
    SIGALRM is POSIX-only, which is fine here since this script only ever
    runs on the Linux Compute Engine VM, never locally on Windows.
    """
    if seconds is None or seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def _on_alarm(signum, frame):
        raise StepTimeoutError(f"{description} exceeded {seconds}s timeout")

    previous_handler = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)


def sanitize_filename(text: str) -> str:
    """Sanitizes strings to ensure filesystem compatibility."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s-]", "", str(text)).strip()
    return re.sub(r"[-\s]+", "_", cleaned)


def download_from_gcs(gcs_uri: str, local_path: str):
    """Executes a subprocess to retrieve the input artifact from a GCS bucket."""
    print(f"Synchronizing input artifact from Google Cloud Storage: {gcs_uri}")
    try:
        subprocess.run(["gcloud", "storage", "cp", gcs_uri, local_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Critical Error: GCS retrieval failed. {e}")
        raise


def upload_to_gcs(local_dir: str, gcs_uri: str):
    """Executes a subprocess to push the finalized directory structure to a GCS bucket."""
    print(f"Synchronizing output artifacts to Google Cloud Storage: {gcs_uri}")
    try:
        subprocess.run(["gcloud", "storage", "cp", "-r", local_dir, gcs_uri], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Critical Error: GCS upload failed. {e}")
        raise


def delete_existing_gcs_output(gcs_uri: str):
    """
    Removes any prior output at this exact GCS path before uploading, so a
    rerun of the same book replaces it there instead of leaving both
    versions to accumulate. No-ops cleanly if nothing exists there yet
    (expected on a book's first run).

    Note: this only catches a prior version that landed under this *exact*
    folder name. If the bibliographic-metadata extraction ever produces a
    different name for the same book between runs (e.g. PDF metadata found
    on one run but not another), the old differently-named folder won't be
    caught here -- worth an occasional manual `gcloud storage ls` check if
    that's a concern.
    """
    print(f"Checking for a prior version to replace at: {gcs_uri}")
    result = subprocess.run(
        ["gcloud", "storage", "rm", "-r", gcs_uri],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("Removed prior version before uploading the new one.")
    else:
        stderr = (result.stderr or "").lower()
        if "not found" in stderr or "no urls matched" in stderr or "no matches" in stderr:
            print("No prior version found -- nothing to replace.")
        else:
            print(f"WARNING: could not check/clear prior GCS output (continuing anyway): {result.stderr.strip()}")


def load_checkpoint_metadata(metadata_path: str) -> dict:
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                print(f"WARNING: {metadata_path} did not contain a JSON object as expected; ignoring it.")
                return {}
            if data:
                print(f"Resuming with metadata captured on a previous run: {metadata_path}")
            return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_checkpoint_metadata(metadata_path: str, metadata: dict):
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


def _load_or_compute_boundaries(run_config_path, converter, reader, workspace, total_pages,
                                 max_chunk_size, max_front_matter_pages, max_boundary_shift,
                                 chapter_chunking_enabled):
    """
    Loads persisted chunk boundaries and folio offset from run_config.json
    if present (a resumed run), otherwise computes them once and persists
    the result -- guarantees identical chunking and tagging across resumes
    regardless of any nondeterminism in the boundary safety probe.
    """
    if os.path.exists(run_config_path):
        try:
            with open(run_config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if "boundaries" in saved:
                boundaries = [tuple(pair) for pair in saved["boundaries"]]
                return boundaries, saved.get("folio_offset"), saved.get("folio_start_page", total_pages)
            print(f"WARNING: {run_config_path} predates chapter-aware chunking (no 'boundaries' key). "
                  f"Existing chunk files use an incompatible scheme; discarding them and starting fresh.")
            chunks_dir = os.path.join(os.path.dirname(run_config_path), "chunks")
            shutil.rmtree(chunks_dir, ignore_errors=True)
            os.makedirs(chunks_dir, exist_ok=True)
        except (json.JSONDecodeError, OSError):
            pass

    boundaries, folio_offset, folio_start_page = compute_chunk_boundaries(
        converter, reader, workspace, total_pages, max_chunk_size,
        max_front_matter_pages, max_boundary_shift, chapter_chunking_enabled,
    )
    with open(run_config_path, "w", encoding="utf-8") as f:
        json.dump({
            "chunk_size": max_chunk_size,
            "boundaries": [list(pair) for pair in boundaries],
            "folio_offset": folio_offset,
            "folio_start_page": folio_start_page,
        }, f)
    return boundaries, folio_offset, folio_start_page


def process_page_range(converter, reader, workspace, start_page, end_page, images_dir,
                        chunk_timeout_s, page_timeout_s, folio_offset, folio_start_page):
    """
    Runs Marker over a single page-range chunk, falling back to per-page
    processing (and finally raw PyPDF extraction) on failure -- including a
    failure to complete within chunk_timeout_s/page_timeout_s.
    Returns (chunk_text, chunk_meta, hit_exception).
    Images are written directly to images_dir rather than held in memory.
    """
    temp_chunk_pdf = os.path.join(workspace, "temp_marker_slice.pdf")
    hit_exception = False
    chunk_meta = {}

    writer = PdfWriter()
    for page_num in range(start_page, end_page):
        writer.add_page(reader.pages[page_num])
    with open(temp_chunk_pdf, "wb") as f:
        writer.write(f)

    try:
        with time_limit(chunk_timeout_s, f"chunk pages {start_page + 1}-{end_page}"):
            rendered = converter(temp_chunk_pdf)
        chunk_text, chunk_meta, chunk_images = text_from_rendered(rendered)
        chunk_text = remap_page_markers(chunk_text, start_page, folio_offset, folio_start_page)
        chunk_text = remap_image_links(chunk_text, start_page + 1, chunk_images.keys())
        for img_key, img_data in chunk_images.items():
            img_data.save(os.path.join(images_dir, f"pg_{start_page + 1}_{img_key}"))

    except Exception as chunk_err:
        hit_exception = True
        print(f"Structural layout parsing failure on pages {start_page + 1}-{end_page}: {chunk_err}")
        text_segments = []

        for single_p in range(start_page, end_page):
            single_pdf_path = os.path.join(workspace, f"temp_p_{single_p}.pdf")
            single_writer = PdfWriter()
            single_writer.add_page(reader.pages[single_p])
            with open(single_pdf_path, "wb") as pf:
                single_writer.write(pf)

            try:
                with time_limit(page_timeout_s, f"page {single_p + 1}"):
                    p_rendered = converter(single_pdf_path)
                p_text, _, p_imgs = text_from_rendered(p_rendered)
                p_text = remap_page_markers(p_text, single_p, folio_offset, folio_start_page)
                p_text = remap_image_links(p_text, single_p + 1, p_imgs.keys())
                text_segments.append(p_text)
                for img_k, img_v in p_imgs.items():
                    img_v.save(os.path.join(images_dir, f"pg_{single_p + 1}_{img_k}"))
            except Exception as p_err:
                print(f"VLM bypassed on complex page {single_p + 1} ({p_err}). Initiating standard PyPDF fallback.")
                raw_text = reader.pages[single_p].extract_text() or ""
                text_segments.append(tag_single_page(raw_text, single_p, folio_offset, folio_start_page))
            finally:
                if os.path.exists(single_pdf_path):
                    os.remove(single_pdf_path)

        chunk_text = "\n\n".join(text_segments)

    finally:
        if os.path.exists(temp_chunk_pdf):
            os.remove(temp_chunk_pdf)

    return chunk_text, chunk_meta, hit_exception


_UNSAFE_BLOCK_TYPES = {"Table", "TableGroup", "Equation", "Form"}


def _page_looks_unterminated(rendered, page_text: str) -> bool:
    """
    Best-effort check for whether a single converted page's content looks
    like it's mid-table or mid-formula rather than cleanly ended.

    Primary signal: the page's last rendered block type, if marker's
    rendered-document structure exposes one in a form this can walk
    without guessing at an unconfirmed internal API. This is deliberately
    defensive -- the exact attribute path for a single-page render wasn't
    verified against the actual installed Marker version from outside the
    VM (no CUDA available here); if it's not available in whatever shape
    is expected, this silently falls through to the text-heuristic check
    below rather than raising.

    Fallback / second signal: the last non-empty line of the rendered
    markdown contains an unclosed table row or unbalanced math delimiters.
    """
    try:
        blocks = getattr(rendered, "children", None) or getattr(getattr(rendered, "block", None), "children", None)
        if blocks:
            last_block = blocks[-1]
            block_type = getattr(last_block, "block_type", None) or type(last_block).__name__
            if str(block_type) in _UNSAFE_BLOCK_TYPES:
                return True
    except Exception:
        pass

    lines = [ln for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return False
    last_line = lines[-1]
    if last_line.count("|") % 2 == 1:
        return True
    if last_line.count("$$") % 2 == 1:
        return True
    if "\\[" in last_line and "\\]" not in last_line:
        return True
    return False


def probe_and_shift_boundary(converter, reader, workspace, candidate_end_page, max_shift, hard_limit_page):
    """
    Checks whether the page immediately before candidate_end_page looks
    like it ends mid-table/mid-formula, and if so shifts the boundary
    forward one page at a time (re-probing each time) up to max_shift
    pages, never past hard_limit_page. Only used for chunk boundaries that
    aren't already chapter-aligned. Returns the (possibly shifted) end
    page -- always makes forward progress, even if still ambiguous at the
    shift cap.
    """
    end_page = candidate_end_page
    shifted = 0
    while shifted <= max_shift and end_page - 1 >= 0 and end_page < hard_limit_page:
        probe_page = end_page - 1
        temp_pdf = os.path.join(workspace, "temp_boundary_probe.pdf")
        writer = PdfWriter()
        writer.add_page(reader.pages[probe_page])
        with open(temp_pdf, "wb") as f:
            writer.write(f)
        try:
            rendered = converter(temp_pdf)
            page_text, _, _ = text_from_rendered(rendered)
        except Exception as probe_err:
            print(f"WARNING: boundary probe failed on page {probe_page + 1} ({probe_err}); keeping boundary as-is.")
            break
        finally:
            if os.path.exists(temp_pdf):
                os.remove(temp_pdf)

        page_text = page_text if isinstance(page_text, str) else ""
        if not _page_looks_unterminated(rendered, page_text):
            break

        print(f"[System] Chunk boundary at page {end_page} looks unsafe (page {probe_page + 1} may end "
              f"mid-table/mid-formula); shifting forward.")
        end_page += 1
        shifted += 1

    return min(end_page, hard_limit_page)


def compute_chunk_boundaries(converter, reader, workspace, total_pages, max_chunk_size,
                              max_front_matter_pages, max_boundary_shift, chapter_chunking_enabled):
    """
    Returns (boundaries, folio_offset, folio_start_page).

    boundaries is a list of (start_page, end_page) tuples covering the
    whole book. When chapter_chunking_enabled is False, this is exactly
    today's fixed-interval behavior. Otherwise: converts a capped
    front-matter chunk to read the printed TOC, then tries to resolve
    real chapters by fuzzy-matching the PDF's embedded outline (at any
    depth -- some books put chapters at the top level, others nest them
    under Parts) against that TOC; if that doesn't find enough matches
    (no outline, or its titles don't usefully match), falls back to
    anchoring the TOC to physical pages by scanning the front matter for
    printed folio numbers directly. Either way, chapters are greedily
    packed into chunks up to max_chunk_size, and any span that's still
    oversized is refined with a live Marker safety probe.
    folio_offset/folio_start_page (both possibly None/0) are returned so
    callers can pass them through to process_page_range for page/folio
    tagging.
    """
    if not chapter_chunking_enabled:
        boundaries = [
            (start, min(start + max_chunk_size, total_pages))
            for start in range(0, total_pages, max_chunk_size)
        ]
        return boundaries, None, total_pages

    # Shared scratch dir for any Marker conversions this function does on its
    # own (front-matter bootstrap, TOC re-read for folio offset) -- created
    # once up front so every process_page_range call below can rely on it
    # existing, whether or not that call happens to produce any images.
    images_dir = os.path.join(workspace, "marker_checkpoints", "_boundary_bootstrap_images")
    os.makedirs(images_dir, exist_ok=True)

    # Convert the front matter exactly once, unconditionally -- both the
    # outline-matching attempt below and the bootstrap fallback need to
    # read the printed TOC, and this is the one call that gets it for
    # either path. (This chunk gets converted again for real output during
    # the main per-chunk loop later; this pass is only used to extract
    # structure, its markdown is discarded.)
    front_matter_cap = min(max_front_matter_pages, total_pages)
    front_matter_text, _, _ = process_page_range(
        converter, reader, workspace, 0, front_matter_cap, images_dir,
        chunk_timeout_s=1800, page_timeout_s=240,
        folio_offset=None, folio_start_page=total_pages,
    )
    toc_chapters = chapter_index.parse_printed_toc(front_matter_text)

    folio_offset = None
    folio_start_page = total_pages
    rest_chapters: list = []

    all_outline_entries = chapter_index.get_all_outline_entries(reader)
    if all_outline_entries:
        # Confirmed on real books: a PDF's embedded outline doesn't
        # reliably put chapters at the top level -- Axler bookmarks the
        # title page as its first top-level entry; Hammack organizes its
        # outline by Part, with the real chapters nested one level
        # underneath (get_all_outline_entries flattens every depth for
        # exactly this reason). Let the printed TOC arbitrate which
        # entries are actually chapters via fuzzy title matching, rather
        # than assuming any particular outline depth.
        resolved, computed_offset = chapter_index.resolve_chapters_from_outline_and_toc(
            all_outline_entries, toc_chapters
        )
        if len(resolved) >= 2:
            # physical_page comes directly from the matched outline entry
            # here, not from any offset arithmetic -- resolved stays usable
            # for chunking even when computed_offset is None (folio tagging
            # just doesn't happen for this book).
            rest_chapters = resolved
            folio_offset = computed_offset

    if not rest_chapters:
        # Either no outline at all, or its entries' titles didn't usefully
        # match the printed TOC (too few matches to trust) -- fall back to
        # anchoring the TOC to physical pages by scanning the front matter
        # directly, reusing the same front_matter_text already converted
        # above.
        rest_chapters, folio_offset = chapter_index.bootstrap_chapter_index_from_front_matter(front_matter_text)

    if rest_chapters:
        front_matter_end = rest_chapters[0].physical_page
        folio_start_page = front_matter_end
    else:
        front_matter_end = min(20, total_pages)

    packed = chapter_index.pack_chapters_into_chunks(rest_chapters, front_matter_end, total_pages, max_chunk_size)
    known_chapter_pages = {c.physical_page for c in rest_chapters if c.physical_page is not None}

    def _probe_fn(end, hard_limit):
        return probe_and_shift_boundary(converter, reader, workspace, end, max_boundary_shift, hard_limit)

    boundaries = chapter_index.resolve_probe_boundaries(
        packed, front_matter_end, total_pages, known_chapter_pages, probe_fn=_probe_fn,
    )

    # Chunk 0 (front matter) is otherwise atomic -- a single (0, front_matter_end)
    # tuple with no size cap of its own. If the first outline/TOC entry sits
    # deep in the book, that single Marker call could span hundreds of pages,
    # exactly the memory/timeout scenario chunking exists to avoid. Subdivide
    # it the same way the rest of the book's fallback cuts are handled: no
    # chapter data of its own to align to, so pure fixed-interval packing,
    # refined by the same boundary safety probe.
    if front_matter_end > max_chunk_size:
        front_matter_packed = chapter_index.pack_chapters_into_chunks([], 0, front_matter_end, max_chunk_size)
        front_matter_boundaries = chapter_index.resolve_probe_boundaries(
            front_matter_packed, 0, front_matter_end, set(), probe_fn=_probe_fn,
        )
        boundaries = front_matter_boundaries + boundaries[1:]

    return boundaries, folio_offset, folio_start_page


def extract_source_bibliographic_info(reader: PdfReader) -> dict:
    """
    Best-effort extraction of title/author/year from the PDF's own document
    metadata (via pypdf's reader.metadata) -- this is separate from, and more
    likely to be populated than, marker's structural metadata (which only
    ever contains table_of_contents/page_stats, never bibliographic fields).

    LaTeX-produced PDFs often populate this via \\title/\\author + hyperref,
    but plenty don't (blank, or a generic value like the LaTeX engine name
    instead of the real author) -- every field here is optional, and callers
    should fall back to the filename when it's empty.
    """
    info = {"title": "", "author": "", "year": ""}
    try:
        meta = reader.metadata
    except Exception:
        meta = None
    if not meta:
        return info

    if meta.title and meta.title.strip():
        info["title"] = meta.title.strip()
    if meta.author and meta.author.strip():
        info["author"] = meta.author.strip()
    try:
        if meta.creation_date:
            info["year"] = str(meta.creation_date.year)
    except Exception:
        pass
    return info


# Values commonly left behind by PDF-generating toolchains that don't count
# as a real, descriptive author -- e.g. many LaTeX distributions populate
# /Author with the engine name if \\author{} was never set.
_GENERIC_METADATA_VALUES = {
    "latex", "tex", "pdftex", "pdflatex", "xelatex", "lualatex",
    "miktex", "texlive", "microsoft word", "writer", "unknown", ""
}


def is_descriptive_bibliographic_info(info: dict) -> bool:
    """True if info has a real title, or a real (non-generic) author."""
    title_ok = bool(info.get("title", "").strip())
    author = info.get("author", "").strip().lower()
    author_ok = bool(author) and author not in _GENERIC_METADATA_VALUES
    return title_ok or author_ok


def extract_bibliographic_info_from_markdown(md_text: str) -> dict:
    """
    Heuristic, regex-based extraction of title/author/year from the first
    page or two of marker's own markdown output. This is the last-resort
    tier: extract_bibliographic_info_via_llm() is tried first (when the
    PDF's embedded document metadata is missing or generic) and only falls
    through to this when the LLM call is unavailable, unconfigured, or
    fails outright.

    This is pattern-matching on a typical title/copyright page, not real
    parsing -- it only handles the common textbook layout (title as the
    first heading; a "(c) YEAR by AUTHOR NAME" copyright line near the top)
    and misses anything shaped differently. Treat it as a naming
    convenience, not authoritative bibliographic data.
    """
    info = {"title": "", "author": "", "year": ""}
    # Only look at roughly the first page or two -- title pages are short,
    # and scanning deeper into a large first chunk risks false-positive
    # matches against unrelated text further into the actual book content.
    snippet = md_text[:4000]

    # Title: the first markdown heading, with marker's inline HTML (e.g. the
    # <span id="page-0-0"></span> anchors it emits) and markdown emphasis
    # syntax stripped out.
    heading_match = re.search(r'^#{1,2}\s+(.+)$', snippet, re.MULTILINE)
    if heading_match:
        raw_title = re.sub(r'<[^>]+>', '', heading_match.group(1))
        raw_title = re.sub(r'[*_`]', '', raw_title).strip()
        if raw_title:
            info["title"] = raw_title

    # Year + author together: a copyright line like "(c) 2018 by Richard
    # Hammack" is common on textbook title/copyright pages and ties both
    # fields to one reliable match rather than guessing at them separately.
    copyright_match = re.search(
        r'©\s*(\d{4})\s+by\s+([A-Z][\w.\'-]+(?:\s+[A-Z][\w.\'-]+){0,3})',
        snippet
    )
    if copyright_match:
        info["year"] = copyright_match.group(1)
        # Defensive: the name-word pattern can occasionally span a stray
        # newline (e.g. if the next paragraph also starts with a capitalized
        # word) -- truncate to the first line to avoid swallowing extra text.
        info["author"] = copyright_match.group(2).split("\n")[0].strip()
    else:
        # Fall back to a bare year near a copyright symbol/word, without an
        # attached author name.
        year_match = re.search(r'©\s*(\d{4})|\bCopyright\b.{0,10}?(\d{4})', snippet)
        if year_match:
            info["year"] = year_match.group(1) or year_match.group(2)

    return info


def resolve_llm_project(explicit_project):
    """--llm-project if given, otherwise whatever project Application Default
    Credentials resolve to (already configured on this VM via Step 1.1 /
    Step 2.1). Returns None if neither is available, in which case LLM
    bibliographic extraction is skipped in favor of the regex fallback."""
    if explicit_project:
        return explicit_project
    try:
        import google.auth
        _, detected_project = google.auth.default()
        return detected_project
    except Exception:
        return None


def extract_bibliographic_info_via_llm(md_text: str, project: str, location: str, model: str) -> dict:
    """
    Asks a Gemini model, via Vertex AI, to read the start of marker's own
    markdown output and identify the book's title, author, and publication
    year. This is the primary bibliographic-extraction tier when the PDF's
    own metadata is missing or generic -- it handles title/copyright pages
    that don't fit extract_bibliographic_info_from_markdown()'s fixed regex
    shapes (e.g. an author name that isn't on a "(c) YEAR by NAME" line).

    Uses Vertex AI rather than a public API key so it reuses the VM's
    existing Application Default Credentials and the cloud-platform scope
    already required for GCS access (see gcp_instructions.md Step 2.1) --
    no separate secret needs to be distributed. Requires the Vertex AI API
    enabled and the VM's service account granted Vertex AI User on the GCP
    project (one-time, project-level setup -- see gcp_instructions.md).

    Still best-effort: whatever the model reports is not independently
    verified against the actual PDF. Any failure here (missing project,
    package not installed, API/permission error) is caught and reported as
    a WARNING, and the caller falls back to the regex heuristic.
    """
    info = {"title": "", "author": "", "year": ""}
    if not project:
        print("WARNING: no GCP project resolved for LLM bibliographic extraction "
              "(pass --llm-project, or run somewhere Application Default Credentials "
              "resolve one); falling back to regex heuristic.")
        return info

    try:
        from google import genai
    except ImportError:
        print("WARNING: google-genai is not installed; falling back to regex heuristic. "
              "(Rerun marker_setup.sh -- it now installs this.)")
        return info

    snippet = md_text[:6000]
    prompt = (
        "Below is the start of a textbook's front matter, extracted as Markdown by an "
        "OCR/layout pipeline (formatting may be imperfect). Identify the book's title, "
        "the primary author's full name, and its publication/copyright year.\n\n"
        "Respond with ONLY a JSON object with exactly these keys: "
        '"title", "author", "year" (a 4-digit string, or "" if not present). '
        'Use "" for any field you cannot determine with confidence -- do not guess.\n\n'
        f"--- MARKDOWN START ---\n{snippet}\n--- MARKDOWN END ---"
    )

    try:
        client = genai.Client(vertexai=True, project=project, location=location)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0,
                # Gemini models think by default, and thinking tokens are
                # billed as output tokens even though they never appear in
                # the response. There's no reasoning benefit to spotting a
                # title/author/year on a title page, so this is pure wasted
                # cost and latency for this call -- keep it as low as this
                # model generation allows. Gemini 3.x replaced the old
                # integer thinking_budget with a thinking_level enum, and
                # sending both in one request is a 400 -- confirmed via a
                # real "INVALID_ARGUMENT" from the live API when this still
                # said thinking_budget against gemini-3.6-flash. "minimal"
                # is the lowest level Flash-tier models support (Pro-tier
                # models can't go below "low" and can't disable thinking at
                # all -- irrelevant here since this only ever uses Flash).
                "thinking_config": {"thinking_level": "minimal"},
            },
        )
        parsed = json.loads(response.text)
        if isinstance(parsed, dict):
            for key in ("title", "author", "year"):
                value = parsed.get(key)
                if isinstance(value, str):
                    info[key] = value.strip()
    except Exception as llm_err:
        print(f"WARNING: LLM-based bibliographic extraction failed ({llm_err}); "
              f"falling back to regex heuristic.")

    return info


def merge_bibliographic_info(primary: dict, fallback: dict) -> dict:
    """Fill in only the blank fields of `primary` from `fallback`."""
    merged = dict(primary)
    for key in ("title", "author", "year"):
        if not merged.get(key):
            merged[key] = fallback.get(key, "")
    return merged


def process_one_pdf(converter, raw_input: str, raw_output: str, workspace: str, args) -> str:
    """
    Runs the full checkpointed extraction + assembly + upload pipeline for a
    single PDF, reusing the already-loaded `converter`. Returns the final
    output destination (GCS URI or local path) on success; raises on
    unrecoverable failure. `args` is the parsed CLI namespace (chunk size,
    timeouts, and LLM bibliographic-extraction settings).
    """
    is_gcs_input = raw_input.startswith("gs://")
    is_gcs_output = raw_output.startswith("gs://")
    input_key = sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0]) or "untitled_input"

    if is_gcs_input:
        # Named per-book (rather than one shared temp filename) so a failure
        # partway through one book in a batch can never be confused with, or
        # clobbered mid-write by, the next book's download.
        input_pdf = os.path.join(workspace, f"temp_gcs_input_{input_key}.pdf")
        download_from_gcs(raw_input, input_pdf)
    else:
        input_pdf = os.path.abspath(raw_input)

    try:
        if not os.path.exists(input_pdf):
            raise FileNotFoundError(f"Input PDF not found at {input_pdf}")

        if torch.cuda.is_available():
            print(f"Hardware Detected: {torch.cuda.get_device_name(0)}")
            print(f"VRAM Capacity: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        print(f"Loaded document mapping: {total_pages} total pages.")

        source_info = extract_source_bibliographic_info(reader)
        if is_descriptive_bibliographic_info(source_info):
            print(f"PDF document metadata found -- title: '{source_info['title']}' | "
                  f"author: '{source_info['author']}' | year: '{source_info['year']}'")
        else:
            print("No descriptive PDF document metadata found; will try parsing the "
                  "markdown title page instead once conversion finishes.")

        # Checkpoint directory setup. Keyed off the *source* filename (the
        # GCS URI or local path the user passed in), not the local downloaded
        # temp file -- so resuming works across runs even though gs:// inputs
        # get re-downloaded to a fresh local temp file each time.
        checkpoint_dir = os.path.join(workspace, "marker_checkpoints", input_key)
        chunks_dir = os.path.join(checkpoint_dir, "chunks")
        images_dir = os.path.join(checkpoint_dir, "images")
        metadata_path = os.path.join(checkpoint_dir, "metadata.json")
        os.makedirs(chunks_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)

        master_metadata = load_checkpoint_metadata(metadata_path)

        start_time = time.time()
        run_config_path = os.path.join(checkpoint_dir, "run_config.json")
        boundaries, folio_offset, folio_start_page = _load_or_compute_boundaries(
            run_config_path, converter, reader, workspace, total_pages,
            args.chunk_size, args.max_front_matter_pages, args.max_boundary_shift,
            args.chapter_chunking,
        )

        # Iterative Structural Extraction (resumable)
        for start_page, end_page in boundaries:
            chunk_tag = f"{start_page:05d}_{end_page:05d}"
            chunk_md_path = os.path.join(chunks_dir, f"{chunk_tag}.md")
            done_marker = os.path.join(chunks_dir, f"{chunk_tag}.done")

            if os.path.exists(done_marker):
                print(f"Skipping pages {start_page + 1}-{end_page} of {total_pages} (already completed on a prior run).")
                continue

            print(f"\nProcessing page subset: {start_page + 1} to {end_page} of {total_pages}...")

            chunk_text, chunk_meta, _hit_exception = process_page_range(
                converter, reader, workspace, start_page, end_page, images_dir,
                args.chunk_timeout, args.page_timeout, folio_offset, folio_start_page
            )

            # Write chunk text before the done marker, so a crash mid-write
            # never leaves a chunk falsely marked complete.
            with open(chunk_md_path, "w", encoding="utf-8") as f:
                f.write(chunk_text)

            # Capture metadata from the first chunk that actually returns any --
            # a chunk 0 that hit the per-page fallback path may return nothing,
            # so don't lock in an empty result if a later chunk has it.
            # marker's text_from_rendered() doesn't reliably return a dict here
            # (observed a plain str on one run) -- guard the type explicitly so
            # a surprising value never crashes final assembly after all chunks
            # have already done the expensive part of the work.
            if isinstance(chunk_meta, dict) and chunk_meta and not master_metadata:
                master_metadata = chunk_meta
                save_checkpoint_metadata(metadata_path, master_metadata)

            with open(done_marker, "w") as f:
                f.write(str(time.time()))

            gc.collect()
            # torch.cuda.empty_cache() releases PyTorch's cached CUDA memory
            # blocks back to the driver, forcing the next chunk to cudaMalloc
            # fresh instead of reusing the cache -- real overhead per chunk,
            # but negligible next to a chunk's own processing time (minutes).
            # Unconditional rather than exception-only: a real VM run hit
            # repeated "Inference error: Connection error" ~620 pages into a
            # 5-book/899-page batch in one continuous process (with
            # SURYA_INFERENCE_KEEP_ALIVE keeping the inference server warm
            # the whole time) -- consistent with VRAM accumulating across
            # many successful chunks and eventually starving that server,
            # not with any single chunk being too large on its own.
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        elapsed = time.time() - start_time
        print(f"\nExtraction complete. Total computation time this run: {elapsed:.2f}s.")

        # Artifact Assembly (reads chunk files from disk; nothing has been
        # held in memory across the loop above)
        chunk_files = sorted(glob.glob(os.path.join(chunks_dir, "*.md")))

        # marker's own metadata dict only ever contains structural fields
        # (table_of_contents, page_stats) -- bibliographic info comes from a
        # tiered fallback instead: (1) the PDF's own document metadata
        # (source_info, extracted above via pypdf), then (2) an LLM reading
        # of the first chunk's markdown title page if (1) wasn't descriptive
        # enough, then (3) a regex heuristic over the same text if the LLM
        # tier is unavailable/fails, then (4) the filename if nothing found
        # anything usable.
        markdown_info = {"title": "", "author": "", "year": ""}
        if not is_descriptive_bibliographic_info(source_info) and chunk_files:
            with open(chunk_files[0], "r", encoding="utf-8") as f:
                first_chunk_text = f.read(6000)

            if args.llm_bib:
                markdown_info = extract_bibliographic_info_via_llm(
                    first_chunk_text, args.llm_project, args.llm_location, args.llm_model
                )

            if not is_descriptive_bibliographic_info(markdown_info):
                markdown_info = extract_bibliographic_info_from_markdown(first_chunk_text)

            if is_descriptive_bibliographic_info(markdown_info):
                print(f"Bibliographic info parsed from markdown title page -- "
                      f"title: '{markdown_info['title']}' | author: '{markdown_info['author']}' | "
                      f"year: '{markdown_info['year']}'")
            else:
                print("Markdown title page didn't yield usable bibliographic info either; "
                      "naming output from the source filename.")

        bib_info = merge_bibliographic_info(source_info, markdown_info)

        if is_descriptive_bibliographic_info(bib_info):
            title_part = sanitize_filename(bib_info["title"]) or \
                sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0])
            if bib_info["author"]:
                first_author = bib_info["author"].split(",")[0].split(" and ")[0].strip()
                lastname_part = sanitize_filename(first_author.split()[-1]) if first_author else "UnknownAuthor"
            else:
                lastname_part = "UnknownAuthor"
            year_part = bib_info["year"] or "0000"
            folder_name = f"{lastname_part}_{title_part}_{year_part}"
        else:
            folder_name = sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0]) or "converted_textbook"

        local_build_dir = os.path.join(workspace, f"marker_assembly_output_{input_key}")
        if os.path.exists(local_build_dir):
            shutil.rmtree(local_build_dir)
        os.makedirs(local_build_dir, exist_ok=True)

        with open(os.path.join(local_build_dir, f"{folder_name}.md"), "w", encoding="utf-8") as out_f:
            for i, chunk_file in enumerate(chunk_files):
                with open(chunk_file, "r", encoding="utf-8") as in_f:
                    if i > 0:
                        out_f.write("\n\n")
                    out_f.write(in_f.read())

        if os.listdir(images_dir):
            shutil.copytree(images_dir, os.path.join(local_build_dir, "images"))

        # Ships the chapter-boundary/folio-offset data alongside the output
        # so downstream local tooling (describe_images.py) can filter
        # front-matter images without needing the VM, the source PDF, or
        # recomputing anything -- pure filesystem read.
        if os.path.exists(run_config_path):
            shutil.copy2(run_config_path, os.path.join(local_build_dir, "run_config.json"))

        master_metadata.update({
            "total_pages_processed": total_pages,
            "processing_time_seconds": round(elapsed, 2),
            "source_pdf_document_info": source_info,
            "markdown_parsed_info": markdown_info,
        })
        with open(os.path.join(local_build_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as json_f:
            json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)

        # Resolve Output Trajectory
        if is_gcs_output:
            target_gcs_path = f"{raw_output.rstrip('/')}/{folder_name}"
            delete_existing_gcs_output(target_gcs_path)
            upload_to_gcs(local_build_dir, target_gcs_path)
            shutil.rmtree(local_build_dir)
            final_destination = target_gcs_path
        else:
            output_dir = os.path.abspath(raw_output)
            final_destination = os.path.join(output_dir, folder_name)
            os.makedirs(output_dir, exist_ok=True)
            if os.path.exists(final_destination):
                shutil.rmtree(final_destination)
            shutil.copytree(local_build_dir, final_destination)
            shutil.rmtree(local_build_dir)

        print(f"Artifacts successfully synchronized to target destination: {final_destination}")

        # Checkpoint cleanup (only once final artifacts are confirmed
        # written/uploaded above)
        shutil.rmtree(checkpoint_dir, ignore_errors=True)
        return final_destination

    finally:
        if is_gcs_input and os.path.exists(input_pdf):
            os.remove(input_pdf)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract one or more textbook PDFs into structured Markdown using Marker."
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="One or more input PDFs, each a gs:// URI or local path. "
             "Marker's models are loaded once and reused across all of them."
    )
    parser.add_argument(
        "--output", required=True,
        help="Output directory (gs:// URI or local path), shared across all inputs. "
             "Each book is written to its own subfolder there."
    )
    parser.add_argument("--lang", default="en", help="OCR language (default: en)")
    parser.add_argument(
        "--chunk-size", type=int, default=150,
        help="Maximum pages per chunk (soft cap, default: 150) -- chunks are aligned to chapter "
             "boundaries when available and may be smaller. If a book has checkpoints from a "
             "prior run with a different chunk size, the recorded value is used instead -- see "
             "run_config.json."
    )
    parser.add_argument(
        "--max-boundary-shift", type=int, default=15,
        help="Max pages the safety probe may shift a fallback chunk boundary forward when it "
             "looks like it lands mid-table/mid-formula (default: 15)."
    )
    parser.add_argument(
        "--max-front-matter-pages", type=int, default=50,
        help="Cap on how far the front-matter TOC bootstrap will scan before giving up when "
             "there's no embedded PDF outline (default: 50)."
    )
    parser.add_argument(
        "--chapter-chunking", action=argparse.BooleanOptionalAction, default=True,
        help="Chapter-aware chunking, aligning chunk boundaries to chapter breaks when available "
             "(default: enabled). Disable with --no-chapter-chunking to fall back to pure "
             "fixed-interval chunking -- useful for debugging or A/B comparison against the new "
             "behavior on a real book."
    )
    parser.add_argument(
        "--chunk-timeout", type=int, default=1800,
        help="Max seconds allowed for one chunk-level Marker call before it's treated as hung "
             "and the chunk falls back to per-page processing (default: 1800). Set 0 to disable."
    )
    parser.add_argument(
        "--page-timeout", type=int, default=240,
        help="Max seconds allowed for one page-level Marker fallback call before giving up on "
             "that page and using raw PyPDF text extraction instead (default: 240). Set 0 to disable."
    )
    parser.add_argument(
        "--enable-multiprocessing", action="store_true",
        help="Let Marker use its internal multiprocessing (default: disabled). Enable this to "
             "benchmark whether it improves GPU utilization on multi-vCPU VMs; leave it off "
             "otherwise, since it's the setting this pipeline has been validated against."
    )
    parser.add_argument(
        "--llm-bib", action=argparse.BooleanOptionalAction, default=True,
        help="Use a Gemini model (via Vertex AI) to read the markdown title page for "
             "title/author/year when the PDF's own metadata is missing (default: enabled). "
             "Falls back to a regex heuristic automatically if this fails or isn't configured "
             "-- see gcp_instructions.md for the one-time Vertex AI project setup this needs. "
             "Disable with --no-llm-bib to skip straight to the regex heuristic."
    )
    parser.add_argument(
        "--llm-project", default=None,
        help="GCP project for Vertex AI calls (default: resolved from Application Default "
             "Credentials, already configured on this VM)."
    )
    parser.add_argument(
        "--llm-location", default="us-central1",
        help="Vertex AI region for the Gemini call (default: us-central1)."
    )
    parser.add_argument(
        "--llm-model", default="gemini-3.6-flash",
        help="Gemini model name for bibliographic extraction (default: gemini-3.6-flash)."
    )
    return parser.parse_args()


def run_conversion():
    args = parse_args()
    workspace = os.getcwd()

    print("==================================================")
    print("Initializing Native GCP Marker Pipeline")
    print("==================================================")

    if not torch.cuda.is_available():
        # Marker runs fine without CUDA, which is exactly the danger: it
        # silently falls back to plain PyPDF text extraction for every page
        # -- no OCR, no layout, no images -- rather than raising. That
        # produces output that looks plausible but is badly degraded, which
        # is worse than a loud failure here. This should never happen after
        # a successful marker_setup.sh run; if it does, the environment is
        # broken in a way worth stopping for rather than pushing through.
        print("FATAL: CUDA is not available in this environment.")
        print("Proceeding would silently degrade every page to plain PyPDF text extraction")
        print("(no OCR, no layout, no images) instead of failing loudly.")
        print("This usually means Step 3.1 (marker_setup.sh) hasn't completed successfully on")
        print("this VM. Reset: stop and delete this VM (gcp_instructions.md Step 4, Option B),")
        print("recreate it, and rerun Step 3.1 from a clean disk before retrying.")
        sys.exit(1)

    if args.llm_bib:
        args.llm_project = resolve_llm_project(args.llm_project)
        if args.llm_project:
            print(f"LLM bibliographic extraction: enabled (project='{args.llm_project}', "
                  f"location='{args.llm_location}', model='{args.llm_model}').")
        else:
            print("LLM bibliographic extraction: enabled but no GCP project could be resolved -- "
                  "will fall back to the regex heuristic for every book. Pass --llm-project to fix.")

    print(f"Loading vision models once for this batch of {len(args.inputs)} document(s) "
          f"(Target Language: '{args.lang}')...")
    model_dict = create_model_dict()
    converter_config = {
        "langs": [args.lang],
        "paginate_output": True,
        # Off by default -- this is the setting the pipeline has been
        # validated against. --enable-multiprocessing exists to benchmark
        # whether letting Marker parallelize CPU-bound pre/post-processing
        # improves GPU utilization on multi-vCPU VMs.
        "disable_multiprocessing": not args.enable_multiprocessing,
    }
    converter = PdfConverter(artifact_dict=model_dict, config=converter_config)

    results = []
    for idx, raw_input in enumerate(args.inputs, start=1):
        print(f"\n{'=' * 60}\nDocument {idx}/{len(args.inputs)}: {raw_input}\n{'=' * 60}")
        try:
            final_destination = process_one_pdf(converter, raw_input, args.output, workspace, args)
            results.append((raw_input, "OK", final_destination))
        except Exception as book_err:
            # A single book's unrecoverable failure (e.g. a corrupt PDF)
            # shouldn't sink the rest of the batch -- record it and move on.
            print(f"CRITICAL: '{raw_input}' failed and will be skipped: {book_err}")
            results.append((raw_input, "FAILED", str(book_err)))

    print(f"\n{'=' * 60}\nBatch summary\n{'=' * 60}")
    for raw_input, status, detail in results:
        if status == "OK":
            print(f"  [OK]     {raw_input} -> {detail}")
        else:
            print(f"  [FAILED] {raw_input} ({detail})")

    if any(status == "FAILED" for _, status, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    run_conversion()
