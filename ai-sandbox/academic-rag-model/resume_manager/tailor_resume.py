"""
tailor_resume.py
CLI entry point for one application: tailor -> validate -> render
(spec §4-§7). Run per job application, after the bootstrap
(convert_resume.py) has produced resume_master.md.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
from pathlib import Path

from resume_manager.render import render_resume_pdf
from resume_manager.tailor import tailor_resume
from resume_manager.validate import format_report, validate_tailored

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "application"


def run_tailoring(master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str) -> str:
    """Runs tailor -> validate -> render for one application and
    returns a one-line status message. Raises FileNotFoundError up
    front if either input file is missing, before any Ollama call
    (spec §8)."""
    if not os.path.exists(master_resume_path):
        raise FileNotFoundError(f"{master_resume_path} not found -- run convert_resume.py's bootstrap first.")
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"job description file not found: {jd_path}")

    with open(master_resume_path, "r", encoding="utf-8") as f:
        master_resume = f.read()
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    tailored = tailor_resume(master_resume, job_description)
    if tailored is None:
        raise RuntimeError("local Ollama tailoring call failed or timed out -- is `ollama serve` running?")

    date_str = datetime.date.today().isoformat()
    app_dir = os.path.join(resume_manager_dir, "applications", f"{date_str}-{_slugify(application_name)}")
    os.makedirs(app_dir, exist_ok=True)

    with open(os.path.join(app_dir, "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_description)
    with open(os.path.join(app_dir, "tailored_resume.md"), "w", encoding="utf-8") as f:
        f.write(tailored)

    problems = validate_tailored(master_resume, tailored)
    report = format_report(problems)
    with open(os.path.join(app_dir, "validation_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)

    pdf_path = os.path.join(app_dir, "Tailored_Resume.pdf")
    render_resume_pdf(tailored, pdf_path)

    return f"Wrote {pdf_path}.\n{report}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Tailor the master resume to one job description and render a PDF.")
    parser.add_argument("--jd-file", required=True, help="Path to a local text file containing the job description.")
    parser.add_argument("--application-name", required=True, help="Short name for this application (e.g. 'acme-corp').")
    parser.add_argument("--resume-manager-dir", default=str(_DEFAULT_RESUME_MANAGER_DIR))
    args = parser.parse_args()

    master_resume_path = os.path.join(args.resume_manager_dir, "resume_master.md")
    print(run_tailoring(master_resume_path, args.jd_file, args.application_name, args.resume_manager_dir))


if __name__ == "__main__":
    main()
