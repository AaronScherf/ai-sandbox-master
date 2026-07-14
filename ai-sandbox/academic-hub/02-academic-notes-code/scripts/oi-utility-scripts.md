# Open Interpreter Prompts:
Ensure you are in the correct root directory:
C:\Users\theaa\ai-sandbox-master\ai-sandbox

Docker prompts:
docker compose down
docker compose up -d

Use docker compose up -d --build: Use this only when you add new system packages (apt-get), install new global Python libraries (pip install), add global Node tools (npm install), or change environment variables (ENV) inside the Dockerfile.

docker compose up -d --build

To open the docker instance:
docker exec -it open_interpreter_sandbox bash

To open the Open Interpreter with a Gemini backend using the API:
interpreter --model gemini/gemini-2.5-flash

To open the Gemini CLI directly using the API:
gemini

## Splitting textbooks by chapter 

"""CRITICAL DIRECTION: Do not use cd or change the current working directory of the terminal at any point. Keep the execution context locked at the root /workspace directory. Write all Python file paths using absolute references starting with /workspace/... to ensure paths remain consistent across different code blocks.

TARGET_DIR = \`/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers\`

Look inside the directory at TARGET_DIR. I have an unorganized textbook PDF here. Find the filename of the PDF using bash commands to proceed to the next step.

Please perform the following automated pipeline:

1. METADATA EXTRACTION: Write a temporary Python script to read the first 10 pages of the PDF. Use a regex or pass the extracted text back to your language model to accurately isolate the core title, the primary author's first and last name, and the publication year. Print these discovered variables out for confirmation before proceeding.

2. SYSTEM SANITIZATION: Dynamically generate a clean lower-kebab-case string based on what you found, formatted exactly as: `authorlastname-authorfirstname-textbooktitle-year`. If the PDF file is not already named with this style of string, rename the original PDF file to this clean string (keeping the .pdf extension).

3. SUBDIRECTORY ARCHITECTURE: If a subdirectory matching the filename for the PDF does not already exist in the TARGET_DIR, create a new subdirectory in this folder using that exact same `authorlastname-authorfirstname-textbooktitle-year` naming convention.

4. CHAPTER SPLITTING ENGINE: Use a Python script (like pypdf) to analyze the file. Check if the PDF contains an embedded digital table of contents/bookmarks. Print the result of whether it contains an embedded table of contents for confirmation before proceeding.
    - IF IT DOES have a digital table of contents/bookmarks:  Extract the table of contents in text format and print the first ten chapter titles for confirmation before proceeding. Cross-reference the bookmarks against the confirmed table of contents. Separate the table of contents as a separate chapter 0, then skip any title, copyright, contents, or preface sections. Focus on chapter headings, not subsections per chapter. For the remaining chapters with content, write a Python script to split the PDF into sections per chapter, saving each chapter as a separate lower-kebab-case PDF inside the newly created subdirectory, formatting the files exactly as: `authorlastname-chapter-[chapternumber]-[chaptertitle].pdf`. For chapter number, extract the number of the chapter from the bookmark if possible; if not, extract it directly from the relevant text on the first page of that chapter. Use the standard numerical format `00`, `01`, `02`, ... , `09`, `10`, `11`, etc. for chapter numbers.
    - IF IT DOES NOT have a digital table of contents/bookmarks: Scan pages 1 through 20 for a visual Table of Contents. If you find a table of contents, extract the full table of contents in text format and print the first ten chapter titles for confirmation before proceeding. Use the confirmed table of contents as a list to identify the sections of the text corresponding to each chapter. Focus on chapter headings, not subsections per chapter. If you locate a standard visual pattern for chapter headers (e.g., 'Chapter X' or 'Section 1'), write a Python script to scan the headers of every page in the book to search for the chapter breaks and extract the precise page numbers where chapters break. Compare the number of chapter splits found with the confirmed table of contents list found and print the results of this comparison for confirmation before proceeding. Continue to write a Python script to use those page numbers to slice the PDF into individual files inside the new subdirectory using the exact same naming format: `authorlastname-chapter-[chapternumber]-[chaptertitle].pdf`. Use the standard numerical format `00`, `01`, `02`, ... , `09`, `10`, `11`, etc. for chapter numbers.

5. CHECK THE WORK: After generating the chapter subsection PDFs, check within the TARGET_DIR to make sure they logically correspond to an entire chapter of a textbook. If the previous chapter splitting process resulted in PDFs of less than 10 pages, they likely are not full chapters. If you determine that the previous process may have split the textbook into subsections instead of chapters, or split too much of the front matter into isolated PDFs, ask if the script split the textbook too finely. If so, ask for permission to delete the files generated in the previous step, refine the script, and try again to generate higher level chapter splits.

6. Ask for final confirmation to terminate the pipeline. If permission is granted, move the `authorlastname-authorfirstname-textbooktitle-year` PDF file from the TARGET_DIR to the subdirectory with the same name."""


## Summarizing Textbooks by Chapter

"""# ==========================================================================
# ⚙️ CONFIGURATION VARIABLES
# ==========================================================================
TARGET_DIR = "/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers"
BOOK_FOLDER = "rudin-walter-principles-of-mathematical-analysis-1976"
TARGET_CHAPTER_NUM = "06"  # Using two digits to match standard file structures
OUTPUT_BASE_DIR = "/workspace/academic-hub/01-resources/math-camp/briefings"

# ==========================================================================
# 🛑 ENVIRONMENT & STRING EXECUTION RULES
# ==========================================================================
- CRITICAL DIRECTION: Do not change the current working directory of the terminal using 'cd'. Keep the execution context locked at the root `/workspace` directory. Use absolute paths starting with `/workspace` for all file operations.
- LATEX ESCAPE SAFEGUARD: When writing math symbols to the final Markdown file via Python, you MUST treat strings as raw strings (e.g., `r"..."` in Python) or double-escape all backslashes (e.g., use `\\alpha` instead of `\alpha`). This prevents text corruption like `\a` turning into an ASCII bell character.
- HEADLESS ENVIRONMENT: This container is a headless Docker instance with no GUI or desktop utilities. Do NOT attempt to use 'xdg-open', 'open', or any external file-viewing commands. Once the Markdown file is successfully written, print a final verification message and stop.

Please execute the following rigorous data pipeline:

### Step 1: Targeted File Verification
Construct the absolute path to the textbook folder using: `TARGET_DIR/BOOK_FOLDER`. Scan this folder and locate the specific PDF file that contains "chapter-TARGET_CHAPTER_NUM" or the most similar match. Print the exact filename found to the terminal for confirmation. Save this filename as `CHAPTER_FILE`.

### Step 2: Establish Output Architecture
Verify if the directory `OUTPUT_BASE_DIR/BOOK_FOLDER` exists. If not, create it. Inside that directory, create a dedicated subdirectory using the exact `CHAPTER_FILE` text identified in Step 1. This folder will be your `CHAPTER_OUTPUT_DIR`.y

### Step 3: Raw Text Extraction (No Filtering)
Write a straightforward Python script using PyMuPDF (fitz) or pypdf to extract the raw text content page-by-page from `CHAPTER_FILE`. Do NOT attempt to use regex to find headers, filter formulas, or parse the layout. Simply join all the raw extracted text into one massive, unbroken text string. Print the total character count of the extracted text to the terminal for confirmation.

### Step 4: Subsection Themes
Thematically identify subsections within the chapter based on the content of the text, using subsection headers if present to help divide the chapter into logical sections. Print the subsection headings to the terminal for confirmation before proceeding.

### Step 4: Generate Exhaustive PhD-Level Analytical Briefing
Using the entire extracted text, generate a massive, deeply detailed academic summary report.

Target this report explicitly to a First-Year Economics PhD student who needs absolute mathematical rigor for metrics and microeconomic theory foundations.

You must satisfy these structural parameters:
1. **No Shortcuts:** Do not truncate definitions or gloss over proofs. Treat every single subsection discovered in Step 4 as a major heading in your report.
2. **Mathematical Foundations:** Re-state core definitions, formulae, and technical conditions exactly as given in the text using flawless Markdown LaTeX.
3. **Theorem & Proof Breakdowns:** For major theorems, outline the core strategy of the proof, noting where important mathematical properties or assumptions are critically invoked.
4. **Economic Application Integration:** Retain and expand upon the relevance section. Provide clear latex-driven examples of how this specific mathematical chapter maps to other advanced mathematical concepts or economics.

Write the final output as a beautifully formatted `ch_[TARGET_CHAPTER_NUM]_summary_report.md` file directly into your `CHAPTER_OUTPUT_DIR`."""



# Send direct to Google API
"""Write and run a local Python script that reads the PDF file located at `workspace\academic-hub\01-resources\math-camp\textbooks-and-papers\rudin-walter-principles-of-mathematical-analysis-1976\rudin-chapter-6-the-riemann-stieltjes-integral.pdf`, sends its entire contents directly to the Google Gen AI API using my GEMINI_API_KEY environment variable with the gemini-2.5-flash model, asks it for a PhD-level analytical briefing of the math text, and writes the output directly to a file located in the path `workspace\academic-hub\01-resources\math-camp\briefings\rudin-walter-principles-of-mathematical-analysis-1976\rudin-chapter-6-the-riemann-stieltjes-integral`."""



"""Navigate to the simon-blume subdirectory in the path \`/workspace/academic-hub/01-resources/math-camp/textbooks-and-papers\`. Using the PDF contained in that subdirectory, check the metadata and bookmarks for a table of contents. If a table of contents is    
present, split the PDF into chapters and create new PDF files, using the naming convention [ch_X_subdirectoryname.pdf] where X is the chapter number and subdirectory name is the name of the folder generated in the last step. If the table of contents is not   
available from the metadata, search through the first few pages of the PDF to find it within the text, and proceed with the same instructions. Print the number of chapters found before proceeding with the PDF splitting for confirmation."""