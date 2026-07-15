import os
import glob
import shutil
import subprocess
import time
import sys

def install_remote_dependencies():
    print("📦 Bootstrapping cloud instance environment packages...")
    try:
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "poppler-utils", "tesseract-ocr", "libgl1", "libglx-mesa0"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["apt-get", "clean"], stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "marker-pdf", "pypdf"], check=True, stdout=subprocess.DEVNULL)
        print("✅ Environment successfully configured.")
    except Exception as e:
        print(f"⚠️ Warning during packaging: {e}.")

def fetch_from_drive_hex(hex_id, target_path):
    try:
        file_id = bytes.fromhex(hex_id).decode('utf-8')
        print(f"📡 Downloading textbook asset via gdown...")
        command = ["gdown", "--id", file_id, "-O", target_path]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to download from Drive: {result.stderr}")
            sys.exit(1)
        return file_id
    except Exception as decode_err:
        print(f"❌ Token hex processing failure: {decode_err}")
        sys.exit(1)

def run_conversion():
    if len(sys.argv) < 2:
        print("❌ Error: Missing Hex-Encoded Google Drive ID.")
        return

    hex_id = sys.argv[1]
    workspace = "/content" if os.path.exists("/content") else os.getcwd()
    local_input = os.path.join(workspace, "textbook.pdf")
    temp_out_dir = os.path.join(workspace, "marker_raw_output")

    # 1. Mount Google Drive explicitly if running in Colab
    # This exposes your Drive at /content/drive/MyDrive
    drive_target_dir = "/content/drive/MyDrive/academic_resources/processed_textbooks"

    # Fallback to local if running outside of Colab context
    if not os.path.exists("/content"):
        drive_target_dir = os.path.join(workspace, "output")

    # Download the file and get the clean string ID
    file_id = fetch_from_drive_hex(hex_id, local_input)

    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)

    # 2. Run Marker at full scale
    command = ["marker_single", local_input, "--output_dir", temp_out_dir]
    print(f"🚀 Marker engine starting on Cloud GPU...")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()

    if process.returncode != 0:
        print(f"❌ Marker process failed internally with exit code {process.returncode}")
        return

    # 3. Locate the generated output folder
    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: No output directories generated.")
        return
    actual_output_path = generated_folders[0]

    # 4. Copy the unzipped raw markdown and image subfolders straight into Google Drive
    final_book_folder = os.path.join(drive_target_dir, f"Book_{file_id}")
    print(f"📂 Saving assets directly to Google Drive folder: {final_book_folder}")

    if os.path.exists(final_book_folder):
        shutil.rmtree(final_book_folder)

    shutil.copytree(actual_output_path, final_book_folder)
    print(f"🎉 Complete! Markdown file and extracted graph images are securely stored in your Drive.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()
    run_conversion()
