import os
import glob
import shutil
import subprocess
import time
import sys
import json
import re

# Import Marker components directly
try:
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models  # (or create_model_dict depending on version)
    from marker.output import save_markdown
except ImportError:
    pass

def install_remote_dependencies():
    print("📦 Bootstrapping cloud instance environment packages...")
    try:
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "poppler-utils", "tesseract-ocr", "libgl1", "libglx-mesa0"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["apt-get", "clean"], stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)
        # Force a specific version if required, otherwise standard install
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "marker-pdf", "pypdf"], check=True, stdout=subprocess.DEVNULL)
        print("✅ Environment successfully configured.")
    except Exception as e:
        print(f"⚠️ Warning during packaging: {e}.")

def clean_string(text):
    """Helper to sanitize text for directory and file names."""
    if not text:
        return ""
    return re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '_')

def run_conversion():
    if len(sys.argv) < 3:
        print("❌ Error: Missing required path arguments.")
        print("Usage: python convert_textbook.py <RELATIVE_INPUT_PDF_PATH> <RELATIVE_OUTPUT_FOLDER_PATH>")
        return

    # Check for Colab execution environment
    is_colab = os.path.exists("/content")
    drive_root = "/content/drive/MyDrive" if is_colab else os.getcwd()

    input_relative_path = sys.argv[1]
    output_relative_path = sys.argv[2]

    absolute_input_pdf = os.path.join(drive_root, input_relative_path)
    absolute_output_dir = os.path.join(drive_root, output_relative_path)

    if not os.path.exists(absolute_input_pdf):
        print(f"❌ Error: Could not find your textbook inside Google Drive at: {absolute_input_pdf}")
        return

    # Now that marker-pdf is guaranteed to be installed, import modules safely
    from marker.convert import convert_single_pdf
    from marker.models import load_all_models
    from marker.output import save_markdown

    print(f"🚀 Loading Deep Learning Models onto GPU...")
    # load_all_models() automatically places weights on your Colab GPU instance
    model_lst = load_all_models()

    print(f"⏳ Executing Marker native conversion pipeline for: {os.path.basename(absolute_input_pdf)}")
    start_time = time.time()

    # Run native conversion. Returns markdown text, image dict, and metadata dict
    full_text, images, out_metadata = convert_single_pdf(absolute_input_pdf, model_lst)

    print(f"⏱️ Model processing finished in {time.time() - start_time:.2f} seconds.")

    # 1. Safely extract metadata fields natively discovered by Marker's VLM models
    title = clean_string(out_metadata.get("title", ""))
    authors = out_metadata.get("authors", [])

    lastname = "UnknownAuthor"
    if authors:
        # Take the first author's last name
        primary_author = authors[0].split()
        if primary_author:
            lastname = clean_string(primary_author[-1])

    year = clean_string(str(out_metadata.get("year", "0000")))
    if year == "":
        year = "0000"

    # Default fallback string assembly if metadata fields came back blank
    if not title:
        title = clean_string(os.path.splitext(os.path.basename(absolute_input_pdf))[0])

    folder_name = f"{lastname}_{title}_{year}"
    final_destination = os.path.join(absolute_output_dir, folder_name)

    # 2. Local workspace creation to prevent network speed bottleneck drops on Drive
    workspace = "/content" if is_colab else os.getcwd()
    local_temp_dir = os.path.join(workspace, "marker_working_build")

    if os.path.exists(local_temp_dir):
        shutil.rmtree(local_temp_dir)
    os.makedirs(local_temp_dir, exist_ok=True)

    # 3. Save standard outputs locally using Marker utility frameworks
    # This writes out the .md asset alongside a subfolder containing your math/image crops
    save_markdown(local_temp_dir, folder_name, full_text, images, out_metadata)

    # 4. Copy the compiled local folder build to its final destination in Drive
    print(f"📂 Saving assets directly to Google Drive directory: {final_destination}")
    os.makedirs(absolute_output_dir, exist_ok=True)
    if os.path.exists(final_destination):
        shutil.rmtree(final_destination)

    shutil.copytree(local_temp_dir, final_destination)

    # Cleanup temporary local instance workspace build items
    shutil.rmtree(local_temp_dir)
    print(f"\n🎉 Success! Your Markdown files and graphics folders are securely stored in your Drive.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()
    run_conversion()
