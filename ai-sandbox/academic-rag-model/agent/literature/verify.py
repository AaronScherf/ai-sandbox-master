"""A second, independent look at the facts only one extraction pass found: does the cited page support each one?"""
from __future__ import annotations

from pathlib import Path

from core.agent_tasks.tasks import Passage, Task

from .compare import single_pass_facts
from .papers import Paper
from .stage import Target, _offered_pages, _sha
from .transcript import check_quote, split_pages

STAGE = "verify"
VERDICTS = ("supported", "not_supported", "unclear")

INSTRUCTIONS = """\
Below are claims about the paper whose pages are listed under "Offered passages". For each numbered claim, decide
whether the paper's own text supports it. Answer as a YAML mapping under `## Result`:

  verdicts:
    - {item: 1, verdict: supported, quote: "...", locator: 3, reason: "one short line"}
    - {item: 2, verdict: not_supported, reason: "the paper says X instead"}
    - {item: 3, verdict: unclear, reason: "the offered pages do not settle it"}

Rules:
- Answer every item once. `verdict` is supported, not_supported or unclear.
- `supported` needs a `quote` copied exactly from the page text (8 to 300 characters) and the page number as `locator`.
- Judge only from the paper's own statements, not the reference list and not what you know of the topic.
- A claim is supported only if the paper itself says it holds for this study. A passing mention of a topic is not support."""


def _pages_of(locator) -> list[int]:
    return [locator] if isinstance(locator, int) else list(locator)


def make_tasks(target: Target, papers: list[Paper], *, redo: bool = False):
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    for paper in papers:
        a, b = target.records.read(paper.file_id, "a"), target.records.read(paper.file_id, "b")
        if a is None or b is None:
            skipped[paper.file_id] = "needs two extraction passes first (run collect --double)"
            continue
        items = single_pass_facts(a, b, target.vocabs)
        if not items:
            skipped[paper.file_id] = "the two passes agree on every fact"
            continue
        try:
            md = (Path(target.index_root) / paper.path).read_text(encoding="utf-8")
        except OSError as exc:
            skipped[paper.file_id] = f"cannot read the transcript: {exc}"
            continue
        sha = _sha(md)
        done = a.get("verification")
        if done and done.get("transcript_sha") == sha and not redo:
            skipped[paper.file_id] = "already verified (use --redo to verify again)"
            continue
        pages = split_pages(md)
        wanted = sorted({n for i in items for n in _pages_of(i["locator"]) if n in pages})
        if not wanted:
            skipped[paper.file_id] = "none of the cited pages is in the transcript"
            continue
        items = [dict(i, n=n) for n, i in enumerate(items, 1)]
        lines = [f"Paper: {paper.title or paper.file_id}", f"file_id: {paper.file_id}", "", "Claims to check:"]
        for i in items:
            extra = f" ({i['shown']})" if i["shown"] != i["label"] else ""
            lines.append(f"{i['n']}. {i['facet'].replace('_', ' ')}: {i['label']}{extra}")
        tasks.append(Task(
            id=f"verify-{paper.file_id}", stage=STAGE,
            subject={"file_id": paper.file_id, "transcript_sha": sha,
                     "items": [{k: i[k] for k in ("n", "facet", "shown", "label", "pass")} for i in items]},
            instructions=INSTRUCTIONS, context="\n".join(lines),
            passages=[Passage(id=f"P{n}", source=paper.title or paper.file_id, ref=f"page {n}", text=pages[n]) for n in wanted]))
    return tasks, skipped


def validate_result(entry: dict, result, target: Target) -> list[str]:
    if not isinstance(result, dict) or not isinstance(result.get("verdicts"), list):
        return ["result: must be a mapping with a `verdicts` list"]
    pages = _offered_pages(entry)
    known = {i["n"] for i in entry["subject"]["items"]}
    out: list[str] = []
    seen: set = set()
    for k, row in enumerate(result["verdicts"]):
        path = f"verdicts[{k}]"
        if not isinstance(row, dict):
            out.append(f"{path}: must be a mapping with item, verdict and reason")
            continue
        n = row.get("item")
        if n not in known:
            out.append(f"{path}.item: {n!r} is not a numbered claim on this card")
            continue
        if n in seen:
            out.append(f"{path}.item: claim {n} is answered twice")
        seen.add(n)
        verdict = row.get("verdict")
        if verdict not in VERDICTS:
            out.append(f"{path}.verdict: must be one of {', '.join(VERDICTS)}")
        elif verdict == "supported":
            if not isinstance(row.get("quote"), str) or "locator" not in row:
                out.append(f"{path}: supported needs a quote and a locator")
            else:
                problem = check_quote(row["quote"], row["locator"], pages)
                if problem:
                    out.append(f"{path}.quote: {problem}")
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            out.append(f"{path}.reason: required text")
    for n in sorted(known - seen):
        out.append(f"item {n}: no verdict given")
    return out


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    by_item = {row["item"]: row for row in result["verdicts"]}
    items = []
    for it in s["items"]:
        row = by_item[it["n"]]
        out = {"facet": it["facet"], "shown": it["shown"], "label": it["label"], "pass": it["pass"],
               "verdict": row["verdict"], "reason": row["reason"].strip()}
        if row["verdict"] == "supported":
            out.update(quote=row["quote"], locator=row["locator"])
        items.append(out)
    record = target.records.read(s["file_id"], "a")
    record["verification"] = {"transcript_sha": s["transcript_sha"], "run_id": provenance["run"],
                              "agent_name": provenance["agent"], "items": items}
    target.records.write(record, "a")
    return None


def silver_split(records, file_id: str, vocabs: dict | None = None) -> dict:
    """Facts for one paper in three groups: `agreed` (both passes), `confirmed` (one pass, verifier found support),
    `open` (one pass, verifier said not supported or unclear, or nobody has verified it yet)."""
    from .compare import agreed_facts

    a, b = records.read(file_id, "a"), records.read(file_id, "b")
    if a is None or b is None:
        return {"agreed": [], "confirmed": [], "open": []}
    verdicts = {(i["facet"], i["shown"], i["pass"]): i["verdict"] for i in (a.get("verification") or {}).get("items", [])}
    confirmed, open_ = [], []
    for item in single_pass_facts(a, b, vocabs):
        (confirmed if verdicts.get((item["facet"], item["shown"], item["pass"])) == "supported" else open_).append(item)
    return {"agreed": agreed_facts(a, b, vocabs), "confirmed": confirmed, "open": open_}
