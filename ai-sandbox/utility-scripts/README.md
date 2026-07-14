# Utility Scripts Directory

This directory contains reusable local automation and optimization tools for the Gemini CLI agent workspace. Check this manifest before writing new code.

## Available Tools

### 1. OCR Agent & PDF Chapter Splitter (`ocr_agent.py`)
*   **Purpose**: Extracts plain text from large or scanned PDFs using Tesseract OCR, processes structural layouts using regex, and caches files as chapters to minimize API token usage.
*   **When to use**: Whenever the user asks to summarize, analyze, or query any multi-page PDF document.
*   **Execution Command**:
    ```bash
    python utility-scripts/ocr_agent.py <path_to_pdf>
    ```
*   **Outputs**: Creates a cached `./extracted_chapters/` directory containing a structural map layout (`document_manifest.json`) alongside isolated text chunk assets.

## 2. PDF Analysis Tools
*Note: The following scripts are currently specialized for specific PDF documents and may require modifications to their file path variables to be used on other documents.*

### `check_all_pages_text.py`
*   **Purpose**: Checks a PDF to determine if it has a searchable text layer and provides sample text.

### `extract_first_pages.py`
*   **Purpose**: Extracts text from the first N pages of a PDF.

### `extract_pdf_text.py`
*   **Purpose**: Performs text extraction using both PyMuPDF and pypdf libraries to compare results.

### `extract_toc.py`
*   **Purpose**: Extracts the Table of Contents structure using PyMuPDF.

### `find_toc.py`
*   **Purpose**: Scans the first 30 pages of a PDF for keywords related to a "Table of Contents".

### `list_outlines.py`
*   **Purpose**: Lists PDF outline bookmarks (if available).

## 3. Deprecated
*   `ocr_agent_old.py`
*   `ocr_agent_old2.py`
