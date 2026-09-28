"""
sync_tailored_md.py
Syncs a hand-edited tailored_resume.md back into tailored_resume.yaml and
re-renders Tailored_Resume.pdf from it (spec §14) -- the write-back half
of the two-way Markdown editing loop for one application's tailored
resume. No staleness guard is needed here (unlike sync_master_md.py):
nothing else writes to a given application's own files after
tailor_resume.py finishes, so there's no concurrent writer this could
conflict with.
"""
from __future__ import annotations

import argparse
import os

import yaml

from resume_manager.markdown_sync import export_to_markdown, import_from_markdown
from resume_manager.render import render_resume_pdf


def sync_tailored_md(application_dir: str, target_pages: int = 2) -> str:
    """Reads tailored_resume.md in `application_dir`, overwrites
    tailored_resume.yaml with the parsed content, re-exports the .md
    (so it stays byte-consistent with whatever normalization the parse/
    re-render applied), and re-renders Tailored_Resume.pdf from it.
    Returns a one-line status message; raises FileNotFoundError if the
    .md file doesn't exist."""
    tailored_md_path = os.path.join(application_dir, "tailored_resume.md")
    tailored_yaml_path = os.path.join(application_dir, "tailored_resume.yaml")
    if not os.path.exists(tailored_md_path):
        raise FileNotFoundError(f"{tailored_md_path} not found -- nothing to sync.")

    with open(tailored_md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    tailored = import_from_markdown(markdown_text)
    with open(tailored_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(tailored, f, sort_keys=False, allow_unicode=True)
    with open(tailored_md_path, "w", encoding="utf-8") as f:
        f.write(export_to_markdown(tailored))

    pdf_path = os.path.join(application_dir, "Tailored_Resume.pdf")
    render_resume_pdf(tailored, pdf_path, target_pages=target_pages)

    return f"Synced {tailored_md_path} -> {tailored_yaml_path} and re-rendered {pdf_path}."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync a hand-edited tailored_resume.md back into tailored_resume.yaml and re-render the PDF.",
    )
    parser.add_argument("--application-dir", required=True, help="Path to one application's output folder.")
    args = parser.parse_args()
    print(sync_tailored_md(args.application_dir))


if __name__ == "__main__":
    main()
