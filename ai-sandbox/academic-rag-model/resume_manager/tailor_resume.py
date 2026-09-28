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
import tempfile
from pathlib import Path

import yaml

from resume_manager.markdown_sync import export_to_markdown
from resume_manager.render import render_resume_pdf
from resume_manager.tailor import apply_tailoring, generate_clarifying_questions, tailor_resume
from resume_manager.validate import format_report, validate_tailored
from resume_manager.user_facts import load_user_facts, validate_user_facts

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


def _select_work_experience_bullets(
    master: dict, tailoring_result: dict, target_pages: int, scratch_pdf_path: str,
) -> dict[str, int]:
    """Greedy render-measure-retry search (spec §13b), at bullet
    granularity -- replaces an earlier whole-entry-only version that left
    a large blank gap at the bottom of page 1 whenever the *next entire
    entry* didn't fit, even though there was clearly room for more of it.

    Walks `ranked_ids` in order; for each entry, tries adding its bullets
    one at a time (in their given order -- already the most-to-least
    important order within that entry). After each single addition,
    re-renders to `scratch_pdf_path` (never the application's real output
    path) and checks the real page count. The result (a map of entry id
    to how many of its bullets to include) grows for as long as each
    successive addition still fits `target_pages`; the search stops
    entirely, across all remaining entries and bullets, at the first
    addition that doesn't fit -- page count only ever grows as more
    content is added, so nothing added after a failure would fit either.
    An entry whose very first bullet doesn't fit is left out of the
    returned map entirely (an entry can't be shown with zero bullets).
    The single exception: if the map would otherwise be empty (not even
    one entry's first bullet fit), the top-ranked entry's first bullet is
    included anyway -- an inherent overflow at the readable floor
    (render_resume_pdf's own density-tier loop, §6) is accepted rather
    than producing a resume with zero Work Experience.

    Runs entirely at the fill loop's own level -- render_resume_pdf's
    density-tier shrinking is still free to kick in per attempt, but this
    search never treats "a tighter tier would let me add more" as a
    reason to keep going; it only asks "does this candidate fit," the
    same question at every step, using whatever page count
    render_resume_pdf actually reports."""
    master_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    ranked_ids = tailoring_result.get("ranked_ids") or []
    bullets_by_id = tailoring_result.get("bullets_by_id") or {}
    # Reserve the last page for Education/Awards/Publications/Skills (2026-
    # 09-28 layout fix): render.py's forced page break guarantees they
    # start fresh on whatever page follows Work Experience, so this loop
    # must measure Work Experience *in isolation* against the pages left
    # for it -- otherwise a heavy static section (real, confirmed: the
    # actual master's Skills section alone took 2 full pages) crowds out
    # Work Experience's own growth, or forces everything to a cramped
    # density tier just to make both fit together. Falls back to today's
    # combined-budget measurement for a single-page target, where there's
    # no second page to reserve anything for.
    reserve_last_page_for_static = target_pages >= 2
    work_experience_target_pages = target_pages - 1 if reserve_last_page_for_static else target_pages
    budget: dict[str, int] = {}
    for entry_id in ranked_ids:
        source = master_by_id.get(entry_id)
        if source is None:
            continue  # unknown id -- apply_tailoring reports/skips it; nothing to size here
        # Real, confirmed bug this fixes (2026-09-26): falls back to the
        # entry's original master bullets, exactly like apply_tailoring
        # already does -- a lower-ranked entry the LLM ranked but forgot
        # to rewrite bullets for was being treated as having zero
        # bullets and silently skipped with no attempt at all, even when
        # there was clearly still room for more content.
        all_bullets = bullets_by_id.get(entry_id) or source["bullets"]
        total_bullets = len(all_bullets)
        for n in range(1, total_bullets + 1):
            candidate, _ = apply_tailoring(
                master, tailoring_result, bullet_budget={**budget, entry_id: n},
                include_static_sections=not reserve_last_page_for_static,
            )
            page_count = render_resume_pdf(candidate, scratch_pdf_path, target_pages=work_experience_target_pages)
            if page_count <= work_experience_target_pages:
                budget[entry_id] = n
            else:
                if not budget and ranked_ids:
                    budget[ranked_ids[0]] = 1
                return budget
    return budget


def run_tailoring(
    master_resume_path: str, jd_path: str, application_name: str, resume_manager_dir: str,
    guidance: str | None = None, target_pages: int = 2, user_facts: list[dict] | None = None,
    brainstorm_status: str = "not used",
) -> str:
    """Runs tailor -> validate -> render for one application and returns
    a one-line status message. Raises FileNotFoundError up front if
    either input file is missing, before any Ollama call (spec §8).
    `guidance` (spec §11) is optional free text from --interactive's Q&A
    step -- None reproduces today's non-interactive behavior exactly.
    `target_pages` (spec §13b, Revision 6) drives the render-measure-retry
    fill loop that decides how many ranked Work Experience entries to
    include, filling available space up to that page budget."""
    if not os.path.exists(master_resume_path):
        raise FileNotFoundError(f"{master_resume_path} not found -- run convert_resume.py's bootstrap first.")
    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"job description file not found: {jd_path}")

    with open(master_resume_path, "r", encoding="utf-8") as f:
        master = yaml.safe_load(f)
    user_facts = validate_user_facts(user_facts, master)
    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    tailoring_result = tailor_resume(master, job_description, guidance=guidance, user_facts=user_facts)
    if tailoring_result is None:
        raise RuntimeError(
            "local Ollama tailoring call failed, timed out, or returned invalid YAML -- "
            "is `ollama serve` running?"
        )

    with tempfile.TemporaryDirectory() as scratch_dir:
        bullet_budget = _select_work_experience_bullets(
            master, tailoring_result, target_pages, os.path.join(scratch_dir, "scratch.pdf"),
        )

    tailored, reconstruction_problems = apply_tailoring(master, tailoring_result, bullet_budget=bullet_budget)

    date_str = datetime.date.today().isoformat()
    app_dir = os.path.join(resume_manager_dir, "applications", f"{date_str}-{_slugify(application_name)}")
    os.makedirs(app_dir, exist_ok=True)

    with open(os.path.join(app_dir, "job_description.txt"), "w", encoding="utf-8") as f:
        f.write(job_description)
    if guidance:
        with open(os.path.join(app_dir, "guidance.txt"), "w", encoding="utf-8") as f:
            f.write(guidance)
    if user_facts:
        with open(os.path.join(app_dir, "user_facts.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump(user_facts, f, sort_keys=False, allow_unicode=True)
    with open(os.path.join(app_dir, "tailored_resume.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(tailored, f, sort_keys=False, allow_unicode=True)
    # Editable Markdown twin (spec §14) -- no embedded hash: unlike
    # resume_master.yaml, nothing else writes to this one application's
    # own files after the fact, so there's no concurrent-writer conflict
    # for sync_tailored_md.py to guard against.
    with open(os.path.join(app_dir, "tailored_resume.md"), "w", encoding="utf-8") as f:
        f.write(export_to_markdown(tailored))

    problems = [f"[reconstruction] {problem}" for problem in reconstruction_problems]
    problems += validate_tailored(master, tailored, user_facts=user_facts)
    report = format_report(problems, brainstorm_status=brainstorm_status)
    with open(os.path.join(app_dir, "validation_report.txt"), "w", encoding="utf-8") as f:
        f.write(report)

    pdf_path = os.path.join(app_dir, "Tailored_Resume.pdf")
    render_resume_pdf(tailored, pdf_path, target_pages=target_pages)

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
    parser.add_argument(
        "--facts-file", help="YAML file with entry-scoped, user-confirmed facts and required coverage concepts.",
    )
    args = parser.parse_args()

    master_resume_path = os.path.join(args.resume_manager_dir, "resume_master.yaml")
    guidance = _collect_guidance(master_resume_path, args.jd_file) if args.interactive else None
    user_facts = None
    if args.facts_file:
        with open(master_resume_path, "r", encoding="utf-8") as f:
            master = yaml.safe_load(f)
        user_facts = load_user_facts(args.facts_file, master)
    print(run_tailoring(
        master_resume_path, args.jd_file, args.application_name, args.resume_manager_dir,
        guidance=guidance, user_facts=user_facts,
    ))


if __name__ == "__main__":
    main()
