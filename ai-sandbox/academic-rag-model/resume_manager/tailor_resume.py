"""
tailor_resume.py
CLI entry point for one application: tailor -> validate -> render (spec
§4-§7 Revision 2). Run per job application, after the bootstrap
(convert_resume.py) has produced resume_master.yaml.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
from pathlib import Path

import yaml

from resume_manager.render import render_resume_pdf
from resume_manager.tailor import apply_tailoring, generate_clarifying_questions, tailor_resume
from resume_manager.validate import format_report, validate_tailored

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-") or "application"


def collect_answers_interactively(questions: list[str]) -> list[str]:
    """Prints each question and reads one free-text answer via input() --
    the only I/O in this module's --interactive flow (spec §11)."""
    return [input(f"{question}\n> ") for question in questions]


def build_guidance_text(questions: list[str], answers: list[str]) -> str:
    """Pairs each question with its answer into one guidance block --
    pure formatting, no I/O, so it's testable without mocking input()
    (spec §11). Serves double duty: passed to tailor_resume() as prompt
    guidance, and written verbatim as guidance.txt's human-readable
    transcript."""
    return "\n\n".join(f"Q: {question}\nA: {answer}" for question, answer in zip(questions, answers))


def _collect_guidance(master_resume_path: str, jd_path: str) -> str | None:
    """Runs the --interactive Q&A step (spec §11): generates clarifying
    questions from the master resume + JD via the local Ollama model,
    collects free-text answers from the terminal, and returns the
    combined guidance text. Returns None -- printing a warning, never
    raising -- if question generation failed, so a bad/unreachable
    Ollama call never aborts the whole --interactive run (spec §8)."""
    with open(master_resume_path, "r", encoding="utf-8") as f:
        master = yaml.safe_load(f)
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    questions = generate_clarifying_questions(master, job_description)
    if not questions:
        print(
            "WARNING: could not generate clarifying questions (Ollama unreachable, timed out, "
            "or returned an unexpected response) -- continuing without guidance."
        )
        return None

    answers = collect_answers_interactively(questions)
    return build_guidance_text(questions, answers)


def run_tailoring(
    master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str,
    guidance: str | None = None,
) -> str:
    """Runs tailor -> validate -> render for one application and returns
    a one-line status message. Raises FileNotFoundError up front if
    either input file is missing, before any Ollama call (spec §8).
    `guidance` (spec §11) is optional free text from --interactive's Q&A
    step -- None reproduces today's non-interactive behavior exactly."""
    if not os.path.exists(master_resume_path):
        raise FileNotFoundError(f"{master_resume_path} not found -- run convert_resume.py's bootstrap first.")
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"job description file not found: {jd_path}")

    with open(master_resume_path, "r", encoding="utf-8") as f:
        master = yaml.safe_load(f)
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    tailoring_result = tailor_resume(master, job_description, guidance=guidance)
    if tailoring_result is None:
        raise RuntimeError(
            "local Ollama tailoring call failed, timed out, or returned invalid YAML -- "
            "is `ollama serve` running?"
        )

    tailored, reconstruction_problems = apply_tailoring(master, tailoring_result)

    date_str = datetime.date.today().isoformat()
    app_dir = os.path.join(resume_manager_dir, "applications", f"{date_str}-{_slugify(application_name)}")
    os.makedirs(app_dir, exist_ok=True)

    with open(os.path.join(app_dir, "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_description)
    if guidance:
        with open(os.path.join(app_dir, "guidance.txt"), "w", encoding="utf-8") as f:
            f.write(guidance)
    with open(os.path.join(app_dir, "tailored_resume.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(tailored, f, sort_keys=False, allow_unicode=True)

    problems = reconstruction_problems + validate_tailored(master, tailoring_result)
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
    parser.add_argument(
        "--interactive", action="store_true",
        help="Ask 2-4 JD-grounded clarifying questions before tailoring, to steer entry selection and bullet framing.",
    )
    args = parser.parse_args()

    master_resume_path = os.path.join(args.resume_manager_dir, "resume_master.yaml")
    guidance = _collect_guidance(master_resume_path, args.jd_file) if args.interactive else None
    print(run_tailoring(master_resume_path, args.jd_file, args.application_name, args.resume_manager_dir, guidance=guidance))


if __name__ == "__main__":
    main()
