import os
import glob
import subprocess
import zipfile

# Configuration
PDF_DIR = "./app/data"
OUTPUT_DIR = "./output"
REMOTE_INPUT = "textbook.pdf"
REMOTE_OUTPUT = "output_package.zip"  # Now explicitly tracking the .zip file
CONVERSION_SCRIPT = "convert_textbook.py"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Starting Colab session...")
subprocess.run(["colab", "new", "--gpu", "T4"], check=True)

# Upload the conversion script once to the Colab session root environment
print("Uploading conversion script to Colab root...")
subprocess.run(["colab", "upload", CONVERSION_SCRIPT, CONVERSION_SCRIPT], check=True)

pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))

for pdf_path in pdf_files:
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"\n--- Processing: {base_name}.pdf ---")

    try:
        print("Uploading PDF to Colab...")
        subprocess.run(["colab", "upload", pdf_path, REMOTE_INPUT], check=True)

        print("Running conversion script on Colab...")
        subprocess.run(["colab", "exec", "-f", CONVERSION_SCRIPT], check=True)

        # Define paths for downloading and extracting
        local_zip_path = os.path.join(OUTPUT_DIR, f"{base_name}.zip")
        local_extract_folder = os.path.join(OUTPUT_DIR, base_name)

        print(f"Downloading archive package to {local_zip_path}...")
        subprocess.run(["colab", "download", REMOTE_OUTPUT, local_zip_path], check=True)

        # Automatically extract the folder contents locally
        print(f"Unzipping contents into: {local_extract_folder}/")
        os.makedirs(local_extract_folder, exist_ok=True)
        with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
            zip_ref.extractall(local_extract_folder)

        # Clean up the local temporary zip file to keep storage tidy
        os.remove(local_zip_path)

        print(f"✅ Successfully processed, downloaded, and extracted {base_name}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing {base_name}. Stopping batch. Error: {e}")
        break

print("\nBatch processing complete. Check your './output/' directory for extracted book folders.")
