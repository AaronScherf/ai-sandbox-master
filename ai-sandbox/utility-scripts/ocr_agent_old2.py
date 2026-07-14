import os
import sys
import re
import json
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

def memory_safe_ocr_pipeline(pdf_path, output_dir="extracted_chapters"):
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # 1. Determine total pages safely without rendering images
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"Detected {total_pages} total pages in PDF.")
    except Exception as e:
        print(f"Error reading PDF metadata: {e}")
        sys.exit(1)

    print("Running memory-safe streaming OCR extraction...")
    raw_master_path = os.path.join(output_dir, "entire_document_raw.txt")

    # Open the output text file in write mode to stream text straight to disk
    with open(raw_master_path, "w", encoding="utf-8") as out_file:
        # Stream page-by-page using single-page step iterations
        for page_num in range(1, total_pages + 1):
            try:
                # Convert ONLY one single page to image at a time to prevent OOM
                page_image = convert_from_path(
                    pdf_path,
                    dpi=300,
                    first_page=page_num,
                    last_page=page_num
                )[0]

                # Run OCR on the single page image
                text = pytesseract.image_to_string(page_image, lang='eng')

                # Write to disk instantly and inject structural page markers
                out_file.write(f"\n[PAGE_MARKER_START_{page_num}]\n{text}\n[PAGE_MARKER_END_{page_num}]\n")
                print(f"Successfully processed page {page_num}/{total_pages}")

                # Explicitly hint to Python to clear the image data from memory
                del page_image

            except Exception as e:
                print(f"Warning: Failed to process page {page_num} due to: {e}")
                out_file.write(f"\n[PAGE_MARKER_START_{page_num}]\n[OCR_FAILED_FOR_THIS_PAGE]\n[PAGE_MARKER_END_{page_num}]\n")

    # Read the text file back to chunk it into chapters via regex
    print("Parsing extracted text for structural chapters...")
    with open(raw_master_path, "r", encoding="utf-8") as f:
        complete_text = f.read()

    chapter_pattern = re.compile(r'(?i)\n(?:Chapter|Section)\s+([0-9\d+|I|V|X|L|C]+[^\n]*)')
    matches = list(chapter_pattern.finditer(complete_text))
    manifest = {"has_chapters": False, "chapters": [], "total_pages": total_pages}

    if matches:
        manifest["has_chapters"] = True
        print(f"Detected {len(matches)} chapter divisions!")

        for idx, match in enumerate(matches):
            start_index = match.start()
            end_index = matches[idx + 1].start() if idx + 1 < len(matches) else len(complete_text)

            chapter_title_raw = match.group(0).strip()
            safe_title = "".join(c for c in chapter_title_raw if c.isalnum() or c in " ").strip().replace(" ", "_")

            chapter_text_block = complete_text[start_index:end_index]
            chunk_filename = f"chunk_{idx+1}_{safe_title}.txt"
            chunk_path = os.path.join(output_dir, chunk_filename)

            with open(chunk_path, "w", encoding="utf-8") as f:
                f.write(chapter_text_block)

            manifest["chapters"].append({
                "chapter_index": idx + 1,
                "detected_title": chapter_title_raw,
                "file_path": chunk_path,
                "character_size": len(chapter_text_block)
            })
    else:
        print("No chapter headings found via text regex patterns.")

    # Save the master index mapping
    manifest_path = os.path.join(output_dir, "document_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Pipeline complete! Manifest map written to: {manifest_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_agent.py <path_to_pdf>")
        sys.exit(1)
    memory_safe_ocr_pipeline(sys.argv[1])
