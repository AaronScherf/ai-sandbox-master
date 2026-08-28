#!/usr/bin/env python3
"""
postprocess_notes.py
Downstream correction pass over transcribe_notes.py's already-produced
.md output -- see
docs/superpowers/specs/2026-08-26-notes-postprocessing-design.md for
the full design. Targets local-only pages (never seen by a vision
model); re-verifies flagged candidates against their real source PDF
page, reusing transcribe_notes.py's existing repair machinery, rather
than trusting a model's self-reported confidence on text alone.
"""
from __future__ import annotations

import argparse
import json
import os

from gemini_utils import get_gemini_client, load_dotenv_override
from local_model_scoring import score_causal_zscore, score_masked_candidates
from postprocess_discovery import (
    derive_eligible_pages,
    discover_markdown_files,
    is_correction_target,
    parse_frontmatter,
    split_pages_by_tag,
)
from postprocess_findings import (
    build_changelog_entry,
    documents_needing_review,
    find_isolated_candidate_spans,
    group_findings_by_signature,
    is_allowlisted_span,
    search_reference_documents,
)
from transcribe_notes import (
    _MODEL_TYPESET,
    build_final_markdown,
    build_frontmatter,
    repair_page_individually,
)

_MASKED_MODEL = "distilbert-base-cased"
_CAUSAL_MODEL = "gpt2"
_MASKED_PROBABILITY_THRESHOLD = 0.01
# Raised from 3.0 after real-corpus testing against Practice Sheet.pdf (a
# document with no known transcription defects): at 3.0, GPT-2's causal
# z-score flagged ~60 tokens across a 12-page sample, and every single one
# sampled downstream was a genuinely correct word ("subject", "space",
# "compact", "Let", "near") -- LaTeX-heavy, terse problem-set prose reads as
# high-surprisal to GPT-2 regardless of correctness. Raising to 5.0 cuts
# that sample's raw hits to 20/2150 (~67% reduction) without a clean cutoff
# fully separating signal from noise -- some correct words (e.g. "subject",
# z=5.91-6.27) still clear even this bar. This is a noise-volume mitigation,
# not a fix for the underlying precision problem; see
# docs/2026-08-27-notes-postprocessing-status.md.
_CAUSAL_ZSCORE_THRESHOLD = 5.0
_PATTERN_REVIEW_THRESHOLD = 5


def find_source_pdf(md_path: str, frontmatter: dict) -> str | None:
    """
    The source PDF for a processed_outputs/<name>.md file lives one
    directory up, named from frontmatter["source_pdf"]. Returns None
    (rather than raising) if it's missing -- detection still runs,
    verification is skipped for that document (see the design spec's
    edge case for a moved/deleted source PDF).
    """
    source_pdf = frontmatter.get("source_pdf")
    if not source_pdf:
        return None
    candidate = os.path.join(os.path.dirname(os.path.dirname(md_path)), source_pdf)
    return candidate if os.path.isfile(candidate) else None


def page_lines_from_source(pdf_path: str, page_index: int) -> list[list[dict]]:
    """Touches PyMuPDF -- not unit-tested locally, matching extract_all_page_texts's own split."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        # get_text()'s return type is a Union keyed off its "output" param;
        # coerced to dict defensively, same as extract_all_page_texts's own
        # str() coercion for "text" mode -- this file has already hit an
        # unreliable-looking PyMuPDF return shape once before.
        text_dict: dict = doc[page_index].get_text("dict")  # type: ignore[assignment]
        return [
            line.get("spans", [])
            for block in text_dict.get("blocks", [])
            for line in block.get("lines", [])
        ]
    finally:
        doc.close()


def find_candidates_for_page(pdf_path: str, page_num: int, page_text: str) -> list[dict]:
    """
    Runs detection for one page, layered rather than parallel -- the
    causal z-score signal is a cheap first pass (one forward pass for
    the whole page) that narrows down which character positions get the
    more expensive masked-LM confirmation pass, rather than masked-
    scoring every non-whitespace character on the page unconditionally.
    Confirmed necessary against a real corpus run (Practice Sheet.pdf):
    scoring every character was both far too slow (thousands of forward
    passes per document) and far too noisy (28 of ~41 already-verified-
    clean pages flagged on causal z-score alone, with no masked-LM
    corroboration) -- this matches the design spec's actual intent
    ("a first coarse pass ahead of the more expensive masked rescan"),
    which the original implementation deviated from by treating both as
    independent, equally-weighted signals. Structural candidates (free,
    targets the one confirmed real bug shape directly) are still added
    independently, since they're already high-precision on their own.
    Returns candidates that survived both stages, each a dict with at
    least "text" and "start"/"end" (or "origin" for structural-only
    candidates without character offsets).
    """
    lines = page_lines_from_source(pdf_path, page_num - 1)
    candidates = [
        {**c, "source": "structural"} for c in find_isolated_candidate_spans(lines)
    ]

    zscore_hits = [
        hit for hit in score_causal_zscore(_CAUSAL_MODEL, page_text)
        if hit["z_score"] > _CAUSAL_ZSCORE_THRESHOLD
    ]
    if zscore_hits:
        narrowed_spans = [(hit["start"], hit["end"]) for hit in zscore_hits]
        for hit in score_masked_candidates(_MASKED_MODEL, page_text, narrowed_spans):
            if hit["probability"] < _MASKED_PROBABILITY_THRESHOLD:
                candidates.append({**hit, "source": "causal_then_masked"})

    # is_allowlisted_span() is True for ANY ASCII text (inherited from
    # is_expected_char's original corruption-detection semantics: ASCII
    # is never "exotic-looking"), not just legitimate math-range Unicode
    # -- confirmed a real bug against Analysis_Exercises.pdf page 6:
    # applying it unconditionally suppressed the structural candidate for
    # the real "p" bug, since "p" is ordinary ASCII. Only non-ASCII
    # allowlisted text (Greek letters, math symbols) should be
    # suppressed -- that's the actual false-positive class this layer
    # exists for; ASCII candidates are exactly where a real substitution
    # bug hides and must never be filtered by this check.
    return [
        c for c in candidates
        if c["text"].isascii() or not is_allowlisted_span(c["text"])
    ]


def process_document(
    md_path: str, client, reference_texts: dict[str, str], dry_run: bool = False,
) -> list[dict]:
    """
    Runs the full detection -> suppression -> verification -> correction
    pipeline against one target document. Returns the list of unresolved
    (low-confidence/unverifiable) findings, for the caller to fold into
    corpus-wide pattern aggregation. High-confidence fixes are written
    directly into md_path (unless dry_run); every decision is appended
    to <name>_postprocess_log.json. `reference_texts` (document path ->
    full text, built once in main() from every discovered .md file) is
    used to fold cross-reference hits into the hint text sent to
    verification -- extra context for the judge, per the design spec,
    never a deciding vote on its own (the source-image re-check is still
    what decides the fix).
    """
    with open(md_path, encoding="utf-8") as f:
        original_text = f.read()
    frontmatter, body = parse_frontmatter(original_text)
    eligible_pages = derive_eligible_pages(frontmatter)
    if not eligible_pages:
        return []

    source_pdf = find_source_pdf(md_path, frontmatter)
    total_pages = frontmatter["total_pages"]
    pages_text = split_pages_by_tag(body)

    unresolved: list[dict] = []
    changelog: list[dict] = []
    any_change = False

    for page_num in eligible_pages:
        page_text = pages_text.get(page_num, "")
        if not page_text:
            continue

        if source_pdf is None:
            entry = build_changelog_entry(
                page_num, "", None, [], "unverifiable",
                "source PDF not found; detection skipped entirely for this document",
            )
            changelog.append(entry)
            unresolved.append({"document": md_path, "flagged_text": "", **entry})
            continue

        candidates = find_candidates_for_page(source_pdf, page_num, page_text)
        if not candidates:
            continue

        if dry_run:
            sources = ", ".join(sorted({c["source"] for c in candidates}))
            print(f"  page {page_num}: {len(candidates)} candidate(s) ({sources}) -- would verify against source image")
            continue

        # Cross-reference: fold hits for each candidate's flagged text
        # into the hint sent to verification -- confirming/clarifying
        # domain terminology the judge might not otherwise recognize.
        # Informational only; the source-image re-check below is still
        # the deciding signal (see the design spec's edge case for
        # conflicting cross-reference readings).
        cross_ref_notes = []
        for candidate in candidates:
            for hit in search_reference_documents(candidate["text"], reference_texts, context_chars=60)[:3]:
                cross_ref_notes.append(hit["context"])
        hint_text = page_text
        if cross_ref_notes:
            hint_text += "\n\n(Similar text found elsewhere in the corpus, for context: " + " | ".join(cross_ref_notes) + ")"

        try:
            corrected = repair_page_individually(
                client, _MODEL_TYPESET, source_pdf, page_num, hint_text, total_pages,
            )
        except Exception as err:
            for candidate in candidates:
                entry = build_changelog_entry(
                    page_num, candidate["text"], None, [candidate["source"]],
                    "unverifiable", str(err),
                )
                changelog.append(entry)
                unresolved.append({"document": md_path, "flagged_text": candidate["text"], **entry})
            continue

        signal_sources = sorted({c["source"] for c in candidates})
        if corrected.strip() == page_text.strip():
            changelog.append(build_changelog_entry(
                page_num, "", None, signal_sources, "high",
                "re-verified against source image; matched existing text, no change needed",
            ))
            continue

        pages_text[page_num] = corrected
        any_change = True
        changelog.append(build_changelog_entry(
            page_num, page_text, corrected, signal_sources, "high",
            "re-verified against source image; text differed, applied correction",
        ))

    if changelog and not dry_run:
        log_path = md_path.replace(".md", "_postprocess_log.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(changelog, f, indent=2)

        frontmatter["postprocessed"] = True
        new_body = build_final_markdown(
            {str(k): v for k, v in pages_text.items()}, total_pages,
        ) if any_change else body
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(build_frontmatter(frontmatter) + new_body)

    return unresolved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post-process transcribe_notes.py output: catch and correct errors "
                    "on local-only pages that were never seen by a vision model."
    )
    parser.add_argument(
        "--root", action="append", required=True,
        help="Root directory to scan recursively for processed_outputs/*.md files "
             "(repeatable, e.g. --root academic-hub/academic_notes/math-camp).",
    )
    parser.add_argument("--file", default=None, help="Only process this one target .md filename.")
    parser.add_argument(
        "--reprocess", action="store_true",
        help="Reprocess documents even if already marked postprocessed: true.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be flagged/fixed without writing anything.",
    )
    args = parser.parse_args()

    load_dotenv_override()
    all_files = discover_markdown_files(args.root)

    reference_texts = {}
    targets = []
    for path in all_files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        frontmatter, body = parse_frontmatter(text)
        reference_texts[path] = body
        is_target = args.reprocess or is_correction_target(frontmatter)
        if is_target and "routing" in frontmatter:
            if args.file is None or os.path.basename(path) == args.file:
                targets.append(path)

    if not targets:
        print("No target documents found.")
        return

    client = None if args.dry_run else get_gemini_client()
    if not args.dry_run and client is None:
        return

    all_unresolved: list[dict] = []
    for path in targets:
        print(f"[{os.path.basename(path)}] processing...")
        unresolved = process_document(path, client, reference_texts, dry_run=args.dry_run)
        all_unresolved.extend(unresolved)

    grouped = group_findings_by_signature(all_unresolved)
    review_needed = documents_needing_review(grouped, threshold=_PATTERN_REVIEW_THRESHOLD)
    if review_needed:
        print(f"\nDocuments with a consistent low-confidence pattern (>= {_PATTERN_REVIEW_THRESHOLD} similar findings):")
        for doc in review_needed:
            print(f"  {doc}")
    else:
        print("\nNo documents crossed the pattern-review threshold.")


if __name__ == "__main__":
    main()
