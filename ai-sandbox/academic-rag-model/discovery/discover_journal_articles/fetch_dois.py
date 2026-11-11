"""
fetch_dois.py
Route 4: fetch exactly the DOIs you name. python -m discovery.discover_journal_articles.fetch_dois

Unlike discover.py (faculty/topic queries behind a relevance gate) and
snowball.py (citation graph), this takes an explicit list of DOIs, so no
relevance model is loaded and nothing is filtered out. Each DOI is resolved
in OpenAlex, fetched through the same open-access -> arXiv -> EZProxy chain
(access.resolve_full_text), written next to a metadata sidecar, and recorded
in the same manifest, so a paper that cannot be fetched lands on
needs_manual_downloads.md exactly like any other route's outcome. Like
discover.py it never imports indexer/ and never runs conversion.

A per-DOI report (doi_fetch_report.md, beside the manifest) records the
outcome of every DOI in the run, including DOIs OpenAlex does not know.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from core.env.gemini_utils import load_dotenv_override
from discovery.discover_journal_articles.access import resolve_full_text
from discovery.discover_journal_articles.atomic_io import write_bytes_atomic
from discovery.discover_journal_articles.discovery import doi_url, resolve_work_by_doi
from discovery.discover_journal_articles.manifest import (
    load_manifest,
    manifest_key,
    manifest_path,
    record_outcome,
    save_manifest,
)
from discovery.discover_journal_articles.metadata_sidecar import write_sidecar
from discovery.discover_journal_articles.topic_routing import pdf_filename, route_to_folder, sanitize_topic_name
from discovery.discover_journal_articles.worklist import write_needs_manual_worklist

_DOI_PREFIX_RE = re.compile(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)", re.IGNORECASE)
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
_TRAILING_PUNCT = ".,;:"


def _clean_doi(raw: str) -> str | None:
    """A bare DOI from one list entry, or None when it is not a DOI. Strips a doi:/doi.org prefix and trailing
    punctuation, but keeps a closing parenthesis that balances an opening one inside the DOI (legacy SICI-style
    and Elsevier PII DOIs contain parentheses)."""
    text = _DOI_PREFIX_RE.sub("", raw.strip())
    while text and (text[-1] in _TRAILING_PUNCT or (text[-1] == ")" and text.count(")") > text.count("("))):
        text = text[:-1]
    return text if _DOI_RE.match(text) else None


def parse_doi_text(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Parses a DOI list: one DOI per line, `#` starts a comment (kept as the DOI's label), blank lines ignored,
    CRLF tolerated. Returns ([(doi, label)], [rejected lines]). Duplicates (case-insensitive) keep the first."""
    entries: list[tuple[str, str]] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        body, _, comment = line.partition("#")
        body = body.strip()
        if not body:
            continue
        doi = _clean_doi(body.split()[0])
        if doi is None:
            rejected.append(line.strip())
            continue
        if doi.lower() in seen:
            continue
        seen.add(doi.lower())
        entries.append((doi, comment.strip()))
    return entries, rejected


def collect_dois(cli_dois: list[str], doi_file: str | None) -> tuple[list[tuple[str, str]], list[str]]:
    lines = list(cli_dois or [])
    if doi_file:
        lines.extend(Path(doi_file).read_text(encoding="utf-8").splitlines())
    return parse_doi_text("\n".join(lines))


def _target_folder(args: argparse.Namespace, work) -> Path:
    if getattr(args, "folder", None):
        folder = Path(args.articles_dir) / sanitize_topic_name(args.folder)
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    return route_to_folder(args.articles_dir, work)


def run(args: argparse.Namespace) -> list[dict]:
    mailto = getattr(args, "mailto", None) or os.environ.get("OPENALEX_CONTACT_EMAIL")
    ezproxy_cookie = getattr(args, "ezproxy_cookie", None) or os.environ.get("EZPROXY_SESSION_COOKIE")
    core_api_key = getattr(args, "core_api_key", None) or os.environ.get("CORE_API_KEY")
    dry_run = bool(getattr(args, "dry_run", False))

    entries, rejected = collect_dois(args.doi, args.doi_file)
    manifest_file = manifest_path(args.articles_dir)
    manifest = load_manifest(manifest_file)
    budget = getattr(args, "time_budget_seconds", None)
    deadline = time.monotonic() + budget if budget else None

    results: list[dict] = [
        {"doi": line, "label": "", "outcome": "not_a_doi", "tier": None, "folder": None} for line in rejected
    ]
    for doi, label in entries:
        rec = {"doi": doi, "label": label, "outcome": None, "tier": None, "folder": None}
        results.append(rec)

        existing = manifest.get(doi.lower())
        if existing and existing.get("status") in ("fetched", "downloaded"):
            rec["outcome"], rec["folder"] = "already_seen", existing.get("folder")
            continue
        if deadline is not None and time.monotonic() >= deadline:
            rec["outcome"] = "not_attempted_time_budget"
            continue

        work = resolve_work_by_doi(doi, mailto)
        if work is None:
            rec["outcome"] = "not_in_openalex"
            continue
        if dry_run:
            rec["outcome"] = "would_try"
            rec["tier"] = "open_access_listed" if work.is_oa else "no_open_access_listed"
            continue

        key = manifest_key(work)
        folder = _target_folder(args, work)
        rec["folder"] = folder.name
        result = resolve_full_text(work, mailto, ezproxy_cookie, args.pace_per_hour, core_api_key, deadline=deadline)
        if result.status == "fetched":
            pdf_path = folder / pdf_filename(work)
            write_bytes_atomic(pdf_path, result.content)
            write_sidecar(pdf_path, work, None, result.tier)
            record_outcome(manifest, key, "fetched", folder=folder.name)
            rec["outcome"], rec["tier"] = "fetched", result.tier
        else:
            record_outcome(manifest, key, "needs_manual", folder=folder.name, metadata={
                "title": work.title, "authors": work.authors, "year": work.year, "doi_url": doi_url(work),
            })
            rec["outcome"] = "needs_manual"
        save_manifest(manifest_file, manifest)  # per DOI: an interrupted run keeps what it fetched

    if not dry_run:
        write_needs_manual_worklist(manifest, args.articles_dir)
        report = Path(args.articles_dir) / ".discovery" / "doi_fetch_report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(render_report(results), encoding="utf-8", newline="\n")
    return results


def render_report(results: list[dict]) -> str:
    lines = ["# DOI fetch report", "", "| DOI | Label | Outcome | Tier | Folder |", "|---|---|---|---|---|"]
    for r in results:
        label = (r["label"] or "").replace("|", "/")
        lines.append(f"| `{r['doi']}` | {label} | {r['outcome']} | {r['tier'] or ''} | {r['folder'] or ''} |")
    counts: dict[str, int] = {}
    for r in results:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    lines += ["", "Totals: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch full text for an explicit list of DOIs.")
    parser.add_argument("--doi", action="append", default=[], help="A DOI to fetch (repeatable).")
    parser.add_argument("--doi-file", help="Text file: one DOI per line, `#` starts a comment.")
    parser.add_argument("--folder", help="Save every paper in this folder under the articles dir (default: topic routing).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve each DOI in OpenAlex and report open-access status; download and write nothing.")
    parser.add_argument("--pace-per-hour", type=float, default=25.0,
                        help="EZProxy-tier pacing only (see discover.py).")
    parser.add_argument("--time-budget-seconds", type=float, default=None,
                        help="Stop cleanly after this many seconds; remaining DOIs are reported as not attempted.")
    default_articles_dir = Path(__file__).resolve().parent.parent.parent.parent / "research" / "journal-articles"
    parser.add_argument("--articles-dir", default=str(default_articles_dir))
    args = parser.parse_args()

    if not args.doi and not args.doi_file:
        parser.error("give at least one --doi or a --doi-file")

    load_dotenv_override()
    if not os.environ.get("OPENALEX_CONTACT_EMAIL"):
        print("ERROR: OPENALEX_CONTACT_EMAIL must be set in .env (required by OpenAlex/Unpaywall).")
        sys.exit(1)

    results = run(args)
    print(render_report(results))
    if not args.dry_run:
        print(f"Report written to {Path(args.articles_dir) / '.discovery' / 'doi_fetch_report.md'}")


if __name__ == "__main__":
    main()
