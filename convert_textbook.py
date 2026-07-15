import os
import glob
import shutil
import subprocess
import time
import sys

def install_remote_dependencies():
    """Ensures the cloud instance has Marker installed before execution."""
    print("📦 Bootstrapping cloud instance environment packages...")
    try:
        # Install system-level dependencies for rendering
        subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["apt-get", "install", "-y", "poppler-utils", "tesseract-ocr", "libgl1", "libglx-mesa0"], check=True, stdout=subprocess.DEVNULL)

        # Install python packages using the bundled pip tool
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-m", "pip", "install", "marker-pdf", "pypdf"], check=True, stdout=subprocess.DEVNULL)
        print("✅ Environment successfully configured.")
    except Exception as e:
        print(f"⚠️ Warning during packaging: {e}. Attempting execution anyway...")

def run_conversion():
    # Read the file path dynamically passed from the CLI
    if len(sys.argv) < 2:
        print("❌ Error: Missing input file argument.")
        print("Usage: python convert_textbook.py <path_to_pdf>")
        return

    local_input = os.path.abspath(sys.argv[1])
    workspace = "/content" if os.path.exists("/content") else os.getcwd()


    temp_out_dir = os.path.join(workspace, "marker_raw_output")
    final_output_zip = os.path.join(workspace, "output_package.zip")

    if not os.path.exists(local_input):
        print(f"❌ Error inside runner: Input file not found at {local_input}")
        print("Current Workspace location:", workspace)
        print("Files present in execution scope:", os.listdir(os.path.dirname(local_input) if os.path.dirname(local_input) else "."))
        return

    # Clean up previous temporary paths
    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)
    if os.path.exists(final_output_zip):
        os.remove(final_output_zip)

    # Execute Marker at full scale using the cloud GPU framework
    command = [
        "marker_single",
        local_input,
        "--output_dir", temp_out_dir
    ]

    print(f"🚀 Marker engine starting on Cloud GPU for: {os.path.basename(local_input)}")
    start_time = time.time()

    # Stream the output process in real-time
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end="")
    process.wait()

    if process.returncode != 0:
        print(f"❌ Marker process failed internally with exit code {process.returncode}")
        return

    # Locate the generated output folder
    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: Marker finished but no output directories were generated.")
        return

    actual_output_path = generated_folders[0]

    # Zip the output folder (Markdown text + Graph Images Folder)
    print("📦 Archiving Markdown text and graph images...")
    shutil.make_archive(os.path.join(workspace, "temp_archive"), 'zip', actual_output_path)

    # Save directly as a native zip package
    shutil.move(os.path.join(workspace, "temp_archive.zip"), final_output_zip)
    print(f"🎉 Process complete. Package ready for automatic artifact retrieval.")

if __name__ == "__main__":
    if os.path.exists("/content"):
        install_remote_dependencies()

    run_conversion()
