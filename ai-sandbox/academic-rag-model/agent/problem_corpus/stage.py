"""Subscription task stage for extracting problem records from indexed files."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from core.agent_tasks.tasks import Passage, Task
from core.indexer.index_card import compute_content_hash, load_shard, now_iso

from .boundaries import detect_spans
from .extractor import (_FRONTMATTER_RE, _PROBLEM_BEARING_FOLDER_CATEGORIES,
                        _folder_category_from_path, _record_id)
from .store import load_records, save_file_records

STAGE = "problem_corpus"

INSTRUCTIONS = """Extract every offered problem into the YAML mapping below. Keep the mathematical
content of each problem verbatim, removing only its leading problem number or label. Copy a student's
worked solution verbatim if present; otherwise use null. Never call a solution verified. Give a short,
specific topic tag. Include exactly one item for each offered passage, in the same order:

problems:
  - problem_text: "Find the eigenvalues of A."
    solution_text: null
    topic_tag: "eigenvalues"

Use YAML block scalars (|) for multiline text. Do not invent a solution or omit a problem."""


@dataclass(frozen=True)
class Target:
    root: str


def _task_id(course: str, file_id: str) -> str:
    digest = hashlib.sha256(f"{course}:{file_id}".encode("utf-8")).hexdigest()[:16]
    return f"problem-{digest}"


def _current(target: Target, subject: dict) -> bool:
    """A filled card is usable only while both its index entry and file are current."""
    matches = [card for card in load_shard(target.root, subject["course"])
               if card.get("file_id") == subject["file_id"] and card.get("path") == subject["path"]
               and not card.get("orphaned") and not card.get("needs_indexing")]
    if not matches or matches[0].get("content_hash") != subject["content_hash"]:
        return False
    try:
        return compute_content_hash(os.path.join(target.root, subject["path"])) == subject["content_hash"]
    except OSError:
        return False


def make_tasks(target: Target, *, course: str | None = None, file: str | None = None,
               redo: bool = False) -> tuple[list[Task], dict[str, str]]:
    """Collect one task per changed problem-bearing file, using the existing span detector."""
    from core.indexer.index_card import list_courses

    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    for course_name in list_courses(target.root):
        if course is not None and course_name != course:
            continue
        existing = load_records(target.root, course_name)
        for card in load_shard(target.root, course_name):
            if card.get("orphaned") or card.get("needs_indexing"):
                continue
            path = card["path"]
            if _folder_category_from_path(path) not in _PROBLEM_BEARING_FOLDER_CATEGORIES:
                continue
            if file is not None and not path.endswith(file):
                continue
            file_id = card["file_id"]
            md_path = os.path.join(target.root, path)
            try:
                if compute_content_hash(md_path) != card["content_hash"]:
                    skipped[path] = "source changed since indexing; reindex before collecting"
                    continue
                with open(md_path, encoding="utf-8") as source:
                    body = _FRONTMATTER_RE.sub("", source.read(), count=1)
            except OSError as exc:
                skipped[path] = f"cannot read source: {exc}"
                continue
            current = [r for r in existing if r["source"]["file_id"] == file_id]
            if current and all(r["content_hash"] == card["content_hash"] for r in current) and not redo:
                skipped[path] = "current records already exist (use --redo to extract again)"
                continue
            spans = detect_spans(body)
            if not spans:
                skipped[path] = "no problem spans detected"
                continue
            subject = {"course": course_name, "file_id": file_id, "path": path,
                       "content_hash": card["content_hash"],
                       "labels": [span.problem_label for span in spans]}
            passages = [Passage(id=f"P{i + 1}", source=path, ref=span.problem_label, text=span.text)
                        for i, span in enumerate(spans)]
            tasks.append(Task(id=_task_id(course_name, file_id), stage=STAGE, subject=subject,
                              instructions=INSTRUCTIONS,
                              context=f"Course: {course_name}\nSource: {path}\nProblem count: {len(spans)}",
                              passages=passages))
    return tasks, skipped


def validate_result(entry: dict, result: dict, target: Target) -> list[str]:
    problems: list[str] = []
    subject = entry["subject"]
    if not _current(target, subject):
        problems.append("source or index changed since collection; collect a new card")
    items = result.get("problems")
    if not isinstance(items, list) or len(items) != len(entry["passages"]):
        problems.append(f"problems must contain exactly {len(entry['passages'])} items in passage order")
        return problems
    for i, (item, passage) in enumerate(zip(items, entry["passages"]), start=1):
        if not isinstance(item, dict):
            problems.append(f"problem {i}: expected a mapping")
            continue
        if set(item) != {"problem_text", "solution_text", "topic_tag"}:
            problems.append(f"problem {i}: use only problem_text, solution_text, and topic_tag")
            continue
        statement = item["problem_text"]
        solution = item["solution_text"]
        topic = item["topic_tag"]
        source = passage["text"]
        if not isinstance(statement, str) or not statement.strip() or statement.strip() not in source:
            problems.append(f"problem {i}: problem_text must be nonempty and copied from its offered passage")
        if solution is not None and (not isinstance(solution, str) or not solution.strip() or solution.strip() not in source):
            problems.append(f"problem {i}: solution_text must be null or copied verbatim from its offered passage")
        if not isinstance(topic, str) or not topic.strip() or "\n" in topic:
            problems.append(f"problem {i}: topic_tag must be a short, nonempty single line")
    return problems


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    subject = entry["subject"]
    if not _current(target, subject):
        return "source or index changed since validation; collect a new card"
    course, file_id, path = subject["course"], subject["file_id"], subject["path"]
    records = []
    for i, (item, label) in enumerate(zip(result["problems"], subject["labels"])):
        solution = item["solution_text"]
        records.append({
            "id": _record_id(file_id, i, label), "course": course,
            "topic_tag": item["topic_tag"].strip(), "problem_text": item["problem_text"].strip(),
            "solution_text": solution.strip() if solution is not None else None,
            "solution_provenance": "student_attempt" if solution is not None else None,
            "source": {"file_id": file_id, "path": path, "root": target.root,
                       "citation": f"{os.path.basename(path)}, {label}",
                       "folder_category": _folder_category_from_path(path)},
            "content_hash": subject["content_hash"], "extracted_at": now_iso(),
        })
    save_file_records(target.root, course, file_id, records)
    return None
