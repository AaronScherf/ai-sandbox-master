
import pypdf

def print_outlines(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    if reader.outline:
        for item in reader.outline:
            if isinstance(item, list):
                for subitem in item:
                    print(subitem.title)
            else:
                print(item.title)
    else:
        print("No outline/bookmarks found.")

pdf_path = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers/simon-blume-mathematics-for-economists-2004/Mathematics-for-Economists-by-Carl-P-Simon-and-Lawrence-E-Blume-2004.pdf"
print_outlines(pdf_path)
