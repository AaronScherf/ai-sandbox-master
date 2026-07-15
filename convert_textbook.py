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

def run_conversion():
    if len(sys.argv) < 3:
        print("❌ Error: Missing required path arguments.")
        print("Usage: colab run convert_textbook.py <RELATIVE_INPUT_PDF_PATH> <RELATIVE_OUTPUT_FOLDER_PATH>")
        print("Example: colab run convert_textbook.py 'Books/math.pdf' 'Processed/Calculus'")
        return

    # 1. Mount Google Drive securely inside the cloud container
    if os.path.exists("/content"):
        print("🔐 Mounting Google Drive storage space securely...")
        from google.colab import drive
        drive.mount('/content/drive', force_remount=True)

    # Define the root of your MyDrive space
    drive_root = "/content/drive/MyDrive" if os.path.exists("/content") else os.getcwd()

    # Read the text paths directly from your terminal arguments
    input_relative_path = sys.argv[1]
    output_relative_path = sys.argv[2]

    # Combine paths to target your true Google Drive storage layouts
    absolute_input_pdf = os.path.join(drive_root, input_relative_path)
    absolute_output_dir = os.path.join(drive_root, output_relative_path)

    # Temporary working directory local to the container to avoid network sync lag
    workspace = "/content" if os.path.exists("/content") else os.getcwd()
    temp_out_dir = os.path.join(workspace, "marker_raw_output")

    if not os.path.exists(absolute_input_pdf):
        print(f"❌ Error: Could not find your textbook inside Google Drive at: {absolute_input_pdf}")
        return

    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)

    # 2. Execute Marker at full scale using the cloud GPU
    command = ["marker_single", absolute_input_pdf, "--output_dir", temp_out_dir]
    print(f"🚀 Marker engine starting on Cloud GPU for: {os.path.basename(absolute_input_pdf)}")

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

    # 3. Locate the generated output folder inside the container
    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: No output assets generated.")
        return
    actual_output_path = generated_folders[0]

    # 4. Copy the raw unzipped Markdown and image folders straight into your target Drive path
    book_folder_name = os.path.splitext(os.path.basename(absolute_input_pdf))[0]
    final_destination = os.path.join(absolute_output_dir, f"Processed_{book_folder_name}")

    print(f"📂 Saving assets directly to Google Drive directory: {final_destination}")
    os.makedirs(absolute_output_dir, exist_ok=True)
    if os.path.exists(final_destination):
        shutil.rmtree(final_destination)

    shutil.copytree(actual_output_path, final_destination)
    print(f"\n🎉 Success! Your Markdown files and graphics folders are securely stored in your Drive.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()
    run_conversion()
