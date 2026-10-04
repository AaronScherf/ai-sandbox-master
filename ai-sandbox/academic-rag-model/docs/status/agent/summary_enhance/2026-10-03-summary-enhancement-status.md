# Summary Enhancement Pipeline: Status Summary

Start here for "what happened and where do we stand" on the Markdown study guide enhancement pipeline — `agent/summary_enhance/`, which takes basic tutor/lecture notes summaries, matches them against source textbook passages, and synthesizes rich, mathematically rigorous standalone study guides.

Design reference: `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md`;
v2 addendum: `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-v2-design.md`;
implementation plans: `docs/superpowers/plans/2026-10-03-summary-enhancement.md` and `2026-10-03-summary-enhancement-v2.md`.

## What shipped

1. **Multi-Stage Synthesis Pipeline (`agent/summary_enhance/`)**:
   - **Topic Planning**: Analyzes input summary and extracts 3–8 logical mathematical topics.
   - **Per-Topic Synthesis**: Dispatches synthesis calls per topic with structured JSON schema outputs (`schema.py`).
   - **Grounded & External Content**: Explicitly separates grounded textbook material from external contextual explanations via block types (`grounded` vs. `external`), tagged with `*(External context)*`.
   - **Display-Math Formatting (`mathfmt.py`)**: Converts inline math expressions exceeding 10 symbols into clean standalone LaTeX `$$...$$` blocks, leaving table cells and list items intact.
   - **Worked Examples**: Optional code-execution or structured numeric worked examples with realistic calculations (`*(Worked example — illustrative data, not from the textbooks)*`).
   - **Provenance Mapping**: Preserves source attribution in frontmatter `source_map` without cluttering the body text with raw `[S#...]` brackets.

2. **CLI & Execution Controls**:
   - `python -m agent.summary_enhance.enhance_summary --input <file.md> [--course <course>] [--min-words 1400] [--dry-run]`
   - Non-destructive output generation: never overwrites the source guide directly; creates `.enhanced.md` alongside an atomic write and backup recovery copy.
   - Exit codes: 0 (OK), 1 (no client), 2 (bad input), 3 (invalid after retry), 4 (LLM error), 5 (write error).

## Real-world validation & bug fixes

- **Full test suite**: Comprehensive unit and contract tests in `tests/agent/summary_enhance/`.
- **Key fixes shipped to `main`**:
  - `4e186ba`: Repair JSON escape corruption for LaTeX backslash sequences (`\b`, `\f`, `\t`, `\r`) rather than failing the run.
  - `fd0cc2e`: Review fixes for preserving external tags after math splitting, fence-safe paragraph rendering, currency-safe `$` math parsing, and JSON retry isolation.
- **Active worktree notice**:
  - Ongoing minor rendering and paragraph restyling cleanup is in progress in `.worktrees/claude-summary-polish` (`claude/summary-polish`), refining prompt phrasing and paragraph joining.
