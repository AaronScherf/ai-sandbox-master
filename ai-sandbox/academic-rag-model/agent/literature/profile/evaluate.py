"""Evaluation harness: 3ie study-record CSVs as bibliographic gold, per-stratum scoring and a blind-labelling page.

The 3ie CSVs (research/resources/3ie/all_study_record*.csv) are test inputs only; they are never copied into the
repository. They give inclusion positives and bibliographic gold (title, authors, DOI, journal, publication type),
not per-study intervention or outcome codes.
"""

import csv
import html
from collections.abc import Callable

from agent.literature.profile.metadata import title_match
from agent.literature.profile.tagging import covered_terms

_PUBLICATION_TYPES = {
    "journal article": "journal_article", "published working paper": "working_paper", "published report": "report",
    "3ie series report": "report", "3ie grantee final report": "report", "thesis": "thesis",
    "published protocol": "protocol", "book or book chapter": "other",
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


def blind_label_page(papers: list[dict]) -> str:
    """HTML for the owner (or a second model) to label papers before any extractor result is seen. Only the file id,
    title, authors and abstract are read from each paper dict; predictions never reach the page."""
    cards = []
    for p in papers:
        fid = html.escape(str(p["file_id"]))
        authors = html.escape("; ".join(p.get("authors") or []))
        cards.append(
            f'<section data-file-id="{fid}"><h3>{html.escape(p.get("title") or fid)}</h3><p>{authors}</p>'
            f'<p>{html.escape((p.get("abstract") or "")[:1500])}</p>'
            '<label>Report type <select name="report_type"><option>journal_article</option><option>working_paper</option>'
            '<option>report</option><option>program_document</option><option>grey_literature</option>'
            '<option>thesis</option><option>protocol</option><option>notes</option><option>other</option></select></label> '
            '<label>Applicability <select name="applicability"><option>both</option><option>intervention_only</option>'
            '<option>outcome_only</option><option>not_applicable</option></select></label> '
            '<label>Main intervention <input name="main_intervention"></label> '
            '<label>Main outcome <input name="main_outcome"></label></section>')
    return "\n".join(cards)
