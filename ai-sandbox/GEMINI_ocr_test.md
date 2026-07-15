# Agent Instructions: Plain Text Optimization Routing

Whenever the user prompts you to analyze, search, summarize, or query a PDF document contained in the workspace that contains over 30 pages, you MUST follow this two-step cost-reduction execution pattern to drastically reduce API token overhead:

1. **Do Not Direct-Read**: Never upload raw multi-page PDF binaries natively to the Gemini model payload context if they are over 30 pages.  Isolate text strictly to the minimum required fragments to generate a correct answer.
2. **Text Conversion Over Binary Slicing**: Always choose to trigger local plain text compilation over PDF binary split tools:
   `python utility_scripts/ocr_agent.py <path_to_pdf>`
3. **Locate the Dynamic Cache Folder**: The script creates a cache directory directly next to the source PDF named `<pdf_filename_without_extension>_extracted_cache/`. Locate this directory and look inside it for `document_manifest.json`.
4. **Targeted Reading Strategy**:
   * Review the `document_manifest.json` file inside that specific path to find chapter boundaries.
   * Read text chunk files on demand based on what the user is asking.
5. **Isolate Text Processing**: Locate the `file_path` of the text chunk corresponding to the requested segment. Never pass the entire raw text corpus into your active history unless strictly required.
6. **Multimodal Formula Verification**: If the user asks a deep technical question about an equation or expression, locate the text line containing the math markdown reference anchor tag: `![Mathematical Formula Reference](./formulas/math_page_X.png)`. Use your terminal vision file viewing tools to open and inspect **only** that specific cropped equation image file to formulate a highly precise explanation while keeping token usage to a minimum.

# Storage and Reusability of Helper Scripts

1. **Workspace Directory Constraints**: You must store all helper scripts, automation tools, and Python utilities inside the `./utility_scripts/` directory. Never leave floating Python scripts in the root directory.
2. **Search Before Code Generation**: Before you write or generate any new Python code, you MUST inspect the `./utility_scripts/README.md` file to see if a tool already exists for the task.
3. **Reuse Existing Automation**: If a script already exists in `./utility_scripts/` that fulfills or can be adapted for the requested task (e.g., `ocr_agent.py`), you MUST execute that existing script instead of writing a new one.
4. **Maintenance Pattern**: Only generate a new script if no comparable utility exists in `./utility_scripts/`. If you create a new tool, save it directly to `./utility_scripts/` and give it a clear, descriptive filename for future sessions.