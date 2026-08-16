#!/usr/bin/env python3
"""
convert_textbook.py
Extracts textbook-length PDFs into structured Markdown using Marker.
Optimized for GCP Compute Engine VMs with native Google Cloud Storage (GCS) pipeline integration.
"""

import os
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


def run_conversion():
    if len(sys.argv) < 3:
        print("Usage: python3 convert_textbook.py <INPUT_PDF_OR_GCS_URI> <OUTPUT_DIR_OR_GCS_URI> [OCR_LANG] [CHUNK_SIZE]")
        sys.exit(1)

    raw_input = sys.argv[1]
    raw_output = sys.argv[2]
    ocr_language = sys.argv[3] if len(sys.argv) > 3 else "en"
    chunk_size = int(sys.argv[4]) if len(sys.argv) > 4 else 50

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

    temp_chunk_pdf = os.path.join(workspace, "temp_marker_slice.pdf")

    combined_text_segments = []
    combined_images = {}
    master_metadata = {}

    start_time = time.time()

    # 2. Iterative Structural Extraction
    for start_page in range(0, total_pages, chunk_size):
        end_page = min(start_page + chunk_size, total_pages)
        print(f"\nProcessing page subset: {start_page + 1} to {end_page} of {total_pages}...")

        writer = PdfWriter()
        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])

        with open(temp_chunk_pdf, "wb") as f:
            writer.write(f)

        try:
            rendered = converter(temp_chunk_pdf)
            chunk_text, chunk_meta, chunk_images = text_from_rendered(rendered)
            combined_text_segments.append(chunk_text)

            for img_key, img_bytes in chunk_images.items():
                combined_images[f"pg_{start_page + 1}_{img_key}"] = img_bytes

            if start_page == 0 and chunk_meta:
                master_metadata = chunk_meta

        except Exception as chunk_err:
            print(f"Structural layout parsing failure on pages {start_page + 1}-{end_page}: {chunk_err}")

            for single_p in range(start_page, end_page):
                single_pdf_path = os.path.join(workspace, f"temp_p_{single_p}.pdf")
                single_writer = PdfWriter()
                single_writer.add_page(reader.pages[single_p])
                with open(single_pdf_path, "wb") as pf:
                    single_writer.write(pf)

                try:
                    p_rendered = converter(single_pdf_path)
                    p_text, _, p_imgs = text_from_rendered(p_rendered)
                    combined_text_segments.append(p_text)
                    for img_k, img_v in p_imgs.items():
                        combined_images[f"pg_{single_p + 1}_{img_k}"] = img_v
                except Exception as p_err:
                    print(f"VLM bypassed on complex page {single_p + 1} ({p_err}). Initiating standard PyPDF fallback.")
                    raw_text = reader.pages[single_p].extract_text() or ""
                    combined_text_segments.append(f"\n\n<!-- PyPDF Fallback: Page {single_p + 1} -->\n\n{raw_text}")
                finally:
                    if os.path.exists(single_pdf_path):
                        os.remove(single_pdf_path)
        finally:
            if os.path.exists(temp_chunk_pdf):
                os.remove(temp_chunk_pdf)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    elapsed = time.time() - start_time
    print(f"\nExtraction complete. Total computation time: {elapsed:.2f}s.")

    # 3. Artifact Assembly
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

    with open(os.path.join(local_build_dir, f"{folder_name}.md"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(combined_text_segments))

    if combined_images:
        images_dir = os.path.join(local_build_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        for img_name, img_data in combined_images.items():
            img_data.save(os.path.join(images_dir, img_name))

    master_metadata.update({"total_pages_processed": total_pages, "processing_time_seconds": round(elapsed, 2)})
    with open(os.path.join(local_build_dir, f"{folder_name}_metadata.json"), "w", encoding="utf-8") as json_f:
        json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)

    # 4. Resolve Output Trajectory
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

    # 5. Local State Cleanup
    if is_gcs_input and os.path.exists(input_pdf):
        os.remove(input_pdf)

if __name__ == "__main__":
    run_conversion()