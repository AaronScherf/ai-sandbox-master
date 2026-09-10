"""
convert_resume.py
One-off bootstrap: copies the source resume PDF into resume-manager/,
extracts it locally, deterministically parses it into the structured
schema (no LLM call -- spec §3 Revision 3), and verifies that parse
before trusting it. Not part of the per-application pipeline -- run once,
or re-run if the source PDF changes.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import yaml

from resume_manager.extract import DefectivePageError, extract_resume_text
from resume_manager.normalize import extract_resume_schema, verify_extraction
from resume_manager.schema import assign_ids

_DEFAULT_SOURCE_PDF = (
    Path(__file__).resolve().parent.parent.parent / "personal-website" / "AaronScherf.github.io"
    / "static" / "uploads" / "resume.pdf"
)
_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)


def bootstrap_resume(source_pdf: str, resume_manager_dir: str) -> str:
    """Runs the full bootstrap (spec §3) and returns a one-line status
    message. A DefectivePageError from extraction propagates -- that's
    meant to stop the run for the user's direct attention (spec §8). An
    extraction-verification mismatch does NOT raise -- that's the expected
    "flag for review" path."""
    os.makedirs(resume_manager_dir, exist_ok=True)
    dest_pdf = os.path.join(resume_manager_dir, "resume.pdf")
    shutil.copyfile(source_pdf, dest_pdf)

    raw_text = extract_resume_text(dest_pdf)
    processed_dir = os.path.join(resume_manager_dir, "processed_outputs")
    os.makedirs(processed_dir, exist_ok=True)
    raw_path = os.path.join(processed_dir, "resume_raw.md")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_text)

    parsed = extract_resume_schema(raw_text)
    if parsed is None:
        return (
            f"Extraction wrote {raw_path}, but the deterministic parser didn't recognize this "
            f"document's structure -- see the WARNING above for exactly which section/line "
            f"didn't match, and either adjust the source PDF's formatting or extend "
            f"resume_manager/normalize.py's parsing rules."
        )

    assign_ids(parsed.get("work_experience") or [], "org")
    assign_ids(parsed.get("education") or [], "institution")

    problems = verify_extraction(parsed, raw_text)
    master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
    if not problems:
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(parsed, f, sort_keys=False, allow_unicode=True)
        return f"Wrote {master_path} (extraction verified clean)."

    review_path = os.path.join(resume_manager_dir, "resume_master.review.yaml")
    with open(review_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(parsed, f, sort_keys=False, allow_unicode=True)
    report = "\n".join(f"- {p}" for p in problems)
    return (
        f"Extraction verification flagged {len(problems)} issue(s) -- wrote {review_path} "
        f"for manual review instead of {master_path}:\n{report}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-off bootstrap: convert resume.pdf into the structured master resume.",
    )
    parser.add_argument("--source-pdf", default=str(_DEFAULT_SOURCE_PDF))
    parser.add_argument("--resume-manager-dir", default=str(_DEFAULT_RESUME_MANAGER_DIR))
    args = parser.parse_args()

    try:
        print(bootstrap_resume(args.source_pdf, args.resume_manager_dir))
    except DefectivePageError as err:
        print(f"ERROR: {err}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
