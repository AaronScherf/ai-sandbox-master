"""
render.py
Deterministic templating of a structured resume (schema.py's shape) into
Typst markup, then a PDF via the `typst` package -- no LLM output is ever
handed straight to a renderer (spec §6 Revision 2). Replaces the earlier
Markdown+xhtml2pdf path: xhtml2pdf rendered `<ul>/<li>` bullets with no
visible marker at all (confirmed against a real application run,
2026-09-26) and had generally plain default typography; Typst renders
real bullet glyphs out of the box and has a much better-looking default
typeface, with no native-library install risk (a self-contained wheel,
same precedent as `resvg-py` for Excalidraw notes).

**Standing style rules** (confirmed real feedback, 2026-09-26, after
reviewing the first real Typst-rendered PDF -- these are deterministic
code, not something re-derived or hand-tuned per application):
- Every list of bullets belonging to one entry/section is built as a
  single Typst list block (lines joined with one "\\n", never a blank
  line) -- a blank line between two "- " lines makes Typst treat them as
  *separate* one-item lists, each carrying its own block spacing, which
  is what produced visibly uneven gaps between bullets vs. between a
  heading and its first bullet.
- The contact line under the name is centered, matching the name itself.
- A work-experience entry's heading (`job-heading`, in the Typst
  preamble) puts its date range in a right-aligned column next to the
  org, and the role on its own line below -- confirmed real feedback
  that combining org + role on one line still wrapped for the longest
  titles even after moving the date aside; the role alone, with the
  full line width to itself, fits one line for every real title in the
  actual resume.
- `_DENSITY_TIERS` below is a page-fit mechanism: `render_resume_pdf`
  compiles at the most spacious tier, counts the resulting PDF's pages
  via `pypdf` (already a project dependency), and steps to the next
  tighter tier and recompiles if the content overflows `target_pages` --
  never shrinking past the last tier's floor (9.5pt body), so a resume
  adapts to however much content a given application's tailoring
  produced instead of needing per-application manual tuning.
"""
from __future__ import annotations

import re

import typst
from pypdf import PdfReader

from resume_manager.schema import MISSING_VALUE_PLACEHOLDERS

_TYPST_ESCAPE_RE = re.compile(r"[\\*_`$#<>@\[\]]")


def _escape_typst(value: str) -> str:
    """Escapes Typst markup syntax characters found in resume *content*
    (never in this module's own template strings) so they render as
    literal text instead of opening math/heading/reference/emphasis
    syntax -- e.g. a bullet containing "$1.5M" (real content in the
    user's actual resume) or an email address's "@" must not be
    interpreted as Typst markup."""
    return _TYPST_ESCAPE_RE.sub(lambda m: "\\" + m.group(0), value)


def _typst_string_literal(value: str) -> str:
    """Escapes a value for use inside a double-quoted Typst string
    argument (e.g. `link("...")`) -- only backslash and the closing quote
    need escaping there, distinct from `_escape_typst`'s markup escaping."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


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


def _work_experience_display_dates(entries: list[dict]) -> list[tuple[str | None, str | None]]:
    """Returns a (start, end) pair per entry to display, carrying forward
    the previous entry's real dates when this entry shares the same `org`
    and its own start/end are both the "Not specified" placeholder --
    confirmed real against the actual resume: multiple roles under one
    employer often share a single date range printed once, against only
    the first-listed role (the three-USAID-roles case). Only ever changes
    what's *displayed*; `resume_master.yaml`/`resume_master.review.yaml`
    keep storing the honest "Not specified" untouched."""
    result: list[tuple[str | None, str | None]] = []
    carry_org = carry_start = carry_end = None
    for entry in entries:
        org = entry.get("org")
        start, end = entry.get("start_date"), entry.get("end_date")
        if org == carry_org and _display(start) is None and _display(end) is None:
            result.append((carry_start, carry_end))
        else:
            result.append((start, end))
            carry_org, carry_start, carry_end = org, start, end
    return result


# Page-fit tiers, most spacious first. `render_resume_pdf` steps down this
# list only as far as needed to fit `target_pages`. The last tier is the
# legibility floor -- never shrunk further even if content still overflows.
_DENSITY_TIERS: list[dict] = [
    {
        "body_size": "10.5pt", "h1_size": "22pt", "h2_size": "13pt", "h3_size": "11pt",
        "list_spacing": "0.45em", "h2_above": "1.2em", "h3_above": "1.0em",
        "margin_h": "0.6in", "margin_top": "0.6in", "margin_bottom": "0.8in",
    },
    {
        "body_size": "10pt", "h1_size": "20pt", "h2_size": "12pt", "h3_size": "10.5pt",
        "list_spacing": "0.35em", "h2_above": "0.9em", "h3_above": "0.8em",
        "margin_h": "0.55in", "margin_top": "0.5in", "margin_bottom": "0.6in",
    },
    {
        "body_size": "9.5pt", "h1_size": "18pt", "h2_size": "11pt", "h3_size": "10pt",
        "list_spacing": "0.28em", "h2_above": "0.7em", "h3_above": "0.6em",
        "margin_h": "0.5in", "margin_top": "0.4in", "margin_bottom": "0.5in",
    },
]


def _build_preamble(tier: dict) -> str:
    return f"""
#set page(paper: "us-letter", margin: (top: {tier["margin_top"]}, right: {tier["margin_h"]}, bottom: {tier["margin_bottom"]}, left: {tier["margin_h"]}))
#set text(size: {tier["body_size"]}, fill: rgb("#333333"))
#set heading(numbering: none)
#set list(spacing: {tier["list_spacing"]})
#show heading.where(level: 1): it => align(center, block(below: 0.4em)[
  #text(size: {tier["h1_size"]}, fill: rgb("#111111"), upper(it.body))
])
#show heading.where(level: 2): it => block(above: {tier["h2_above"]}, below: 0.5em)[
  #text(size: {tier["h2_size"]}, fill: rgb("#003366"), tracking: 0.5pt, upper(it.body))
  #line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
]
#show heading.where(level: 3): it => block(above: {tier["h3_above"]}, below: 0.2em)[
  #text(size: {tier["h3_size"]}, weight: "bold", it.body)
]
#let job-heading(org, role, dates) = block(above: {tier["h3_above"]}, below: 0.2em)[
  #if dates == none [
    #text(size: {tier["h3_size"]}, weight: "bold", org)
  ] else [
    #grid(columns: (1fr, auto), column-gutter: 1em, align: (left, right),
      text(size: {tier["h3_size"]}, weight: "bold", org),
      text(size: {tier["h3_size"]}, weight: "bold", dates),
    )
  ]
  #text(size: {tier["h3_size"]}, style: "italic", role)
]
""".strip()


def _non_breakable_section(section_parts: list[str]) -> str:
    """Wraps a whole section's content (heading through its last entry) in
    one Typst non-breakable block (spec §13a) so it moves to the next page
    as one atomic unit instead of splitting mid-section -- confirmed
    empirically during planning (2026-09-26) that wrapping only the
    heading + first entry does NOT stop later entries from spilling
    independently onto the next page; the whole section must be one
    block. Never used for Work Experience, which must stay
    breakable/flowing since the fill loop in tailor_resume.py (spec §13b)
    deliberately grows its length to fill available space -- and because
    a non-breakable block's content silently clips at the page boundary
    if it's ever taller than one full page (confirmed empirically), never
    errors or flows to a new page, which would be a real risk for Work
    Experience's variable, potentially large size but isn't for the
    handful of entries Education/Awards/Publications/Skills realistically
    contain."""
    return "#block(breakable: false)[\n" + "\n\n".join(section_parts) + "\n]"


def build_typst(resume: dict, tier: dict | None = None) -> str:
    """Pure templating, no I/O, no LLM -- the same input and tier always
    produce the same output (spec §6)."""
    tier = tier or _DENSITY_TIERS[0]
    parts: list[str] = [_build_preamble(tier)]

    contact = resume.get("contact") or {}
    name = _display(contact.get("name"))
    if name:
        parts.append(f"= {_escape_typst(name)}")
    contact_line = " • ".join(
        _escape_typst(value) for value in [
            # Confirmed real preference (2026-09-26): location dropped so
            # the contact line fits one line -- it's omitted here, not in
            # `_display()`, since resume_master.yaml's location field is
            # still real, useful data elsewhere (verification, etc.).
            _display(contact.get("email")),
            _display(contact.get("linkedin_url")), _display(contact.get("github_url")),
            _display(contact.get("website_url")),
        ] if value
    )
    if contact_line:
        parts.append(f"#align(center)[{contact_line}]")

    if resume.get("work_experience"):
        parts.append("== Work Experience")
        display_dates = _work_experience_display_dates(resume["work_experience"])
        for entry, (start, end) in zip(resume["work_experience"], display_dates):
            date_range = _date_range(start, end)
            org = _escape_typst(entry["org"])
            role = _escape_typst(entry["role"])
            dates_arg = f"[{_escape_typst(date_range)}]" if date_range else "none"
            parts.append(f"#job-heading([{org}], [{role}], {dates_arg})")
            location = _display(entry.get("location"))
            if location:
                parts.append(_escape_typst(location))
            bullets = "\n".join(f"- {_escape_typst(b)}" for b in entry.get("bullets") or [])
            if bullets:
                parts.append(bullets)

    if resume.get("education"):
        section_parts = ["== Education"]
        for entry in resume["education"]:
            section_parts.append(f"=== {_escape_typst(entry['institution'])}")
            degree = _display(entry.get("degree")) or ""
            gpa = _display(entry.get("gpa"))
            degree_line = f"{_escape_typst(degree)} • GPA: {_escape_typst(gpa)}" if gpa else _escape_typst(degree)
            location = _display(entry.get("location"))
            date_range = _date_range(entry.get("start_date"), entry.get("end_date"))
            location_date_line = " • ".join(
                _escape_typst(value) for value in [location, date_range] if value
            )
            thesis = _display(entry.get("thesis"))
            lines = []
            if degree_line:
                lines.append(f"- {degree_line}")
            if location_date_line:
                lines.append(f"- {location_date_line}")
            if thesis:
                lines.append(f"- Thesis: {_escape_typst(thesis)}")
            if lines:
                section_parts.append("\n".join(lines))
        parts.append(_non_breakable_section(section_parts))

    if resume.get("awards"):
        section_parts = ["== Awards & Scholarships"]
        lines = []
        for entry in resume["awards"]:
            line = f"- {_escape_typst(entry['name'])} ({_escape_typst(entry['date'])})"
            description = _display(entry.get("description"))
            if description:
                line += f" — {_escape_typst(description)}"
            lines.append(line)
        section_parts.append("\n".join(lines))
        parts.append(_non_breakable_section(section_parts))

    if resume.get("publications"):
        section_parts = ["== Research Presentations & Publications"]
        lines = []
        for entry in resume["publications"]:
            line = (
                f"- {_escape_typst(entry['title'])} ({_escape_typst(entry['date'])}) "
                f"— {_escape_typst(entry['venue'])}"
            )
            link = _display(entry.get("link"))
            if link:
                line += f' (#link("{_typst_string_literal(link)}")[link])'
            lines.append(line)
        section_parts.append("\n".join(lines))
        parts.append(_non_breakable_section(section_parts))

    if resume.get("skills"):
        section_parts = ["== Skills"]
        for entry in resume["skills"]:
            items = ", ".join(_escape_typst(item) for item in entry.get("items") or [])
            section_parts.append(f"*{_escape_typst(entry['category'])}*: {items}")
        parts.append(_non_breakable_section(section_parts))

    return "\n\n".join(parts)


def _pdf_page_count(path: str) -> int:
    return len(PdfReader(path).pages)


def render_resume_pdf(resume: dict, output_path: str, target_pages: int = 2) -> int:
    """Templates `resume` to Typst markup, writes it alongside the PDF as
    `<output_path minus extension>.typ` (a debuggable intermediate
    artifact, the same role `resume_raw.md` plays for extraction), then
    compiles it to `output_path` via the `typst` package. Steps down
    `_DENSITY_TIERS` (spacious -> tight) and recompiles whenever the
    result overflows `target_pages`, stopping at the first tier that fits
    or the last tier regardless -- a real overflow at the tightest tier is
    a signal to trim entries during tailoring, not to shrink text below a
    readable floor. Returns the final compiled PDF's page count (spec
    §13b: `tailor_resume.py`'s fill loop uses this return value directly
    to decide how many Work Experience entries fit, instead of a separate
    page-count call). Raises if `typst.compile` reports an error -- an
    application's PDF is either fully written or not written at all,
    never a silently-broken partial file."""
    typst_path = re.sub(r"\.pdf$", ".typ", output_path, flags=re.IGNORECASE)
    if typst_path == output_path:
        typst_path = output_path + ".typ"
    page_count = 0
    for tier in _DENSITY_TIERS:
        typst_source = build_typst(resume, tier)
        with open(typst_path, "w", encoding="utf-8") as f:
            f.write(typst_source)
        typst.compile(typst_path, output=output_path)
        page_count = _pdf_page_count(output_path)
        if page_count <= target_pages:
            return page_count
    return page_count
