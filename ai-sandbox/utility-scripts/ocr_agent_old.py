import os
import sys
import json
import pytesseract
from pypdf import PdfReader
from pdf2image import convert_from_path

def extract_pdf_structure(pdf_path):
    """Extracts internal bookmarks/outlines from the PDF metadata."""
    reader = PdfReader(pdf_path)
    bookmarks = []

    def parse_outlines(outline_list):
        for item in outline_list:
            if isinstance(item, list):
                parse_outlines(item) # Recursively handle nested chapters
            else:
                try:
                    # pypdf gets the 0-indexed page number for the bookmark destination
                    page_num = reader.get_destination_page_number(item) + 1
                    bookmarks.append({"title": item.title, "start_page": page_num})
                except Exception:
                    pass

    try:
        outlines = reader.outline
        if outlines:
            parse_outlines(outlines)
            # Sort chronologically by page number
            bookmarks = sorted(bookmarks, key=lambda x: x["start_page"])
    except Exception as e:
        print(f"Warning: Could not extract native bookmarks ({e})")

    return bookmarks

def optimize_pdf_for_agent(pdf_path, output_dir="extracted_pages"):
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # 1. Read metadata structure first
    bookmarks = extract_pdf_structure(pdf_path)

    # 2. Convert PDF pages to images for OCR
    print(f"Converting pages from {pdf_path}...")
    pages = convert_from_path(pdf_path, dpi=300)

    catalog = {}
    extracted_text_by_page = {}

    # 3. Standard page-by-page OCR extraction
    print(f"Processing {len(pages)} pages using Tesseract OCR...")
    for i, page_image in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page_image, lang='eng')
        extracted_text_by_page[i] = text

        # Save standard single-page chunk
        page_path = os.path.join(output_dir, f"page_{i}.txt")
        with open(page_path, "w", encoding="utf-8") as f:
            f.write(text)

    # 4. Generate Chapter Splitting based on bookmarks
    chapters_manifest = []
    if bookmarks:
        print(f"Found {len(bookmarks)} bookmarks. Splitting text into chapters...")
        for idx, book in enumerate(bookmarks):
            start = book["start_page"]
            # If it's the last bookmark, capture until the final page
            end = bookmarks[idx + 1]["start_page"] - 1 if idx + 1 < len(bookmarks) else len(pages)

            # Combine page texts for this specific chapter segment
            chapter_text = []
            for p_num in range(start, end + 1):
                chapter_text.append(extracted_text_by_page[p_num])

            chapter_full_text = "\n".join(chapter_text)
            safe_title = "".join(c for c in book["title"] if c.isalnum() or c in "._- ").strip().replace(" ", "_")
            chapter_filename = f"chapter_{idx+1}_{safe_title}.txt"
            chapter_path = os.path.join(output_dir, chapter_filename)

            with open(chapter_path, "w", encoding="utf-8") as f:
                f.write(chapter_full_text)

            chapters_manifest.append({
                "chapter_number": idx + 1,
                "title": book["title"],
                "start_page": start,
                "end_page": end,
                "file_path": chapter_path,
                "character_count": len(chapter_full_text)
            })

    # 5. Build and save the final Master Index File
    master_manifest = {
        "has_chapters": len(chapters_manifest) > 0,
        "chapters": chapters_manifest,
        "total_pages": len(pages)
    }

    manifest_path = os.path.join(output_dir, "document_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(master_manifest, f, indent=2)

    print(f"\nProcessing Complete! Manifest created at: {manifest_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_agent.py <path_to_pdf>")
        sys.exit(1)
    optimize_pdf_for_agent(sys.argv[1])
