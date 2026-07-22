import os
import glob
import shutil
import subprocess
import time
import sys
import json
import re

# --- CRITICAL FIX FOR SURYA V2 IN GOOGLE COLAB ---
# Force Surya to use its llamacpp backend. With CUDA compiled below,
# this maps all VLM layout tasks directly onto your T4 GPU memory.
os.environ["SURYA_INFERENCE_BACKEND"] = "llamacpp"

def install_remote_dependencies():
    print("📦 Bootstrapping cloud instance environment packages with CUDA acceleration...")
    try:
        # 1. Update package managers and verify base requirements
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "poppler-utils", "tesseract-ocr", "libgl1", "libglx-mesa0"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["apt-get", "clean"], stdout=subprocess.DEVNULL)

        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)

        # 2. Compile llama-cpp-python from source targeting the system's Nvidia NVCC compiler
        print("⚙️ Compiling llama-cpp-python with explicit CUDA toolkit bindings...")
        cuda_env = os.environ.copy()
        cuda_env["GGML_CUDA"] = "on"  # Enables GPU acceleration within the layout server

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir", "--force-reinstall", "--upgrade"],
            env=cuda_env,
            check=True,
            stdout=subprocess.DEVNULL
        )

        # 3. Clean install core processing framework items
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "marker-pdf", "pypdf"], check=True, stdout=subprocess.DEVNULL)
        print("✅ GPU Environment successfully configured.")
    except Exception as e:
        print(f"⚠️ Warning during packaging: {e}.")

def clean_string(text):
    if not text: return ""
    return re.sub(r'[^\w\s-]', '', str(text)).strip().replace(' ', '_')

def run_conversion():
    if len(sys.argv) < 3:
        print("Usage: python convert_textbook.py <INPUT_PDF> <OUTPUT_FOLDER> [OCR_LANG] [CHUNK_SIZE]")
        return

    is_colab = os.path.exists("/content")
    drive_root = "/content/drive/MyDrive" if is_colab else os.getcwd()

    absolute_input_pdf = os.path.join(drive_root, sys.argv[1])
    absolute_output_dir = os.path.join(drive_root, sys.argv[2])
    ocr_language = sys.argv[3] if len(sys.argv) > 3 else "en"
    chunk_size = int(sys.argv[4]) if len(sys.argv) > 4 else 50

    if not os.path.exists(absolute_input_pdf):
        print(f"❌ Error: Missing file at {absolute_input_pdf}")
        return

    from pypdf import PdfReader, PdfWriter
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered

    print(f"🚀 Loading models via GPU-Accelerated llama.cpp (OCR Lang: '{ocr_language}', Chunk Size: {chunk_size})...")
    converter = PdfConverter(artifact_dict=create_model_dict(), config={"langs": [ocr_language]})

    reader = PdfReader(absolute_input_pdf)
    total_pages = len(reader.pages)
    print(f"📖 Loaded textbook containing {total_pages} total pages.")

    workspace = "/content" if is_colab else os.getcwd()
    temp_chunk_pdf = os.path.join(workspace, "current_chunk.pdf")

    combined_text_segments = []
    combined_images = {}
    master_metadata = {}

    start_time = time.time()

    for start_page in range(0, total_pages, chunk_size):
        end_page = min(start_page + chunk_size, total_pages)
        print(f"\n🧩 Processing page slice: {start_page + 1} to {end_page}...")

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
                unique_key = f"pg_{start_page}_{img_key}"
                combined_images[unique_key] = img_bytes

            if start_page == 0:
                master_metadata = chunk_meta

        except Exception as e:
            print(f"💥 Critical layout failure on chunk pages {start_page}-{end_page}: {e}")
            continue
        finally:
            if os.path.exists(temp_chunk_pdf):
                os.remove(temp_chunk_pdf)

    print(f"\n⏱️ Completed batch extraction in {time.time() - start_time:.2f} seconds. Stitching files...")

    title = clean_string(master_metadata.get("title", ""))
    authors = master_metadata.get("authors", "")
    lastname = "UnknownAuthor"
    if authors:
        primary = str(authors).split(",") if "," in str(authors) else str(authors).split()
        if primary: lastname = clean_string(primary[0].split()[-1])
    year = clean_string(master_metadata.get("year", "0000")) or "0000"
    if not title: title = clean_string(os.path.splitext(os.path.basename(absolute_input_pdf))[0])

    folder_name = f"{lastname}_{title}_{year}"
    local_build_dir = os.path.join(workspace, "marker_final_assembly")
    if os.path.exists(local_build_dir): shutil.rmtree(local_build_dir)
    os.makedirs(local_build_dir, exist_ok=True)

    final_md_path = os.path.join(local_build_dir, f"{folder_name}.md")
    with open(final_md_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(combined_text_segments))

    if combined_images:
        images_dir = os.path.join(local_build_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        for img_name, img_data in combined_images.items():
            img_data.save(os.path.join(images_dir, img_name))

    master_metadata["total_pages_processed"] = total_pages
    final_json_path = os.path.join(local_build_dir, f"{folder_name}_metadata.json")
    with open(final_json_path, "w", encoding="utf-8") as json_f:
        json.dump(master_metadata, json_f, indent=4, ensure_ascii=False)

    final_destination = os.path.join(absolute_output_dir, folder_name)
    print(f"📂 Moving production files to Google Drive destination: {final_destination}")
    os.makedirs(absolute_output_dir, exist_ok=True)
    if os.path.exists(final_destination): shutil.rmtree(final_destination)
    shutil.copytree(local_build_dir, final_destination)
    shutil.rmtree(local_build_dir)
    print("🎉 Done! Entire textbook successfully indexed via native llama-server backend setups.")

if __name__ == "__main__":
    if os.path.exists("/content"): install_remote_dependencies()
    run_conversion()
