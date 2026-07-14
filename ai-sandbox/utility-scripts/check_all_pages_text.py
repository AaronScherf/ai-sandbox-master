import fitz

pdf_path = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers/Mathematics-for-Economists-by-Carl-P-Simon-and-Lawrence-E-Blume-2004.pdf"
doc = fitz.open(pdf_path)

pages_with_text = []
for idx, page in enumerate(doc):
    text = page.get_text()
    if text.strip():
        pages_with_text.append(idx)
        if len(pages_with_text) >= 10:
            break

print(f"Pages with text: {pages_with_text}")
if pages_with_text:
    print(f"Sample text from page {pages_with_text[0]}:")
    print(doc[pages_with_text[0]].get_text()[:500])
else:
    print("Absolutely no text layer found in any of the 952 pages.")
