# Unexpected results and bug handoff

This is an agent procedure, not an automated runtime validator. Gemini must
apply it while operating pipelines and reviewing their output. Existing
validators still run normally; passing them does not prove the result meets
the user's request.

## Check the result

Before a run, identify the expected behavior from the request, documented
contract, and relevant input. Ask for clarification only where it changes
the acceptance criteria. After a run, check exit status, validation reports,
artifact existence/freshness, and the actual content against those criteria.

Examples: a resume must preserve source facts and meet requested constraints;
a tutor answer must address the question with relevant supporting citations;
a website page must render the intended content, not merely build successfully.
Record checks you could not perform rather than claiming success.

Trigger a report when a command fails, output is missing/stale/invalid, the
result contradicts the agreed expectation, OR the user says the result is
incorrect. User feedback triggers investigation even if every validator passed.
A complaint is evidence of a mismatch, not proof of a specific code defect.

## Gemini's response

1. Acknowledge and flag the mismatch clearly. Stop using the affected output
   as a successful result; pause dependent publication, submission, or runs.
   Preserve the failed artifact before retries, respecting workspace ownership.
2. Record the user's correction, expected versus actual behavior, and evidence
   from the original run. Do not silently edit generated output to conceal a
   failure or repeatedly regenerate until an acceptable sample appears.
3. If safe, attempt a minimal reproduction using isolated inputs/outputs.
   Do not rerun a costly, destructive, or live-data operation merely to gather
   evidence. If reproduction is unavailable, record why and mark it unconfirmed.
   For model outputs, retain the failing sample and record variability, model,
   prompt/history where available, and retrieval inputs. Never invent missing
   logs, prompts, seeds, or a root cause.
4. Create the report below in the repository where the behavior originates.
   If it spans repositories, identify each checkout and relevant revision.
   Separate observed facts, hypotheses, and open questions. A clear editorial
   preference can be revised by Gemini, but still record the reported mismatch;
   do not label preference changes as confirmed software bugs.
5. Route the case and give the user the absolute report path, a short summary,
   proposed reviewer, and a ready-to-use handoff prompt. This prepares a handoff;
   do not claim another agent has received or reviewed it without evidence.
   Continue unaffected work within the assigned scope.

## Report storage and template

Resolve the owned repository root with `git rev-parse --show-toplevel`.
Write reports below that absolute root, regardless of the current directory:
`<repo-root>/.agent-reports/bugs/<YYYYMMDD-HHMMSS>-<short-slug>/`.
Use a unique directory; do not overwrite a report. Before saving any evidence,
run `git -C <repo-root> check-ignore -v -- <absolute-report-path>` for the
intended report and attachment paths and require a matching rule. If any path
is not ignored, stop saving evidence there until the repository's rule is fixed.
The rule must be in the actual repository receiving the files; an outer repo's
.gitignore does not protect a child repository. Existing tracked files are not
protected by adding an ignore rule. Never force-add reports.
If reporting from a read-only/shared checkout, first create an owned worktree
and record the original run's checkout separately.

Never include credentials. Minimize personal information and copyrighted
excerpts; use local paths or redacted/synthetic reproductions where possible.
Do not stage private artifacts or publish a GitHub issue automatically.
Reports stay local unless the user authorizes sharing; provide the exact path
so a reviewer can open them. Preserve or transfer needed reports before retiring
a worktree; gitignore is not a backup or access-control mechanism.

Create report.md with these fields (use "unknown" or "not checked" as needed):

- Title, timestamp, reporter, status (reported / reproduced / awaiting review /
  fixed-awaiting-validation / verified / unresolved), proposed reviewer.
- User request and correction; source of expected behavior.
- Expected result and actual result; impact and affected outputs.
- Original repository/worktree, branch, commit, relevant dirty paths;
  reviewer checkout/base needed to reproduce. A commit alone does not capture
  uncommitted changes; reference any safely retained relevant diff separately.
- Exact command or interaction sequence, working directory, sanitized inputs,
  runtime/dependency versions, model/backend/options, corpus/index version
  or freshness where known.
- Reproduction steps, number of attempts, reproducibility, limitations.
- Evidence paths: failing artifact, logs/exit status, validation output,
  relevant citations/screenshots. Label redactions and unavailable evidence.
- Initial code map: entry point, relevant modules, shared helpers, callers,
  tests, schemas/configuration, and documentation examined. This is a starting
  map, not an instruction to limit review to those files.
- Facts versus suspected causes; alternative explanations such as stale data,
  wrong configuration, unclear requirements, or model variability.
- Existing checks that missed the issue; proposed acceptance criteria and a
  minimal regression case. Do not weaken tests to accept incorrect behavior.
- Handoff prompt: "Review <absolute report path> against the relevant full
  codebase at <checkout/revision>. Reproduce the mismatch, trace callers and
  shared dependencies beyond the initial file list, distinguish a code defect
  from data/configuration/requirements issues, and propose or implement a fix
  within your role. Validate against the recorded acceptance criteria."
- Reviewer findings, fix commit (if any), validation commands/results, and
  remaining limitations. Leave these pending until someone actually reviews.

## Reviewer responsibilities

Codex receives well-specified bugs with clear expected behavior and routine
fixes. Claude receives ambiguous expectations, architectural/cross-component
design tradeoffs, or missing capabilities. Broad read-only evidence gathering
can stay with Gemini. Uncertain ownership routes to Claude for triage.

The reviewer must independently evaluate the evidence against the relevant
full codebase: trace the entry point through callers, shared helpers, data
contracts, configuration, and tests. Do not accept Gemini's suspected cause
as established or patch only the visible symptom. This does not require
dumping every file into context. Follow worktree ownership and local guidance.

Codex escalates any design decision to Claude. After a fix, run the minimal
reproduction and relevant regression checks, including affected callers.
Have Gemini re-run the original user workflow when its inputs/runtime are
available. Close only when acceptance criteria have been checked; subjective
correctness may need the user's confirmation. Otherwise retain an unresolved
or awaiting-validation status with the missing check explicitly named.
