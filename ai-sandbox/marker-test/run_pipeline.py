import os
import time
import gc
from pypdf import PdfReader, PdfWriter

# Force single-threaded CPU processing to bypass OOM crashes
os.environ["TORCH_DEVICE"] = "cpu"
os.environ["IN_DET_BATCH_SIZE"] = "1"
os.environ["OCR_BATCH_SIZE"] = "1"
os.environ["MARKER_NUM_THREADS"] = "1"

# Import modern Marker API classes
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

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

    print("Initializing Marker AI configurations... (This takes a moment)")

    # 1. Initialize configuration variables
    config = {
        "output_format": "markdown",
        "disable_image_extraction": False,
        "low_mem": True
    }
    config_parser = ConfigParser(config)

    # 2. Instantiate the unified converter class natively
    converter = PdfConverter(
        config=config_parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=config_parser.get_processors(),
        renderer=config_parser.get_renderer()
    )
    print("AI Engine initialized and cached in RAM.\n")

    for idx, chunk_path in enumerate(chunk_paths):
        print(f"--- Processing Chunk {idx+1}/{len(chunk_paths)}: {chunk_path} ---")
        output_folder = f"/app/output/chunk_{idx}"
        os.makedirs(output_folder, exist_ok=True)

        try:
            # Execute the conversion
            rendered = converter(chunk_path)

            # Access text and extracted images via properties
            full_markdown_text = rendered.markdown
            extracted_images = rendered.images  # Dictionary containing image files

            # Save the parsed markdown text file
            md_path = os.path.join(output_folder, f"chunk_{idx}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(full_markdown_text)

            # Save all mathematical graphs/charts if images exist
            if extracted_images:
                img_dir = os.path.join(output_folder, f"chunk_{idx}_images")
                os.makedirs(img_dir, exist_ok=True)
                for img_name, img_data in extracted_images.items():
                    img_path = os.path.join(img_dir, img_name)
                    img_data.save(img_path)

            print(f"Successfully processed chunk {idx}")

        except Exception as e:
            print(f"Error processing chunk {idx}: {e}")

        # Flush system RAM memory buffers instantly between chunks
        gc.collect()
        print("System RAM garbage collection wiped cleanly.")
        print("--------------------------------------------------\n")

if __name__ == "__main__":
    input_book = "/app/data/textbook.pdf"

    if not os.path.exists(input_book):
        print(f"Error: Could not find your textbook at {input_book}.")
    else:
        start_time = time.time()

        # Slice into 15-page blocks (Sweet spot for 16GB headless systems)
        chunks = split_pdf(input_book, chunk_size=15)
        process_chunks_in_memory(chunks)

        end_time = time.time()
        total_seconds = end_time - start_time
        print(f"Success! Finished in {int(total_seconds // 60)}m {int(total_seconds % 60)}s.")
