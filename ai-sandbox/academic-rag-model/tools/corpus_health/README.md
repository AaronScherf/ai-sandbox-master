# Corpus Health Scanner

`python -m tools.corpus_health scan --config <json>` reports expected-output,
configured Markdown, index, and repository-state gaps without calling a model,
cloud service, or pipeline dry-run, and without mutating corpus files. By
default it updates a local decision ledger and append-only run log under the
outer repository's Git common directory. Use `--no-state` for a report-only
pass. `review` opens a short-lived loopback-only review page and records
accept/decline/defer decisions; acceptance never runs a pipeline.

Copy `corpus_health.example.json` to a local config and adjust the roots and
Markdown policies to the live workspace. Paths are resolved relative to the
config file. An outer-repository worktree usually does not contain the live
nested `academic_notes/` checkout; point `academic_notes_root` to that checkout
explicitly or set it to `null` to report it unavailable. `required_roots` controls
which absent roots make the scan incomplete.

Markdown classification is explicit. Add only categories known to require
frontmatter or indexing. Use `exclude_globs` for generated derivatives that
share a directory with indexed outputs but are not separately indexed. The
example policies cover course summaries, normal processed note outputs, and
textbook RAG files. Unknown Markdown is never classified by extension alone.

The default 8 MiB hash limit keeps the daily pass from reading full textbook
files. Large Markdown receives an `index_state_unverified` informational
finding; use a future explicit deep-audit mode before making a freshness claim.
The index audit reads through public indexer helpers and returns incomplete on
missing or malformed index data.

```powershell
python -m tools.corpus_health scan --config tools/corpus_health/corpus_health.example.json
python -m tools.corpus_health scan --config C:\path\to\corpus-health.json --format json --output C:\logs\corpus-health.json
python -m tools.corpus_health review --config C:\path\to\corpus-health.json --timeout 900
```

Exit status is `0` when every required scan completed, even if findings exist;
`2` means configuration or required-root/index/read errors made the result
incomplete. Reports include only paths, metadata, hashes, and short evidence,
not source-document text.

No apply command or repair adapter is enabled. Writes to `academic_notes/`
remain blocked pending an enforceable sync-quiescence boundary; other repair
adapters require the shared lock to be adopted by every participating writer.
No Windows Task Scheduler task is created by this package; the direct command
above can be configured manually for discovery-only operation.
