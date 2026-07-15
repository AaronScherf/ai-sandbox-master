import os
import glob
import shutil
import subprocess
import time

def run_conversion():
    # Use standard relative parameters provided by the local workspace
    local_input = "./app/data/textbook.pdf"
    temp_out_dir = "./marker_raw_output"
    final_output_zip = "./output_package.zip"

    if not os.path.exists(local_input):
        print(f"❌ Error inside runner: Input file not found at {local_input}")
        return

    # Clean up previous temporary layers
    if os.path.exists(temp_out_dir):
        shutil.rmtree(temp_out_dir)
    if os.path.exists(final_output_zip):
        os.remove(final_output_zip)

    # 1. Execute Marker at full scale using the cloud GPU framework
    command = [
        "marker_single",
        local_input,
        "--output_dir", temp_out_dir
    ]

    print("🚀 Marker engine starting on Cloud GPU...")
    start_time = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)

    if result.returncode != 0:
        print(f"❌ Marker process failed internally: {result.stderr}")
        return

    # 2. Locate the generated output folder
    generated_folders = glob.glob(os.path.join(temp_out_dir, "*"))
    if not generated_folders:
        print("❌ Error: Marker finished but no output directories were generated.")
        return

    actual_output_path = generated_folders[0]

    # 3. Zip the output folder (Markdown text + Graph Images Folder)
    print("📦 Archiving Markdown text and graph images...")
    shutil.make_archive("./temp_archive", 'zip', actual_output_path)

    # 4. Save directly as a native zip package
    shutil.move("./temp_archive.zip", final_output_zip)
    print(f"🎉 Process complete. Package ready for automatic artifact retrieval.")

if __name__ == "__main__":
    run_conversion()
