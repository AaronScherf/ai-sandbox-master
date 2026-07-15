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

    hex_id = sys.argv
    workspace = "/content" if os.path.exists("/content") else os.getcwd()
    local_input = os.path.join(workspace, "textbook.pdf")

    # Keep the raw output local to the container to avoid Google Drive sync lag issues
    temp_out_dir = os.path.join(workspace, "marker_raw_output")
    final_output_zip = os.path.join(workspace, "output_package.zip")

    # Download the textbook file
    file_id = fetch_from_drive_hex(hex_id, local_input)

    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)
    if os.path.exists(final_output_zip):
        os.remove(final_output_zip)

    command = ["marker_single", local_input, "--output_dir", temp_out_dir]
    print(f"🚀 Marker engine starting on Cloud GPU for Book_{file_id}...")

    # Use Popen to actively read logs and keep the terminal connection alive
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    last_ping = time.time()
    for line in process.stdout:
        print(line, end="")
        # Force a terminal text print every 30 seconds to prevent Jupyter connection timeouts
        if time.time() - last_ping > 30:
            print(f"\n[Keep-Alive Ping] Script is active. Processing math page grids...", flush=True)
            last_ping = time.time()

    process.wait()

    if process.returncode != 0:
        print(f"❌ Marker process failed internally with exit code {process.returncode}")
        return

    # Locate the generated output folder inside the container
    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: No output directories generated.")
        return

    actual_output_path = generated_folders[0]  # Safely target the inner string path

    print(f"📦 Compressing assets inside: {actual_output_path}")
    # Package into a single zip file local to the container workspace folder
    shutil.make_archive(os.path.join(workspace, "temp_archive"), 'zip', actual_output_path)
    shutil.move(os.path.join(workspace, "temp_archive.zip"), final_output_zip)
    print(f"🎉 Complete! Package 'output_package.zip' is compiled and ready for retrieval.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()
    run_conversion()
