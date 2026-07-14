import os
import sys
import re
import json
import pytesseract
import multiprocessing
from multiprocessing import Pool
from pdf2image import convert_from_path
from pypdf import PdfReader
import pdfplumber
from PIL import Image

try:
    multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass

def process_single_page(args):
    """
    Worker function: Groups overlapping/stacked equation layers vertically to prevent duplicate fragments and ensure a single clean image per formula.
    """
    pdf_path, page_num, tmp_dir, formula_dir, figure_dir = args
    try:
        page_images = convert_from_path(
            pdf_path, dpi=200, first_page=page_num, last_page=page_num
        )
        actual_page_image = page_images[0]
        width, height = actual_page_image.size
        masked_vertical_zones = []
        compiled_page_text = []
        figure_counter = 1
        math_counter = 1

        # PHASE 1: DISCOVER AND ISOLATE FULL-SCALE GRAPHS/DIAGRAMS (pdfplumber)
        with pdfplumber.open(pdf_path) as pdf:
            page_obj = pdf.pages[page_num - 1]
            drawings = page_obj.rects + page_obj.lines + page_obj.curves
            if len(drawings) >= 5:
                scale_x = width / float(page_obj.width)
                scale_y = height / float(page_obj.height)
                x0 = min([d['x0'] for d in drawings]) * scale_x
                top = min([d['top'] for d in drawings]) * scale_y
                x1 = max([d['x1'] for d in drawings]) * scale_x
                bottom = max([d['bottom'] for d in drawings]) * scale_y
                chart_height = bottom - top
                if chart_height > (0.12 * height):
                    fig_box = (max(0, x0 - 20), max(0, top - 20), min(width, x1 + 20), min(height, bottom + 20))
                    figure_filename = f"figure_p{page_num}_fig{figure_counter}.png"
                    cropped_fig = actual_page_image.crop(fig_box)
                    cropped_fig.save(os.path.join(figure_dir, figure_filename), format="PNG")
                    compiled_page_text.append(f"\n\n![Standalone Document Figure Reference](./figures/{figure_filename})\n\n")
                    masked_vertical_zones.append((top - 10, bottom + 10))
                    figure_counter += 1

        # PHASE 2: ROW CLASSIFICATION MANIFEST BUILDER (Tesseract)
        ocr_data = pytesseract.image_to_data(actual_page_image, output_type=pytesseract.Output.DICT)
        line_boxes = {}
        for idx in range(len(ocr_data['text'])):
            word = ocr_data['text'][idx].strip()
            if not word:
                continue
            top = ocr_data['top'][idx]
            if any(z[0] <= top <= z[1] for z in masked_vertical_zones):
                continue
            matched_line = None
            for existing_top in line_boxes.keys():
                if abs(existing_top - top) < 12:
                    matched_line = existing_top
                    break
            if matched_line is None:
                line_boxes[top] = []
                matched_line = top
            line_boxes[matched_line].append({
                'text': word,
                'left': ocr_data['left'][idx],
                'top': ocr_data['top'][idx],
                'width': ocr_data['width'][idx],
                'height': ocr_data['height'][idx]
            })

        raw_rows_manifest = []
        for row_top in sorted(line_boxes.keys()):
            words_in_row = sorted(line_boxes[row_top], key=lambda x: x['left'])
            row_text_str = " ".join([w['text'] for w in words_in_row])
            if row_top < (0.07 * height) or row_top > (0.93 * height):
                raw_rows_manifest.append({'type': 'text', 'text': row_text_str, 'top': row_top})
                continue
            if any(h in row_text_str.upper() for h in ['CHAPTER', 'SECTION', 'FOUNDATIONS', 'INDEX']):
                raw_rows_manifest.append({'type': 'text', 'text': row_text_str, 'top': row_top})
                continue

            has_massive_horizontal_gaps = False
            if len(words_in_row) > 1:
                for idx in range(len(words_in_row) - 1):
                    current_word_end = words_in_row[idx]['left'] + words_in_row[idx]['width']
                    next_word_start = words_in_row[idx + 1]['left']
                    if (next_word_start - current_word_end) > (0.15 * width):
                        has_massive_horizontal_gaps = True
                        break

            min_left = min([w['left'] for w in words_in_row])
            max_right = max([w['left'] + w['width'] for w in words_in_row])
            is_full_width_sentence = ((max_right - min_left) / width) > 0.65
            is_toc_pattern = bool(re.search(r'\s+\d+$', row_text_str))
            has_math_operators = bool(re.search(r'[=+\-<>~^/|∂∫√∑∏±÷×≈\b\d\b]', row_text_str))
            isolated_vars = re.findall(r'\b[a-zA-Z]\b', row_text_str)
            has_high_var_density = len(isolated_vars) >= 2 and not any(w in row_text_str.lower() for w in ['the', 'and', 'for', 'with', 'that', 'this'])
            is_standalone_block_row = ((max_right - min_left) / width) < 0.50 and min_left > (0.12 * width)
            is_block_math = (has_math_operators or has_high_var_density) and is_standalone_block_row and not is_toc_pattern and not has_massive_horizontal_gaps

            if is_block_math and len(words_in_row) > 0:
                raw_rows_manifest.append({
                    'type': 'math',
                    'text': row_text_str,
                    'top': min([w['top'] for w in words_in_row]),
                    'bottom': max([w['top'] + w['height'] for w in words_in_row]),
                    'left': min_left,
                    'right': max_right
                })
            else:
                raw_rows_manifest.append({'type': 'text', 'text': row_text_str, 'top': row_top})

        # PHASE 3: COMPACTION AND MERGE LOOP (Prevents Multi-Image Splitting)
        unified_manifest = []
        idx = 0
        while idx < len(raw_rows_manifest):
            current_item = raw_rows_manifest[idx]
            if current_item['type'] == 'math':
                while (idx + 1 < len(raw_rows_manifest)) and \
                      (raw_rows_manifest[idx + 1]['type'] == 'math') and \
                      (raw_rows_manifest[idx + 1]['top'] <= current_item['bottom'] + 45):
                    next_math = raw_rows_manifest[idx + 1]
                    current_item['left'] = min(current_item['left'], next_math['left'])
                    current_item['right'] = max(current_item['right'], next_math['right'])
                    current_item['top'] = min(current_item['top'], next_math['top'])
                    current_item['bottom'] = max(current_item['bottom'], next_math['bottom'])
                    current_item['text'] += " " + next_math['text']
                    idx += 1
                unified_manifest.append(current_item)
            else:
                unified_manifest.append(current_item)
            idx += 1

        # PHASE 4: EXECUTE SEGMENTED COMPILATION AND CROPS
        for item in unified_manifest:
            if item['type'] == 'math':
                crop_box = (
                    max(0, item['left'] - 15),
                    max(0, item['top'] - 15),
                    min(width, item['right'] + 15),
                    min(height, item['bottom'] + 15)
                )
                if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
                    formula_filename = f"math_p{page_num}_f{math_counter}.png"
                    formula_path = os.path.join(formula_dir, formula_filename)
                    cropped_formula = actual_page_image.crop(crop_box)
                    cropped_formula.save(formula_path, format="PNG")
                    compiled_page_text.append(f"\n[INDEPENDENT_BLOCK_FORMULA: {item['text']}]")
                    compiled_page_text.append(f"![Mathematical Formula Reference](./formulas/{formula_filename})\n")
                    math_counter += 1
            else:
                compiled_page_text.append(item['text'])

        full_page_output = "\n".join(compiled_page_text)
        tmp_file_path = os.path.join(tmp_dir, f"page_{page_num}.txt")
        with open(tmp_file_path, "w", encoding="utf-8") as f:
            f.write(full_page_output)
        return page_num, True
    except Exception as e:
        return page_num, False

def parallel_ocr_pipeline(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        sys.exit(1)

    pdf_absolute_dir = os.path.dirname(os.path.abspath(pdf_path))
    pdf_filename_raw = os.path.basename(pdf_path)
    pdf_base_name = os.path.splitext(pdf_filename_raw)[0].replace(" ", "_")
    output_dir = os.path.join(pdf_absolute_dir, f"{pdf_base_name}_extracted_cache")
    os.makedirs(output_dir, exist_ok=True)

    tmp_dir = os.path.join(output_dir, "tmp_pages")
    formula_dir = os.path.join(output_dir, "formulas")
    figure_dir = os.path.join(output_dir, "figures")
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(formula_dir, exist_ok=True)
    os.makedirs(figure_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    print(f"Target Directory resolved to: {output_dir}")
    print(f"Processing {total_pages} total pages...")

    num_workers = 3
    tasks = [(pdf_path, p_num, tmp_dir, formula_dir, figure_dir) for p_num in range(1, total_pages + 1)]
    completed_count = 0

    with Pool(processes=num_workers) as pool:
        for _ in pool.imap_unordered(process_single_page, tasks):
            completed_count += 1
            percentage = (completed_count / total_pages) * 100
            bar_length = 25
            filled_length = int(round(bar_length * completed_count / float(total_pages)))
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            sys.stdout.write(f"\r[OCR PROGRESS] |{bar}| {percentage:.1f}% ({completed_count}/{total_pages} pages)")
            sys.stdout.flush()

    print("\n\nAll pages processed. Compiling global document text mapping...")
    raw_master_path = os.path.join(output_dir, "entire_document_raw.txt")
    with open(raw_master_path, "w", encoding="utf-8") as out_file:
        for page_num in range(1, total_pages + 1):
            tmp_file_path = os.path.join(tmp_dir, f"page_{page_num}.txt")
            if os.path.exists(tmp_file_path):
                with open(tmp_file_path, "r", encoding="utf-8") as f:
                    out_file.write(f"\n[PAGE_MARKER_START_{page_num}]\n{f.read()}\n[PAGE_MARKER_END_{page_num}]\n")
                os.remove(tmp_file_path)
            else:
                out_file.write(f"\n[PAGE_MARKER_START_{page_num}]\n[OCR_FAILED]\n[PAGE_MARKER_END_{page_num}]\n")

    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass

    with open(raw_master_path, "r", encoding="utf-8") as f:
        complete_text = f.read()

    chapter_pattern = re.compile(r'(?i)\n(?:Chapter|Section)\s+([0-9\d+|I|V|X|L|C]+[^\n]*)')
    matches = list(chapter_pattern.finditer(complete_text))
    manifest = {"has_chapters": False, "chapters": [], "total_pages": total_pages}

    if matches:
        manifest["has_chapters"] = True
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

    manifest_path = os.path.join(output_dir, "document_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nPipeline finished completely! Manifest map built at: {manifest_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_agent.py <path_to_pdf>")
        sys.exit(1)
    parallel_ocr_pipeline(sys.argv[1])

