#!/usr/bin/env python3
"""
convert_textbook.py
Extracts textbook-length PDFs into structured Markdown using Marker.
Optimized for GCP Compute Engine VMs with native Google Cloud Storage (GCS) pipeline integration.

Checkpointing: each page-range chunk is written to disk (text + images + a
".done" marker) as soon as it finishes. Rerunning on the same source PDF
skips chunks that already completed, so a crash, OOM, or preemption only
costs you the chunk(s) in flight -- not the whole document.
"""

import os
import glob
import sys
import gc
import re
import json
import time
import shutil
import torch
import subprocess
from pypdf import PdfReader, PdfWriter
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

def clean_stale_state():
    # Purge stale surya lock files
    lock_files = glob.glob('/root/.cache/datalab/surya/*.lock')
    for lock_file in lock_files:
        try:
            os.remove(lock_file)
        except OSError:
            pass

clean_stale_state()

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
        sys.exit(1)


def upload_to_gcs(local_dir: str, gcs_uri: str):
    """Executes a subprocess to push the finalized directory structure to a GCS bucket."""
    print(f"Synchronizing output artifacts to Google Cloud Storage: {gcs_uri}")
    try:
        subprocess.run(["gcloud", "storage", "cp", "-r", local_dir, gcs_uri], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Critical Error: GCS upload failed. {e}")
        sys.exit(1)


def load_checkpoint_metadata(metadata_path: str) -> dict:
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                print(f"Resuming with metadata captured on a previous run: {metadata_path}")
            return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_checkpoint_metadata(metadata_path: str, metadata: dict):
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


def process_page_range(converter, reader, workspace, start_page, end_page, images_dir):
    """
    Runs Marker over a single page-range chunk, falling back to per-page
    processing (and finally raw PyPDF extraction) on failure.
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
        rendered = converter(temp_chunk_pdf)
        chunk_text, chunk_meta, chunk_images = text_from_rendered(rendered)
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
                p_rendered = converter(single_pdf_path)
                p_text, _, p_imgs = text_from_rendered(p_rendered)
                text_segments.append(p_text)
                for img_k, img_v in p_imgs.items():
                    img_v.save(os.path.join(images_dir, f"pg_{single_p + 1}_{img_k}"))
            except Exception as p_err:
                print(f"VLM bypassed on complex page {single_p + 1} ({p_err}). Initiating standard PyPDF fallback.")
                raw_text = reader.pages[single_p].extract_text() or ""
                text_segments.append(f"\n\n<!-- PyPDF Fallback: Page {single_p + 1} -->\n\n{raw_text}")
            finally:
                if os.path.exists(single_pdf_path):
                    os.remove(single_pdf_path)

        chunk_text = "\n\n".join(text_segments)

    finally:
        if os.path.exists(temp_chunk_pdf):
            os.remove(temp_chunk_pdf)

    return chunk_text, chunk_meta, hit_exception


def run_conversion():
    if len(sys.argv) < 3:
        print("Usage: python3 convert_textbook.py <INPUT_PDF_OR_GCS_URI> <OUTPUT_DIR_OR_GCS_URI> [OCR_LANG] [CHUNK_SIZE]")
        sys.exit(1)

    raw_input = sys.argv[1]
    raw_output = sys.argv[2]
    ocr_language = sys.argv[3] if len(sys.argv) > 3 else "en"
    # Default raised from 50 -> 150 pages. This is safe to push higher (even
    # to the full document) once checkpointing means a mid-run failure only
    # costs you the in-flight chunk rather than the whole book -- but a
    # smaller chunk size still bounds how much gets redone if a specific
    # book turns out to be unusually memory-hungry (heavy on diagrams/tables).
    chunk_size = int(sys.argv[4]) if len(sys.argv) > 4 else 150

    workspace = os.getcwd()
    is_gcs_input = raw_input.startswith("gs://")
    is_gcs_output = raw_output.startswith("gs://")

    # 1. Resolve Input Trajectory
    if is_gcs_input:
        input_pdf = os.path.join(workspace, "temp_gcs_input_target.pdf")
        download_from_gcs(raw_input, input_pdf)
    else:
        input_pdf = os.path.abspath(raw_input)

    if not os.path.exists(input_pdf):
        print(f"Critical Error: Input PDF not found at {input_pdf}")
        sys.exit(1)

    print("==================================================")
    print("Initializing Native GCP Marker Pipeline")
    print("==================================================")

    if torch.cuda.is_available():
        print(f"Hardware Detected: {torch.cuda.get_device_name(0)}")
        print(f"VRAM Capacity: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

    print(f"Loading vision models (Target Language: '{ocr_language}')...")
    model_dict = create_model_dict()

    converter_config = {
        "langs": [ocr_language],
        "disable_multiprocessing": True
    }
    converter = PdfConverter(artifact_dict=model_dict, config=converter_config)

    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    print(f"Loaded document mapping: {total_pages} total pages.")

    # 2. Checkpoint directory setup. Keyed off the *source* filename (the
    # GCS URI or local path the user passed in), not the local downloaded
    # temp file -- so resuming works even though gs:// inputs get downloaded
    # to a generic "temp_gcs_input_target.pdf" each time.
    input_key = sanitize_filename(os.path.splitext(os.path.basename(raw_input))[0]) or "untitled_input"
    checkpoint_dir = os.path.join(workspace, "marker_checkpoints", input_key)
    chunks_dir = os.path.join(checkpoint_dir, "chunks")
    images_dir = os.path.join(checkpoint_dir, "images")
    metadata_path = os.path.join(checkpoint_dir, "metadata.json")
    os.makedirs(chunks_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    master_metadata = load_checkpoint_metadata(metadata_path)

    start_time = time.time()
    chunk_ranges = list(range(0, total_pages, chunk_size))

    # 3. Iterative Structural Extraction (resumable)
    for start_page in chunk_ranges:
        end_page = min(start_page + chunk_size, total_pages)
        chunk_tag = f"{start_page:05d}_{end_page:05d}"
        chunk_md_path = os.path.join(chunks_dir, f"{chunk_tag}.md")
        done_marker = os.path.join(chunks_dir, f"{chunk_tag}.done")

        if os.path.exists(done_marker):
            print(f"Skipping pages {start_page + 1}-{end_page} of {total_pages} (already completed on a prior run).")
            continue

        print(f"\nProcessing page subset: {start_page + 1} to {end_page} of {total_pages}...")

        chunk_text, chunk_meta, hit_exception = process_page_range(
            converter, reader, workspace, start_page, end_page, images_dir
        )

        # Write chunk text before the done marker, so a crash mid-write
        # never leaves a chunk falsely marked complete.
        with open(chunk_md_path, "w", encoding="utf-8") as f:
            f.write(chunk_text)

        # Capture metadata from the first chunk that actually returns any --
        # a chunk 0 that hit the per-page fallback path may return nothing,
        # so don't lock in an empty result if a later chunk has it.
        if chunk_meta and not master_metadata:
            master_metadata = chunk_meta
            save_checkpoint_metadata(metadata_path, master_metadata)

        with open(done_marker, "w") as f:
            f.write(str(time.time()))

        gc.collect()
        # torch.cuda.empty_cache() releases PyTorch's cached CUDA memory
        # blocks back to the driver, forcing the next chunk to cudaMalloc
        # fresh instead of reusing the cache -- real overhead if you're not
        # actually under memory pressure. Only clear it after a chunk that
        # hit the exception/fallback path, where memory pressure is more
        # plausible. If you see OOMs even so, call it unconditionally here.
        if hit_exception and torch.cuda.is_available():
            torch.cuda.empty_cache()

    elapsed = time.time() - start_time
    print(f"\nExtraction complete. Total computation time this run: {elapsed:.2f}s.")

    # 4. Artifact Assembly (reads chunk files from disk; nothing has been
    # held in memory across the loop above)
    title = sanitize_filename(master_metadata.get("title", ""))
    authors = master_metadata.get("authors", "")
    lastname = sanitize_filename(str(authors).split(",")[-1].split()[-1]) if authors else "UnknownAuthor"
    year = sanitize_filename(master_metadata.get("year", "0000")) or "0000"
    if not title:
        title = sanitize_filename(os.path.splitext(os.path.basename(input_pdf))[0])

    folder_name = f"{lastname}_{title}_{year}"
    local_build_dir = os.path.join(workspace, "marker_assembly_output")
    if os.path.exists(local_build_dir):
        shutil.rmtree(local_build_dir)
    os.makedirs(local_build_dir, exist_ok=True)

    chunk_files = sorted(glob.glob(os.path.join(chunks_dir, "*.md")))
    with open(os.path.join(local_build_dir, f"{folder_name}.md"), "w", encoding="utf-8") as out_f:
        for i, chunk_file in enumerate(chunk_files):
            with open(chunk_file, "r", encoding="utf-8") as in_f:
                if i > 0:
                    out_f.write("\n\n")
                out_f.write(in_f.read())

    if os.listdir(images_dir):
        shutil.copytree(images_dir, os.path.join(local_build_dir, "images"))

    master_metadata.update({"total_pages_processed": total_pages, "processing_time_seconds": round(elapsed, 2)})
    with open(os.path.join(local_build_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as json_f:
        json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)

    # 5. Resolve Output Trajectory
    if is_gcs_output:
        target_gcs_path = f"{raw_output.rstrip('/')}/{folder_name}"
        upload_to_gcs(local_build_dir, target_gcs_path)
        shutil.rmtree(local_build_dir)
        print(f"Artifacts successfully synchronized to target destination: {target_gcs_path}")
    else:
        output_dir = os.path.abspath(raw_output)
        final_destination = os.path.join(output_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)
        if os.path.exists(final_destination):
            shutil.rmtree(final_destination)
        shutil.copytree(local_build_dir, final_destination)
        shutil.rmtree(local_build_dir)
        print(f"Artifacts successfully synchronized to target destination: {final_destination}")

    # 6. Checkpoint + local state cleanup (only once final artifacts are
    # confirmed written/uploaded above)
    shutil.rmtree(checkpoint_dir, ignore_errors=True)
    if is_gcs_input and os.path.exists(input_pdf):
        os.remove(input_pdf)

if __name__ == "__main__":
    run_conversion()