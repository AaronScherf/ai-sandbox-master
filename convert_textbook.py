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

def decode_hex_string(hex_str, context_name):
    try:
        return bytes.fromhex(hex_str).decode('utf-8')
    except Exception as e:
        print(f"❌ Error decoding hex string for {context_name}: {e}")
        sys.exit(1)

def run_conversion():
    if len(sys.argv) < 3:
        print("❌ Error: Missing required arguments.")
        print("Usage: colab run convert_textbook.py <HEX_FILE_ID> <HEX_FOLDER_ID>")
        return

    # Extract both arguments from the script parameters
    hex_file_id = sys.argv[1]
    hex_folder_id = sys.argv[2]

    # Safely restore case-sensitive IDs from the lowercase hex strings
    file_id = decode_hex_string(hex_file_id, "File ID")
    folder_id = decode_hex_string(hex_folder_id, "Folder ID")

    workspace = "/content" if os.path.exists("/content") else os.getcwd()
    local_input = os.path.join(workspace, "textbook.pdf")
    temp_out_dir = os.path.join(workspace, "marker_raw_output")

    print(f"📡 Downloading textbook asset via gdown...")
    download_cmd = ["gdown", "--id", file_id, "-O", local_input]
    if subprocess.run(download_cmd).returncode != 0:
        print("❌ Failed to download textbook from Drive.")
        sys.exit(1)

    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)

    # 1. Execute Marker at full scale using the cloud GPU
    command = ["marker_single", local_input, "--output_dir", temp_out_dir]
    print(f"🚀 Marker engine starting on Cloud GPU for Book_{file_id}...")

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    last_ping = time.time()
    for line in process.stdout:
        print(line, end="")
        if time.time() - last_ping > 30:
            print(f"\n[Keep-Alive Ping] Script is active. Processing math page grids...", flush=True)
            last_ping = time.time()

    process.wait()

    if process.returncode != 0:
        print(f"❌ Marker process failed internally with exit code {process.returncode}")
        return

    # 2. Locate the generated output folder inside the container
    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: No output directories generated.")
        return
    actual_output_path = generated_folders[0]

    # 3. Zip the final results inside the container workspace
    print("📦 Packing Markdown text and graph images into deployment archive...")
    local_zip_base = os.path.join(workspace, f"Book_{file_id}")
    shutil.make_archive(local_zip_base, 'zip', actual_output_path)
    final_local_zip = f"{local_zip_base}.zip"

    # 4. Upload the completed zip package directly into your target Google Drive folder!
    print(f"⬆️ Shifting final asset package up to Google Drive target folder (ID: {folder_id})...")
    upload_cmd = ["gdown", final_local_zip, "--folder", folder_id]

    if subprocess.run(upload_cmd).returncode == 0:
        print("\n" + "="*50)
        print("🎉 Complete! Conversion finished successfully.")
        print(f"📁 Asset package uploaded securely to your custom Google Drive directory.")
        print("="*50)
    else:
        print("❌ Error uploading final zip package to your target Google Drive folder.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()
    run_conversion()
