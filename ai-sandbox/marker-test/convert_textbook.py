#!/usr/bin/env python3
"""
convert_textbook.py
Extracts textbook-length PDFs into structured Markdown and images using Marker
accelerated via PyTorch CUDA on Google Colab.
"""

import os
import sys
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
    """Sanitize strings for filesystem safety."""
    if not text:
        return ""
    # Strip non-alphanumeric characters, replace whitespace with underscores
    cleaned = re.sub(r"[^\w\s-]", "", str(text)).strip()
    return re.sub(r"[-\s]+", "_", cleaned)


def run_conversion():
    if len(sys.argv) < 3:
        print("Usage: python3 convert_textbook.py <INPUT_PDF_PATH> <OUTPUT_FOLDER_PATH> [OCR_LANG] [CHUNK_SIZE]")
        sys.exit(1)

    # Resolve Drive paths within Google Colab
    is_colab = os.path.exists("/content")
    drive_root = "/content/drive/MyDrive" if is_colab else os.getcwd()

    raw_input_path = sys.argv[1]
    raw_output_path = sys.argv[2]
    ocr_language = sys.argv[3] if len(sys.argv) > 3 else "en"
    chunk_size = int(sys.argv[4]) if len(sys.argv) > 4 else 50

    # Ensure paths resolve properly relative to Drive root if not absolute
    input_pdf = raw_input_path if os.path.isabs(raw_input_path) else os.path.join(drive_root, raw_input_path)
    output_dir = raw_output_path if os.path.isabs(raw_output_path) else os.path.join(drive_root, raw_output_path)

    if not os.path.exists(input_pdf):
        print(f"❌ Critical Error: Input PDF not found at target: {input_pdf}")
        sys.exit(1)

    # Log device capabilities
    print("==================================================")
    print("🚀 Initializing Marker PDF Conversion Pipeline")
    print("==================================================")
    if torch.cuda.is_available():
        print(f"✅ GPU Acceleration Active: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM Allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
    else:
        print("⚠️ Warning: CUDA device not detected. Falling back to CPU execution.")

    # Initialize Marker conversion models
    print(f"📥 Loading models into memory (Target OCR Language: '{ocr_language}')...")
    model_dict = create_model_dict()
    converter = PdfConverter(
        artifact_dict=model_dict,
        config={"langs": [ocr_language]}
    )

    # Read input document structure
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    print(f"📖 Loaded document: {total_pages} total pages to process.")

    workspace = "/content" if is_colab else os.getcwd()
    temp_chunk_pdf = os.path.join(workspace, "temp_marker_slice.pdf")

    combined_text_segments = []
    combined_images = {}
    master_metadata = {}

    start_time = time.time()

    # Process document in slices to manage VRAM pressure
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

            # Preserve and namespace images extracted in this batch
            for img_key, img_bytes in chunk_images.items():
                unique_key = f"pg_{start_page + 1}_{img_key}"
                combined_images[unique_key] = img_bytes

            # Capture primary metadata from the initial block
            if start_page == 0 and chunk_meta:
                master_metadata = chunk_meta

        except Exception as e:
            print(f"⚠️ Error encountered while processing pages {start_page + 1}-{end_page}: {e}")
        finally:
            if os.path.exists(temp_chunk_pdf):
                os.remove(temp_chunk_pdf)
            
            # Explicit garbage collection and CUDA cache clearing to prevent OOM
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    elapsed_time = time.time() - start_time
    print(f"\n⏱️ Extraction complete in {elapsed_time:.2f}s ({elapsed_time / 60:.2f} min). Assembling artifact...")

    # Derive standardized naming structure
    title = sanitize_filename(master_metadata.get("title", ""))
    authors = master_metadata.get("authors", "")
    lastname = "UnknownAuthor"
    if authors:
        primary = str(authors).split(",") if "," in str(authors) else str(authors).split()
        if primary:
            lastname = sanitize_filename(primary[-1].split()[-1])
            
    year = sanitize_filename(master_metadata.get("year", "0000")) or "0000"
    if not title:
        title = sanitize_filename(os.path.splitext(os.path.basename(input_pdf))[0])

    folder_name = f"{lastname}_{title}_{year}"
    local_build_dir = os.path.join(workspace, "marker_assembly_output")
    
    if os.path.exists(local_build_dir):
        shutil.rmtree(local_build_dir)
    os.makedirs(local_build_dir, exist_ok=True)

    # 1. Output combined Markdown document
    final_md_path = os.path.join(local_build_dir, f"{folder_name}.md")
    with open(final_md_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(combined_text_segments))

    # 2. Output extracted figures/images
    if combined_images:
        images_dir = os.path.join(local_build_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        for img_name, img_data in combined_images.items():
            img_data.save(os.path.join(images_dir, img_name))

    # 3. Output metadata JSON
    master_metadata["total_pages_processed"] = total_pages
    master_metadata["processing_time_seconds"] = round(elapsed_time, 2)
    final_json_path = os.path.join(local_build_dir, f"{folder_name}_metadata.json")
    with open(final_json_path, "w", encoding="utf-8") as json_f:
        json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)

    # Transfer assembled build to Google Drive
    final_destination = os.path.join(output_dir, folder_name)
    print(f"📂 Transferring artifacts to Google Drive: {final_destination}")
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(final_destination):
        shutil.rmtree(final_destination)
    shutil.copytree(local_build_dir, final_destination)
    shutil.rmtree(local_build_dir)

    print("🎉 Success! Conversion finished and synchronized with Google Drive.")


if __name__ == "__main__":
    run_conversion()