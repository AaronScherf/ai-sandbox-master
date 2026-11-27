# Drafting handoff: study Guide 0a or 0b (Microeconomics Part 2 toolkit)

Written 2026-11-26, for a Claude or Codex session. One session drafts one file. The owner's opening message says which: **0a** or **0b**. If it does not, ask.

The draft will be reviewed against the sources by another session, so for each theorem statement and key formula record the file and line (or PDF page) you checked it against, and include that list in your report. Report only checks you actually ran.

## Read first
All under `ai-sandbox/academic-rag-model/docs/superpowers/specs/`:
- `2026-11-26-microecon-part2-study-guides-design-v1.md`: intent, source rules, anti-goals.
- `2026-11-26-microecon-guide0-topics-v1.md`: your topic list, running examples, drafting notes.

The design is settled. Do not reopen the topics, format or location; draft.

## The split
| File | Content | Practice questions | Rough length (planner's call) |
|---|---|---|---|
| `Guide 0a - Math Toolkit.md` | Part A (A1–A10) | about 4 | 4,000–6,000 words |
| `Guide 0b - Micro Toolkit.md` | Parts B–E | about 6 | 8,000–11,000 words |

Write to `ai-sandbox/academic-hub/academic_notes/microecon/part_2/study_guides/`. Refer across files by topic code ("see A7"). Running examples belong to 0b.

## Reader and format
Little or no micro background. Write to be read on its own, in Obsidian Markdown with `$…$` and `$$…$$` math.

1. Short opening: what this guide is for and a table of topics with the later guides that use each.
2. One section per topic, headed with its code: plain-language idea; definition or statement; short derivation where it helps; one worked example with numbers; the common mistake; "used in" line.
3. One-page formula sheet.
4. Practice questions, then answers at the end.
5. Sources list: file and section for each topic.

Plain prose, no filler. Draw a figure only where it carries the idea (Edgeworth box, corner solution, separating hyperplane); describe it in words as well.

## Sources
Paths are under `ai-sandbox/academic-hub/`. Grep for headings and read ranges; the textbook files are large.
- Jehle and Reny: `academic_notes/microecon/part_2/textbooks/processed_outputs/Jehle_Advanced_Microeconomic_Theory_2011/chapters/` (`01_`–`05_`, `10_` and `11_` appendices).
- Mas-Colell et al.: `academic_notes/microecon/part_1/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/` (`05_production`, `06_choice_under_uncertainty`).
- Course notation: `academic_notes/microecon/part_2/professor_notes/processed_outputs/` (this year's lectures) and `class_2024/Recitations/processed_outputs/Recitation_1_Part_2.md`.
- Practice questions: prior-year problem sets under `class_2024/` and `class_2025/`. Never use or solve this year's Problem Set 4.

## Accuracy rules
- Check every theorem statement and key formula against the source text. For transcribed course files, also check the page image (`pypdfium2` in the shared `.venv` renders PDFs from `academic_resources/`), because some prior-year transcriptions were once fabricated and subscript errors can survive.
- Work every numerical example and practice answer yourself, and verify the arithmetic with a short script in your scratchpad.
- Correct source typos openly, naming the page.
- Write explanations and examples in your own words. Do not copy textbook passages or exercises at length.

## Ground rules
- Create only your one guide file. `academic_notes/` is a separate repo; read `docs/WORKTREE_DATA_AND_RETIRE.md` before writing. Other sessions may be writing there: touch nothing else, run no pipeline, indexer or paid API call, and do not commit or push.
- Do not spawn subagents.

## Report
1. Clickable `file://` link to the guide.
2. Word count, and any topic you could not support from a source.
3. What you verified and how; anything you did not verify.
4. Source typos or conflicts found.
5. Format choices you made that later guides should keep or change (this is the trial run).
