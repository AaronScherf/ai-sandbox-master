"""Read submitted reviews from GitHub issues through the `gh` CLI."""
from __future__ import annotations

import json
import re
import subprocess

from pydantic import ValidationError

from .reviews import ReviewFile

_FENCE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


def extract_review_json(body: str) -> dict:
    """Pull the review JSON out of an issue body (fenced by the issue form, or pasted bare)."""
    m = _FENCE.search(body or "")
    text = m.group(1) if m else (body or "")
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"no review JSON found: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("review JSON must be an object")
    return data


def fetch_review_issues(repo: str, run=subprocess.run) -> tuple[list[tuple[int, ReviewFile]], list[str]]:
    cmd = ["gh", "issue", "list", "--repo", repo, "--label", "review", "--state", "open",
           "--json", "number,body", "--limit", "100"]
    result = run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh issue list failed for {repo}: {result.stderr.strip() or 'no output'}")
    reviews: list[tuple[int, ReviewFile]] = []
    problems: list[str] = []
    for issue in json.loads(result.stdout or "[]"):
        number = issue["number"]
        try:
            reviews.append((number, ReviewFile.model_validate(extract_review_json(issue.get("body", "")))))
        except (ValueError, ValidationError) as exc:
            problems.append(f"issue #{number}: {exc}")
    return reviews, problems


def close_issue(repo: str, number: int, run=subprocess.run) -> None:
    result = run(["gh", "issue", "close", str(number), "--repo", repo, "--comment", "Applied to the graph. Thank you for the review."],
                 capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh issue close #{number} failed: {result.stderr.strip()}")
