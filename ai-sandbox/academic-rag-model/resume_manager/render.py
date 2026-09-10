"""
render.py
Deterministic templating of a structured resume (schema.py's shape) into
Markdown, then HTML, then a styled PDF via xhtml2pdf (spec §6 Revision 2)
-- no LLM output is ever handed straight to the `markdown` library.
"""
from __future__ import annotations

import markdown as markdown_lib
from xhtml2pdf import pisa

_CSS = """
<style>
@page {
    size: letter;
    margin: 0.6in 0.6in 0.8in 0.6in;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    color: #333;
    font-size: 10.5pt;
    line-height: 1.4;
}
h1 {
    text-align: center;
    text-transform: uppercase;
    color: #111;
    font-size: 22pt;
    margin-bottom: 5px;
}
h2 {
    color: #003366;
    border-bottom: 1px solid #ccc;
    font-size: 13pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 20px;
    margin-bottom: 8px;
}
h3 {
    font-size: 11pt;
    margin-top: 10px;
    margin-bottom: 3px;
}
ul {
    margin-top: 0;
    margin-bottom: 10px;
    padding-left: 20px;
}
li {
    margin-bottom: 3px;
}
</style>
"""


def build_markdown(resume: dict) -> str:
    """Pure templating, no I/O, no LLM -- the same input always produces
    the same output (spec §6)."""
    parts: list[str] = []

    contact = resume.get("contact") or {}
    if contact.get("name"):
        parts.append(f"# {contact['name']}")
    contact_line = " • ".join(
        value for value in [
            contact.get("location"), contact.get("email"), contact.get("linkedin_url"),
            contact.get("github_url"), contact.get("website_url"),
        ] if value
    )
    if contact_line:
        parts.append(contact_line)

    if resume.get("work_experience"):
        parts.append("## Work Experience")
        for entry in resume["work_experience"]:
            parts.append(f"### {entry['org']} — {entry['role']} ({entry['start_date']} – {entry['end_date']})")
            if entry.get("location"):
                parts.append(entry["location"])
            for bullet in entry.get("bullets") or []:
                parts.append(f"- {bullet}")

    if resume.get("education"):
        parts.append("## Education")
        for entry in resume["education"]:
            parts.append(f"### {entry['institution']}")
            degree_line = entry.get("degree", "")
            if entry.get("gpa"):
                degree_line += f" • GPA: {entry['gpa']}"
            parts.append(f"- {degree_line}")
            parts.append(f"- {entry.get('location', '')} • {entry['start_date']} – {entry['end_date']}")
            if entry.get("thesis"):
                parts.append(f"- Thesis: {entry['thesis']}")

    if resume.get("awards"):
        parts.append("## Awards & Scholarships")
        for entry in resume["awards"]:
            parts.append(f"- {entry['name']} ({entry['date']}) — {entry['description']}")

    if resume.get("publications"):
        parts.append("## Research Presentations & Publications")
        for entry in resume["publications"]:
            line = f"- {entry['title']} ({entry['date']}) — {entry['venue']}"
            if entry.get("link"):
                line += f" ([link]({entry['link']}))"
            parts.append(line)

    if resume.get("skills"):
        parts.append("## Skills")
        for entry in resume["skills"]:
            items = ", ".join(entry.get("items") or [])
            parts.append(f"- **{entry['category']}**: {items}")

    return "\n\n".join(parts)


def render_resume_pdf(resume: dict, output_path: str) -> None:
    """Templates `resume` to Markdown, then HTML, then a styled PDF at
    `output_path`. Raises if xhtml2pdf reports an error (pisa.CreatePDF's
    `.err` is non-zero) -- an application's PDF is either fully written
    or not written at all, never a silently-broken partial file."""
    markdown_text = build_markdown(resume)
    html_body = markdown_lib.markdown(markdown_text)
    full_html = f"<html><head>{_CSS}</head><body>{html_body}</body></html>"
    with open(output_path, "wb") as f:
        result = pisa.CreatePDF(full_html, dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} error(s) rendering {output_path}")
