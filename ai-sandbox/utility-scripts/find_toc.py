import fitz # PyMuPDF
import re

pdf_path = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers/simon-blume-mathematics-for-economists-2004/Mathematics-for-Economists-by-Carl-P-Simon-and-Lawrence-E-Blume-2004.pdf"

doc = fitz.open(pdf_path)

# Extract text from the first 30 pages and look for TOC keywords
for i in range(30):
    page_text = doc[i].get_text()
    if re.search(r'Contents', page_text, re.IGNORECASE):
        print(f"--- Possible Contents on Page {i+1} ---")
        print(page_text)
        break
else:
    print("No TOC found in first 30 pages.")
