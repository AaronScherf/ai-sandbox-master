
3. **Read the Layout Index First**: Open and inspect `./extracted_pages/document_manifest.json` using your file viewing tools before reading any text content.

4. **Execute Targeted Chapter Reading**:
    * **If `has_chapters` is true**: Match the user's intent to the chapter list. Locate the specific `file_path` for the relevant chapter (e.g., `./extracted_pages/chapter_4_Security.txt`). Read ONLY that isolated chapter file.
    * **If `has_chapters` is false** (or the query spans multiple boundaries): Locate the relevant individual page blocks (`page_X.txt`) mapped to the requested info.