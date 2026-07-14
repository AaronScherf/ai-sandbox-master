import pypdf
import fitz # PyMuPDF

pdf_path = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers/Mathematics-for-Economists-by-Carl-P-Simon-and-Lawrence-E-Blume-2004.pdf"

print("--- pypdf Metadata ---")
reader = pypdf.PdfReader(pdf_path)
print(f"pypdf page count: {len(reader.pages)}")
print(f"pypdf metadata: {reader.metadata}")

print("\n--- fitz (PyMuPDF) Metadata ---")
doc = fitz.open(pdf_path)
print(f"fitz page count: {len(doc)}")
print(f"fitz metadata: {doc.metadata}")

print("\n--- Checking for bookmarks/TOC ---")
print(f"pypdf bookmarks: {reader.outline}")
print(f"fitz toc: {doc.get_toc()}")

print("\n--- Testing text extraction across pages ---")
for i in range(100):
    text_pypdf = reader.pages[i].extract_text()
    text_fitz = doc[i].get_text()
    if text_pypdf.strip() or text_fitz.strip():
        print(f"Page {i} has text!")
        print(f"pypdf length: {len(text_pypdf)}, fitz length: {len(text_fitz)}")
        print(f"fitz sample: {repr(text_fitz[:200])}")
        break
else:
    print("No text found in first 100 pages.")
