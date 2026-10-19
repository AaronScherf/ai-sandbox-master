"""How much of a course's material reaches the concept-graph seed card, against how much exists (TODO-0074).

Counts, per kind of material and per file, the labelled statements and section headings that
`agent.concept_graph.stages.seed.outline_context` offers against all that the files hold, lists the files a role cap
or the textbook chapter scope leaves out, and checks whether the graph's concept names appear in the offered
material, only in the left-out material, or in neither. No model or embedding calls.

The per-kind limits below mirror `outline_context`; keep them in step when that function changes.

    python -m tools.seed_card_coverage --hub-root ../academic-hub --course microecon --graph ../../microecon-concept-graph
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

from agent.concept_graph.stages import seed
from agent.concept_graph.store import GraphStore
from core.course_materials import load_catalog

UNLIMITED = 10_000
# (statements, headings) offered per file; 0 means that kind is not offered for this material by design.
LIMITS = {"instructor": (25, 20), "recitation": (0, 15), "prior": (25, 0), "textbook": (0, 40), "student_notes": (12, 12)}


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def measure(hub_root: str, course: str, graph_root: str) -> None:
    hub = Path(hub_root)
    catalog = load_catalog(hub_root, course)
    store = GraphStore(graph_root)
    graph, config = store.read_all(), store.read_seed_config()
    offered: list[str] = []
    existing: list[str] = []
    rows = []  # (group, file, statements offered, statements, headings offered, headings, left out)

    def tally(group: str, kind: str, m, left_out: bool) -> None:
        text = (hub / m.path).read_text(encoding="utf-8", errors="ignore")
        statements = seed.statement_anchors(text, limit=UNLIMITED)
        headings = seed.section_headings(text, limit=UNLIMITED)
        max_st, max_hd = (0, 0) if left_out else LIMITS[kind]
        existing.extend(statements + headings)
        offered.extend(statements[:max_st] + headings[:max_hd])
        rows.append((group, kind, m.path.rsplit("/", 1)[-1], min(max_st, len(statements)), len(statements),
                     min(max_hd, len(headings)), len(headings), left_out))

    for i, m in enumerate(catalog.by_role("instructor")):
        tally("instructor", "instructor", m, i >= seed.ROLE_CAPS["instructor"])
    for i, m in enumerate(catalog.by_role("recitation")):
        tally("recitation", "recitation", m, i >= seed.ROLE_CAPS["recitation"])
    for label in catalog.offerings():
        for i, m in enumerate(catalog.by_role("instructor", offering=label)):
            tally(f"prior {label}", "prior", m, i >= seed.ROLE_CAPS["prior"])
    wanted = {k.lower(): set(v) for k, v in config.textbook_chapters.items()}
    for m in catalog.by_role("textbook"):
        chapter = seed._CHAPTER_FILE.search(m.path)
        if not chapter or int(chapter.group(1)) == 0:
            continue
        scope = wanted.get((m.book or "").lower()) or wanted.get(m.path.split("/")[-3].lower()) or set()
        tally(f"textbook {m.book}", "textbook", m, int(chapter.group(1)) not in scope)
    by_date = defaultdict(list)
    for m in catalog.by_role("student_notes"):
        if m.date:
            by_date[m.date].append(m)
    for i, date in enumerate(sorted(by_date)):
        for m in by_date[date]:
            tally("student_notes", "student_notes", m, i >= seed.ROLE_CAPS["student_notes"])

    print("== offered/existing per group; files left out by a role cap or the chapter scope ==")
    totals = defaultdict(lambda: [0] * 6)
    for group, _, _, so, sa, ho, ha, out in rows:
        t = totals[group]
        for j, v in enumerate((so, sa, ho, ha, out, 1)):
            t[j] += v
    for group, (so, sa, ho, ha, out, n) in totals.items():
        print(f"{group:28s} statements {so:4d}/{sa:<4d} headings {ho:4d}/{ha:<4d} files left out {out}/{n}")

    print("\n== files cut by a per-file limit ==")
    for group, kind, name, so, sa, ho, ha, out in rows:
        max_st, max_hd = LIMITS[kind]
        if not out and ((max_st and so < sa) or (max_hd and ho < ha)):
            print(f"{group:20s} {name[:60]:60s} statements {so}/{sa} headings {ho}/{ha}")

    context, passages = seed.outline_context(hub_root, course, config=config, catalog=catalog)
    print(f"\n== card: header {len(context)} chars (cut at 12000), {len(passages)} passages, "
          f"{sum(len(p.text) for p in passages)} passage chars ==")

    offered_text = f" {' '.join(_norm(x) for x in offered)} "
    existing_text = f" {' '.join(_norm(x) for x in existing)} "
    where: Counter = Counter()
    left_out_only = []
    for node in graph.nodes:
        name = f" {_norm(node.name)} "
        if name in offered_text:
            where["offered"] += 1
        elif name in existing_text:
            where["left-out material only"] += 1
            left_out_only.append(node.name)
        else:
            where["name not found verbatim"] += 1
    print("\n== graph concepts by where their name appears ==", dict(where))
    print("in left-out material only:", left_out_only)

    offered_set = set(offered)
    never = [x for x in existing if x not in offered_set
             and re.match(r"(?i)(definition|theorem|axiom|proposition|lemma)", x)]
    print(f"\n== {len(never)} labelled statements never reach the card; first 20 ==")
    for x in never[:20]:
        print("  ", x[:150])

    per_section = Counter(n.section for n in graph.nodes)
    print(f"\n== concepts per section (floor {config.min_nodes_per_section}) ==")
    for s in sorted(graph.sections, key=lambda s: s.order):
        print(f"  {s.id:34s} {per_section[s.id]:3d}  {s.title}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--hub-root", required=True, help="the academic-hub folder")
    parser.add_argument("--course", required=True, help="course folder name under academic_notes/")
    parser.add_argument("--graph", required=True, help="the concept-graph repository (config/ and data/)")
    args = parser.parse_args()
    measure(args.hub_root, args.course, args.graph)


if __name__ == "__main__":
    main()
