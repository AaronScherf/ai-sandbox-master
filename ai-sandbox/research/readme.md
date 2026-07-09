# 🔬 Independent Research & AI Analytics Hub
## 🚨 CRITICAL DATA PIPELINE RULE: `journal-articles`
The `/journal-articles` directory is a **downstream, read-only layer** managed by Paperpile. Never add, rename, or delete files here locally. 

## 📂 Project Architecture
- **`/independent-research/notes`:** Handwritten design sketches and canvas ideas exported from My Script Notes (Nebo). (Managed by Rclone).
- **`/independent-research/projects`:** Isolated Git repositories for each project (e.g., `ai-trading-bot`).

## 🤖 AI Analysis
Spin up **Open Interpreter** in the Docker sandbox to read your PDF literature safely (via read-only volume mounts) and synthesize insights directly into your Markdown project notes.
