# Project steering and to-do review

`python -m tools.project_steering scan` reads one explicit to-do tracker and
refreshes a provisional local work view. It makes no model or network calls and
does not edit the tracker. Run it from `academic-rag-model/`:

```powershell
python -m tools.project_steering scan --tracker C:\path\to\docs\trackers\academic_hub_to_do.md --state-dir C:\path\to\local\project-steering
```

Both paths must be absolute. Put the state directory outside tracked source and
the nested `academic_notes/` repository. The command writes versioned JSON and
Markdown reports under `runs/`, then atomically replaces `latest.json` to point
at the complete pair. If a write fails, the previous pointer still names the
last complete pair. `--format json` prints the same findings as machine-readable
stdout; the default prints the generated Markdown view.

The scan recognizes eligible task bullets under `##` headings, including dated
bullets in subsections and undated textbook tasks (`added: "unknown"`). It retains
line-numbered diagnostics. The Git-workflow brainstorm notes and pasted example
remain excluded. Exit `0` means complete coverage; exit `2` means unresolved
classification or an operational error. A partial report is published with
`coverage_complete=false`; source-change and operational errors publish nothing.

The one-time ID migration is separate from `scan`. In an assigned outer-repository
worktree, run `preview-ids --tracker <absolute-path>` and inspect its diff and
`source_sha256`. Then run `apply-ids --tracker <same-path> --source-sha256 <hash>`.
An intervening tracker edit rejects the apply; recover with a fresh preview.
The marker is an invisible Markdown comment at each task bullet start. The
scheduled scan never invokes this command or edits the tracker.

Owner decisions live in a versioned, locked `decisions.json` under `--state-dir`.
Use `review --tracker <absolute-path> --state-dir <absolute-path>` to start the
short-lived loopback page and follow the printed URL. Set impact and urgency
from 0–3, choose an effort band, and optionally confirm dependencies, defer,
decline, or mark done. Scores and shortlist explanations update after each save.
The page never executes work items. The generated view stays provisional until
the owner supplies these inputs. An `URGENT` word and pause/defer wording remain
unreviewed suggestions, not automatic priority or status decisions.

The daily scheduler is still a later milestone in the
[plan](../../docs/superpowers/plans/academic_hub/2026-10-09-project-steering.md).
