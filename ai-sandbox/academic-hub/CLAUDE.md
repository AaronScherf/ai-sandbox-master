# CLAUDE.md — academic-hub

Content vault (Obsidian), not code. The pipelines that write here live in `../academic-rag-model/`. See `README.md` for the full layout.

- `academic_notes/` is a **separate nested git repo** (tablet sync); commits there go to that repo, not the outer one.
- `academic_resources/` holds heavy sources: PDFs, raw textbook conversions, images. Treat as read-only unless asked. Files mirror `academic_notes/`'s `<course>/<category>/` paths.
- Textbook `.md` / `.rag.md` files can be several hundred KB. Grep or read line ranges, never whole files.
- Don't read `.index/` directly; query it with `python -m indexer.index_search query "..."` from `../academic-rag-model/`.
- Much of this content is third-party copyrighted. Check the root `.gitignore` before staging anything new here.
