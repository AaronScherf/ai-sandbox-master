#!/usr/bin/env python3
"""
convert_textbook.py
Extracts textbook-length PDFs into structured Markdown using Marker.
Relies on PyTorch/Transformers natively to parse math and tables,
strictly bypassing Docker.
"""

import os
import sys

# ==============================================================================
# STRICT ENVIRONMENT LOCKS (Must occur before importing marker)
# ==============================================================================
# Force Marker to use explicit boolean strings to disable the Docker sandbox
os.environ["MARKER_DISABLE_DOCKER"] = "true"
os.environ["DISABLE_DOCKER"] = "true"

# Optimize PyTorch memory for Colab's T4 GPU
os.environ["TORCH_DEVICE"] = "cuda"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import gc
import re
import json
import time
import shutil
import torch
from pypdf import PdfReader, PdfWriter
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


def sanitize_filename(text: str) -> str:
    if not text: return ""
    cleaned = re.sub(r"[^\w\s-]", "", str(text)).strip()
    return re.sub(r"[-\s]+", "_", cleaned)


def run_conversion():
    if len(sys.argv) < 3:
        print("Usage: python3 convert_textbook.py <INPUT_PDF> <OUTPUT_FOLDER> [OCR_LANG] [CHUNK_SIZE]")
        sys.exit(1)

    is_colab = os.path.exists("/content")
    drive_root = "/content/drive/MyDrive" if is_colab else os.getcwd()

    raw_input_path = sys.argv[1]
    raw_output_path = sys.argv[2]
    ocr_language = sys.argv[3] if len(sys.argv) > 3 else "en"
    chunk_size = int(sys.argv[4]) if len(sys.argv) > 4 else 50

    input_pdf = raw_input_path if os.path.isabs(raw_input_path) else os.path.join(drive_root, raw_input_path)
    output_dir = raw_output_path if os.path.isabs(raw_output_path) else os.path.join(drive_root, raw_output_path)

    if not os.path.exists(input_pdf):
        print(f"❌ Error: Input PDF not found at {input_pdf}")
        sys.exit(1)

    print("==================================================")
    print("🚀 Initializing Native PyTorch/Marker Pipeline")
    print("==================================================")
    if torch.cuda.is_available():
        print(f"✅ GPU Acceleration Active: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ Warning: CUDA device not detected. Running on CPU.")

    print(f"📥 Loading native vision models (Target Language: '{ocr_language}')...")
    model_dict = create_model_dict()

    # Configuration allows native VLM rendering of equations and tables without Docker
    converter_config = {
        "langs": [ocr_language],
        "disable_multiprocessing": True
    }
    converter = PdfConverter(artifact_dict=model_dict, config=converter_config)

    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    print(f"📖 Loaded document: {total_pages} total pages.")

    workspace = "/content" if is_colab else os.getcwd()
    temp_chunk_pdf = os.path.join(workspace, "temp_marker_slice.pdf")

    combined_text_segments = []
    combined_images = {}
    master_metadata = {}

    start_time = time.time()

    for start_page in range(0, total_pages, chunk_size):
        end_page = min(start_page + chunk_size, total_pages)
        print(f"\n🧩 Processing page slice: {start_page + 1} to {end_page} of {total_pages}...")

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
            print(f"⚠️ Chunk failure on pages {start_page + 1}-{end_page}: {chunk_err}")
            print("🔄 Falling back to single-page processing for isolated structural parsing...")

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
                    print(f"❌ PyTorch parsing bypassed on page {single_p + 1} ({p_err}). Reverting to PyPDF text layer.")
                    raw_text = reader.pages[single_p].extract_text() or ""
                    combined_text_segments.append(f"\n\n<!-- PyPDF Fallback: Page {single_p + 1} -->\n\n{raw_text}")
                finally:
                    if os.path.exists(single_pdf_path): os.remove(single_pdf_path)
        finally:
            if os.path.exists(temp_chunk_pdf): os.remove(temp_chunk_pdf)
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            gc.collect()

    elapsed = time.time() - start_time
    print(f"\n⏱️ Extraction complete in {elapsed:.2f}s. Assembling output...")

    title = sanitize_filename(master_metadata.get("title", ""))
    authors = master_metadata.get("authors", "")
    lastname = sanitize_filename(str(authors).split(",")[-1].split()[-1]) if authors else "UnknownAuthor"
    year = sanitize_filename(master_metadata.get("year", "0000")) or "0000"
    if not title: title = sanitize_filename(os.path.splitext(os.path.basename(input_pdf))[0])

    folder_name = f"{lastname}_{title}_{year}"
    local_build_dir = os.path.join(workspace, "marker_assembly_output")
    if os.path.exists(local_build_dir): shutil.rmtree(local_build_dir)
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

    final_destination = os.path.join(output_dir, folder_name)
    print(f"📂 Transferring artifacts to Google Drive: {final_destination}")
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(final_destination): shutil.rmtree(final_destination)
    shutil.copytree(local_build_dir, final_destination)
    shutil.rmtree(local_build_dir)

    print("🎉 Success! Text, math, and tables processed via PyTorch.")

if __name__ == "__main__":
    run_conversion()