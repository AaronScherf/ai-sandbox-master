import json
import subprocess

import pytest

from agent.concept_graph.gh_issues import close_issue, extract_review_json, fetch_review_issues

REVIEW = {"schema_version": 1, "graph_version": "v", "reviewer": {"name": "Ada"}, "created": "t",
          "decisions": [{"target": {"kind": "node", "id": "preorder"}, "action": "accept"}]}


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_extract_from_a_json_fence_a_plain_fence_and_a_bare_body():
    raw = json.dumps(REVIEW)
    assert extract_review_json(f"### Review\n\n```json\n{raw}\n```\n") == REVIEW
    assert extract_review_json(f"### Review\n\n```\n{raw}\n```\n") == REVIEW
    assert extract_review_json(raw) == REVIEW


def test_extract_rejects_non_json():
    with pytest.raises(ValueError):
        extract_review_json("hello, I forgot to paste anything")


def test_fetch_parses_good_issues_and_reports_bad_ones():
    issues = [{"number": 7, "body": "```json\n" + json.dumps(REVIEW) + "\n```"}, {"number": 8, "body": "oops"}]
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return completed(json.dumps(issues))

    reviews, problems = fetch_review_issues("me/graph", run=run)
    assert [n for n, _ in reviews] == [7] and reviews[0][1].reviewer.name == "Ada"
    assert len(problems) == 1 and "#8" in problems[0]
    assert calls[0][:3] == ["gh", "issue", "list"] and "me/graph" in calls[0] and "review" in calls[0]


def test_fetch_raises_when_gh_fails():
    with pytest.raises(RuntimeError, match="gh"):
        fetch_review_issues("me/graph", run=lambda cmd, **kw: completed("", returncode=1))


def test_close_issue_calls_gh():
    calls = []
    close_issue("me/graph", 7, run=lambda cmd, **kw: calls.append(cmd) or completed())
    assert calls[0][:3] == ["gh", "issue", "close"] and "7" in calls[0]
