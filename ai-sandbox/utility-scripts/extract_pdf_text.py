
import pypdf

def extract_text_from_first_pages(pdf_path, num_pages=20):
    reader = pypdf.PdfReader(pdf_path)
    text = ""
    for i in range(min(num_pages, len(reader.pages))):
        text += reader.pages[i].extract_text()
    return text

pdf_path = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers/simon-blume-mathematics-for-economists-2004/Mathematics-for-Economists-by-Carl-P-Simon-and-Lawrence-E-Blume-2004.pdf"
print(extract_text_from_first_pages(pdf_path))
