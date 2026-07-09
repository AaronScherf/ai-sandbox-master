# 🚀 Master AI Sandbox Workspace Orchestrator

Welcome to the **Master AI Sandbox Workspace Orchestrator** (`ai-sandbox-master`). This repository acts as the central control plane and backup engine for your entire academic productivity suite, independent research, and web portfolio infrastructure.

It is designed to cleanly manage, synchronize, and secure your files, providing an isolated containerized workspace for AI-driven synthesis (using Open Interpreter or other local models) without exposing sensitive credentials or interfering with nested Git subprojects.

---

## 📂 Architecture Map

By decoupling the parent orchestrator from the nested child directories, the project maintains a clean separation of concerns:

```text
ai-sandbox-master/                  <-- Parent Orchestrator (This Repository)
├── .git/                           <-- Master Version Tracking (Private GitHub Backup)
├── .gitignore                      <-- Prevents nested repos/data from leaking into Master
├── workspace_generator.sh          <-- Master Setup, Generation, and Sync Script
├── Instructions for Starting...    <-- Human-readable Setup Blueprint
├── README.md                       <-- Main Directory Documentation (This File)
└── ai-sandbox/                     <-- Isolated containerized workspace
    ├── .env                        <-- SECURE Local variables & API Keys (Git-Ignored)
    ├── docker-compose.yml          <-- Container architecture setup (Git-Tracked)
    ├── readme.md                   <-- Sandbox Workspace Registry
    │
    ├── 📚 academic-hub/
    │   ├── 🔄 01-resources/        <-- Synced via Rclone to Drive (Git-Ignored)
    │   └── 🐙 02-academic-notes/   <-- Git Repo (Synced to private academic GitHub)
    │
    ├── 🌐 personal-website/
    │   └── AaronScherf.../         <-- Git Repo (Synced to your public portfolio GitHub)
    │
    └── 🔬 research/
        ├── 🔄 journal-articles/   <-- Downstream Read-Only PDFs (Paperpile managed)
        └── 📂 independent-res.../
            ├── 🔄 notes/           <-- Synced via Rclone (Nebo canvas exports)
            └── 📂 projects/        <-- Isolated Git repositories per project
```

---

## ⚙️ How `workspace_generator.sh` Works

The `workspace_generator.sh` is an automated bash script that safely bootstraps, updates, and synchronizes your environment. Here is a breakdown of its core pipeline:

### 1. Master Git Pull & Clone Sync
* **Pull Mode**: If the parent `.git` exists, it queries GitHub and fetches any script or manual updates, pulling them down before any folders are modified.
* **Clone Mode**: If `.git` doesn't exist but `GITHUB_SANDBOX_URL` is configured, it automatically initializes and checkouts the master orchestrator repo.

### 2. Scaffold Missing Directory Tree
* Re-scaffolds the entire academic, research, and personal-website folder architectures cleanly.
* Because `mkdir -p` is used, **no existing local data, PDFs, notes, or files are ever overwritten or deleted**.

### 3. Smart Universal Child Git Update
* Clones your portfolio repository (`AaronScherf.github.io`) if it isn't present.
* Scans recursively starting at depth 2 inside `ai-sandbox` to find **every** nested subdirectory containing a `.git` folder, automatically performing a `git pull` to update your notes, website, and research projects.

### 4. Inject System Manuals & Safeguard Local Configs
* Updates and injects standard system markdown manuals (`readme.md` files) across the directories.
* **API Protection**: Checks if `ai-sandbox/.env` or `ai-sandbox/docker-compose.yml` already exist. If found, it **skips** generating them to preserve your active API keys and custom container modifications.

### 5. Automated Repository Publisher (using `gh`)
* If run on a new system where `.git` is missing, it initializes Git, adds all files, makes an initial commit, and checks for the GitHub CLI (`gh`).
* If logged in, it auto-creates a private `ai-sandbox-master` repository on your GitHub account and pushes to it instantly. If not, it displays clear manual instructions.

### 6. Rclone Bisync Syncing (Optional)
* If `ENABLE_RCLONE_SYNC` is toggled to `true`, it initiates a background bidirectional sync using `rclone bisync` to mirror your handwritten notes (`independent-research/notes`) and textbook resources (`academic-hub/01-resources`) with Google Drive.

---

## 🔒 Security & Best Practices

### 🔑 Secret Lockdown (`.env`)
To prevent accidental exposure of your Google Gemini API keys (or other LLM backend credentials), all secrets are migrated out of `docker-compose.yml` into `ai-sandbox/.env`. 
* **`ai-sandbox/.env`**: Contains your raw `GEMINI_API_KEY=...`.
* **`ai-sandbox/docker-compose.yml`**: References variables using `${GEMINI_API_KEY}`, keeping the file safe to publish.
* **Git Safeguard**: Both `.env` and `ai-sandbox/.env` are hardcoded into the master `.gitignore` to guarantee your keys can never be leaked to GitHub.

### 🔀 Avoiding Nested Repository Corruption
Commiting a folder containing a `.git` directory inside another Git repository normally causes "embedded submodule" warnings, breaking push histories. 
* The parent `.gitignore` explicitly ignores `personal-website/`, `research/.../projects/`, and `academic-hub/02-academic-notes-code/`.
* This keeps the parent orchestrator and each sub-project completely decoupled, enabling you to commit and push to them independently without interference.

---

## 🚀 Quick Start

1. **Verify or Configure Variables**:
   Open `workspace_generator.sh` and ensure your switches and links are correct:
   ```bash
   ENABLE_GIT_UPDATES=true
   ENABLE_RCLONE_SYNC=false
   GITHUB_SANDBOX_URL="https://github.com/AaronScherf/ai-sandbox-master.git"
   ```

2. **Execute the Sync**:
   Run the orchestrator from Git Bash or your terminal:
   ```bash
   bash workspace_generator.sh
   ```

3. **Provide API Credentials**:
   Open `ai-sandbox/.env` and paste your Google Gemini key:
   ```text
   GEMINI_API_KEY=your_actual_key_here
   ```

4. **Spin up your Container**:
   ```bash
   cd ai-sandbox
   docker compose up -d
   ```
