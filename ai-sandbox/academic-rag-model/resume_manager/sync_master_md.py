"""
sync_master_md.py
Syncs a hand-edited resume_master.md back into resume_master.yaml (spec
§14) -- the write-back half of the two-way Markdown editing loop; the
export half runs automatically from convert_resume.py and
merge_resumes.py every time they write resume_master.yaml.

Guards against silently clobbering an auto-merge (merge_resumes.py) that
ran after resume_master.md was last exported but before this sync: the
exported file embeds a hash of the YAML it came from
(markdown_sync.compute_yaml_hash()), and this script refuses to write
resume_master.yaml unless that hash still matches the file's current
content. There's no such guard needed on the tailored-resume side
(sync_tailored_md.py) -- nothing else writes to one application's own
files after tailoring finishes, so there's no concurrent writer to
conflict with.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from resume_manager.markdown_sync import (
    compute_yaml_hash, export_to_markdown, extract_embedded_hash, import_from_markdown,
)

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)


def sync_master_md(resume_manager_dir: str) -> str:
    """Reads resume_master.md, verifies its embedded hash still matches
    resume_master.yaml's current content, and if so, overwrites the YAML
    with the parsed Markdown (then re-exports the .md so its hash reflects
    the new state, ready for the next edit cycle). Returns a one-line
    status message; raises FileNotFoundError if either file is missing,
    and RuntimeError (never silently overwriting) if the master changed
    since this .md was exported."""
    master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
    master_md_path = os.path.join(resume_manager_dir, "resume_master.md")
    if not os.path.exists(master_md_path):
        raise FileNotFoundError(f"{master_md_path} not found -- nothing to sync.")
    if not os.path.exists(master_path):
        raise FileNotFoundError(f"{master_path} not found -- run convert_resume.py's bootstrap first.")

    with open(master_md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()
    with open(master_path, "r", encoding="utf-8") as f:
        current_master = yaml.safe_load(f)

    embedded_hash = extract_embedded_hash(markdown_text)
    current_hash = compute_yaml_hash(current_master)
    if embedded_hash != current_hash:
        raise RuntimeError(
            f"{master_path} has changed since {master_md_path} was last exported "
            f"(likely from a merge_resumes.py run) -- re-export resume_master.md "
            f"(re-run convert_resume.py or merge_resumes.py, or just open the current "
            f"resume_master.md again) and redo your edits against the current version, "
            f"rather than risk silently losing what changed. Refusing to overwrite."
        )

    updated_master = import_from_markdown(markdown_text)
    with open(master_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(updated_master, f, sort_keys=False, allow_unicode=True)
    with open(master_md_path, "w", encoding="utf-8") as f:
        f.write(export_to_markdown(updated_master, embed_hash=True))

    return f"Synced {master_md_path} -> {master_path}."


def main() -> None:
    print(sync_master_md(str(_DEFAULT_RESUME_MANAGER_DIR)))


if __name__ == "__main__":
    main()
