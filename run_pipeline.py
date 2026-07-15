import os
import time
import gc
from pypdf import PdfReader, PdfWriter

# Explicitly force CPU execution globally before any AI packages load
os.environ["TORCH_DEVICE"] = "cpu"
os.environ["IN_DET_BATCH_SIZE"] = "1"
os.environ["OCR_BATCH_SIZE"] = "1"
os.environ["MARKER_NUM_THREADS"] = "1"

# Import marker directly into the script code to save system memory
from marker.convert import convert_single_pdf
from marker.models import load_all_models

def split_pdf(input_path, chunk_size=15):
    """Slices the book into ultra-safe, low-RAM 15-page segments"""
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)

    print(f"--- Document Slicing ---")
    print(f"Total Pages: {total_pages}. Slicing into safe {chunk_size}-page chunks...")

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

    print(f"Splitting complete into {len(chunk_paths)} temporary chunks.\n")
    return chunk_paths

def process_chunks_in_memory(chunk_paths):
    os.makedirs("/app/output", exist_ok=True)

    print("Loading AI translation models into CPU memory... (This takes a moment)")
    # Load models exactly once into the script session
    model_lst = load_all_models()
    print("Models successfully cached.\n")

    for idx, chunk_path in enumerate(chunk_paths):
        print(f"--- Processing Chunk {idx+1}/{len(chunk_paths)}: {chunk_path} ---")
        output_folder = f"/app/output/chunk_{idx}"

        try:
            # Native Python execution (Bypasses CLI subprocess memory overhead)
            full_text, images, out_meta = convert_single_pdf(chunk_path, model_lst)

            # Create output directories for this chunk
            os.makedirs(output_folder, exist_ok=True)
            img_dir = os.path.join(output_folder, f"chunk_{idx}_images")
            os.makedirs(img_dir, exist_ok=True)

            # Save the parsed markdown text file
            md_path = os.path.join(output_folder, f"chunk_{idx}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(full_text)

            # Save all extracted mathematical graphs and charts
            for img_name, img_data in images.items():
                img_path = os.path.join(img_dir, img_name)
                img_data.save(img_path)

            print(f"Successfully processed chunk {idx}")

        except Exception as e:
            print(f"Error processing chunk {idx}: {e}")

        # Flush the system RAM memory buffers instantly between chunks
        del full_text, images
        gc.collect()
        print("System RAM garbage collection wiped cleanly.")
        print("--------------------------------------------------\n")

if __name__ == "__main__":
    input_book = "/app/data/textbook.pdf"

    if not os.path.exists(input_book):
        print(f"Error: Could not find your textbook at {input_book}.")
    else:
        start_time = time.time()

        # Slice into 15-page blocks (Perfect sweet spot for 16GB headless systems)
        chunks = split_pdf(input_book, chunk_size=15)
        process_chunks_in_memory(chunks)

        end_time = time.time()
        total_seconds = end_time - start_time
        print(f"Success! Finished in {int(total_seconds // 60)}m {int(total_seconds % 60)}s.")
