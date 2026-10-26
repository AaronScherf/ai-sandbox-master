"""Read-only metrics for agent landings: approvals per landing, check-to-land
time, merge commits on main, and leftover worktrees.

Reads `main`'s history and `.git/agent-landing-log.jsonl` (written by
`tools.land_branch`); writes nothing. Used for the revisits in
`docs/superpowers/specs/2026-10-25-landing-approval-by-change-design.md` §5.

    python -m tools.landing_metrics --since 2026-10-26
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from tools.git_workflow import MAIN_BRANCH, git_common_dir, is_ancestor, list_worktrees, run_git
from tools.land_branch import LOG_NAME


@dataclass(frozen=True)
class Landing:
    branch: str
    approvals: int  # approval rounds the owner was asked for
    minutes: float  # first passing check to landed
    landed_at: datetime


def _at(entry: dict) -> datetime:
    return datetime.fromisoformat(entry["at"])


def landings(entries: list[dict], since: datetime | None = None) -> list[Landing]:
    """One row per landed branch.

    Each distinct passing change before the landing is one approval round:
    keyed by `change_id` when the check logged one, else by SHA (entries from
    before 2026-10-25). Each `land` STOP adds a round, since the owner is asked
    again.
    """
    sha_branch: dict[str, str] = {}
    passing: dict[str, list[dict]] = {}
    stops: dict[str, list[datetime]] = {}
    for e in entries:
        if e.get("event") == "check" and "branch" in e:
            sha_branch[e["sha"]] = e["branch"]
            if e.get("checks") in ("passed", "skipped"):
                passing.setdefault(e["branch"], []).append(e)
        elif e.get("event") == "land" and e.get("result") != "landed":
            stops.setdefault(e["branch"], []).append(_at(e))

    rows: list[Landing] = []
    seen: set[str] = set()
    for e in entries:
        if e.get("event") != "outcome" or e.get("outcome") != "landed":
            continue
        branch = sha_branch.get(e["sha"])
        if branch is None or branch in seen:
            continue
        seen.add(branch)
        landed_at = _at(e)
        checks = [c for c in passing.get(branch, []) if _at(c) <= landed_at]
        if not checks or (since and landed_at < since):
            continue
        changes = {c.get("change_id") or c["sha"] for c in checks}
        n_stops = sum(1 for t in stops.get(branch, []) if t <= landed_at)
        minutes = (landed_at - _at(checks[0])).total_seconds() / 60
        rows.append(Landing(branch, len(changes) + n_stops, minutes, landed_at))
    return rows


def summarize(rows: list[Landing]) -> dict:
    minutes = sorted(r.minutes for r in rows)
    return {
        "landed": len(rows),
        "multi_approval": sum(1 for r in rows if r.approvals > 1),
        "extra_rounds": sum(r.approvals - 1 for r in rows),
        "median_minutes": statistics.median(minutes) if minutes else 0,
        "p90_minutes": minutes[int(0.9 * (len(minutes) - 1))] if minutes else 0,
    }


def commit_stats(cwd: Path, since: str, until: str) -> dict:
    """Commits on main between two dates: total, merge commits, `todo:` commits."""
    out = run_git(["log", MAIN_BRANCH, f"--since={since}", f"--until={until}",
                   "--format=%P%x09%s"], cwd)
    lines = [line.split("\t", 1) for line in out.splitlines() if line]
    return {
        "commits": len(lines),
        "merges": sum(1 for parents, _ in lines if len(parents.split()) > 1),
        "todo": sum(1 for _, subject in lines if subject.startswith("todo:")),
    }


def worktree_stats(cwd: Path) -> dict:
    """Linked worktrees (excluding the main checkout) and how many are already merged."""
    linked = [w for w in list_worktrees(cwd)[1:] if w.branch]
    merged = sum(1 for w in linked if is_ancestor(cwd, w.branch, MAIN_BRANCH))
    return {"worktrees": len(linked), "merged": merged}


def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "n/a"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only metrics for agent landings.")
    parser.add_argument("--since", required=True, help="YYYY-MM-DD, start of the window")
    parser.add_argument("--until", default=date.today().isoformat(),
                        help="YYYY-MM-DD, end of the window (default: today)")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    until = datetime.fromisoformat(args.until).replace(tzinfo=timezone.utc)
    log = git_common_dir(args.repo) / LOG_NAME
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
               if line.strip()] if log.exists() else []
    rows = [r for r in landings(entries, since=since) if r.landed_at <= until.replace(hour=23, minute=59)]
    s = summarize(rows)
    c = commit_stats(args.repo, args.since, f"{args.until} 23:59")
    w = worktree_stats(args.repo)

    print(f"Window {args.since} to {args.until}")
    print(f"Landings: landed {s['landed']}, needing >1 approval {s['multi_approval']} "
          f"({_pct(s['multi_approval'], s['landed'])}), extra rounds {s['extra_rounds']}")
    print(f"First passing check to landed: median {s['median_minutes']:.0f} min, "
          f"p90 {s['p90_minutes']:.0f} min")
    print(f"Main: {c['commits']} commits, {c['merges']} merge commits "
          f"({_pct(c['merges'], c['commits'])}), {c['todo']} todo: commits")
    print(f"Worktrees now: {w['worktrees']}, already merged {w['merged']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
