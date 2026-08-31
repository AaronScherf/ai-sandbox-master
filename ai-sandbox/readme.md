# 🗺️ AI Sandbox Root

Root directory for academic, research, and web-portfolio infrastructure. See
the top-level `README.md` (one level up) for the full architecture map,
what's tracked vs. gitignored and why, and how to stand up your own copy.
See [`academic-rag-model/README.md`](academic-rag-model/README.md) for the
actual conversion/indexing/RAG pipelines.

## Directory map

```text
ai-sandbox/
├── .env                                <-- GEMINI_API_KEY (gitignored)
├── readme.md                           <-- this file
│
├── academic-rag-model/                 <-- conversion/indexing/RAG pipelines (tracked)
│
├── academic-hub/                       <-- see academic-hub/README.md
│   ├── academic_notes/<course>/        <-- your own TA notes, problem sets, exams (tracked)
│   ├── academic_resources/<course>/
│   │   ├── textbooks/                  <-- copyrighted PDFs + full-text .md (gitignored)
│   │   ├── lecture-slides/             <-- gitignored
│   │   └── lecture-recordings/         <-- gitignored
│   └── .index/                         <-- source-indexer cards (tracked); .index/chunks/ gitignored
│
├── research/                           <-- see research/README.md
│   ├── independent-research/           <-- your own essays, research notes (tracked)
│   ├── journal-articles/               <-- copyrighted PDFs + full-text .md (gitignored)
│   └── .index/                         <-- same tracked/gitignored split as above
│
└── personal-website/
    └── AaronScherf.github.io/          <-- separate git repo
```

## Golden rules

1. **Tracked vs. gitignored is about copyright, not about git vs. rclone.**
   Your own authored content (notes, essays, index metadata) is tracked in
   this repo regardless of size. Other people's copyrighted full text
   (textbook PDFs, journal-article PDFs, and their full-text conversions) is
   gitignored regardless of format — see the root `.gitignore`'s own
   comments for the exact patterns.
2. **Gitignored PDFs are your responsibility to back up.** `workspace_generator.sh`
   (one level up) can optionally rclone-bisync just the gitignored
   `academic_resources/<course>/textbooks/` and `research/journal-articles/`
   folders to a remote — off by default (`ENABLE_RCLONE_SYNC=false`), narrow
   in scope (not lecture slides/recordings, not a blanket sync).
3. **Never `git init` inside a gitignored or child-repo folder** — the
   personal website and any of your own independent project repos
   (`research/independent-research/projects/**`) are deliberately separate
   git repos, kept out of this one so each has its own independent history.
4. **Naming convention:** directories and files use lowercase alphanumeric
   characters separated by hyphens (`lower-kebab-case`), except where an
   existing tool's own convention overrides it (e.g. Python packages use
   `snake_case`).
