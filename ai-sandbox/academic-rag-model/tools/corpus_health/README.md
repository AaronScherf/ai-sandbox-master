# Corpus Health Scanner

`python -m tools.corpus_health scan --config <json>` reports expected-output,
configured Markdown, index, and repository-state gaps without calling a model,
cloud service, or pipeline dry-run, and without mutating corpus files. By
default it updates a local decision ledger and append-only run log under the
outer repository's Git common directory. Use `--no-state` for a report-only
pass. `review` opens a short-lived loopback-only review page and records
accept/decline/defer decisions; acceptance never runs a pipeline. A separate
`apply --accepted` invocation processes accepted findings.

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
The example excludes audio-generator narration (`*.narrated.md`) and its
`*__index.md` manifest, plus three named plotting/HTML test artifacts in
`summaries/`. Substantive study-guide drafts and the Gemini session remain
eligible until they are reviewed individually.

Transcription findings can be deferred in the local decision ledger when a
specific source PDF is intentionally held for later. The notes router has no
ignore manifest and does not read this ledger; use explicit `--file` or
`--course` selection when running it directly. Deferred findings remain
visible in reports and in `review --include-deferred` but leave the default
pending review queue.

Textbook PDFs are streamed in full to compute the same source ID recorded by
the converter's metadata and index cards. This finds converted books even when
their bibliographic output folder differs from the PDF filename. The default
8 MiB hash limit applies to other freshness checks, including Markdown: large
Markdown receives an `index_state_unverified` informational finding until a
future explicit deep audit verifies its content.
The index audit reads through public indexer helpers and returns incomplete on
missing or malformed index data.

```powershell
python -m tools.corpus_health scan --config tools/corpus_health/corpus_health.example.json
python -m tools.corpus_health scan --config C:\path\to\corpus-health.json --format json --output C:\logs\corpus-health.json
python -m tools.corpus_health review --config C:\path\to\corpus-health.json --timeout 900
python -m tools.corpus_health apply --config C:\path\to\corpus-health.json --accepted
```

Exit status is `0` when every required scan completed, even if findings exist;
`2` means configuration or required-root/index/read errors made the result
incomplete. Reports include only paths, metadata, hashes, and short evidence,
not source-document text.

`apply` currently enables only exact-card passage-chunk repair for an accepted
`index_chunks_missing_or_stale` finding whose card and source are still current.
It invokes the indexer's `chunk --file-id ... --json` command under the shared
writer lock, then audits the index before recording success. This can call the
configured Gemini embedding API once per generated chunk, so review acceptance
must be per source. Other accepted findings receive a recorded `blocked` reason.
A failed action returns to review on the next scan; a blocked action is rechecked
on the next `apply --accepted`. Notes writes remain disabled until the source
pipeline quality issues are fixed, affected notes are reviewed after
reprocessing, and `academic_notes/` sync quiescence is established. Textbook
GPU/VM conversion and broad index-card rebuilds stay outside automated apply.
The local shared lock is now held by the direct notes PDF, Excalidraw, and
router CLIs; academic-hub notes postprocessing; local textbook image
description; and the index `rebuild`, `chunk`, `retag`, and standalone
subset-linking CLIs. Their read-only dry runs do not take the lock. This is a
cooperative protocol, so it does not cover unadapted direct writers such as
`duplicate_check`, source migration, offering-link maintenance, or video-note
indexing, nor programmatic calls that bypass these CLIs. The remote textbook
converter and Obsidian sync also remain outside it. Do not run unadapted
writers concurrently with `apply` against the same index.
### Daily discovery on Windows

`run_daily_scan.ps1` is a discovery-only Task Scheduler entry point. It always
runs `scan`; it cannot invoke `review` or `apply`. It sets Python UTF-8 mode
(needed for non-ASCII filenames in the live JSON report), fixes the working
directory to this package, writes a timestamped JSON report and error/exit log,
and returns the scan's exit code. The log and optional state directory must be
outside the configured hub and notes roots. By default the scanner updates its
local decision ledger under the Git common directory; it does not write corpus
files or Git history.

Copy `corpus_health.example.json` to a stable local path, set the live hub and
notes checkout roots explicitly, and save it as UTF-8 **without a BOM**. Keep
the log directory outside both corpus roots. On this Windows workspace, use a
Task Scheduler daily trigger and these action fields (adjust paths if moved):

```text
Program/script: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
Add arguments: -NoProfile -NonInteractive -File "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\tools\corpus_health\run_daily_scan.ps1" -Python "C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model\.venv\Scripts\python.exe" -Config "C:\Users\theaa\AppData\Local\CorpusHealth\scan.json" -LogDirectory "C:\Users\theaa\AppData\Local\CorpusHealth\logs"
Start in: C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-rag-model
```

Set the task to run under the account that can read both roots, including when
the user is not logged on. Use "Do not start a new instance" if a previous
scan is still running. Check Task Scheduler's Last Run Result and the latest
`corpus-health-*.log`; `0` means a complete scan and `2` means a configuration
or incomplete-scan error. The JSON report is written alongside the log, and
findings alone do not make the exit status nonzero. There is no automatic
retry or repair: investigate an error and run the discovery command again.
The task is intentionally not registered by this package.

On 2026-10-09, three read-only scans of the live hub and notes roots completed
in 21.1–27.7 seconds of scanner time, considering 693–694 files and hashing
444–445. Each complete run reported 305–306 findings and zero scan errors.
The report exposes root availability and Git status, but does not instrument
every metadata lookup, so a precise metadata-check count is unavailable.
These runs establish a baseline, not a multi-day observation period. Compare
the daily reports and manually review a sample of findings before changing
scan policy or considering any unattended repair.
