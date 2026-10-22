"""Render the review and the annotated bibliography. Deterministic: the bibliography never depends on model prose."""
from __future__ import annotations

import re

from .annotation import annotation_of, cite_keys
from .cluster import load_cluster, topic_dir
from .contribute import load_annotations
from .stage import Target
from .synth import assign_ids, load_outputs

_CITE = re.compile(r"P(\d+)(?:\.R\d+)?")


def _anchor(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")


def _bibliography(cluster, anns, notes, keys) -> str:
    out = [f"# Annotated bibliography: {cluster.name}", ""]
    for fid in sorted(cluster.file_ids):
        ann, note, ident = anns[fid], notes[fid], anns[fid]["identity"]
        out += [f"## {keys[fid]}", "", f"{ident.get('title') or fid} ({ident.get('publication_year', 'year unknown')})"]
        if ident.get("doi"):
            out.append(f"DOI: {ident['doi']}")
        for facet in ("study_design", "countries", "intervention", "outcome"):
            if ann["facts"].get(facet):
                out.append(f"- {facet.replace('_', ' ')}: " + "; ".join(f"{f['label']} [{f['tier']}]" for f in ann["facts"][facet]))
        for r in ann["results"]:
            out.append(f"- result {r['id']}: {r['claim']} ({r['effect_direction']}, {r['magnitude']}; page {r['locator']})")
        for part, title in (("contribution", "Contribution"), ("limitations", "Limitations")):
            n = note[part]
            out += ["", f"**{title}.** {n['text']}", f"> {n['quote']} (page {n['locator']})"]
        out.append("")
    return "\n".join(out)


def render(target: Target, name: str):
    cluster = load_cluster(target.index_root, name)
    notes = load_annotations(target.index_root, name)
    if missing := [f for f in cluster.file_ids if f not in notes]:
        raise ValueError("annotate these papers first: " + ", ".join(missing))
    final = load_outputs(target.index_root, name).get("synth-final")
    if final is None:
        raise ValueError("synth-final is missing: run `synthesize` (and `synthesize --merge` if it made chunk cards), "
                         "fill the cards and submit them")
    anns = {f: annotation_of(target.records, f, target.vocabs, cluster.floor) for f in cluster.file_ids}
    keys = cite_keys({f: anns[f]["identity"] for f in cluster.file_ids})
    by_pid = {pid: fid for fid, pid in assign_ids(cluster.file_ids).items()}
    where = ", ".join(f"{c['facet']}={c['value']}" for c in cluster.constraints)
    lines = ["---", f'title: "Literature review: {name}"', "tags: [literature-review]", f'cluster: "{where}"',
             f"tier_floor: {cluster.floor}", f"papers: {len(cluster.file_ids)}", "---", "", f"# Literature review: {name}", ""]
    for sec in final["sections"]:
        lines += [f"## {sec['heading']}", ""]
        for para in sec["paragraphs"]:
            fids = list(dict.fromkeys(by_pid[f"P{_CITE.fullmatch(c).group(1)}"] for c in para["cites"]))
            links = "; ".join(f"[{keys[f]}](bibliography.md#{_anchor(keys[f])})" for f in fids)
            lines += [f"{para['text'].strip()} ({links})", ""]
    folder = topic_dir(target.index_root, name)
    review_path, bib_path = folder / "review.md", folder / "bibliography.md"
    review_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    bib_path.write_text(_bibliography(cluster, anns, notes, keys), encoding="utf-8", newline="\n")
    return review_path, bib_path
