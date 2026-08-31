#!/bin/bash
# ==========================================================================
# workspace_generator.sh
#
# What this script is actually for (rewritten 2026-08-31): scaffolding the
# folders `.gitignore` deliberately excludes from this repo -- real
# copyrighted textbook/journal-article PDFs and their full-text
# conversions -- plus keeping independent child git repos (the personal
# website, any of your own standalone project repos) up to date, and
# optionally backing up those gitignored PDFs via rclone.
#
# What it's deliberately NOT for any more: cloning or initializing this
# repo itself. That's redundant now that this script ships as a tracked
# file inside ai-sandbox-master -- a normal `git clone`/`git pull` of this
# repo already gets you this script, the code, and everything this repo
# actually tracks (academic-rag-model, academic-hub's derivative index/
# metadata, your own academic_notes/ and research writing). Run this
# script *after* cloning, to fill in the gap git leaves on purpose.
# ==========================================================================

# ==========================================================================
# ⚙️ CONFIGURATION VARIABLES & FEATURE SWITCHES
# ==========================================================================
ENABLE_GIT_UPDATES=true    # Pull updates for child repos (personal-website, your own project repos)
ENABLE_RCLONE_SYNC=false   # Defaulting to false so it doesn't error out on a fresh machine with no rclone remote configured

RCLONE_REMOTE="gdrive:master-workspace"
GITHUB_WEBSITE_URL="https://github.com/AaronScherf/AaronScherf.github.io.git"
SANDBOX_DIR="ai-sandbox"

echo "🚀 Scaffolding gitignored folders and syncing child repos..."

# ==========================================================================
# 1. SCAFFOLD THE FOLDERS .gitignore DELIBERATELY EXCLUDES
# ==========================================================================
# academic_notes/ (your own TA notes, problem sets, exams) is tracked and
# already comes down with a normal git clone -- not scaffolded here.
# academic_resources/<course>/{textbooks,lecture-slides,lecture-recordings}/
# and research/journal-articles/ are the actual IP-sensitive content
# .gitignore protects (see the root .gitignore's own comments for exactly
# why each one), so a fresh clone needs these created empty and ready for
# your own PDFs.
#
# Course list is derived from whatever academic_notes/ subfolders already
# exist (tracked, so present after any clone) rather than hardcoded --
# replicating this project with different courses just means creating
# your own academic-hub/academic_notes/<course>/ before running this, and
# the loop below picks it up automatically.
echo "📂 Scaffolding gitignored content folders per course..."
mkdir -p "$SANDBOX_DIR/academic-hub/academic_notes"
for course_dir in "$SANDBOX_DIR"/academic-hub/academic_notes/*/; do
    [ -d "$course_dir" ] || continue
    course=$(basename "$course_dir")
    echo "   -> $course"
    mkdir -p "$SANDBOX_DIR/academic-hub/academic_resources/$course"/{textbooks,lecture-slides,lecture-recordings}
done
mkdir -p "$SANDBOX_DIR/research/journal-articles"
echo "✅ Gitignored content folders ready for your own PDFs."

# ==========================================================================
# 2. CHILD GIT REPOS: CLONE/PULL (personal-website + any of your own
#    independent project repos, e.g. under research/independent-research/projects/)
# ==========================================================================
if [ "$ENABLE_GIT_UPDATES" = true ]; then
    echo "🐙 Processing child git repositories..."

    # Aaron-specific convenience -- replicating this project with your own
    # portfolio site means changing GITHUB_WEBSITE_URL above, or just
    # removing this block and cloning your own site manually.
    if [ ! -d "$SANDBOX_DIR/personal-website/AaronScherf.github.io/.git" ]; then
        echo "   -> Cloning personal website repository for the first time..."
        git clone "$GITHUB_WEBSITE_URL" "$SANDBOX_DIR/personal-website/AaronScherf.github.io"
    fi

    # Find every directory in the sandbox with its own .git and pull it --
    # covers the personal website above and any of your own standalone
    # project repos (research/independent-research/projects/**), which are
    # deliberately excluded from this parent repo rather than embedded, so
    # each keeps its own independent history.
    echo "   -> Scanning for child repositories to pull updates..."
    find "$SANDBOX_DIR" -type d -name ".git" | while read -r gitdir; do
        repo_path=$(dirname "$gitdir")
        echo "      🔍 Checking: $repo_path"
        (
            cd "$repo_path" || exit
            git fetch -q
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
    echo "✅ Child git repositories processed."
else
    echo "⏭️ Git updates are disabled in config. Skipping child-repo sync..."
fi

# ==========================================================================
# 3. GENERATE LOCAL CONFIG (GUARDED -- never overwrites an existing file)
# ==========================================================================
# Every write in this section is now guarded, unlike the pre-2026-08-31
# version of this script, which unconditionally overwrote every readme.md
# on every run -- confirmed live this had already gone stale in a way that
# actively contradicted the real, current setup (research/readme.md's old
# "journal-articles is Paperpile-managed" claim, which stopped being true
# once that folder got reorganized thematically). If a file already
# exists, this script leaves it alone -- edit these docs directly, they
# won't get silently clobbered by a future run.
echo "📝 Generating local config and docs where missing..."

if [ ! -f "$SANDBOX_DIR/.env" ]; then
    echo "   -> ai-sandbox/.env not found. Generating from .env.example convention..."
    cat << 'EOF' > "$SANDBOX_DIR/.env"
# ==========================================================================
# 🔑 SECURE LOCAL ENVIRONMENT VARIABLES (IGNORED BY GIT)
# ==========================================================================
GEMINI_API_KEY=YOUR_ACTUAL_GEMINI_KEY_HERE
EOF
else
    echo "   -> ai-sandbox/.env already exists. Skipping."
fi

# docker-compose.yml intentionally not generated here as of this rewrite --
# Docker is a real, wanted part of this project's future (reproducibility,
# and possibly hosting an Open Interpreter/Claude-based tutor agent), but
# the old generated config (Open Interpreter + gemini-2.5-flash, volumes
# mounted at the old 01-resources/02-academic-notes-code paths) no longer
# matches either the current folder layout or an actually-decided Docker
# design. Left as an explicit open decision -- see the root README -- not
# silently dropped.

if [ ! -f "$SANDBOX_DIR/readme.md" ]; then
    echo "   -> ai-sandbox/readme.md not found. Generating..."
    cat << 'EOF' > "$SANDBOX_DIR/readme.md"
# 🗺️ AI Sandbox Root

Root directory for academic, research, and web-portfolio infrastructure. See
the top-level `README.md` (one level up) for the full architecture map and
`academic-rag-model/README.md` for the actual conversion/indexing pipelines.

## What's tracked vs. gitignored
Code, derivative index/metadata (titles, summaries, tags -- not full text),
and your own authored coursework/research writing are tracked in this repo.
Actual copyrighted PDFs (published textbooks, journal articles) and their
full-text conversions are deliberately gitignored -- see the root
`.gitignore`'s own comments for exactly which paths and why. Run
`workspace_generator.sh` (one level up) to scaffold those gitignored
folders empty and ready for your own PDFs.

## Naming convention
Directories and files use lowercase alphanumeric characters separated by
hyphens (`lower-kebab-case`), except where an existing tool's own
convention overrides it (e.g. Python packages use `snake_case`).
EOF
else
    echo "   -> ai-sandbox/readme.md already exists. Skipping."
fi

echo "✅ Local config and docs ready."

# ==========================================================================
# 4. RCLONE BISYNC -- the actual IP-sensitive PDFs (textbooks, journal
#    articles), backed up across local/external/Google Drive
# ==========================================================================
if [ "$ENABLE_RCLONE_SYNC" = true ]; then
    echo "🔄 Synchronizing gitignored PDF content via rclone..."

    for course_dir in "$SANDBOX_DIR"/academic-hub/academic_resources/*/; do
        [ -d "$course_dir" ] || continue
        course=$(basename "$course_dir")
        echo "   -> Syncing: academic-hub/academic_resources/$course/textbooks"
        rclone bisync "$RCLONE_REMOTE/academic-hub/academic_resources/$course/textbooks" \
            "$SANDBOX_DIR/academic-hub/academic_resources/$course/textbooks" \
            --create-empty-src-dirs --progress
    done

    echo "   -> Syncing: research/journal-articles"
    rclone bisync "$RCLONE_REMOTE/research/journal-articles" "$SANDBOX_DIR/research/journal-articles" \
        --create-empty-src-dirs --progress

    echo "✅ Rclone synchronization complete."
else
    echo "⏭️ Rclone sync is disabled in config. Skipping..."
fi

echo "🎉 Done. Gitignored folders are scaffolded, child repos are up to date."
