# 🚀 ai-sandbox-master

Root orchestrator repository for an academic productivity suite: PDF/document
conversion pipelines, a searchable cross-course index, a grounded tutoring
agent, independent research writing, and a personal-website portfolio. The
actual conversion/indexing code lives in [`ai-sandbox/marker-conversion/`](ai-sandbox/marker-conversion/README.md)
— start there for the pipelines themselves. This file covers the repo as a
whole: what's tracked, what isn't, and how to stand up your own copy.

## Architecture map

```text
ai-sandbox-master/                       <-- this repo
├── .gitignore                           <-- excludes copyrighted PDFs/full-text (see its own comments)
├── workspace_generator.sh               <-- scaffolds the folders .gitignore excludes; see below
├── README.md                            <-- this file
└── ai-sandbox/
    ├── .env                             <-- GEMINI_API_KEY (gitignored)
    ├── readme.md                        <-- ai-sandbox-level map, generated if missing
    │
    ├── marker-conversion/               <-- conversion/indexing/RAG pipelines (tracked)
    │
    ├── academic-hub/
    │   ├── academic_notes/<course>/     <-- your own TA notes, problem sets, exams (tracked)
    │   ├── academic_resources/<course>/
    │   │   ├── textbooks/               <-- copyrighted textbook PDFs + full-text .md (gitignored)
    │   │   ├── lecture-slides/          <-- gitignored (institution/professor-owned)
    │   │   └── lecture-recordings/      <-- gitignored
    │   └── .index/                      <-- source-indexer cards + tags (tracked); .index/chunks/ (gitignored — verbatim excerpts)
    │
    ├── research/
    │   ├── independent-research/        <-- your own essays, research notes, index cards (tracked)
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
2. Copy `ai-sandbox/.env.example` to `ai-sandbox/.env` and add your own
   `GEMINI_API_KEY`.
3. Create your own `academic-hub/academic_notes/<course>/` folder(s) for
   whatever courses you're tracking — there's nothing to inherit here, this
   is where you establish your own course list.
4. Run `bash workspace_generator.sh` from the repo root. It scaffolds the
   gitignored `academic_resources/<course>/{textbooks,lecture-slides,lecture-recordings}/`
   folders for each course you created in step 3, plus `research/journal-articles/`,
   and pulls updates for any child git repos (the personal website, your own
   independent project repos). See the script's own header comments for
   exactly what it does and doesn't do — it's deliberately narrow now: it
   fills the gap `.gitignore` leaves on purpose, it doesn't reimplement
   `git clone`.
5. Drop your own PDFs into the scaffolded folders and run the
   `marker-conversion` pipelines against them — see
   [`ai-sandbox/marker-conversion/README.md`](ai-sandbox/marker-conversion/README.md).

Nothing about steps 3-5 requires sharing any of the original author's actual
PDFs or notes — only the code, prompts, and pipeline structure are shared;
your content stays local (and gitignored) throughout.

## Open decisions

- **Docker.** Not currently part of the day-to-day workflow — everything
  above runs directly with a Python venv and a Gemini API key. Worth
  revisiting for reproducibility and as a possible host for a future
  Open-Interpreter/Claude-based tutor agent once that design is settled, but
  there's no current `docker-compose.yml` to keep in sync, so none is
  generated. Flagged here rather than silently dropped.
- **Tutor/study agent.** [`marker-conversion/rag/`](ai-sandbox/marker-conversion/rag/README.md)
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
