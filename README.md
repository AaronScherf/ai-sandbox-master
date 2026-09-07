# 🚀 ai-sandbox-master

Root orchestrator repository for an academic productivity suite: PDF/document
conversion pipelines, a searchable cross-course index, a grounded tutoring
agent, independent research writing, and a personal-website portfolio. The
actual conversion/indexing code lives in [`ai-sandbox/academic-rag-model/`](ai-sandbox/academic-rag-model/README.md)
— start there for the pipelines themselves. This file covers the repo as a
whole: what's tracked, what isn't, and how to stand up your own copy.

## Architecture map

```text
ai-sandbox-master/                       <-- this repo
├── .gitignore                           <-- excludes copyrighted PDFs/full-text, secrets, and local tool state (see its own comments)
├── workspace_generator.sh               <-- scaffolds the folders .gitignore excludes; see below
├── README.md                            <-- this file
└── ai-sandbox/
    ├── .env                             <-- GEMINI_API_KEY + GCP/journal_discovery vars, from .env.example (gitignored)
    ├── readme.md                        <-- ai-sandbox-level map, generated if missing
    │
    ├── academic-rag-model/              <-- conversion/indexing/RAG pipelines (tracked)
    │
    ├── academic-hub/                    <-- see academic-hub/README.md
    │   ├── academic_notes/<course>/     <-- your own TA notes, problem sets, exams (tracked); audio_generator's sibling *.mp3 narrations here are gitignored
    │   ├── academic_resources/<course>/
    │   │   ├── textbooks/               <-- copyrighted textbook PDFs + full-text .md (gitignored)
    │   │   ├── lecture-slides/          <-- gitignored (institution/professor-owned)
    │   │   └── lecture-recordings/      <-- gitignored
    │   └── .index/                      <-- source-indexer cards + tags (tracked); .index/chunks/ (gitignored — verbatim excerpts)
    │
    ├── research/                        <-- see research/README.md
    │   ├── independent-research/        <-- your own essays, research notes, index cards (tracked); projects/** are separate child git repos, cloned automatically per workspace_generator.sh's INDEPENDENT_RESEARCH_REPOS list
    │   ├── journal-articles/            <-- published journal-article PDFs + full-text .md (gitignored)
    │   └── .index/                      <-- same tracked/gitignored split as academic-hub's
    │
    └── personal-website/
        └── AaronScherf.github.io/       <-- separate git repo, Hugo/HugoBlox portfolio site
```

The dividing line throughout: **your own authored content and derivative
metadata (titles, summaries, tags) are tracked; other people's copyrighted
full text (published textbooks, journal articles) is not.** See the root
`.gitignore`'s own comments for the exact patterns and reasoning.

## Getting started (your own copy, your own content)

1. `git clone` this repo.
2. Create your own `academic-hub/academic_notes/<course>/` folder(s) for
   whatever courses you're tracking — there's nothing to inherit here, this
   is where you establish your own course list.
3. Run `bash workspace_generator.sh` from the repo root. It scaffolds the
   gitignored `academic_resources/<course>/{textbooks,lecture-slides,lecture-recordings}/`
   folders for each course you created in step 2, plus `research/journal-articles/`;
   clones the personal website and every independent research/thesis repo
   listed in the script's own `INDEPENDENT_RESEARCH_REPOS` array (first run
   only — a normal `git pull` after that), and pulls updates for any other
   child git repo it finds already on disk; and copies `ai-sandbox/.env.example`
   to `ai-sandbox/.env` if you haven't created one yet. See the script's own
   header comments for exactly what it does and doesn't do — it's
   deliberately narrow now: it fills the gaps `.gitignore` leaves on
   purpose, it doesn't reimplement `git clone` for this repo itself.
4. Fill in your own values in `ai-sandbox/.env` — at minimum `GEMINI_API_KEY`;
   see the file's own comments for what each pipeline (textbook conversion,
   `journal_discovery`, `analyze_textbook`) needs.
5. Replicating this project with your own independent research/thesis repos
   (rather than the original author's) means editing `INDEPENDENT_RESEARCH_REPOS`
   in `workspace_generator.sh` first — each entry is `path/relative/to/projects/|git-url`.
   They're deliberately kept as separate child repos (own history), not
   embedded in this one; step 3 clones (or pulls) whatever's listed there.
6. Drop your own PDFs into the scaffolded folders and run the
   `academic-rag-model` pipelines against them — see
   [`ai-sandbox/academic-rag-model/README.md`](ai-sandbox/academic-rag-model/README.md).

Nothing about steps 2-6 requires sharing any of the original author's actual
PDFs or notes — only the code, prompts, and pipeline structure are shared;
your content stays local (and gitignored) throughout.

## Open decisions

- **Docker.** Not currently part of the day-to-day workflow — everything
  above runs directly with a Python venv and a Gemini API key. Worth
  revisiting for reproducibility and as a possible host for a future
  Open-Interpreter/Claude-based tutor agent once that design is settled, but
  there's no current `docker-compose.yml` to keep in sync, so none is
  generated. Flagged here rather than silently dropped.
- **Tutor/study agent.** [`academic-rag-model/rag/`](ai-sandbox/academic-rag-model/rag/README.md)
  is a working grounded Q&A CLI today; a fuller agentic tutor (Open
  Interpreter or a Claude-based framework) is still an open design question,
  not yet built.

## Backing up gitignored content

Large PDFs (textbooks, journal articles) aren't tracked in git and need
their own backup. `ENABLE_RCLONE_SYNC` in `workspace_generator.sh` (off by
default) bisyncs just those folders — `academic_resources/<course>/textbooks/`
and `research/journal-articles/` — to a configured rclone remote. It does not
sync lecture slides/recordings or anything else; narrow it further or widen
it in the script if your own setup differs.

If you use Zotero to catalogue these PDFs, keep its data directory at
Zotero's own default location (or anywhere else no other sync tool touches)
— never inside this repo or any other synced folder. Zotero's own docs warn
that cloud-sync/bisync tools don't respect the file locks its SQLite library
relies on, and will corrupt it. Use linked (not stored-copy) attachments
pointing at the PDFs above, with a **Linked Attachment Base Directory** set
under `ai-sandbox/research/journal-articles/` so the links are relative and
resolve the same way on another machine; sync the library itself (citations,
tags, collections) via Zotero's own account sync, which is also what
`journal_discovery/zotero_sync.py`'s `ZOTERO_LIBRARY_ID`/`ZOTERO_API_KEY`
already assume.
