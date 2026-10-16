"""Measures how often page_looks_defective() flags journal-article pages, per signal.

Prints aggregates only (never page text), so it is safe to run on copyrighted PDFs. Used to calibrate the
journal-prose defect profile (see docs/superpowers/plans/literature_taxonomy/2026-10-16-stage1-*.md)."""
from __future__ import annotations

import argparse
import json
import sys

from pipelines.convert_journal_articles.convert_journal_articles import discover_pdf_files
from pipelines.transcribe_notes import transcribe_notes as tn

SIGNALS = ("collapsed_prose", "unexpected_chars", "repeated_char_run", "lost_exponent")


def signals_for(text: str) -> set[str]:
    """Which of page_looks_defective's four signals fire on this page (mirrors its checks one for one)."""
    out: set[str] = set()
    if tn._has_collapsed_prose_run(text):
        out.add("collapsed_prose")
    if sum(1 for c in text if not c.isspace() and not tn.is_expected_char(c)) > tn._MAX_UNEXPECTED_CHARS:
        out.add("unexpected_chars")
    if tn._has_suspicious_repeated_char_run(text):
        out.add("repeated_char_run")
    if tn._has_lost_exponent_outside_scripts(text):
        out.add("lost_exponent")
    return out


def audit_pdf(pdf_path: str, check_math_notation: bool = True) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    reliable = tn.has_reliable_pagination(reader.metadata)
    by_signal: dict[str, int] = {}
    defective = 0
    if reliable:
        for text in tn.extract_all_page_texts(pdf_path, total):
            fired = signals_for(text)
            if not check_math_notation:
                fired.discard("lost_exponent")
            if fired:
                defective += 1
            for s in fired:
                by_signal[s] = by_signal.get(s, 0) + 1
    return {"pages": total, "reliable": reliable, "defective_pages": defective, "by_signal": by_signal}


def summarize(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["reliable"]]
    scored_pages = sum(r["pages"] for r in scored)
    by_signal: dict[str, int] = {}
    for r in scored:
        for s, n in r["by_signal"].items():
            by_signal[s] = by_signal.get(s, 0) + n
    over = sum(1 for r in scored if r["pages"] and r["defective_pages"] / r["pages"] > tn._MAX_DEFECT_RATIO_FOR_HYBRID)
    defective = sum(r["defective_pages"] for r in scored)
    return {
        "documents": len(rows), "pages": sum(r["pages"] for r in rows), "defective_pages": defective,
        "defect_rate": (defective / scored_pages) if scored_pages else 0.0,
        "by_signal": by_signal, "docs_over_hybrid_threshold": over,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Aggregate defect-heuristic rates over a PDF folder (no text output).")
    p.add_argument("--articles-dir", required=True)
    p.add_argument("--no-math-notation", action="store_true", help="Score as the journal profile would.")
    args = p.parse_args()
    rows = []
    for path in discover_pdf_files(args.articles_dir):
        try:
            rows.append(audit_pdf(path, check_math_notation=not args.no_math_notation))
        except Exception as err:  # unreadable PDF: count it, do not abort the audit
            print(f"skip (unreadable): {type(err).__name__}", file=sys.stderr)
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
