from __future__ import annotations

import argparse
import sys
from pathlib import Path
import threading
import webbrowser

from tools.corpus_health.config import load_config
from tools.corpus_health.discovery import scan
from tools.corpus_health.review_server import ReviewServer
from tools.corpus_health.state import StateError, StateStore, default_state_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only academic-hub corpus health scanner.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser("scan", help="scan configured roots without pipeline or model calls")
    scan_parser.add_argument("--config", required=True, type=Path, help="JSON scanner configuration")
    scan_parser.add_argument("--format", choices=("text", "json"), default="text")
    scan_parser.add_argument("--output", type=Path, help="optional report destination; stdout is always printed")
    scan_parser.add_argument("--state-dir", type=Path, help="override the local operational state directory")
    scan_parser.add_argument("--no-state", action="store_true", help="do not update the local ledger or run history")
    review_parser = subparsers.add_parser("review", help="review pending findings in a local browser page")
    review_parser.add_argument("--config", required=True, type=Path, help="same configuration used for scan")
    review_parser.add_argument("--state-dir", type=Path, help="override the local operational state directory")
    review_parser.add_argument("--timeout", type=int, default=900)
    review_parser.add_argument("--include-deferred", action="store_true",
                               help="include deferred findings in the review page")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "scan":
            report = scan(config)
            if not args.no_state:
                try:
                    directory = args.state_dir or default_state_dir(config.academic_hub_root)
                    store = StateStore(directory)
                    report.findings = store.refresh(report.findings)
                    store.record_run(report.to_dict())
                except (OSError, StateError) as exc:
                    report.complete = False
                    report.errors.append(f"local state unavailable; recurring findings cannot be classified: {exc}")
            rendered = report.to_json() if args.format == "json" else report.to_text()
            print(rendered)
            if args.output:
                output_path = args.output.expanduser().resolve()
                corpus_roots = [config.academic_hub_root.resolve()]
                if config.academic_notes_root:
                    corpus_roots.append(config.academic_notes_root.resolve())
                if any(output_path == root or output_path.is_relative_to(root) for root in corpus_roots):
                    raise ValueError("report output must be outside academic-hub and academic_notes corpus roots")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered + "\n", encoding="utf-8")
            return 0 if report.complete else 2

        if args.timeout <= 0:
            raise ValueError("review timeout must be positive")
        directory = args.state_dir or default_state_dir(config.academic_hub_root)
        store = StateStore(directory)
        pending = store.pending(include_deferred=args.include_deferred)
        if not pending:
            print("No pending findings to review.")
            return 0
        def validate_current(entries: list[dict]) -> bool:
            current_report = scan(config)
            current = {StateStore.finding_id(finding): finding for finding in current_report.findings}
            for entry in entries:
                if entry is None:
                    return False
                finding_id = entry["finding_id"]
                updated = current.get(finding_id)
                if updated is None:
                    return False
                if updated.fingerprint != entry.get("finding", {}).get("fingerprint"):
                    return False
                if StateStore.action_signature(updated) != entry.get("action_signature"):
                    return False
            return True

        server = ReviewServer(store, args.timeout, validator=validate_current,
                              include_deferred=args.include_deferred)
        timer = threading.Timer(args.timeout, server.shutdown)
        timer.daemon = True
        timer.start()
        print(f"Reviewing {len(pending)} findings at {server.review_url}")
        webbrowser.open(server.review_url)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            print("Review stopped.")
        finally:
            timer.cancel()
            server.server_close()
        return 0
    except (OSError, ValueError, StateError) as exc:
        print(f"corpus-health: {exc}", file=sys.stderr)
        return 2
