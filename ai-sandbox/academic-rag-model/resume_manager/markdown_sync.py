"""
markdown_sync.py
Two-way Markdown editing for resume_master.yaml and a per-application
tailored_resume.yaml (spec §14): export_to_markdown() renders a resume
dict as a hand-editable Markdown file; import_from_markdown() parses one
back into the same dict shape.

Deliberately NOT the same compact, prose-style Markdown render.py builds
for the final PDF (spec §6) -- that format drops missing/placeholder
fields and never needs to be parsed back, so it can freely omit anything
not worth showing a reader. This format's job is reliable round-tripping
of a hand-edited file back into structured data, so every field gets an
explicit "- Label: value" line (including the literal "Not specified"
placeholder where that's the real stored value) -- unambiguous to parse
and, since the audience here is editing data rather than reading a
finished resume, more useful to see than a cosmetically-cleaned view.

Work Experience and Education entries carry their `id` as an invisible
`<!-- id: ... -->` marker so a re-import can match an edited entry back
to the right one; Awards/Publications/Skills have no id scheme in the
schema (spec §3) and are simply rebuilt wholesale from whatever entries
appear in the file, in order.
"""
from __future__ import annotations

import hashlib
import re

import yaml

_ID_COMMENT_RE = re.compile(r"^<!--\s*id:\s*(.+?)\s*-->$")
_HASH_COMMENT_RE = re.compile(r"^<!--\s*resume-master-yaml-hash:\s*([0-9a-f]+)\s*-->\s*\n*")
_LABEL_LINE_RE = re.compile(r"^-\s*([A-Za-z ]+):\s*(.*)$")

_CONTACT_FIELDS = [
    ("Location", "location"), ("Email", "email"), ("LinkedIn", "linkedin_url"),
    ("GitHub", "github_url"), ("Website", "website_url"),
]
_WORK_EXPERIENCE_FIELDS = [("Location", "location"), ("Start", "start_date"), ("End", "end_date")]
_EDUCATION_FIELDS = [
    ("Degree", "degree"), ("GPA", "gpa"), ("Location", "location"),
    ("Start", "start_date"), ("End", "end_date"), ("Thesis", "thesis"),
]
_AWARD_FIELDS = [("Description", "description"), ("Date", "date")]
_PUBLICATION_FIELDS = [("Date", "date"), ("Venue", "venue"), ("Link", "link")]


def compute_yaml_hash(resume: dict) -> str:
    """Stable hash of a resume dict's canonical YAML form. `sync_master_md.py`
    embeds this at export time and checks it again at import time, to
    detect whether resume_master.yaml changed in between (e.g. via a
    merge_resumes.py run) -- the guard against a stale hand-edit silently
    clobbering an auto-merged addition it never saw."""
    canonical = yaml.safe_dump(resume, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _field_lines(entry: dict, fields: list[tuple[str, str]]) -> list[str]:
    return [f"- {label}: {entry.get(key, '')}" for label, key in fields if entry.get(key) is not None]


def export_to_markdown(resume: dict, embed_hash: bool = False) -> str:
    """Pure formatting, no I/O. `embed_hash=True` (used for the ongoing
    master resume, never for a one-off per-application tailored resume)
    prepends a hash of `resume`'s canonical YAML as an invisible comment,
    consumed by `sync_master_md.py`'s staleness guard."""
    parts: list[str] = []
    if embed_hash:
        parts.append(f"<!-- resume-master-yaml-hash: {compute_yaml_hash(resume)} -->")

    contact = resume.get("contact") or {}
    if contact.get("name"):
        parts.append(f"# {contact['name']}")
    contact_lines = _field_lines(contact, _CONTACT_FIELDS)
    if contact_lines:
        parts.append("\n".join(contact_lines))

    if resume.get("work_experience"):
        parts.append("## Work Experience")
        for entry in resume["work_experience"]:
            block = [f"### {entry['org']} — {entry['role']}"]
            if entry.get("id"):
                block.append(f"<!-- id: {entry['id']} -->")
            block.extend(_field_lines(entry, _WORK_EXPERIENCE_FIELDS))
            parts.append("\n".join(block))
            bullets = entry.get("bullets") or []
            if bullets:
                parts.append("Bullets:\n" + "\n".join(f"- {b}" for b in bullets))

    if resume.get("education"):
        parts.append("## Education")
        for entry in resume["education"]:
            block = [f"### {entry['institution']}"]
            if entry.get("id"):
                block.append(f"<!-- id: {entry['id']} -->")
            block.extend(_field_lines(entry, _EDUCATION_FIELDS))
            parts.append("\n".join(block))

    if resume.get("awards"):
        parts.append("## Awards & Scholarships")
        for entry in resume["awards"]:
            block = [f"### {entry['name']}"]
            block.extend(_field_lines(entry, _AWARD_FIELDS))
            parts.append("\n".join(block))

    if resume.get("publications"):
        parts.append("## Research Presentations & Publications")
        for entry in resume["publications"]:
            block = [f"### {entry['title']}"]
            block.extend(_field_lines(entry, _PUBLICATION_FIELDS))
            parts.append("\n".join(block))

    if resume.get("skills"):
        parts.append("## Skills")
        for entry in resume["skills"]:
            block = [f"### {entry['category']}"]
            block.extend(f"- {item}" for item in entry.get("items") or [])
            parts.append("\n".join(block))

    return "\n\n".join(parts) + "\n"


def _parse_labeled_lines(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = _LABEL_LINE_RE.match(line.strip())
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def extract_embedded_hash(markdown_text: str) -> str | None:
    """Returns the hash embedded by `export_to_markdown(..., embed_hash=True)`,
    or None if `markdown_text` has no such marker. `sync_master_md.py`
    compares this against `compute_yaml_hash()` of the *current*
    resume_master.yaml to detect a stale export before overwriting it."""
    match = _HASH_COMMENT_RE.match(markdown_text)
    return match.group(1) if match else None


def _apply_labeled_fields(entry: dict, lines: list[str], field_map: list[tuple[str, str]]) -> None:
    fields = _parse_labeled_lines(lines)
    for label, key in field_map:
        if label in fields:
            entry[key] = fields[label]


def import_from_markdown(markdown_text: str) -> dict:
    """Parses Markdown produced by `export_to_markdown()` back into a
    resume dict of the same shape as resume_master.yaml/
    tailored_resume.yaml. Strips a leading hash comment if present (that
    marker is for `sync_master_md.py`'s own staleness check, not resume
    content). A block this parser doesn't recognize is silently ignored
    rather than raising -- this format is meant for direct hand-editing,
    where stray text (a comment-to-self, a blank scratch line) is normal,
    not an error to fail on."""
    text = _HASH_COMMENT_RE.sub("", markdown_text, count=1)
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]

    resume: dict = {
        "contact": {}, "work_experience": [], "education": [],
        "awards": [], "publications": [], "skills": [],
    }
    section: str | None = None
    current: dict | None = None

    for block in blocks:
        lines = block.split("\n")
        first = lines[0].strip()

        if first.startswith("# "):
            resume["contact"]["name"] = first[2:].strip()
            continue
        if first == "## Work Experience":
            section, current = "work_experience", None
            continue
        if first == "## Education":
            section, current = "education", None
            continue
        if first == "## Awards & Scholarships":
            section, current = "awards", None
            continue
        if first == "## Research Presentations & Publications":
            section, current = "publications", None
            continue
        if first == "## Skills":
            section, current = "skills", None
            continue

        if section is None:
            _apply_labeled_fields(resume["contact"], lines, _CONTACT_FIELDS)
            continue

        if first.startswith("### "):
            heading_text = first[4:].strip()
            if section == "work_experience":
                org, _, role = heading_text.partition(" — ")
                current = {"org": org.strip(), "role": role.strip(), "bullets": []}
                resume["work_experience"].append(current)
                id_match = len(lines) > 1 and _ID_COMMENT_RE.match(lines[1].strip())
                if id_match:
                    current["id"] = id_match.group(1)
                    lines = [lines[0]] + lines[2:]
                _apply_labeled_fields(current, lines[1:], _WORK_EXPERIENCE_FIELDS)
            elif section == "education":
                current = {"institution": heading_text}
                resume["education"].append(current)
                id_match = len(lines) > 1 and _ID_COMMENT_RE.match(lines[1].strip())
                if id_match:
                    current["id"] = id_match.group(1)
                    lines = [lines[0]] + lines[2:]
                _apply_labeled_fields(current, lines[1:], _EDUCATION_FIELDS)
            elif section == "awards":
                current = {"name": heading_text}
                resume["awards"].append(current)
                _apply_labeled_fields(current, lines[1:], _AWARD_FIELDS)
            elif section == "publications":
                current = {"title": heading_text}
                resume["publications"].append(current)
                _apply_labeled_fields(current, lines[1:], _PUBLICATION_FIELDS)
            elif section == "skills":
                current = {"category": heading_text, "items": [l.strip()[2:].strip() for l in lines[1:] if l.strip().startswith("- ")]}
                resume["skills"].append(current)
            continue

        if first == "Bullets:" and section == "work_experience" and current is not None:
            current["bullets"] = [l.strip()[2:].strip() for l in lines[1:] if l.strip().startswith("- ")]
            continue

    return resume
