"""
run_all.py
TODO-0037: a convenience wrapper that chains discover.py's search/fetch
stage straight into convert_journal_articles.py's conversion stage --
which already performs index-card generation and OpenAlex-identity
stamping internally (process_pdf()'s own indexing hook, then
attach_identity()), so there is no separate "generate index cards" call
to make. Both standalone entry points are untouched and still work on
their own:
    python -m discovery.discover_journal_articles.discover ...
    python -m pipelines.convert_journal_articles.convert_journal_articles ...
This just saves the manual discover -> convert -> submit hand-off for
the common case of "find some papers on X and get them into the index".

Scoping, deliberately: only the PDFs *this* discovery run actually
fetched are ever passed into conversion -- never the whole
research/journal-articles/ corpus. Re-running this against a topic that
already has papers on disk must not silently reconvert them.

Cost control is not reinvented here: convert_journal_articles.py's own
existing guard is reused as-is. `--driver agent` (the default, $0) can
only ever *stage* task cards (`--collect`'s own scope) -- finishing the
transcription needs a human/agent hand-off, which is exactly why this
wrapper calls `_collect()` and then prints the same bootstrap contract
`convert_journal_articles.py --bootstrap` prints, pointing at the
follow-up `--submit` command, rather than pretending to finish the job
in one process. Only the explicit `--driver api` opt-in spends real
money, same as the standalone script. Discovery itself never calls
Gemini (relevance scoring is local sentence-transformers, confirmed in
discover_journal_articles/README.md) so there is no separate cost gate
needed for that stage.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

from core.env.gemini_utils import get_gemini_client, load_dotenv_override
from discovery.discover_journal_articles.discover import run as discover_run
from pipelines.convert_journal_articles.convert_journal_articles import (
    _CHECK_MATH_NOTATION,
    _JOURNAL_DOC_TYPES,
    _DEFAULT_MAX_PAGES,
    _bootstrap_text,
    _collect,
    _eligible_pdfs,
    _page_count,  # re-exported so tests can patch it here, same convention as test_cli_driver.py
    discover_pdf_files,
)
from pipelines.convert_journal_articles.identity import attach_identity
from pipelines.transcribe_notes.transcribe_notes import process_pdf

from discovery.discover_journal_articles.discover import (
    _DEFAULT_BATCH_SIZE,
    _DEFAULT_MAX_EXAMINED,
    _DEFAULT_MAX_RESULTS,
    _DEFAULT_PACE_PER_HOUR,
    _DEFAULT_RELEVANCE_THRESHOLD,
)

_JOURNAL_KWARGS = {"known_doc_types": _JOURNAL_DOC_TYPES, "check_math_notation": _CHECK_MATH_NOTATION}


def _convert_via_api(pdf_paths: list[str], args) -> int:
    """Mirrors convert_journal_articles.py's own --driver api loop exactly: process_pdf() writes the
    index card as part of conversion, attach_identity() stamps discovery metadata onto it right after.
    One paper's failure is reported and skipped, never fatal to the rest of the batch. Returns the
    count that actually converted successfully (not just attempted)."""
    client = get_gemini_client()
    if client is None:
        print("WARNING: no Gemini client available; skipping conversion and index-card generation.")
        return 0
    converted = 0
    for pdf_path in pdf_paths:
        try:
            process_pdf(pdf_path, client, args.model, args.index_root, **_JOURNAL_KWARGS)
        except Exception as err:  # one bad paper must not abort the rest of the batch
            print(f"[{os.path.basename(pdf_path)}] error: {err}")
            continue
        attach_identity(pdf_path, args.index_root)
        print(f"[{os.path.basename(pdf_path)}] converted and indexed")
        converted += 1
    return converted


def run_pipeline(args: argparse.Namespace) -> dict:
    """Runs discovery, then -- for whatever it actually fetched -- conversion and index-card
    generation (via convert_journal_articles.py's own machinery). Returns discover.run()'s counts
    dict, augmented with `converted`/`collected`/`collect_run_id`. Every stage degrades gracefully:
    zero new papers means conversion/indexing never run at all; an oversized or malformed paper is
    skipped and reported, not fatal to the run."""
    counts = discover_run(args)
    counts["converted"] = 0
    counts["collected"] = 0

    fetched_paths = counts.get("fetched_paths", [])
    if not fetched_paths:
        print("No new papers fetched this run; skipping conversion and index-card generation.")
        return counts

    eligible = _eligible_pdfs(fetched_paths, args.max_pages)
    if not eligible:
        print("Every newly fetched paper was flagged oversized (--max-pages); nothing to convert.")
        return counts

    if args.driver == "api":
        counts["converted"] = _convert_via_api(eligible, args)
    else:
        run_id = args.run_id or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        args.run_id = run_id
        _collect(eligible, args)
        counts["collected"] = len(eligible)
        counts["collect_run_id"] = run_id

    return counts


def _print_report(counts: dict, args: argparse.Namespace) -> None:
    print(f"\nFetched: {counts['fetched']}")
    print(f"Needs manual download: {counts['needs_manual']}")
    if counts["needs_manual"] or counts.get("already_seen"):
        print(f"Manual-download worklist: {Path(args.articles_dir) / 'needs_manual_downloads.md'}")
    if counts["converted"]:
        print(f"Converted and indexed via API: {counts['converted']}")
    if counts["collected"]:
        run_id = counts["collect_run_id"]
        print(f"\nStaged {counts['collected']} paper(s) for agent transcription under run '{run_id}'.")
        print(_bootstrap_text(run_id))
        print(
            "Index cards are generated automatically as part of that step. Once the cards above are "
            "filled, run:\n"
            f"  python -m pipelines.convert_journal_articles.convert_journal_articles --submit {run_id} "
            f"--articles-dir {args.articles_dir} --index-root {args.index_root}"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover journal-article PDFs for a topic/faculty, then convert and index "
                    "whatever was fetched, in one command. Thin orchestration only: see discover.py "
                    "and convert_journal_articles.py for every flag's own full documentation; both "
                    "remain fully usable standalone for anything this wrapper doesn't cover "
                    "(e.g. --retry, --zotero sync details, --submit, --backfill-identity)."
    )
    parser.add_argument("--faculty", action="append", default=[], help="Faculty name to query (repeatable).")
    parser.add_argument("--topic", action="append", default=[], help="Topic/keyword query (repeatable).")
    parser.add_argument("--relevance-prompt", help="Required: what you're actually looking for.")
    parser.add_argument("--relevance-threshold", type=float, default=_DEFAULT_RELEVANCE_THRESHOLD)
    parser.add_argument("--batch-size", type=int, default=_DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-results", type=int, default=_DEFAULT_MAX_RESULTS)
    parser.add_argument("--max-examined", type=int, default=_DEFAULT_MAX_EXAMINED)
    parser.add_argument("--pace-per-hour", type=float, default=_DEFAULT_PACE_PER_HOUR)
    parser.add_argument("--time-budget-seconds", type=float, default=900.0)
    parser.add_argument("--zotero", action="store_true", help="Also sync fetched papers into Zotero.")
    default_articles_dir = Path(__file__).resolve().parent.parent.parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    default_index_root = Path(__file__).resolve().parent.parent.parent.parent / "research"
    parser.add_argument("--index-root", default=str(default_index_root))
    parser.add_argument("--max-pages", type=int, default=_DEFAULT_MAX_PAGES)
    parser.add_argument("--model", default=None, help="Gemini model override, passed through to conversion.")
    parser.add_argument(
        "--driver", choices=["api", "agent"], default="agent",
        help="Conversion transport, same meaning and same $0 default as convert_journal_articles.py's own "
             "--driver. 'agent' only stages task cards here (finishing needs the printed --submit "
             "hand-off); 'api' converts and indexes immediately via the metered Gemini API.",
    )
    parser.add_argument("--run-id", default=None, help="Run id for the agent-driver collect stage (default: a timestamp).")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip discovery entirely (it makes real network calls to OpenAlex/Unpaywall/etc., which "
             "--dry-run does not control) and instead preview conversion routing for whatever journal "
             "articles are already on disk under --articles-dir, exactly like convert_journal_articles.py "
             "--dry-run would.",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    load_dotenv_override()
    if not os.environ.get("OPENALEX_CONTACT_EMAIL"):
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex/Unpaywall).")
        sys.exit(1)
    if not args.relevance_prompt:
        parser.error("--relevance-prompt is required")
    if not args.faculty and not args.topic:
        parser.error("at least one --faculty or --topic is required")

    if args.dry_run:
        print(
            "DRY RUN: discovery stage skipped (it makes real network calls, which --dry-run does not "
            "gate); previewing conversion routing for what's already on disk under "
            f"{args.articles_dir} instead."
        )
        for pdf_path in _eligible_pdfs(discover_pdf_files(args.articles_dir), args.max_pages):
            process_pdf(pdf_path, None, args.model, args.index_root, dry_run=True, **_JOURNAL_KWARGS)
        return

    counts = run_pipeline(args)
    _print_report(counts, args)


if __name__ == "__main__":
    main()
