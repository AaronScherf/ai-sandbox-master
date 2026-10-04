# summary_enhance

Optional follow-up to the RAG tutor. Takes an existing RAG-generated summary, loads the exact
indexed chunks listed in its `indexer_source_refs`, and asks a Gemini model (paid key) to write
a thorough standalone study guide: one section per topic, several sub-sections each.

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test" --dry-run
    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test" --worked-example

- **Clean body, provenance in frontmatter.** No inline citations or Sources list. The frontmatter
  `source_map` lists each cited chunk (`chunk_id`, `file_id`, `path`, `citation`) with `used_in`
  (the `Topic > Section` headings that rely on it).
- **No tags in the text.** One intro sentence says that added intuition and worked examples are not
  from the textbooks. Which paragraph is which is recorded in the frontmatter `paragraph_kinds`: for
  each `Topic > Section`, one letter per body paragraph (`G` textbook-grounded, `E` external,
  `W` worked example), in document order.
- **Readable paragraphs.** A prose paragraph of more than five sentences is cut into roughly equal
  paragraphs at sentence boundaries (7 sentences -> 4 + 3); the text is unchanged.
- **Restyle without an API call.** `python -m agent.summary_enhance.restyle <enhanced.md>` rewrites a
  format-2 guide into the current format (see that module's docstring).
- **Display math.** Inline formulas longer than 10 symbols are moved to their own `$$` block.
- **Depth.** One synthesis call per topic; `--min-words` (default 1400) per topic, at least 3
  sections, at least half the words textbook-grounded. With no `--topic`, one planning call picks 3-8 topics.
- **Worked examples (`--worked-example`).** One extra call per topic with Gemini's code-execution
  tool, so the arithmetic is computed, not guessed.
- Output: `<guide-stem>.enhanced.md` beside the guide; `--output` to choose a path (must be under
  `<corpus>/academic_notes/`); `--force` to replace.
- Model: `gemini-3.8-flash` by default (`--model` to override). Uses `PAID_GEMINI_KEY`; from a git
  worktree (no `.env`), pass `--env-file <main checkout>/ai-sandbox/.env`.
- Never runs git. Keep outputs in the private notes vault.
- Validation checks that cited labels exist, not that a passage entails the claim, and code execution
  makes worked-example numbers real but not the prose around them: spot-check both.
- Specs: `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md` (v1) and
  `...-v2-design.md`. Tests: `python -m pytest tests/agent/summary_enhance -q` (no network).
