"""The gap report: a JSON document built from the classification and coverage, and Markdown rendered from the JSON."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .classify import GapResult
from .corpus import Corpus
from .match import Constraint, fact_matches, vocab_for
from .resolve import full_path, level_of

SCHEMA_VERSION = 1
CAVEAT = "Facets are per paper: a direct hit means the paper has all the facts, not that it links them; check each paper's results."
_RUN_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def gap_dir(report_root, run_id: str) -> Path:
    if not _RUN_ID.fullmatch(run_id or ""):
        raise ValueError(f"run id {run_id!r}: use lowercase letters, digits, - and _ (up to 64 characters)")
    return Path(report_root) / run_id


def _describe(c: Constraint, vocabs: dict) -> dict:
    vocab = vocab_for(c.facet, vocabs)
    term = vocab.terms.get(c.value) if vocab is not None else None
    return {"phrase": c.phrase, "facet": c.facet, "value": c.value, "label": term.label if term else c.value,
            "level": level_of(c.value, vocab) if term else None, "resolved_by": c.resolved_by,
            "path": full_path(c.value, vocab) if term else None, "members": list(c.members)}


def _fact_path(fact, vocabs: dict) -> str | None:
    vocab = vocab_for(fact.facet, vocabs)
    return full_path(fact.shown, vocab) if vocab is not None and fact.shown in vocab.terms else None


def _breakdown(constraints: list[Constraint], vocabs: dict, direct: list[str], corpus: Corpus) -> list[dict]:
    """For each label group, the direct papers under each member term's branch."""
    out = []
    for c in constraints:
        if len(c.term_ids) < 2:
            continue
        vocab = vocab_for(c.facet, vocabs)
        branches = []
        for tid in c.term_ids:
            one = Constraint(c.facet, tid)
            papers = [fid for fid in direct if any(fact_matches(one, f, vocabs) for f in corpus.facts[fid])]
            branches.append({"term_id": tid, "path": full_path(tid, vocab), "papers": papers})
        out.append({"facet": c.facet, "label": vocab.terms[c.value].label, "branches": branches})
    return out


def _paper(corpus: Corpus, fid: str) -> dict:
    row = corpus.papers.get(fid)
    return {"file_id": fid, "title": row.title if row else None, "year": row.year if row else None}


def build_report(question: str, constraints: list[Constraint], vocabs: dict, result: GapResult, cov: dict, corpus: Corpus,
                 *, unmapped=(), include_quotes: bool = False, probe: dict | None = None) -> dict:
    facets = {c.facet for c in constraints}
    evidence = []
    for fid, kind, labels in ([(f, "direct", []) for f in result.direct]
                              + [(f, "adjacent", result.adjacent[f]) for f in sorted(result.adjacent)]):
        facts = [{"facet": f.facet, "shown": f.shown, "label": f.label, "tier": f.tier, "path": _fact_path(f, vocabs),
                  **({"quote": f.quote} if include_quotes else {})}
                 for f in corpus.facts.get(fid, []) if f.facet in facets]
        results = [{"claim": r["claim"], "direction": r["direction"], **({"quote": r["quote"]} if include_quotes else {})}
                   for r in corpus.results.get(fid, [])]
        evidence.append({**_paper(corpus, fid), "kind": kind, "labels": labels, "facts": facts, "results": results})
    return {
        "schema_version": SCHEMA_VERSION,
        "question": question,
        "unmapped_phrases": list(unmapped),
        "constraints": [_describe(c, vocabs) for c in constraints],
        "verdict": result.verdict,
        "rule": result.rule,
        "counts": {"direct": len(result.direct), "adjacent": len(result.adjacent),
                   "different_method": len(result.different_method), "partial": len(result.partial)},
        "caveat": CAVEAT,
        "unwidenable": result.unwidenable,
        "breakdown": _breakdown(constraints, vocabs, result.direct, corpus),
        "coverage": cov,
        "evidence": evidence,
        "partial": [{**_paper(corpus, fid), "matched": n} for fid, n in result.partial],
        "different_method": [_paper(corpus, fid) for fid in result.different_method],
        "external": {"probe": probe} if probe else None,
    }


def _paper_line(p: dict) -> str:
    return f"{p['title'] or p['file_id']} ({p['year'] or 'year unknown'}, `{p['file_id']}`)"


def render_markdown(report: dict) -> str:
    cov = report["coverage"]
    out = []
    if cov["db"]["stale"]:
        out += ["> **Warning:** a record, the exclusion list or the proposals changed after the database was built. "
                "The verdict and counts come from the database snapshot; rebuild with `db build`.", ""]
    if report["unmapped_phrases"]:
        out += ["> Not mapped to any vocabulary term (not part of this analysis): "
                + "; ".join(report["unmapped_phrases"]), ""]
    out += [f"# Gap analysis: {report['question']}", "", "## Constraints", ""]
    for c in report["constraints"]:
        where = f" under {c['path']}" if c.get("path") and c["path"] != c["label"] and not c.get("members") else ""
        group = f", all {len(c['members'])} terms labelled {c['label']}" if c.get("members") else ""
        out.append(f"- {c['facet']}: **{c['label']}**{where} (`{c['value']}`, level {c['level'] if c['level'] is not None else '-'}"
                   f"{group}), resolved from '{c['phrase']}' by {c['resolved_by']}")
    for b in report.get("breakdown", []):
        out += ["", f"Direct papers by branch for {b['label']}:"]
        out += [f"- {x['path']}: {', '.join(f'`{p}`' for p in x['papers']) or 'none'}" for x in b["branches"]]
    if report["unwidenable"]:
        out += ["", "Cannot be widened (so adjacent evidence for these is not searched): " + ", ".join(report["unwidenable"])]
    n = report["counts"]
    out += ["", "## Verdict", "", f"**{report['verdict']}**", "", report["rule"], "",
            f"Direct: {n['direct']}. Adjacent: {n['adjacent']}. Different method: {n['different_method']}. "
            f"Partial matches: {n['partial']}.", "", report["caveat"], "", "## Coverage", "",
            f"- Eligible papers: {cov['eligible']}; excluded: {cov['excluded']}; eligible without a record: "
            f"{cov['without_record']}; open (tier C) facts left out: {cov['open_tier_c']}.",
            f"- Database: `{cov['db']['path']}` ({cov['db']['papers']} papers).",
            f"- Designs among direct and adjacent papers: {cov['designs'] or 'none'}.",
            f"- Countries: {cov['countries'] or 'none'}.",
            f"- Years: {'-'.join(map(str, cov['year_range'])) if cov['year_range'] else 'none'}.",
            f"- Result directions: {cov['result_directions'] or 'none'}.",
            f"- Thin (fewer than 3 direct papers): {'yes' if cov['thin'] else 'no'}.", f"- {cov['completeness']}"]
    spots = cov["blind_spots"]
    if spots:
        out += ["", "### Blind spots (not counted in the verdict)", ""]
        for facet, ids in spots.get("proposed", {}).items():
            out.append(f"- {len(ids)} paper(s) have proposed (non-vocabulary) values in {facet} and may cover this question "
                       f"under wording the vocabulary lacks: {', '.join(ids)}")
        if "no_country_fact" in spots:
            out.append(f"- {len(spots['no_country_fact'])} paper(s) have no country fact: {', '.join(spots['no_country_fact']) or 'none'}")
            out.append(f"- {len(spots['broad_scale'])} paper(s) are multi-country or global and not direct: "
                       f"{', '.join(spots['broad_scale']) or 'none'}")
    probe = (report.get("external") or {}).get("probe")
    if probe:
        out += ["", "## Recall probe", ""]
        if "error" in probe:
            out.append(f"Probe not run: {probe['error']}")
        elif not probe["retrieved"]:
            out.append(f'OpenAlex returned no results for "{probe["query"]}".')
        else:
            lo, hi = probe["interval"]
            out.append(f'Top {probe["retrieved"]} OpenAlex results by relevance for "{probe["query"]}"; {probe["in_corpus"]} are in '
                       f"the corpus ({lo:.0%} to {hi:.0%} interval). This measures the corpus against OpenAlex's ranking for this "
                       "wording, not against all the literature.")
    out += ["", "## Evidence", ""]
    for e in report["evidence"]:
        out += [f"### {_paper_line(e)}: {e['kind']}"]
        out += [f"- {label}" for label in e["labels"]]
        out += [f"- fact: {f['facet']} = {f.get('path') or f['label']} (tier {f['tier']})" + (f' — "{f["quote"]}"' if "quote" in f else "") for f in e["facts"]]
        out += [f"- result ({r['direction']}): {r['claim']}" + (f' — "{r["quote"]}"' if "quote" in r else "") for r in e["results"]]
        out.append("")
    if not report["evidence"]:
        out += ["No direct or adjacent papers.", ""]
    if report["partial"]:
        out += ["## Partial matches (no verdict applies)", ""]
        out += [f"- {_paper_line(p)}: matches {p['matched']} constraint(s) exactly" for p in report["partial"]] + [""]
    if report["different_method"]:
        out += ["## Different method", ""] + [f"- {_paper_line(p)}" for p in report["different_method"]] + [""]
    return "\n".join(out).rstrip() + "\n"


def write_report(report: dict, run_dir) -> tuple[Path, Path]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in (("report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
                       ("report.md", render_markdown(report))):
        path = run_dir / name
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
        paths.append(path)
    return paths[0], paths[1]
