# Resume Manager Tailoring Guidance Status — 2026-09-28

## Shipped

`apply_from_prompt.py` now accepts either `--guidance` or `--guidance-file`.
The supplied instructions go to the Gemini relevance brainstorm and the
local Ollama tailoring call. They are retained for Ollama if Gemini is
unavailable, and the application saves them in `guidance.txt`. The prompts
allow explicit user-provided facts to supplement the matching master-resume
entry while prohibiting the models from inferring further claims. The
README documents both options.

The change and its first tailored Ukraine application were merged into
`main` in commit `12cb13d`. The focused suite passed after integration:
77 tests across `test_apply_from_prompt.py`, `test_resume_tailor.py`,
`test_tailor_resume_cli.py`, and `test_resume_validate.py`.

## Real Ukraine run

The test used the current `resume_master.md` and this opportunity: remote
monitoring and evaluation consulting in Ukraine, focused on third-party
monitoring, energy resilience, asset data, and humanitarian equipment.
The user's guidance identified firsthand responsibility for equipment
inventories and asset databases covering electrical infrastructure and
humanitarian equipment across more than 16 projects, linked to the $5Bn
support figure in the USAID Ukraine entry. It also prioritized USAID and
post-ZEW experience, modest bullet edits, and no claims of direct project
implementation.

One local run with explicit guidance produced a two-page resume whose USAID
Ukraine bullet included inventory and asset-database management across 16+
projects alongside the $5Bn tracking figure. Its validation report flagged
one possible dropped `$413` metric in a separate USAID entry. That output is
in `applications/2026-09-28-remote-monitoring-and-evaluation-consultant/`.

## Gemini availability and fallback behavior

The user explicitly authorized sending the full master resume and tailoring
guidance to Gemini. On 2026-09-28, the CLI made a Gemini relevance-brainstorm
request as part of a full run; Gemini returned HTTP 503 `UNAVAILABLE` due to
high demand. The CLI continued with local Ollama and rendered a PDF. A direct
retry of the Gemini brainstorm also returned 503, so no Gemini guidance was
available for a complete Gemini-to-Ollama run.

The fallback output in
`applications/2026-09-28-ukraine-energy-resilience-monitoring-consultant/`
reported no validation discrepancies, but it omitted the user-provided
inventory and asset-database detail despite that text appearing in
`guidance.txt`. It also emitted two similar bullets about 20 program
evaluations, one describing them as supervised. This shows that the numeric
validator does not detect omitted qualitative guidance or semantic
duplication, and that a clean validation report does not establish that all
user priorities were followed.

An earlier local run's report flagged three possible dropped metrics
(`$413`, `$1.7Bn`, `$60M`); the more explicit retry preserved two of those
and flagged only `$413`. The model's retention of details varies between
runs. Review the tailored bullets against the master and `guidance.txt`
before using an application output.

## Open items

- Retry the Gemini-backed flow when the service is available, then review
  whether Gemini guidance helps the local model follow user-supplied facts.
- Consider adding checks for missing user-priority facts and duplicated or
  unsupported claims. Current validation covers numeric metrics and
  repeated openings, not semantic coverage or duplication.
- Keep reviewing dropped metrics flagged in each application's
  `validation_report.txt`; the prompt's preservation rule does not guarantee
  that every run retains every metric.
