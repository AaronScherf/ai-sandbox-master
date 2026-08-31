# Research

Independent research writing plus the published literature it engages with.
See the root [`README.md`](../../README.md) for the whole-repo architecture
and [`academic-rag-model/`](../academic-rag-model/README.md) for the
pipelines that populate and index this folder.

- [`independent-research/`](independent-research/) — your own essays,
  research notes, and project write-ups, organized thematically. Tracked in
  git.
- `journal-articles/` — published journal-article PDFs and their full-text
  Markdown conversions. Gitignored — same third-party-copyright reasoning as
  `academic-hub/academic_resources/`'s textbooks; see the root
  `.gitignore`'s own comments. Run `workspace_generator.sh` (repo root) to
  scaffold this empty.
- `.index/` — the source-indexer's per-file cards and corpus-wide tags
  (derivative metadata, tracked); `.index/chunks/` (verbatim passage
  excerpts, gitignored).

`academic-hub` and `research` are independent search roots — 
`academic-rag-model/indexer/index_search.py`'s `--root` flag is repeatable,
so a query can span both corpora at once.
