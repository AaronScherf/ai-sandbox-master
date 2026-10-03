# Summary enhancement pipeline — design

Date: 2026-10-03 · Branch: `claude/summary-enhance` · Path: architectural

## Purpose

An optional follow-up to the RAG tutor. It takes an existing RAG-generated
summary (e.g. `academic_notes/econometrics/summaries/wald_lm_lr_tests.md`),
loads the exact indexed passages that summary already cites, and asks a
stronger external LLM to rewrite it as one coherent study guide with one
section per topic (e.g. Wald, LR, LM/score), each synthesizing the textbook
sources. The model may add intuition, examples and background, but those
additions must be structurally separate from, and visibly labeled apart from,
claims grounded in the textbooks.

## Requirements (from the user)

- New optional module; no change to `core/` or the restricted RAG prompt in
  `rag_agent.py`.
- Passages are resolved **by `(file_id, chunk_id)`** from the guide's
  `indexer_source_refs` frontmatter, not by similarity search.
- **One** enhanced `.md` file per run, with one section per topic.
- The original guide is never overwritten by default; an explicit output
  path is supported.
- The output records the generation model/method and exactly which indexed
  chunks were used.
- Real synthesis uses the existing paid Gemini key (`PAID_GEMINI_KEY`) via
  `core.env.gemini_utils.get_gemini_client("PAID_GEMINI_KEY")`. Tests make no
  paid or network calls.
- Output stays local/private: inside the corpus root's `academic_notes/`
  vault (a separate, private nested repo). The tool never runs git. No
  textbook-derived text goes anywhere else.
- Never print `.env` contents.

## Architecture

New package `agent/summary_enhance/` with tests in
`tests/agent/summary_enhance/`.

| Module | Responsibility |
|---|---|
| `source_loader.py` | Parse guide frontmatter (`indexer_source_refs`, JSON on one line) and body. For each ref, resolve the chunk via `core.indexer.chunk_index.load_chunks(root, course)`, matching `chunk_id` and checking `file_id`. Course is derived from the `academic_notes/<course>/` segment of the guide path. Any unresolved ref raises `MissingSourcesError` listing every missing ID. Returns `SourceChunk(label, chunk_id, file_id, path, citation, text, root)` with labels `S1..Sn`. |
| `prompt.py` | `PROMPT_VERSION`; builds the prompt from guide body, labeled passages and topics. States the grounded/elaboration contract and the JSON schema. |
| `schema.py` | Dataclasses and JSON schema: `Enhanced{topics:[Topic{title, grounded:[Block{text, sources:[S#]}], elaboration:[Block{kind, text}]}]}`; elaboration `kind` in {intuition, example, background}. Elaboration blocks carry no source labels. |
| `validate.py` | Rejects: any `S#` not among the input labels; any grounded block with empty `sources`; a requested topic missing from the output; empty grounded list for a topic. Returns the list of errors. |
| `llm.py` | `LLMClient` protocol: `generate_structured(prompt, schema) -> dict`. `GeminiClient` wraps `client.models.generate_content` with JSON response mime type and schema, `temperature` low, through `call_with_retries`. `DEFAULT_MODEL` is a named constant, overridable by `--model`. |
| `render.py` | Deterministic Markdown from the validated structure: frontmatter, `# Title`, a short provenance note, one `## <Topic>` per topic with grounded synthesis and inline citations rendered from labels (e.g. `[Cameron §7.2, p. 247]`), then a blockquote callout per elaboration block: `> **Not from the textbooks — LLM elaboration (intuition):** ...`. Final `## Sources` lists only the chunks actually cited (path, citation, file_id, chunk_id, corpus), mirroring `report_builder.py`. |
| `enhance.py` | CLI/orchestration: `python -m agent.summary_enhance.enhance <guide.md> [--topic T ...] [--output PATH] [--model M] [--force] [--dry-run]`. |

## Data flow

1. Resolve guide path and corpus root; load and verify chunks (fail loudly on
   missing IDs; no silent degradation).
2. Resolve output path: `--output` or `<guide-dir>/<guide-stem>.enhanced.md`.
   Refuse if it exists without `--force`, if it equals the input, or if it
   is outside `<root>/academic_notes/`.
3. `--dry-run`: print chunk count, prompt character count, model, and
   destination; make no API call; exit.
4. Build the prompt, call `LLMClient`, parse JSON, validate. On validation
   errors, retry once with the errors appended to the prompt; if still
   invalid, abort with the errors and write no file.
5. Render and write atomically (temp file then replace).

Topics: repeated `--topic` flags define sections. If none are given, the
prompt asks the model to choose topics from the guide; the chosen titles are
recorded in the output.

## Output frontmatter

```
title, llm_generated: true, content_kind: enhanced_summary,
generated_by: academic-rag-model/agent/summary_enhance/enhance.py,
enhancement_model, prompt_version, generated_at (ISO UTC),
source_summary: {path (relative to vault), sha256},
topics: [...],
indexer_source_refs: [... only chunks actually cited, same shape as today]
```

## Grounding boundary

Enforced structurally: the model must return separate `grounded` and
`elaboration` arrays. Grounded blocks must cite valid labels; elaboration
blocks cannot cite and are always rendered under the "Not from the
textbooks" callout. Where Cameron and Hansen differ or one is silent (the
guide already flags a Hansen LR gap and a Cameron edition mismatch), the
prompt requires the grounded text to say so rather than fill the gap.

**Known limitation:** validation proves that a cited label exists, not that
the source entails the claim. A manual grounding spot-check is part of the
real-run review. Automated entailment checking is out of scope.

## Error handling

- Missing/stale refs, missing frontmatter or malformed `indexer_source_refs`:
  clear error, no API call.
- Missing paid key: `get_gemini_client` returns None; exit non-zero with its
  message, no file written.
- API failure after retries, invalid JSON, or persistent validation failure:
  non-zero exit, no output file.

## Testing (no paid calls)

Fixture vault under `tmp_path` with a small `.index/chunks/<course>.json`
and a guide with frontmatter. A `FakeLLMClient` returns canned JSON.

- `source_loader`: resolves refs, labels in order, missing IDs listed,
  `file_id` mismatch rejected, malformed frontmatter.
- `prompt`: includes every label and chunk text, topics, version.
- `validate`: unknown label, uncited grounded block, missing topic, empty
  grounded.
- `render`: elaboration always under the callout, only cited chunks in
  Sources and frontmatter, golden-file comparison.
- `enhance` end to end with the fake: default output name, `--output`,
  refuse overwrite, `--force`, input==output refused, outside-vault refused,
  `--dry-run` makes zero client calls, retry-once-then-succeed,
  retry-then-abort writes nothing.
- `GeminiClient` unit test with a stubbed `client.models.generate_content`
  (no network).

## Real run (separate from tests)

After tests pass: a model-availability check (a tiny call to confirm the
chosen Gemini Pro-tier model ID responds; the ID is not guessed in advance),
then one run on `wald_lm_lr_tests.md` (16 chunks) with
`--topic "Wald test" --topic "Likelihood ratio test" --topic
"Lagrange multiplier (score) test"`, writing
`wald_lm_lr_tests.enhanced.md` in the live vault. Reviewed by hand for
grounding and labeling. Committing/pushing to the private vault repo is a
separate, user-authorized step.

## Out of scope (YAGNI)

Extra similarity retrieval, multi-provider clients, automated entailment
checks, batch mode over many guides, any change to `core/` or
`rag_agent.py`.
