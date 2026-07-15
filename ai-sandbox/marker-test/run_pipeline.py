import os
import subprocess
from pypdf import PdfReader, PdfWriter

def split_pdf(input_path, chunk_size=50):
    print(f"Reading {input_path}...")
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    print(f"Total pages found: {total_pages}. Splitting into {chunk_size}-page chunks...")

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
            print(f"Successfully processed chunk {idx}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing chunk {idx}: {e}")

if __name__ == "__main__":
    input_book = "/app/data/textbook.pdf"

    if not os.path.exists(input_book):
        print(f"Error: Could not find your textbook at {input_book}. Did you mount your folder correctly?")
    else:
        chunks = split_pdf(input_book, chunk_size=50)
        process_chunks(chunks)
        print("\nAll done! Check your local folder for the markdown results.")
