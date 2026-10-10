# Project steering scanner (first milestone)

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

The scan recognizes dated top-level task bullets under `##` headings, including
multiline entries and `added`/`updated` dates. Undated bullets are listed under
"Needs classification" and make coverage partial. Bullets in `###` subsections
and the pasted textbook example are shown as structured exclusions. Exit `0`
means complete coverage under these rules; exit `2` means partial coverage or a
read/write error. A partial report is still published with
`coverage_complete=false`; source-change and operational errors publish nothing.

The ordering is provisional. An `URGENT` word and pause/defer wording are only
suggestions. The tool does not yet have owner-reviewed effort, priority, or
confirmed dependency data and does not assert a personalized top three. Stable
IDs, decisions, the interactive review page, and the scheduled runner are later
milestones in the [plan](../../docs/superpowers/plans/academic_hub/2026-10-09-project-steering.md).
