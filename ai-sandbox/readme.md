# 🗺️ Master Workspace Registry (AI Sandbox Root)

This is the root directory for all academic, research, and web portfolio infrastructure. 

## 🤖 The Docker Sandbox & Workspace Generator
Everything within this `ai-sandbox` folder is designed to be **containerized via Docker** to provide a secure environment for Open Interpreter and the Google Gen AI API. 
* The configuration dictating how the AI views these folders can be found in `docker-compose.yml`.
* **Workspace Generator:** This entire directory tree, along with all `.git` updates and `rclone` syncs, is maintained by `workspace_generator.sh`. Running that script will safely generate missing folders, pull down external repository updates, and refresh these instructional manuals without overwriting your files.

## 📐 The Golden Architecture Rules
1. **The Code Ecosystem (GIT):** Managed entirely through Git and pushed to GitHub. Never allow cloud sync engines to touch these folders.
2. **The Data Ecosystem (RCLONE):** Managed by background Rclone bisync scripts mirroring data to Google Drive. Never initialize Git repos inside these folders.
3. **Naming Convention:** All directories and files must use lowercase alphanumeric characters separated by hyphens (`lower-kebab-case`).

## 📂 Directory Architecture Map
ai-sandbox/
├── 🐳 docker-compose.yml                          <-- Core Docker container configuration
├── 📝 readme.md                                   <-- Master Workspace Registry
│
├── 📚 academic-hub/
│   ├── 🔄 01-resources/                           <-- MANAGED BY RCLONE (Synced to Drive, Read-Only for AI)
│   │   ├── econ-101/
│   │   │   ├── briefings/
│   │   │   └── nebo-exports/
│   │   └── [Other Courses...]
│   │
│   └── 🐙 02-academic-notes-code/                 <-- MANAGED BY GIT (Synced to GitHub, Read-Write for AI)
│       ├── econ-101/
│       │   ├── latex/
│       │   └── markdown/
│       └── scripts/
│
├── 🌐 personal-website/                           <-- MANAGED BY GIT (Synced to GitHub, Read-Write for AI)
│   ├── content/
│   └── static/
│
└── 🔬 research/
    ├── 🔄 journal-articles/                       <-- MANAGED BY PAPERPILE (Read-Only for AI)
    │
    ├── 📂 independent-research/
    │   ├── 🔄 notes/                              <-- MANAGED BY RCLONE
    │   └── 📂 projects/
    │       ├── 🐙 ai-trading-bot/                 <-- MANAGED BY GIT (Read-Write for AI)
    │       └── 🐙 neural-net-sim/                 <-- MANAGED BY GIT (Read-Write for AI)
    │
    └── 📂 scripts/
