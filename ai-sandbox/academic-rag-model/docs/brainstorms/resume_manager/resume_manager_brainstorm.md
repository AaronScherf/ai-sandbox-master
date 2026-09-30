# Brainstorming a Resume Manager using a Local LLM

Manage and update your resume by storing your master content as a Markdown file, using a Python script to send that text and a job description to an LLM, and rendering the optimized Markdown output into a styled PDF.1. Maintain Your Master Resume in MarkdownKeep your primary resume as a clean Markdown file (resume.md). Use standard headers (## Experience, ## Skills) so your code can easily parse sections. [1] (https://github.com/SherLock707/TailorCV)Write out all your past roles, metrics, and skills here.Treat this file as your single source of truth. Never overwrite this master file during tailoring; always create a cloned or temporary output for specific applications. [1] (https://python.plainenglish.io/how-i-built-an-auto-updating-resume-using-python-chatgpt-and-linkedin-409998749d27), [2] (https://www.linkedin.com/posts/keiichiogawa_portfolio-llm-activity-7497789910766997504-joge), [3] (https://resumey.pro/blog/make-markdown-resume-on-chatgpt/)2. Build the Python Automation ScriptWrite a Python script to handle input reading, LLM prompting, and file generation. You can use libraries like openai, ollama (for local models like Llama 3), or google-genai alongside a PDF engine like weasyprint or markdown-pdf. [1] (https://medium.com/write-a-catalyst/i-built-an-ai-agent-that-automatically-tailors-my-resume-for-every-job-application-f5a25c2c9e09), [2] (https://github.com/SherLock707/TailorCV)A typical pipeline executes these core functions:Ingest: Read your resume.md and the target job description (JD) text.Prompt the LLM: Instruct the model to rewrite your bullet points to match keywords in the JD while strictly prohibiting the fabrication of fake experience.Validate: Check the generated text to ensure dates, company names, and core metrics remain unchanged. [1] (https://towardsdatascience.com/how-to-build-a-resume-optimizer-with-ai-d73c2f9b9fcd/), [2] (https://github.com/SherLock707/TailorCV), [3] (https://medium.com/write-a-catalyst/i-built-an-ai-agent-that-automatically-tailors-my-resume-for-every-job-application-f5a25c2c9e09), [4] (https://resumey.pro/blog/make-markdown-resume-on-chatgpt/)“The system extracts text from your resume... Calls the local Mistral LLM via Ollama to suggest improvements and generates a cover letter for you.” -- [Build a Custom AI Tool To Tailor Resumes for Any Job].3. Convert Markdown to a Custom PDFOnce the LLM outputs the tailored Markdown content, convert it directly into a polished layout. [1] (https://github.com/SherLock707/TailorCV), [2] (https://medium.com/write-a-catalyst/i-built-an-ai-agent-that-automatically-tailors-my-resume-for-every-job-application-f5a25c2c9e09)Use Python tools like weasyprint combined with a custom CSS stylesheet to control margins, font sizes, and page limits.Alternatively, paste your final Markdown into dedicated design renderers like Markdown Resume App or Resumey.Pro to export a clean PDF. [1] (https://resumey.pro/blog/best-markdown-resume-builder/), [2] (https://markdownresume.app/guide/), [3] (https://resumey.pro/blog/make-markdown-resume-on-chatgpt/)“The pipeline takes your master resume, scrapes a job posting URL, matches keywords, and rewrites bullets. It also generates a submission-ready PDF.” -- Manash Pratim, PhD.If you'd like, I can provide a starter Python script using a specific library (like OpenAI or local Ollama) to parse your markdown and generate the tailored file.

Yes, Ollama can run entirely on a CPU with no GPU. Because smaller models (like Llama 3.1 8B or Mistral 7B) are optimized for efficiency, a modern multi-core CPU with at least 16GB of RAM can process this resume task in about 15–30 seconds.
Here is a complete starter architecture that reads your master Markdown file, uses a local Ollama model to tailor it, and outputs a formatted PDF.
## Prerequisites & Dependencies
First, make sure you have [Ollama downloaded and running](https://ollama.com/) on your machine. Open your terminal and pull a lightweight model:

ollama pull llama3.1:8b

Next, install the required Python libraries. We will use weasyprint because it compiles HTML/CSS into professional, pixel-perfect PDFs, which is much easier to style than rigid PDF engines. We also use markdown to convert the LLM's text into HTML.

pip install ollama markdown weasyprint

(Note: WeasyPrint may require installing system-level dependencies like Pango or GTK depending on your OS. If you want a zero-dependency alternative, you can swap WeasyPrint for reportlab or fpdf2).
------------------------------
## The Automation Script (tailor_resume.py)

import osimport ollamaimport markdownfrom weasyprint import HTML
# 1. Load your raw assetsdef load_text_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()
master_resume = load_text_file("resume.md")job_description = load_text_file("job_description.txt")
# 2. Define your LLM system promptSYSTEM_PROMPT = """
You are an expert resume optimizer. Your task is to tailor a master resume to perfectly match a target job description.
CRITICAL RULES:
1. Do NOT invent, hallucinate, or exaggerate any experience, skills, or metrics.
2. Rewrite existing bullet points to mirror the vocabulary, keywords, and phrasing of the job description.
3. Keep the exact same structure, dates, and contact information.
4. Output your response ONLY as valid Markdown text. Do not include conversational intros or outros (e.g., do not say "Here is your tailored resume")."""
   USER_PROMPT = f"""
### MASTER RESUME:{master_resume}

### TARGET JOB DESCRIPTION:{job_description}

Please optimize the resume based on the rules provided."""

print("🧠 Processing with local Ollama on CPU (this may take a moment)...")
# 3. Request tailoring from local Ollama instanceresponse = ollama.generate(
    model='llama3.1:8b',
    system=SYSTEM_PROMPT,
    prompt=USER_PROMPT,
    options={
        "temperature": 0.2, # Low temperature ensures strict adherence to facts
    }
)
tailored_markdown = response['response']
# Save the tailored markdown markdown text for recordswith open("tailored_output.md", "w", encoding="utf-8") as f:
    f.write(tailored_markdown)

print("📝 Markdown tailored successfully. Converting to PDF...")
# 4. Convert Markdown text to HTML structurehtml_content = markdown.markdown(tailored_markdown)
# 5. Inject CSS styling for a professional PDF layoutcss_style = """
<style>
    @page {
        size: letter;
        margin: 0.6in 0.6in 0.8in 0.6in;
        @bottom-right {
            content: counter(page);
            font-size: 9pt;
            color: #555;
        }
    }
    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
        line-height: 1.4;
        font-size: 10.5pt;
    }
    h1 {
        text-align: center;
        text-transform: uppercase;
        margin-bottom: 5px;
        color: #111;
        font-size: 22pt;
    }
    h2 {
        color: #003366;
        border-bottom: 1px solid #ccc;
        padding-bottom: 2px;
        margin-top: 20px;
        margin-bottom: 8px;
        font-size: 13pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    h3 {
        margin-top: 10px;
        margin-bottom: 3px;
        font-size: 11pt;
    }
    p {
        margin: 0 0 5px 0;
    }
    ul {
        margin-top: 0;
        margin-bottom: 10px;
        padding-left: 20px;
    }
    li {
        margin-bottom: 3px;
    }
</style>"""
complete_html = f"<html><head>{css_style}</head><body>{html_content}</body></html>"
# 6. Render out the custom formatted PDF
HTML(string=complete_html).write_pdf("Tailored_Resume.pdf")
print("🎉 Success! 'Tailored_Resume.pdf' is ready for submission.")

## Execution Flow

1. Save your master resume as resume.md and paste the target job post text into job_description.txt in the same directory.
2. Run python tailor_resume.py.
3. The script feeds the texts to Ollama locally, converts the refined markdown into safe HTML structure, applies the embedded CSS, and saves Tailored_Resume.pdf.

I can help modify this to fit your setup. Would you like to:
Add a feature to automatically scrape the job description from a URLAdjust the script to use a different PDF library if WeasyPrint gives you installation errorsAdd a Cover Letter generation step to the same pipeline

