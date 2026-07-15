import os
import glob
import shutil
import subprocess

# Look for the file directly in the flat /content root folder
COLAB_INPUT = "/content/textbook.pdf"
TEMP_OUT_DIR = "/content/marker_raw_output"
COLAB_OUTPUT_ZIP = "/content/output_package.zip"

def run_colab_automation():
    if not os.path.exists(COLAB_INPUT):
        print(f"❌ Error inside Colab: Input file not found at {COLAB_INPUT}")
        print("Available root items:", os.listdir("/content"))
        return

    # Clean up lingering data layers from previous loops in the session
    if os.path.exists(TEMP_OUT_DIR):
        shutil.rmtree(TEMP_OUT_DIR)
    if os.path.exists(COLAB_OUTPUT_ZIP):
        os.remove(COLAB_OUTPUT_ZIP)

    # Execute Marker at full scale using Colab's GPU
    command = [
        "marker_single",
        COLAB_INPUT,
        "--output_dir", TEMP_OUT_DIR
    ]

    print("🚀 Marker engine starting on Colab GPU...")
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)

    if result.returncode != 0:
        print(f"❌ Marker process failed internally: {result.stderr}")
        return

    # Locate the generated output folder
    generated_folders = glob.glob(os.path.join(TEMP_OUT_DIR, "*"))
    if not generated_folders:
        print("❌ Error: Marker finished but no output directories were generated.")
        return

    actual_output_path = generated_folders[0]

    # Zip the output folder (Markdown file + Graph Images Subfolder)
    print("📦 Archiving Markdown text and graph images...")
    zip_temp_path = "/content/temp_archive"
    shutil.make_archive(zip_temp_path, 'zip', actual_output_path)

    # Save directly as a native zip package
    shutil.move(f"{zip_temp_path}.zip", COLAB_OUTPUT_ZIP)
    print(f"🎉 Process complete. Package ready at: {COLAB_OUTPUT_ZIP}")

if __name__ == "__main__":
    run_colab_automation()
