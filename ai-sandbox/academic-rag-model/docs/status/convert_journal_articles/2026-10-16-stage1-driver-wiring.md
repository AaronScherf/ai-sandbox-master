# Journal converter: stage 1 driver wiring (2026-10-16)

Branch `claude/journal-agent-driver`. Plan: `docs/superpowers/plans/literature_taxonomy/2026-10-16-stage1-journal-converter-driver.md`. Spec: `docs/superpowers/specs/literature_taxonomy/2026-10-15-literature-taxonomy-pipeline-design.md`, section 6 stage 1.

## What changed

- `convert_journal_articles.py` now defaults to `--driver agent`: `--collect` stages task cards, `--submit` validates and writes, `--bootstrap` prints the agent contract, `--allow-api-fallback` is explicit opt-in, `--driver api` keeps the old metered path. A bare run exits 1 without spending anything.
- `process_pdf(check_math_notation=...)` and `submit_doc(known_doc_types=..., check_math_notation=...)` are additive keyword passthroughs (defaults reproduce the notes pipeline exactly) so submit routes a paper the way collect did.
- Card-less (clean machine-text) papers are converted locally at submit with a `NullDriver`; any that actually need an agent are reported.
- OpenAlex identity (`openalex_id`, `doi`, `openalex_topics`, `publication_year`) is stamped from the `.meta.json` sidecar onto the index card after conversion; `--backfill-identity` covers papers converted earlier.
- `research/.agent_work/` is gitignored (cards hold paper text).
- `defect_audit.py` measures the heuristic per signal over a folder (aggregates only).

## Measured defect rate (acceptance for plan item 2)

Corpus: 106 readable PDFs, 3,846 pages (local only, nothing committed).

| Scoring | Defective pages | Rate | Docs over the 10% hybrid threshold |
|---|---|---|---|
| Original (math notation on) | 493 | 25.5% | 34 |
| Journal profile (math notation off) | 302 | 15.6% | 27 |

Per-signal pages flagged, math notation off: `unexpected_chars` 243, `repeated_char_run` 68, `collapsed_prose` 2.

**Target was at most 10%: NOT MET.** The plan said to stop and report instead of tuning further; no other signal was changed. A character census of the `unexpected_chars` pages (counts per character only, no text) shows the cause: the notes-oriented character whitelist rejects ordinary journal-prose characters. Most frequent: é, ¯ (macron), ˆ (circumflex), á, ó, µ, ˜ (small tilde), ö, ä, à, ç, ü, ● and í, i.e. accented names in authors and references, plus combining-accent artifacts. Allowing Latin-1 and Latin Extended letters in the prose profile would very likely clear most of that signal. That is a recall tradeoff (a real corrupted-extraction page could contain accented letters too), so it is the owner's call and is not done here.

## End-to-end check on two real papers

Scratch copies (not in the repo): one clean 40-page paper, one 24-page paper with 11 defective pages.

- `--collect`: the clean paper staged no cards ("free local extraction, 0 API calls"); the defective paper (46% defective, over the hybrid threshold) staged 2 batch cards. `git status` stayed clean (work dir ignored).
- `--submit` with nothing filled: the defective paper reported `incomplete: 2 card(s) still pending/bounced` (no fallback); the clean paper converted locally ("0 transcription calls") and was indexed.
- `--driver api` was not run.

## Deferred / not done

- Page images for result tables (stage 1 item 4): deferred to stage 2.
- Country codes on cards: not in the sidecar; come from the stage-2 extraction record.
- `corpus_write_lock` is held on `--submit` and `--backfill-identity` only. The `--driver api` loop remains unlocked, as before.
- Two existing converter tests (`TestMainOversizedPageGate`) gained `--driver api` in their argv because a bare invocation now exits by design.
