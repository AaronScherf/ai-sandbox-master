# Summary enhancement v2 — design addendum

Date: 2026-10-03 · Branch: `claude/summary-enhance-v2` · Path: architectural (light)
Amends: `2026-10-03-summary-enhancement-design.md` (v1, shipped and merged as `c4bb8dd`).
Everything in v1 not mentioned here is unchanged: guide loading by `chunk_id`, corpus root
derived from the guide path, output guards (inside `<root>/academic_notes/`, never over the
input, no overwrite without `--force`, `--dry-run`), atomic write with recovery copy, exit
codes, paid key via `--env-file`/`PAID_GEMINI_KEY`, the grounded-vs-external contract, and
every validation rule added after the v1 review (control characters, forged labels, forged
structure, newline inside inline math, topic titles).

## Why

The first real output (`wald_lm_lr_tests.enhanced.md`) synthesized well but read like an
annotated source dump rather than a standalone study document:

1. inline `[S#: citation]` markers and a visible Sources list clutter the text;
2. long formulas sit inline;
3. each topic is about a page, too thin for the cost of a paid call;
4. every external paragraph repeats a boxed "Not from the textbooks" banner;
5. there are no worked numeric examples.

## Requirements

- **R1 Clean body.** The body contains no citation markers, no Sources section, no
  provenance comments. An agent finds source sections through frontmatter only.
- **R2 Source map in frontmatter.** For every chunk actually cited, record which sections of
  the document rely on it.
- **R3 Display math.** Any inline formula with more than 10 symbols is rendered as a
  standalone `$$…$$` block. Done by the renderer, so it does not depend on the model.
- **R4 Depth.** At least a couple of pages per topic (default minimum 1400 words per topic),
  structured with sub-headings, covering assumptions, derivation, intuition for the
  statistic, how the two textbooks differ, and common pitfalls.
- **R5 Light external-context tag.** External paragraphs are ordinary prose that begin with
  `*(External context)*`. No boxes, no repeated banners. One short explanatory sentence under
  the document title.
- **R6 Optional worked examples.** `worked_example=True` / `--worked-example` adds, per
  topic, a numeric example on a small made-up dataset showing how the test statistic and
  decision are computed, with the arithmetic done by Gemini's code-execution tool.

## Architecture changes

### Call structure (replaces v1's single call)

Per run: optionally 1 planning call, then for each topic 1 synthesis call, then (if
`worked_example`) 1 worked-example call per topic. Calls are sequential. Every call is
retried once with the validation errors fed back; a second failure aborts the run with
exit 3 and writes nothing. Completed topics are not saved on abort (each call costs cents;
no resume feature).

- **Planning call** (only when no `--topic`): `generate_structured` returning
  `{"topics": [title, ...]}`, 3 to 8 unique non-empty single-line titles.
- **Synthesis call** (per topic): prompt contains the draft guide, all labeled chunks, the
  target topic, and the titles of the other topics (so shared material is not repeated
  everywhere). Returns the topic schema below.
- **Worked-example call** (per topic, optional): `generate_text(..., code_execution=True)`.
  Input: topic title plus the topic's grounded text (the formulas to use). Instructions:
  invent a small dataset, state it, compute each quantity step by step by running code,
  report the numeric statistic, critical value or p-value, and the decision; label all data
  as illustrative. Output is free Markdown (no JSON, because the code-execution tool and a
  JSON response mime type cannot be combined).

### Schema (replaces v1 grounded/elaboration arrays)

```
Enhanced { topics: [ Topic ] }
Topic    { title, sections: [ Section ], worked_example: str | None }
Section  { heading, blocks: [ Block ] }
Block    { type: "grounded" | "external", text, sources: [label] }
```

`sources` is required and non-empty for `grounded`, forbidden (empty) for `external`.
`worked_example` is filled by the third call, never by the synthesis JSON. Labels (`S1`…)
remain internal to prompts and `sources`; they never reach the rendered body.

### Validation additions (synthesis call)

- title matches the requested topic (case/whitespace-insensitive); the requested spelling is
  rendered;
- at least 3 sections, each with a non-empty single-line heading and at least 1 block;
- total words across blocks ≥ `min_words`; grounded words ≥ 50% of total (so length cannot
  be met by padding with external context);
- all v1 per-text checks apply to every block of either type.

### Worked-example validation

Non-empty; ≥ 150 words; contains at least one `$`; no control characters; no label markers;
no heading or blockquote lines (it is nested under the renderer's own heading); no
"not from the textbooks" phrase; no newline inside inline math.

### Renderer

```
---
title, llm_generated: true, content_kind: enhanced_summary, format_version: 2,
generated_by, enhancement_model, prompt_version, generated_at,
source_summary: {path, sha256}, topics: [...],
options: {"worked_example": bool, "min_words": N},
external_context_marker: "(External context)",
source_map: [ {chunk_id, file_id, path, citation, used_in: ["Topic > Heading", ...]}, ... ]
---

# <title> (enhanced)

*Study guide synthesized from the course textbooks. Passages marked (External context) or
(Worked example) come from outside the textbooks.*

## <Topic>
### <Section heading>
paragraphs...
### Worked example            (only when generated)
*(Worked example — illustrative data, not from the textbooks)*
...
```

- `source_map` lists only chunks cited by at least one grounded block, in label order;
  `used_in` holds the `Topic > Section heading` of each section containing a grounded block
  that cites the chunk. `path` is the vault-relative path from the guide's own reference; the
  absolute corpus root is no longer stored (removes the local-path leak noted in the v1
  review). `indexer_source_refs` is not written; enhancing an enhanced guide is out of scope.
- **External tag:** every paragraph of an `external` block (paragraphs split on blank lines)
  begins with `*(External context)* `. If the paragraph starts with `$`, a list marker, a
  table pipe, or `>`, the tag goes on its own line above it.
- **Display-math rule:** within paragraphs of any block and within the worked example, each
  inline `$…$` span whose symbol count exceeds 10 is split out onto its own `$$` block:
  text before (if any), a line `$$`, the formula, `$$`, text after (if any). Trailing
  `.`, `,`, `;`, `:` immediately after the closing `$` moves inside the display block. Symbol
  count: each `\command` is 1; each remaining non-whitespace character other than `{` and `}`
  is 1 (so `^`, `_`, digits and operators count). Existing `$$…$$` spans, fenced code, and
  lines that start a list item, table row, or blockquote are left untouched.

### LLM client

`LLMClient` gains `generate_text(prompt: str, *, code_execution: bool = False) -> str`.
`GeminiClient` sets `max_output_tokens=32768` on both methods (verified against the model's
limit in the real run), and enables `types.Tool(code_execution=types.ToolCodeExecution())`
when asked. If `finish_reason` is `MAX_TOKENS`, raise `ValueError("response truncated")` so
the failure is reported as truncation and is retried. Invalid or empty JSON now also raises
`ValueError`, which `_generate` treats as a validation failure (retry) rather than "model
call failed" (resolves two deferred minors from the v1 review).

### CLI / function

`run(..., worked_example: bool = False, min_words: int = 1400)`;
`--worked-example`; `--min-words N` (positive int). `--dry-run` additionally prints the
planned number of calls and the topic list (or "planning call").

## Testing (still no paid calls)

Extend the fake LLM with `generate_text` (records `code_execution`). New or changed tests:
schema parsing of sections/blocks; every new validation rule (section count, heading
validity, min words, grounded share, worked-example rules); renderer: no `[S`, no Sources
heading, no HTML comments in body, `source_map` content and `used_in`, external tag
placement (plain, math-first, list-first), display-math splitting (threshold at exactly 10
vs 11 symbols, trailing punctuation, already-display, list/table/blockquote skip, fenced
code skip); planning call; per-topic call count and ordering; worked-example flag off makes
zero `generate_text` calls and on makes one per topic with `code_execution=True`; retry once
per call then abort writes nothing; truncation/invalid-JSON now retried; `--min-words` and
`--worked-example` CLI parsing; dry-run reports call count.

## Real run (separate from tests)

1. Availability check: tiny `generate_text` call with `code_execution=True` on
   `gemini-3.8-flash`, and a check that `max_output_tokens=32768` is accepted. If code
   execution is unsupported on that model, stop and ask the user before choosing another
   model (the default model is a user decision).
2. Run on `wald_lm_lr_tests.md` with the three topics and `--worked-example`, writing a
   **new** file (`--output …/wald_lm_lr_tests.enhanced.v2.md`) so the already-pushed v1
   output stays for side-by-side comparison.
3. Review by hand: length per topic, no citation markers in the body, `source_map` correct
   against the cited chunks, display math applied, external tags sparse, worked-example
   numbers re-checked independently. Replacing the pushed file and committing to the vault
   repo remain separate, user-approved steps.

## Known limitations / risks

- Code execution makes the numbers real, but the prose around them can still misstate a
  result; the manual check covers this.
- A minimum-length check can encourage padding; the 50% grounded share and the reviewer
  spot-check are the guards. No automated entailment check (unchanged from v1).
- Per-topic calls re-send the same chunks each time (about 18K input tokens per call for the
  Wald guide); acceptable on a flash model.
- Section-level `used_in` is coarser than paragraph-level markers; chosen to keep the body
  and its embeddings clean.

## Out of scope

Paragraph-level provenance markers, resumable runs, parallel calls, enhancing an enhanced
guide, converting the already-pushed v1 output (a regeneration is a separate, approved run).
