"""
render.py
Deterministic templating of a structured resume (schema.py's shape) into
Markdown, then HTML, then a styled PDF via xhtml2pdf (spec §6 Revision 2)
-- no LLM output is ever handed straight to the `markdown` library.
"""
from __future__ import annotations

import markdown as markdown_lib
from xhtml2pdf import pisa

from resume_manager.schema import MISSING_VALUE_PLACEHOLDERS


def _display(value: str | None) -> str | None:
    """Returns `value` if it's real content, or None if it's empty or a
    known "honestly missing" placeholder (schema.py's
    MISSING_VALUE_PLACEHOLDERS) -- confirmed real request (2026-09-10):
    the literal placeholder text ("Not specified", etc.) is meant for the
    YAML data layer, not the rendered resume a person actually reads.
    "Present" is real content (an ongoing role's end date), not a
    placeholder, so it's untouched by this check."""
    if not value:
        return None
    if value.strip().lower() in MISSING_VALUE_PLACEHOLDERS:
        return None
    return value


def _date_range(start: str | None, end: str | None) -> str:
    """Renders a "start – end" range, falling back to whichever side is
    real if only one is, or "" if neither is -- never a dangling
    "(  –  )" left over from a genuinely-missing date on both sides."""
    start, end = _display(start), _display(end)
    if start and end:
        return f"{start} – {end}"
    return start or end or ""

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
    name = _display(contact.get("name"))
    if name:
        parts.append(f"# {name}")
    contact_line = " • ".join(
        value for value in [
            _display(contact.get("location")), _display(contact.get("email")),
            _display(contact.get("linkedin_url")), _display(contact.get("github_url")),
            _display(contact.get("website_url")),
        ] if value
    )
    if contact_line:
        parts.append(contact_line)

    if resume.get("work_experience"):
        parts.append("## Work Experience")
        for entry in resume["work_experience"]:
            date_range = _date_range(entry.get("start_date"), entry.get("end_date"))
            heading = f"### {entry['org']} — {entry['role']}"
            if date_range:
                heading += f" ({date_range})"
            parts.append(heading)
            location = _display(entry.get("location"))
            if location:
                parts.append(location)
            for bullet in entry.get("bullets") or []:
                parts.append(f"- {bullet}")

    if resume.get("education"):
        parts.append("## Education")
        for entry in resume["education"]:
            parts.append(f"### {entry['institution']}")
            degree = _display(entry.get("degree")) or ""
            gpa = _display(entry.get("gpa"))
            degree_line = f"{degree} • GPA: {gpa}" if gpa else degree
            if degree_line:
                parts.append(f"- {degree_line}")
            location = _display(entry.get("location"))
            date_range = _date_range(entry.get("start_date"), entry.get("end_date"))
            location_date_line = " • ".join(value for value in [location, date_range] if value)
            if location_date_line:
                parts.append(f"- {location_date_line}")
            thesis = _display(entry.get("thesis"))
            if thesis:
                parts.append(f"- Thesis: {thesis}")

    if resume.get("awards"):
        parts.append("## Awards & Scholarships")
        for entry in resume["awards"]:
            line = f"- {entry['name']} ({entry['date']})"
            description = _display(entry.get("description"))
            if description:
                line += f" — {description}"
            parts.append(line)

    if resume.get("publications"):
        parts.append("## Research Presentations & Publications")
        for entry in resume["publications"]:
            line = f"- {entry['title']} ({entry['date']}) — {entry['venue']}"
            link = _display(entry.get("link"))
            if link:
                line += f" ([link]({link}))"
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
