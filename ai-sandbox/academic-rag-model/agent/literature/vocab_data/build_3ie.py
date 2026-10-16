"""Builds vocabulary YAML files from a saved copy of the 3ie Taxonomy explorer page (every branch expanded).

    python -m agent.literature.vocab_data.build_3ie "<saved page.html>" --out <dir>

The output holds 3ie's own wording, so write it to an ignored directory and pass that to the CLI with --vocab-dir.
This script contains no 3ie text. The saved page's list markup nests sector > broad group > group > leaf; each
level becomes a term whose `parent` is the level above. Only the tree under the page's "Interventions" or
"Outcomes" heading (--tree) is read.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import yaml

_LEVELS = (("sector-click", 1), ("board-group-click", 2), ("disaggregated-intervention-click", 3))


class _Tree(HTMLParser):
    def __init__(self, tree: str):
        super().__init__(convert_charrefs=True)
        self.tree = tree
        self.nodes: list[dict] = []
        self._section: str | None = None
        self._h4 = False
        self._pending: int | None = None
        self._label = False
        self._current: dict | None = None
        self._tip_depth = 0
        self._tip_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        if tag == "h4":
            self._h4 = True
        if self._tip_depth:
            self._tip_depth += 1
        elif tag == "div" and "__react_component_tooltip" in cls and "child_search" not in (a.get("id") or ""):
            self._tip_depth, self._tip_text = 1, []
        if self._section != self.tree:
            return
        if tag == "div" and "MuiListItem-root" in cls:
            for marker, level in _LEVELS:
                if marker in cls:
                    self._pending = level
        if tag == "a" and "/taxonomy-search-detail/" in (a.get("href") or "") and self._pending is None:
            self._pending = 4
        if tag == "span" and "MuiListItemText-primary" in cls and self._pending is not None:
            self._label = True

    def handle_endtag(self, tag):
        if tag == "h4":
            self._h4 = False
        if self._tip_depth:
            self._tip_depth -= 1
            if self._tip_depth == 0 and self._current is not None and not self._current["definition"]:
                self._current["definition"] = " ".join("".join(self._tip_text).split())

    def handle_data(self, data):
        if self._h4:
            self._section = data.strip()
        if self._tip_depth:
            self._tip_text.append(data)
        elif self._label and self._pending is not None:
            node = {"level": self._pending, "label": " ".join(data.split()), "definition": ""}
            self.nodes.append(node)
            self._current, self._pending, self._label = node, None, False


def _slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_") or "x"


def parse_tree(html_text: str, tree: str) -> list[dict]:
    p = _Tree(tree)
    p.feed(html_text)
    return p.nodes


def build_vocabulary(nodes: list[dict], name: str, source: str) -> dict:
    terms: list[dict] = []
    ids: set[str] = set()
    stack: dict[int, str] = {}
    for n in nodes:
        parent = stack.get(n["level"] - 1)
        base = f"{name}.{_slug(n['label'])}"
        tid = base
        if tid in ids and parent:  # the same wording under another branch is a different term
            tid = f"{base}_{parent.split('.', 1)[1]}"
        k = 2
        while tid in ids:
            tid, k = f"{base}_{k}", k + 1
        ids.add(tid)
        stack = {lvl: v for lvl, v in stack.items() if lvl < n["level"]}
        stack[n["level"]] = tid
        term = {"id": tid, "label": n["label"]}
        if parent:
            term["parent"] = parent
        if n["definition"]:
            term["definition"] = n["definition"]
        terms.append(term)
    return {"vocabulary": name, "version": 1, "provenance": "3ie", "source": source, "terms": terms}


def sectors_vocabulary(nodes: list[dict], source: str) -> dict:
    seen, terms = set(), []
    for n in nodes:
        if n["level"] == 1 and n["label"] not in seen:
            seen.add(n["label"])
            terms.append({"id": f"sector.{_slug(n['label'])}", "label": n["label"]})
    return {"vocabulary": "sector", "version": 1, "provenance": "3ie", "source": source, "terms": terms}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("--tree", choices=["Interventions", "Outcomes"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source", default="3ie Development Evidence Portal taxonomy explorer, saved page")
    ap.add_argument("--with-sectors", action="store_true", help="Also write sector.yaml from the tree's top level.")
    args = ap.parse_args(argv)
    nodes = parse_tree(Path(args.page).read_text(encoding="utf-8", errors="replace"), args.tree)
    name = "intervention" if args.tree == "Interventions" else "outcome"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    files = [(name, build_vocabulary(nodes, name, args.source))]
    if args.with_sectors:
        files.append(("sector", sectors_vocabulary(nodes, args.source)))
    for n, data in files:
        (out / f"{n}.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10**6),
                                       encoding="utf-8", newline="\n")
        print(f"{n}: {len(data['terms'])} terms -> {out / (n + '.yaml')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
