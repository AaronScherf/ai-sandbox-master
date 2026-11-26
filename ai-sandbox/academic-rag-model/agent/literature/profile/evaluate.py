"""Evaluation harness: 3ie study-record CSVs as bibliographic gold, per-stratum scoring and a blind-labelling page.

The 3ie CSVs (research/resources/3ie/all_study_record*.csv) are test inputs only; they are never copied into the
repository. They give inclusion positives and bibliographic gold (title, authors, DOI, journal, publication type),
not per-study intervention or outcome codes.
"""

import csv
import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from agent.literature.profile.metadata import title_match
from agent.literature.profile.tagging import covered_terms
from agent.literature.profile.taxonomy import ancestors
from core.env.frontmatter import parse_frontmatter

_PUBLICATION_TYPES = {
    "journal article": "journal_article", "published working paper": "working_paper", "published report": "report",
    "3ie series report": "report", "3ie grantee final report": "report", "thesis": "thesis",
    "published protocol": "protocol",
}
_NO_DOI = {"", "no doi", "none", "n/a", "na"}


def map_publication_type(value: str | None) -> str | None:
    """3ie Publication_Of_Type to our report_type; ongoing studies and unknown values are unscored (None)."""
    return _PUBLICATION_TYPES.get((value or "").strip().casefold())


def _doi(value: str | None) -> str | None:
    v = (value or "").strip()
    return None if v.casefold() in _NO_DOI else v.casefold()


def load_3ie_csv(path: str) -> list[dict]:
    """Rows of a 3ie all_study_record CSV. Tolerates the exports' broken encoding (undecodable bytes become U+FFFD)."""
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
    return [{"title": r["Title"], "authors": [a.strip() for a in r["Author_Names"].split(";") if a.strip()],
             "abstract": r["Abstract"], "publication_type": map_publication_type(r["Publication_Of_Type"]),
             "doi": _doi(r["DOI"]), "journal": r["Journal_Name"], "url": r["Url"]} for r in rows]


def _rate(hits: list[bool]) -> float | None:
    return sum(hits) / len(hits) if hits else None


def score_records(predicted: list[dict], answer_key: list[dict], stratum_of: Callable[[dict], str],
                  vocabs: dict | None = None) -> dict[str, dict]:
    """Per-stratum agreement of predictions with the answer key (never pooled). Records are keyed by `file_id`.
    A metric is None when the key has no value for it in that stratum."""
    pred = {p["file_id"]: p for p in predicted}
    strata: dict[str, list[dict]] = {}
    for key in answer_key:
        strata.setdefault(stratum_of(key), []).append(key)
    out: dict[str, dict] = {}
    for name, keys in strata.items():
        hits: dict[str, list[bool]] = {k: [] for k in ("title", "doi", "report_type", "discipline", "applicability", "tag")}
        missing = 0
        for key in keys:
            p = pred.get(key["file_id"])
            if p is None:
                missing += 1
                continue
            if key.get("title"):
                hits["title"].append(title_match(key["title"], p.get("title") or ""))
            if key.get("doi"):
                hits["doi"].append(_doi(key["doi"]) == _doi(p.get("doi")))
            for field in ("report_type", "discipline", "applicability"):
                if key.get(field):
                    hits[field].append(key[field] == p.get(field))
            for kind in ("intervention", "outcome"):
                wanted = key.get(f"main_{kind}") or []
                if wanted and vocabs and kind in vocabs:
                    covered = covered_terms(vocabs[kind], p.get(f"{kind}_tags") or [])
                    hits["tag"] += [t in covered for t in wanted]
        out[name] = {"n": len(keys), "missing_predictions": missing,
                     "title_accuracy": _rate(hits["title"]), "doi_accuracy": _rate(hits["doi"]),
                     "report_type_agreement": _rate(hits["report_type"]), "discipline_agreement": _rate(hits["discipline"]),
                     "applicability_agreement": _rate(hits["applicability"]), "tag_recall": _rate(hits["tag"])}
    return out


_TEMPLATE = Path(__file__).with_name("blind_label.html")
_PAGE_KEYS = ("file_id", "title", "authors", "year", "excerpt")
_ABSTRACT = re.compile(r"^[#*_ ]*(abstract|a b s t r a c t|executive summary|summary)\b(?![^\n]*(?:\. ?){4})",
                       re.IGNORECASE | re.MULTILINE)  # the lookahead skips table-of-contents lines


def excerpt(transcript: str, front: int = 900, limit: int = 3500) -> str:
    """The opening of a transcript as a labeller reads it, without frontmatter or page markers: the first `front`
    characters (cover, journal header, authors: what shows the report type), then `limit` characters from the abstract
    when one starts later than that."""
    text = parse_frontmatter(transcript.replace("\r", ""))[1]
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()
    found = _ABSTRACT.search(text, 0, 12000)
    if found and found.start() > front:
        return text[:front].rstrip() + "\n\n[…]\n\n" + text[found.start():found.start() + limit]
    return text[:front + limit]


def term_list(vocab) -> list[dict]:
    """A 3ie vocabulary as the page's term picker reads it."""
    return [{"id": t.id, "label": t.label, "path": " > ".join(vocab.terms[a].label for a in reversed(ancestors(vocab, t.id))),
             "definition": t.definition or ""} for t in vocab.terms.values()]


def blind_label_page(papers: list[dict], report_types: Iterable[str]) -> str:
    """The labelling page (publish with the `db` capability and `terms.json` beside it) for the owner or a second
    model. Only the keys in `_PAGE_KEYS` are read from each paper dict, so predictions never reach the page. Labels are
    saved to the `labels` collection, one document per file id."""
    data = {"papers": [{k: p.get(k) for k in _PAGE_KEYS} for p in papers], "report_types": sorted(report_types)}
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return _TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob)


_MERGED_TYPES = {"grey_literature": "report"}  # labels saved before the merge


def labels_to_key(labels: dict[str, dict]) -> list[dict]:
    """Saved page labels (file id to label document) as an answer key. A paper without both report type and
    applicability is unfinished and left out."""
    return [{"file_id": fid, "report_type": _MERGED_TYPES.get(v["report_type"], v["report_type"]), "applicability": v["applicability"],
             "main_intervention": v.get("main_intervention") or [], "main_outcome": v.get("main_outcome") or []}
            for fid, v in sorted(labels.items()) if v.get("report_type") and v.get("applicability")]
