# summary_enhance

Optional follow-up to the RAG tutor. Takes an existing RAG-generated summary,
loads the exact indexed chunks listed in its `indexer_source_refs`, and asks a
stronger Gemini model (paid key) to rewrite it as one guide with a section per
topic. Textbook-grounded synthesis (cited as `[S#: citation]`) is kept separate
from LLM elaboration, which is always rendered in a
"Not from the textbooks" callout.

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test" --dry-run
    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" --topic "Likelihood ratio test"

- Output: `<guide-stem>.enhanced.md` beside the guide; `--output` to choose a path
  (must be under `<corpus>/academic_notes/`); `--force` to replace.
- Model: `gemini-3.8-flash` by default (`--model` to override). Uses `PAID_GEMINI_KEY`;
  from a git worktree (no `.env`), pass `--env-file <main checkout>/ai-sandbox/.env`.
- Records `enhancement_model`, `prompt_version`, `source_summary` (path + sha256),
  and exactly the cited chunks in `indexer_source_refs`.
- Never runs git. Keep outputs in the private notes vault.
- Validation checks that cited labels exist, not that a passage entails the claim:
  spot-check grounded text against the sources.
- Spec: `docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md`.
- Tests: `python -m pytest tests/agent/summary_enhance -q` (no network).
