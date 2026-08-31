# Academic Hub

Per-course academic content: your own notes/coursework plus the source
material it's derived from. See the root [`README.md`](../../README.md) for
the whole-repo architecture and [`academic-rag-model/`](../academic-rag-model/README.md)
for the pipelines that populate and index this folder.

- [`academic_notes/<course>/`](academic_notes/) — your own TA notes, problem
  sets, exams, handwritten-note transcriptions. Tracked in git.
- `academic_resources/<course>/{textbooks,lecture-slides,lecture-recordings}/`
  — copyrighted, third-party source material (textbook PDFs and their
  full-text Markdown conversions, lecture slides/recordings). Gitignored —
  see the root `.gitignore`'s own comments for why. Run
  `workspace_generator.sh` (repo root) to scaffold these empty per course.
- `.index/` — the source-indexer's per-file cards and corpus-wide tags
  (derivative metadata, tracked); `.index/chunks/` (verbatim passage
  excerpts, gitignored).

Course folders are driven entirely by what you create under
`academic_notes/` — there's no fixed course list.
