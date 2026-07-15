import os
import glob
import subprocess
import zipfile
import re

# Configuration
PDF_DIR = "./app/data"
OUTPUT_DIR = "./output"
REMOTE_INPUT = "textbook.pdf"
REMOTE_OUTPUT = "output_package.zip"
CONVERSION_SCRIPT = "convert_textbook.py"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- REUSABLE SESSION LOGIC ---
print("Checking for existing, reusable Colab sessions...")
session_id = None

# Query the official CLI for currently running container sessions
list_result = subprocess.run(["colab", "sessions"], capture_output=True, text=True)
active_sessions = re.findall(r"([a-f0-9]{6,8})", list_result.stdout)

if active_sessions:
    session_id = active_sessions[0]
    print(f"🔄 Found an active cloud instance! Reusing Session ID: {session_id}")
else:
    print("✨ No active sessions found. Requesting a new T4 GPU allocation from Google...")
    try:
        new_result = subprocess.run(["colab", "new", "--gpu", "T4"], capture_output=True, text=True, check=True)
        print(new_result.stdout)

        session_match = re.search(r"session '([a-f0-9]+)'", new_result.stdout)
        if session_match:
            session_id = session_match.group(1)
        else:
            print("❌ Critical: Failed to parse a valid session ID string from Colab CLI.")
            exit(1)
    except subprocess.CalledProcessError as e:
        print("\n❌ Google Colab GPU Allocation Limit Reached! Wait 5 minutes for a reset.\n")
        exit(1)

print(f"🎯 Connected to Session: {session_id}")

# Upload the conversion script to the workspace
print("Syncing execution dependencies to remote server...")
subprocess.run(["colab", "upload", "-s", session_id, CONVERSION_SCRIPT, CONVERSION_SCRIPT], check=True)

# Find all textbooks in the folder
pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))

for pdf_path in pdf_files:
    # Extract the clean file base name (e.g. 'textbook')
    file_base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n--- Processing: {file_base_name}.pdf ---")

    try:
        print("Uploading PDF to Colab...")
        # Uploading the exact relative path preserves the folder structural integrity inside Colab
        subprocess.run(["colab", "upload", "-s", session_id, pdf_path, pdf_path], check=True)

        print("Running conversion script on Colab GPU...")
        subprocess.run(["colab", "exec", "-s", session_id, "-f", CONVERSION_SCRIPT], check=True)

        # Paths for local file organization
        local_zip_path = os.path.join(OUTPUT_DIR, f"{file_base_name}.zip")
        local_extract_folder = os.path.join(OUTPUT_DIR, file_base_name)

        print("Downloading archive package...")
        subprocess.run(["colab", "download", "-s", session_id, REMOTE_OUTPUT, local_zip_path], check=True)

        print(f"Extracting contents into local space: {local_extract_folder}/")
        os.makedirs(local_extract_folder, exist_ok=True)
        with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
            zip_ref.extractall(local_extract_folder)

        # Clean up local temporary file block
        os.remove(local_zip_path)
        print(f"✅ Successfully extracted complete assets for: {file_base_name}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing {file_base_name}. Stopping batch loop execution. Error: {e}")
        break

print("\nBatch pipeline finished. Keeping the Colab session open for your next execution run.")
