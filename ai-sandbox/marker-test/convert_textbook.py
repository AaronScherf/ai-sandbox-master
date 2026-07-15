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
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-m", "pip", "install", "marker-pdf", "pypdf"], check=True, stdout=subprocess.DEVNULL)
        print("✅ Environment successfully configured.")
    except Exception as e:
        print(f"⚠️ Warning during packaging: {e}.")

def fetch_from_drive_hex(hex_id, target_path):
    """Decodes the lowercase Hex ID back into the exact case-sensitive Drive ID."""
    try:
        # Convert the lowercase hex string back into the exact case-sensitive File ID
        file_id = bytes.fromhex(hex_id).decode('utf-8')

        print(f"📡 Successfully restored case-sensitive Drive ID via Hex decoding.")
        print(f"Downloading textbook asset via gdown...")

        # Native gdown syntax using the clean --id flag
        command = ["gdown", "--id", file_id, "-O", target_path]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Textbook successfully downloaded from Drive.")
        else:
            print(f"❌ Failed to download from Drive: {result.stderr}")
            sys.exit(1)
    except Exception as decode_err:
        print(f"❌ Token hex processing failure: {decode_err}")
        sys.exit(1)

def run_conversion():
    if len(sys.argv) < 2:
        print("❌ Error: Missing Hex-Encoded Google Drive ID.")
        print("Usage: colab run convert_textbook.py <HEX_ID_STRING>")
        return

    hex_id = sys.argv[1]
    workspace = "/content" if os.path.exists("/content") else os.getcwd()
    local_input = os.path.join(workspace, "textbook.pdf")
    temp_out_dir = os.path.join(workspace, "marker_raw_output")
    final_output_zip = os.path.join(workspace, "output_package.zip")

    # Decode the hex string and pull the file
    fetch_from_drive_hex(hex_id, local_input)

    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)
    if os.path.exists(final_output_zip):
        os.remove(final_output_zip)

    command = ["marker_single", local_input, "--output_dir", temp_out_dir]
    print(f"🚀 Marker engine starting on Cloud GPU...")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()

    if process.returncode != 0:
        print(f"❌ Marker process failed internally with exit code {process.returncode}")
        return

    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: No output directories generated.")
        return

    shutil.make_archive(os.path.join(workspace, "temp_archive"), 'zip', generated_folders)
    shutil.move(os.path.join(workspace, "temp_archive.zip"), final_output_zip)
    print(f"🎉 Process complete. Package ready for automatic retrieval.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()
    run_conversion()
