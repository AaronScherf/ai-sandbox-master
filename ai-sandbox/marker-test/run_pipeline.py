import os
import time
import subprocess
from pypdf import PdfReader, PdfWriter


def calculate_dynamic_chunk_size(input_path):
    """Calculates the optimal chunk size based on file size density per page."""
    file_size_bytes = os.path.getsize(input_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)

    # Calculate MB density per page
    mb_per_page = file_size_mb / total_pages

    print(f"--- Document Analysis ---")
    print(f"Total File Size: {file_size_mb:.2f} MB")
    print(f"Total Pages: {total_pages}")
    print(f"Density: {mb_per_page:.3f} MB per page")

    # Dynamic logic based on visual/data density per page
    if mb_per_page > 0.5:
        chunk_size = 20
        print("-> Detected heavy/high-res scans. Setting cautious chunk size: 20 pages.")
    elif mb_per_page > 0.15:
        chunk_size = 50
        print("-> Detected standard scanned text. Setting standard chunk size: 50 pages.")
    else:
        chunk_size = 100
        print("-> Detected lightweight/optimized text. Setting fast chunk size: 100 pages.")

    return total_pages, chunk_size


def split_pdf(input_path):
    total_pages, chunk_size = calculate_dynamic_chunk_size(input_path)

    os.makedirs("/app/chunks", exist_ok=True)
    chunk_paths = []

    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        for page_num in range(i, min(i + chunk_size, total_pages)):
            writer.add_page(reader.pages[page_num])

        chunk_name = f"/app/chunks/chunk_{i//chunk_size}.pdf"
        with open(chunk_name, "wb") as f:
            writer.write(f)
        chunk_paths.append(chunk_name)

    print("Splitting complete.")
    return chunk_paths

def process_chunks(chunk_paths):
    os.makedirs("/app/output", exist_ok=True)

    for idx, chunk in enumerate(chunk_paths):
        print(f"\n--- Processing Chunk {idx+1}/{len(chunk_paths)}: {chunk} ---")

        # Call the marker CLI command
        # Downloads model weights automatically on the first chunk run
        command = [
            "marker_single",
            chunk,
            "--output_dir", f"/app/output/chunk_{idx}"
        ]

        try:
            subprocess.run(command, check=True)
            print(f"Successfully processed chunk {idx}\n")
        except subprocess.CalledProcessError as e:
            print(f"Error processing chunk {idx}: {e}\n")

        # --- SAFE CROSS-PLATFORM CACHE CLEARING LOGIC ---
        print("Clearing system cache memory variables...")
        try:
            import gc
            import torch

            # Force Python to release system variables from RAM
            gc.collect()

            # Safely check for CUDA before attempting to clear it
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("-> CUDA memory cache cleared successfully.")
            else:
                # If running on CPU, we rely on garbage collection
                print("-> CPU environment detected. Memory collected successfully.")
        except Exception as cache_err:
            print(f"Cache clearing notice: {cache_err}")
        print("--------------------------------------------------\n")


if __name__ == "__main__":
    input_book = "/app/data/textbook.pdf"

    if not os.path.exists(input_book):
        print(f"Error: Could not find your textbook at {input_book}. Did you mount your folder correctly?")
    else:
        # Start the execution timer
        start_time = time.time()
        # We need reader in global scope for split_pdf to use it cleanly
        reader = PdfReader(input_book)
        chunks = split_pdf(input_book)
        process_chunks(chunks)

        # Calculate the total execution time
        end_time = time.time()
        total_seconds = end_time - start_time

        # Format the time nicely into minutes and seconds
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)

        print("==================================================")
        print("All done! Check your output folder for the markdown results.")
        print(f"Total Execution Time: {minutes} minutes and {seconds} seconds.")
        print("==================================================")
