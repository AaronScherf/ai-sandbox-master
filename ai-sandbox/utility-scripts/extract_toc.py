import fitz # PyMuPDF

pdf_path = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers/simon-blume-mathematics-for-economists-2004/Mathematics-for-Economists-by-Carl-P-Simon-and-Lawrence-E-Blume-2004.pdf"

doc = fitz.open(pdf_path)
toc = doc.get_toc()

if toc:
    print("Table of Contents:")
    for item in toc:
        # item is [level, title, page_number]
        print(f"Level {item[0]}: {item[1]} (Page {item[2]})")
else:
    print("No TOC found in PDF bookmarks.")
