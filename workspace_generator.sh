#!/bin/bash

# ==========================================================================
# ⚙️ CONFIGURATION VARIABLES & FEATURE SWITCHES
# ==========================================================================
# On/Off Switches (Set to 'true' to enable, 'false' to disable)
ENABLE_GIT_UPDATES=true
ENABLE_RCLONE_SYNC=false  # Defaulting to false so it doesn't error out on a fresh PC

# External Connections
RCLONE_REMOTE="gdrive:master-workspace"
GITHUB_WEBSITE_URL="https://github.com/AaronScherf/AaronScherf.github.io.git"
GITHUB_SANDBOX_URL="https://github.com/AaronScherf/ai-sandbox-master.git"
SANDBOX_DIR="ai-sandbox"

echo "🚀 Initializing Master Workspace Generation..."

# To do:
# * Change out courses from hardcoded to a variable at the top

# ==========================================================================
# 1. CLONE OR UPDATE MASTER WORKSPACE REPOSITORY
# ==========================================================================
if [ "$ENABLE_GIT_UPDATES" = true ]; then
    echo "🐙 Checking for master workspace repository..."
    if [ -d ".git" ]; then
        echo "   -> Master workspace Git repository found. Pulling latest updates..."
        git fetch -q
        LOCAL=$(git rev-parse @ 2>/dev/null)
        REMOTE=$(git rev-parse @{u} 2>/dev/null)
        if [ "$LOCAL" != "$REMOTE" ] && [ -n "$REMOTE" ]; then
            echo "      📥 Updates found. Pulling latest master workspace changes..."
            git pull -q
        else
            echo "      ✅ Master workspace is up to date."
        fi
    elif [ "$GITHUB_SANDBOX_URL" != "https://github.com/YOUR_USERNAME/YOUR_SANDBOX_REPO_PLACEHOLDER.git" ]; then
        echo "   -> Master workspace Git repository not found but remote URL is configured."
        echo "      Initializing Git and pulling from remote repository..."
        git init -b main
        git remote add origin "$GITHUB_SANDBOX_URL"
        git fetch -q
        git pull origin main -q
    fi
fi

# ==========================================================================
# 1b. CREATE ROOT SANDBOX & DIRECTORY PATHS (Skips if already exists)
# ==========================================================================
echo "📂 Creating root sandbox directory..."
mkdir -p "$SANDBOX_DIR"

echo "📂 Verifying directory structures inside sandbox (Creating if missing)..."

# Academic Hub: 01-resources (Data Layer)
mkdir -p "$SANDBOX_DIR"/academic-hub/01-resources/{econ-101,env-101,math-camp}/{briefings,google-docs,nebo-exports,lecture-recordings,lecture-slides,textbooks-and-papers}

# Academic Hub: 02-academic-notes-code (Logic Layer)
mkdir -p "$SANDBOX_DIR"/academic-hub/02-academic-notes-code/{econ-101/{latex,markdown},env-101/{latex,markdown},math-camp/{latex,markdown},scripts}

# Research Hub
mkdir -p "$SANDBOX_DIR"/research/journal-articles
mkdir -p "$SANDBOX_DIR"/research/independent-research/{notes,projects/{ai-trading-bot,neural-net-sim}}
mkdir -p "$SANDBOX_DIR"/research/scripts

echo "✅ Directories verified."

# ==========================================================================
# 2. GIT CLONE & UNIVERSAL SMART UPDATE PULL (CHILD REPOS)
# ==========================================================================
if [ "$ENABLE_GIT_UPDATES" = true ]; then
    echo "🐙 Processing Child Git Repositories..."

    # Only clone if it doesn't exist. The loop below will handle pulling updates.
    if [ ! -d "$SANDBOX_DIR/personal-website/AaronScherf.github.io/.git" ]; then
        echo "   -> Cloning personal website repository for the first time..."
        git clone "$GITHUB_WEBSITE_URL" "$SANDBOX_DIR/personal-website/AaronScherf.github.io"
    fi

    # Find EVERY directory in the workspace that has a .git folder and smartly update it
    echo "   -> Scanning for existing child repositories to pull updates..."
    find "$SANDBOX_DIR" -type d -name ".git" | while read gitdir; do
        # Extract the parent path of the .git folder
        repo_path=$(dirname "$gitdir")
        echo "      🔍 Checking: $repo_path"
        
        # Run subshell to avoid changing the main script's working directory
        (
            cd "$repo_path" || exit
            # Fetch remote status quietly
            git fetch -q
            
            # Compare local HEAD to upstream remote branch
            LOCAL=$(git rev-parse @ 2>/dev/null)
            REMOTE=$(git rev-parse @{u} 2>/dev/null)
            
            if [ "$LOCAL" != "$REMOTE" ] && [ -n "$REMOTE" ]; then
                echo "         📥 Updates found. Pulling latest changes..."
                git pull -q
            else
                echo "         ✅ Up to date."
            fi
        )
    done
    echo "✅ Child Git repositories processed."
else
    echo "⏭️ Git updates are disabled in config. Skipping Git sync..."
fi

# ==========================================================================
# 3. GENERATE & UPDATE README MANUALS & CONFIGS
# ==========================================================================
echo "📝 Injecting and updating system documentation and configs..."

# Always overwrite markdown manuals to keep guidelines up-to-date
cat << 'EOF' > "$SANDBOX_DIR/readme.md"
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
│       ├── AaronScherf.github.io/
│       │   ├── content/
│       │   └── static/
│       └── readme.md/
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
EOF

# Guard .gitignore in parent directory from being overwritten
if [ ! -f ".gitignore" ]; then
    echo "   -> Master .gitignore not found. Creating default ignore rules..."
    cat << 'EOF' > ".gitignore"
# ==========================================================================
# 🛑 MASTER AI-SANDBOX-MASTER GITIGNORE
# ==========================================================================

# 1. Ignore entirely Rclone/Data managed directories (No massive PDFs)
ai-sandbox/academic-hub/01-resources/
ai-sandbox/research/journal-articles/
ai-sandbox/research/independent-research/notes/

# 2. Ignore nested Git repositories completely
# (Prevents them from becoming broken Git submodules)
ai-sandbox/academic-hub/02-academic-notes-code/
ai-sandbox/personal-website/
ai-sandbox/research/independent-research/projects/

# 3. Ignore local container environment data, environment variables, or system files
.env
ai-sandbox/.env
.idea/
.DS_Store
Thumbs.db
*.log
EOF
else
    echo "   -> Master .gitignore already exists. Skipping write to preserve custom modifications."
fi

# Guard .env from being overwritten
if [ ! -f "$SANDBOX_DIR/.env" ]; then
    echo "   -> .env not found. Generating default secure environment file..."
    cat << 'EOF' > "$SANDBOX_DIR/.env"
# ==========================================================================
# 🔑 SECURE LOCAL ENVIRONMENT VARIABLES (IGNORED BY GIT)
# ==========================================================================
GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_KEY_HERE
EOF
else
    echo "   -> .env already exists. Skipping write to preserve local API keys."
fi

# Guard docker-compose.yml from being overwritten (Wiping out Gemini API Key config)
if [ ! -f "$SANDBOX_DIR/docker-compose.yml" ]; then
    echo "   -> docker-compose.yml not found. Generating default setup..."
    cat << 'EOF' > "$SANDBOX_DIR/docker-compose.yml"
services:
  interpreter_sandbox:
    image: python:3.11-slim
    container_name: open_interpreter_sandbox
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MODEL=gemini/gemini-2.5-flash
      - INTERPRETER_API_KEY=${GEMINI_API_KEY}
    volumes:
      # Relative paths now point to folders directly inside this same root directory
      - ./academic-hub/01-resources:/workspace/academic-hub/01-resources:rw
      - ./research/journal-articles:/workspace/research/journal-articles:rw
      - ./academic-hub/02-academic-notes-code:/workspace/academic-hub/02-academic-notes-code:rw
      - ./personal-website:/workspace/personal-website:rw
      - ./research/independent-research:/workspace/research/independent-research:rw
    working_dir: /workspace
    command: sh -c "pip install --no-cache-dir open-interpreter&& tail -f /dev/null"
EOF
else
    echo "   -> docker-compose.yml already exists. Skipping write to preserve local configuration & API keys."
fi

cat << 'EOF' > "$SANDBOX_DIR/academic-hub/readme.md"
# 📚 Academic Hub
## 🔄 01-resources (Data Layer)
- **Management:** Synced bidirectionally with Google Drive using `rclone bisync`.
- **Purpose:** Storage for heavy course binaries (Lecture recordings, text PDFs, slides, My Script Notes (Nebo) exports).

## 🐙 02-academic-notes-code (Logic/Text Layer)
- **Management:** Managed by Git and pushed to a private GitHub repository.
- **Automation & AI:** Contains `/scripts/daily-podcast.py` triggered nightly. You can boot up **Open Interpreter** from the sandbox to debug these scripts or analyze markdown study notes.
EOF

cat << 'EOF' > "$SANDBOX_DIR/personal-website/readme.md"
# 🌐 Personal Portfolio Website (Local Dev Notes)
## 🤖 AI Assistance
Because this folder is mounted as **Read-Write** in your Docker sandbox, you can ask Open Interpreter to generate new markdown blog posts, draft project summaries, or troubleshoot your Hugo layouts directly within this directory.
EOF

cat << 'EOF' > "$SANDBOX_DIR/research/readme.md"
# 🔬 Independent Research & AI Analytics Hub
## 🚨 CRITICAL DATA PIPELINE RULE: `journal-articles`
The `/journal-articles` directory is a **downstream, read-only layer** managed by Paperpile. Never add, rename, or delete files here locally. 

## 📂 Project Architecture
- **`/independent-research/notes`:** Handwritten design sketches and canvas ideas exported from My Script Notes (Nebo). (Managed by Rclone).
- **`/independent-research/projects`:** Isolated Git repositories for each project (e.g., `ai-trading-bot`).

## 🤖 AI Analysis
Spin up **Open Interpreter** in the Docker sandbox to read your PDF literature safely (via read-only volume mounts) and synthesize insights directly into your Markdown project notes.
EOF

echo "✅ System manuals updated successfully."

# ==========================================================================
# 3b. INITIALIZE & CONFIGURE TOP-LEVEL GIT REPOSITORY (IF NOT PRESENT)
# ==========================================================================
if [ "$ENABLE_GIT_UPDATES" = true ]; then
    echo "🐙 Verifying top-level Git repository in current directory..."
    if [ ! -d ".git" ]; then
        echo "   -> Top-level Git repository not found. Initializing..."
        git init -b main
        git add .
        git commit -m "Initial commit: AI Sandbox master workspace structure"
        
        echo "   -> Checking if GitHub CLI is available to publish repository..."
        if command -v gh &> /dev/null && gh auth status &> /dev/null; then
            REPO_NAME=$(basename "$PWD")
            echo "   -> GitHub CLI detected. Creating private remote repository '$REPO_NAME' on GitHub..."
            gh repo create "$REPO_NAME" --private --source=. --remote=origin --push
            echo "   -> Successfully created and pushed to GitHub!"
        else
            REPO_NAME=$(basename "$PWD")
            echo "   ⚠️ GitHub CLI (gh) not detected or not logged in."
            echo "      To link this new repository to your GitHub account:"
            echo "      1. Go to https://github.com/new and create a blank repository named '$REPO_NAME'"
            echo "      2. Run these commands in this folder:"
            echo "         git remote add origin https://github.com/<your-username>/$REPO_NAME.git"
            echo "         git branch -M main"
            echo "         git push -u origin main"
        fi
    else
        echo "   -> Top-level Git repository is already initialized."
    fi
fi

# ==========================================================================
# 4. RCLONE BISYNC EXECUTION
# ==========================================================================
if [ "$ENABLE_RCLONE_SYNC" = true ]; then
    echo "🔄 Synchronizing Rclone Data Directories..."

    # Syncing Academic Resources
    echo "   -> Syncing: academic-hub/01-resources"
    rclone bisync "$RCLONE_REMOTE/academic-hub/01-resources" "$SANDBOX_DIR/academic-hub/01-resources" --create-empty-src-dirs --progress

    # Syncing Independent Research Notes
    echo "   -> Syncing: research/independent-research/notes"
    rclone bisync "$RCLONE_REMOTE/research/independent-research/notes" "$SANDBOX_DIR/research/independent-research/notes" --create-empty-src-dirs --progress

    echo "✅ Rclone synchronization complete."
else
    echo "⏭️ Rclone sync is disabled in config. Skipping Rclone bisync..."
fi

echo "🎉 Setup & Update Complete! Your architecture is perfectly aligned and secured inside ai-sandbox."
