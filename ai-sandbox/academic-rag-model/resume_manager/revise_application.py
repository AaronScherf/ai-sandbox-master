"""
revise_application.py
Deterministic post-processing for an already-tailored application. Makes a
small, code-only edit (currently: dropping one work_experience entry) to
`tailored_resume.yaml` without any Ollama or Gemini call, then keeps
`tailored_resume.md`, the rendered PDF, and `validation_report.txt`
consistent with the edit. Never opens `resume_master.yaml` for writing, and
never touches `job_description.txt` or `guidance.txt` -- those describe the
original request, not the tailored result, and stay as the record of what
was asked for.
"""
from __future__ import annotations

import argparse
import os
import re

import yaml

from resume_manager.markdown_sync import export_to_markdown
from resume_manager.render import render_resume_pdf
from resume_manager.user_facts import load_user_facts
from resume_manager.validate import format_report, validate_tailored

_BRAINSTORM_STATUS_RE = re.compile(r"^Relevance brainstorm: (.+)\.\s*$")
_UNKNOWN_BRAINSTORM_STATUS = "unknown (original validation report predates Gemini-status tracking)"


def _resume_manager_dir_for(app_dir: str) -> str:
    """Applications live at `<resume_manager_dir>/applications/<name>`
    (tailor_resume.py's own `run_tailoring` lays them out this way) -- so
    the resume-manager root is two directories up, unless overridden."""
    return os.path.dirname(os.path.dirname(os.path.abspath(app_dir)))


def _previous_brainstorm_status(app_dir: str) -> str:
    """Reads the first line of the application's existing
    validation_report.txt to carry its recorded Gemini status forward.
    Falls back to an explicit "unknown" label (never a silent "not used")
    for a report written before this line existed, so a revision can never
    misrepresent whether Gemini was actually used."""
    report_path = os.path.join(app_dir, "validation_report.txt")
    if not os.path.exists(report_path):
        return _UNKNOWN_BRAINSTORM_STATUS
    with open(report_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    match = _BRAINSTORM_STATUS_RE.match(first_line)
    return match.group(1) if match else _UNKNOWN_BRAINSTORM_STATUS


def remove_work_experience_entry(
    app_dir: str, entry_id: str, resume_manager_dir: str | None = None, target_pages: int = 2,
) -> str:
    """Removes one work_experience entry (by id) from an already-tailored
    application, in place. Raises FileNotFoundError if `app_dir` or its
    `tailored_resume.yaml` doesn't exist, or ValueError if `entry_id` isn't
    one of its entries -- both checked before any file is read for editing
    or written, so a bad call leaves every existing output untouched.

    `resume_manager_dir` defaults to the resume-manager root inferred from
    `app_dir`'s own location; pass it explicitly if `app_dir` was moved out
    of that layout. The master resume is only ever opened for reading (to
    re-run the same per-entry fact-diff and user-fact coverage checks
    `validate_tailored` always uses) -- this function never writes to it.
    """
    if not os.path.isdir(app_dir):
        raise FileNotFoundError(f"application directory not found: {app_dir}")
    tailored_path = os.path.join(app_dir, "tailored_resume.yaml")
    if not os.path.exists(tailored_path):
        raise FileNotFoundError(
            f"{tailored_path} not found -- is {app_dir!r} a tailored application directory?"
        )
    with open(tailored_path, "r", encoding="utf-8") as f:
        tailored = yaml.safe_load(f)

    work_experience = tailored.get("work_experience") or []
    if not any(entry.get("id") == entry_id for entry in work_experience):
        raise ValueError(f"entry id {entry_id!r} not found in {tailored_path}")

    resume_manager_dir = resume_manager_dir or _resume_manager_dir_for(app_dir)
    master_resume_path = os.path.join(resume_manager_dir, "resume_master.yaml")
    if not os.path.exists(master_resume_path):
        raise FileNotFoundError(
            f"{master_resume_path} not found -- cannot re-validate without the master resume "
            "(pass resume_manager_dir if the application directory was moved)."
        )
    with open(master_resume_path, "r", encoding="utf-8") as f:
        master = yaml.safe_load(f)

    user_facts_path = os.path.join(app_dir, "user_facts.yaml")
    user_facts = load_user_facts(user_facts_path, master) if os.path.exists(user_facts_path) else None

    brainstorm_status = _previous_brainstorm_status(app_dir)

    tailored["work_experience"] = [e for e in work_experience if e.get("id") != entry_id]

    with open(tailored_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(tailored, f, sort_keys=False, allow_unicode=True)
    with open(os.path.join(app_dir, "tailored_resume.md"), "w", encoding="utf-8") as f:
        f.write(export_to_markdown(tailored))

    problems = validate_tailored(master, tailored, user_facts=user_facts)
    report = format_report(problems, brainstorm_status=brainstorm_status)
    with open(os.path.join(app_dir, "validation_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)

    pdf_path = os.path.join(app_dir, "Tailored_Resume.pdf")
    render_resume_pdf(tailored, pdf_path, target_pages=target_pages)

    return f"Removed '{entry_id}' from {app_dir}. Wrote {pdf_path}.\n{report}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Remove one work_experience entry from an already-tailored application's saved output, "
            "without any Ollama or Gemini call -- keeps tailored_resume.yaml/.md, the rendered PDF, "
            "and validation_report.txt in sync."
        ),
    )
    parser.add_argument("--app-dir", required=True, help="Path to the application directory (contains tailored_resume.yaml).")
    parser.add_argument(
        "--remove-entry-id", required=True,
        help="work_experience id to remove (see tailored_resume.md's <!-- id: ... --> comments, or tailored_resume.yaml's 'id' fields).",
    )
    parser.add_argument(
        "--resume-manager-dir", default=None,
        help="Override the resume-manager root used to re-read resume_master.yaml (default: inferred from --app-dir).",
    )
    args = parser.parse_args()
    print(remove_work_experience_entry(args.app_dir, args.remove_entry_id, args.resume_manager_dir))


if __name__ == "__main__":
    main()
