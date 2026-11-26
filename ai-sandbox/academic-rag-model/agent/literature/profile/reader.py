"""The second reader's folder: an independent model reads whole papers and its answers become a reference to score
against. The folder holds transcripts, the rules and the term lists, never the pipeline's or the owner's answers.
Every intervention or outcome needs a quote, which is checked against the page, and applicability is derived from
that evidence the same way the pipeline derives it from tags.
"""

import json
from pathlib import Path

from agent.literature.profile.classify import TYPE_RULES
from agent.literature.profile.taxonomy import ancestors
from agent.literature.transcript import check_quote, split_pages
from core.env.frontmatter import parse_frontmatter
from core.indexer.research_profile import PUBLISHER_TYPES, REPORT_TYPES, derive_applicability

KINDS = ("intervention", "outcome")

INSTRUCTIONS = """\
# Reading instructions

You are an independent reader. Work only from the files in this folder: do not open anything outside it, and do not
search the web. Read each paper in `papers/` in full, a few papers per session, and write one file
`answers/<file_id>.json` per paper (the file id is the paper's file name).

## Type and publisher

{rules}

## Interventions and outcomes

The allowed terms are in `terms/intervention.txt` and `terms/outcome.txt`, one per line:
`id | path | definition`. Search them; do not invent ids.

Choose a term only when the paper itself evaluates, models or reports that intervention or outcome, not when it is
merely mentioned in passing or in the literature review. A review or synthesis counts for what it synthesises. Judge
interventions and outcomes separately: a paper may have either one without the other, or neither. Use the most
specific term that fits, do not stretch a definition, and choose nothing when nothing fits.

## Answer format

```json
{{
  "report_type": "report",
  "publisher": "name, or empty",
  "publisher_type": "multilateral",
  "evidence": [
    {{"kind": "intervention", "term_id": "intervention.example", "quote": "exact words from the page", "page": 3}}
  ],
  "note": "optional"
}}
```

Each quote is 8 to 300 characters copied exactly from one page. Page numbers are the `<!-- page N -->` markers. Use
`"evidence": []` when the paper has no intervention or outcome from the lists.
"""


def _term_lines(vocab) -> str:
    lines = []
    for t in vocab.terms.values():
        path = " > ".join([vocab.terms[a].label for a in reversed(ancestors(vocab, t.id))] + [t.label])
        lines.append(f"{t.id} | {path} | {' '.join((t.definition or '').split())}")
    return "\n".join(lines) + "\n"


def write_pack(index_root: str, cards: list[dict], vocabs: dict, out: Path) -> None:
    out = Path(out)
    for name in ("papers", "answers", "terms"):
        (out / name).mkdir(parents=True, exist_ok=True)
    for card in cards:
        text = (Path(index_root) / card["path"]).read_text(encoding="utf-8")
        body = parse_frontmatter(text.replace("\r", ""))[1].lstrip()
        (out / "papers" / f"{card['file_id']}.md").write_text(
            f"Title on record: {card.get('title') or card['file_id']}\n\n{body}", encoding="utf-8")
    for kind in KINDS:
        (out / "terms" / f"{kind}.txt").write_text(_term_lines(vocabs[kind]), encoding="utf-8")
    (out / "INSTRUCTIONS.md").write_text(INSTRUCTIONS.format(rules=TYPE_RULES), encoding="utf-8")


def _problems(answer, pages: dict[int, str], vocabs: dict) -> list[str]:
    if not isinstance(answer, dict) or not isinstance(answer.get("evidence"), list):
        return ["give an object with an evidence list (it may be empty)"]
    problems = []
    if answer.get("report_type") not in REPORT_TYPES:
        problems.append(f"report_type {answer.get('report_type')!r} is not one of the listed types")
    if answer.get("publisher_type") not in PUBLISHER_TYPES:
        problems.append(f"publisher_type {answer.get('publisher_type')!r} is not one of the listed groups")
    for item in answer["evidence"]:
        if not isinstance(item, dict) or item.get("kind") not in KINDS:
            problems.append(f"evidence entry needs kind intervention or outcome: {item!r}"[:200])
        elif item.get("term_id") not in vocabs[item["kind"]].terms:
            problems.append(f"{item.get('term_id')}: not an id in terms/{item['kind']}.txt")
        else:
            why = check_quote(item.get("quote"), item.get("page"), pages)
            if why:
                problems.append(f"{item['term_id']}: {why}")
    return problems


def read_answers(pack: Path, vocabs: dict) -> tuple[dict[str, dict], list[str]]:
    """(labels in the shape `eval --labels` reads, problems). A paper with any problem is left out of the labels."""
    pack = Path(pack)
    labels: dict[str, dict] = {}
    problems: list[str] = []
    for paper in sorted((pack / "papers").glob("*.md")):
        fid = paper.stem
        path = pack / "answers" / f"{fid}.json"
        if not path.exists():
            problems.append(f"{fid}: no answer file")
            continue
        try:
            answer = json.loads(path.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            problems.append(f"{fid}: not valid JSON ({exc})")
            continue
        found = _problems(answer, split_pages(paper.read_text(encoding="utf-8")), vocabs)
        if found:
            problems += [f"{fid}: {p}" for p in found]
            continue
        terms = {kind: sorted({e["term_id"] for e in answer["evidence"] if e["kind"] == kind}) for kind in KINDS}
        labels[fid] = {"report_type": answer["report_type"], "publisher": answer.get("publisher") or "",
                       "publisher_type": answer["publisher_type"],
                       "applicability": derive_applicability(terms["intervention"], terms["outcome"], assessed=True),
                       "main_intervention": terms["intervention"], "main_outcome": terms["outcome"],
                       "note": answer.get("note") or ""}
    return labels, problems
