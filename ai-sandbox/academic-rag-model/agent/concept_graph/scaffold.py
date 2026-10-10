"""Create the skeleton of a new public graph repo (docs, licenses, issue form, empty data)."""
from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

SAMPLE = Path(__file__).resolve().parent / "sample_data"
CC_LEGALCODE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt"

MIT = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

README = """# Microeconomics concept graph

An interactive study aid: a map of the key concepts in a graduate microeconomic theory course, from binary
relations up through consumer demand, showing how the ideas connect, which results imply or are equivalent to
which, and under what conditions.

**Open it:** https://{owner}.github.io/{name}/

## How to read it

Select a concept to read what it is, what it needs, and what it leads to. Every connection is written out as a
sentence. "Show what this needs" fades everything except a concept's prerequisites. A dashed outline means an
item has not been reviewed yet.

## How to help review it

1. Open the page, type your name, and accept, reject or edit items as you read.
2. Press **Submit review**. A GitHub issue form opens with your review filled in (or copied to your clipboard to
   paste); press **Submit new issue**. You need a free GitHub account. Without one, use **Download review** and
   send the file to the maintainer.

Reviews are applied by the maintainer; nothing you do in the page changes the shared graph directly.

## What is in this repository

- `data/`: the graph as YAML (sections, nodes, edges).
- `build/graph.json` and `index.html`: the built viewer, served by GitHub Pages.
- `reviews/applied/`: reviews that have been merged.
- Content is original wording with citations; see `NOTICE.md` and the licenses.
"""

NOTICE = """# Notice

This is an independent, educational, non-commercial student project.

- It is **not affiliated with, endorsed by, or sponsored by** any textbook author, publisher, instructor or
  university.
- Sources are **cited for orientation only** (for example a chapter or section number). No text from any source
  is reproduced; explanations are written in the project's own words, and quoted text is not used.
- The content (text and data) is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0**
  (see `LICENSE`). The viewer code is licensed under the **MIT License** (see `LICENSE-CODE`).
- Nothing here is professional or legal advice, and it may contain mistakes: items marked as not yet reviewed
  have not been checked by a person.

## Takedown and corrections

If you hold rights in something you believe appears here, or you spot an error, please contact: {contact}.
We will respond promptly and remove or correct the material.
"""

ISSUE_FORM = """name: Submit a review
description: Paste the review copied from the viewer. Do not edit it.
title: "Review: "
labels: ["review"]
body:
  - type: textarea
    id: review
    attributes:
      label: Review
      description: Paste the text the viewer copied to your clipboard.
      render: json
    validations:
      required: true
"""

VOCAB = """kinds: [object, structure, property, axiom, definition, theorem, lemma, model, function, correspondence, identity, technique, example]
topics: [order-theory, rational-choice, revealed-preference, demand]
"""


def fetch_url_text(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def scaffold(root: Path, repo: str, holder: str, year: int, with_sample: bool = False,
             contact: str | None = None, fetch_text=None) -> list[str]:
    fetch_text = fetch_text or fetch_url_text
    root = Path(root)
    owner, name = repo.split("/", 1)
    contact = contact or f"open an issue at https://github.com/{repo}/issues"
    files: dict[str, str] = {
        "README.md": README.format(owner=owner, name=name),
        "NOTICE.md": NOTICE.format(contact=contact),
        "LICENSE": fetch_text(CC_LEGALCODE_URL),
        "LICENSE-CODE": MIT.format(year=year, holder=holder),
        ".gitignore": ".venv/\n__pycache__/\n*.pyc\nwork/\n",
        ".github/ISSUE_TEMPLATE/review.yml": ISSUE_FORM,
        "config/vocab.yaml": VOCAB,
        "config/site.yaml": f"title: Microeconomics concept graph\nrepo: {repo}\n",
        "data/sections.yaml": "[]\n",
        "data/rejected.yaml": "[]\n",
        "data/nodes/.gitkeep": "",
        "data/edges/.gitkeep": "",
    }
    clashes = [rel for rel in files if (root / rel).exists()]
    if clashes:
        raise FileExistsError("refusing to overwrite existing files: " + ", ".join(sorted(clashes)))
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    created = sorted(files)
    if with_sample:
        # site.yaml keeps the real repo; index.html and build/ are build output, never source.
        shutil.copytree(SAMPLE, root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("site.yaml", "index.html", "build"))
        created += ["(sample sections, nodes and edges copied in)"]
    return created
