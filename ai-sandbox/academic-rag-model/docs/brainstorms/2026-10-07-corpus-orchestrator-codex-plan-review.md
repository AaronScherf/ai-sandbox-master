# Corpus-health orchestrator: Codex plan review

Context: the user asked Codex (as a dry run of the agent-routing convention,
which normally sends architecture to Claude — see
[`docs/AGENT_ROUTING.md`](../../../../docs/AGENT_ROUTING.md)) to plan a daily,
non-agent-invoked orchestrator script that scans the academic-hub corpus for
unprocessed/unindexed files and stale repo state, then applies user-selected
fixes via existing pipeline commands. Codex produced a read-only plan plus
clarifying questions; this doc assesses that plan's quality as if it were the
real architectural decision, then gives the critique and concrete
improvements Codex (or whoever implements this) should fold in. Nothing here
has been implemented — this is a planning artifact only, per
`docs/superpowers/plans/` conventions, filed under `docs/brainstorms/` because
no package/spec exists yet to attach it to.

Prior art already in this repo that bears directly on this design:
- `tools/active_work.py` + `tools/git_workflow.py` — read-only, multi-worktree
  Git status/overlap reporting, already solving a slice of Codex's step 1.
- `tools/reconcile_needs_manual.py` — an existing precedent for a
  cross-cutting script that bridges two pipelines' outputs without them
  calling each other directly, and that regenerates a worklist rather than
  hand-editing one.
- `core/indexer/offering_links.py` + its review Artifact
  (`https://claude.ai/artifact/3xwWTQvW8yfywGbVDqxztE`) — the established
  pattern for "human decision needed" steps in this codebase.
- `academic-rag-model/CLAUDE.md`: *"Any step that needs a human decision
  produces an interactive Artifact by default, not a JSON or Markdown file to
  hand-edit."*

---

## 1. Codex's plan, verbatim

> I'll map the existing pipeline entry points and repository boundaries first, then shape the plan around what the code already supports. I'll keep this read-only since you asked for a plan, and I'll include the unresolved choices that affect the design.
>
> The repository guidance explicitly routes architecture to Claude, but it also says routing is a default and yields to the user's explicit assignment. I'm treating this as your requested design dry run. The Git workflow spec you linked is still a draft, so I'll use its boundary rules as context without treating its proposed tooling or approvals as adopted.
>
> The codebase already has most of the individual operations, but they live in separate pipelines and don't yet form a single **read-only scan → review → selected fixes → verification** workflow. I'd plan a coordinator that discovers gaps and presents a specific action list, then invokes existing commands only for the fixes you select.
>
> The relevant repository boundaries are important to the design: `academic_notes/` is its own nested Git repo, `academic-hub/` holds the resources and tracked index, and `academic-rag-model/` holds the code. The vault guidance also treats resource files as read-only by default and says generated material and index writes need a single writer. That points toward reporting status separately for each repository and never making Git or sync changes part of the default repair run.
>
> ### Proposed plan
>
> 1. **Define the scan boundaries and status report.** Start from configured roots for the code repo, hub resources, notes repo, and index. Report each root's branch and working-tree state independently. Classify Git findings—such as uncommitted files, stale branches, or divergence—as status items that need human judgment, rather than automatically cleaning, committing, merging, or syncing them.
>
> 2. **Build a read-only discovery pass.** Walk the configured corpus and compare sources with expected outputs:
>    - Find note PDFs or scans that have no transcription output.
>    - Find new textbook PDFs without a conversion, and converted textbooks missing expected `.rag.md` output.
>    - Find generated summaries, problem sets, and other Markdown files that lack expected frontmatter or index cards.
>    - Find stale or missing index entries and report relevant metadata mismatches.
>    - Report unrecognized file types and ambiguous source/output matches instead of guessing.
>
>    Reuse existing discovery logic where it's available. The transcription pipeline supports `--dry-run`; the essay converter does too. The indexer has `rebuild`, `retag`, and `chunk` operations, but a full rebuild can do more than identify new files, so the orchestrator should establish a targeted preview before it invokes one.
>
> 3. **Turn findings into an action list.** Each finding should identify the source, destination, proposed existing command, whether it may call an API or cloud service, and expected writes. Group related work, but let the user accept or skip each fix type—or each item if a batch contains mixed or costly work. For example, transcription, textbook conversion, and indexing should be separate choices. Do not infer consent for a paid or cloud conversion from a general "run repairs" choice.
>
> 4. **Apply only accepted fixes through existing pipeline entry points.** Invoke the current module commands with explicit roots and file selections, not new duplicate conversion/indexing logic. Likely operations include note transcription, textbook conversion and its follow-up steps, Markdown indexing, and metadata repair where existing checks support it. Keep each operation scoped to the findings from this scan. Anything that requires a new repair behavior, uncertain file classification, or a broader index rebuild should remain a reported item until its behavior is defined.
>
> 5. **Verify and report.** Re-scan the affected paths after each accepted batch. Show what was repaired, what remains, any command failures, and Git status changes. Do not commit, push, delete branches, or synchronize repositories as a side effect. Save a dated machine-readable report so the next run can compare findings and avoid treating already-reviewed items as new.
>
> 6. **Add scheduled operation after the interactive workflow is settled.** A daily run can safely perform discovery and write a report. Fixes that require a user decision need a review mechanism when nobody is present: either leave them pending for the next interactive run, or create a review queue that you can approve later. A scheduled process should not silently apply fixes whose cost, scope, or output location has not been explicitly authorized.
>
> The likely implementation boundary is a small orchestrator package under `academic-rag-model`, with adapters around the existing commands and a durable report/queue. Before implementation, I'd inventory each pipeline's machine-readable dry-run output and exact file-selection options. If an existing command can only run a broad batch, I'd mark that as a prerequisite rather than let the orchestrator accidentally process the whole corpus.
>
> The main open questions for the brainstorm are:
>
> - Should the daily scheduled run be **discovery-only**, with you choosing fixes later, or should it be able to apply a pre-approved subset such as indexing?
> - What should the review interaction be: terminal prompts during a manual run, a saved approval queue, or both?
> - Are paid API and cloud operations (especially textbook conversion) eligible for later batch approval, or should each book require its own approval?
> - Should Git checks cover only the three repositories' current cleanliness and branch state, or also compare them for expected synchronization and branch staleness?
> - Where should reports and pending decisions live, given that `academic_notes/` is a separate nested repo and the vault has its own sync workflow?
> - Which generated Markdown categories count as "summaries and problem sets," and are there other expected-output rules the scan should enforce?
>
> I kept this to a plan and read-only inspection. I used your explicit assignment as authorization for the architecture dry run despite the default routing in AGENT_ROUTING.md. The linked Git workflow spec remains marked **DRAFT, not approved**, so I treated it as context rather than adopted policy.

---

## 2. Claude's critique of the Codex reasoning

**Overall: directionally sound, appropriately cautious, but shallow on this
codebase's actual precedent and on one load-bearing project convention.**
Codex got the risk posture right — scan/propose/apply-on-consent,
no autonomous Git writes, no inferred consent across cost tiers, reuse
existing commands rather than re-implementing them — and that's the hard part
to get *wrong* in a way that causes damage. But a plan is also judged on
whether it used what's already sitting in the repo, and here it under-used
it.

### What Codex got right
- **Scan → review → apply → verify shape.** Matches how `postprocess_notes`,
  `discover_journal_articles`, and the review-Artifact pattern already work
  in this codebase — Codex re-derived a convention that already exists here,
  which is a good sign for a cold-start agent.
- **Consent granularity.** Explicitly rejecting "infer consent for paid/cloud
  work from a general 'run repairs' click" is exactly the failure mode that
  would burn API budget or trigger an unwanted textbook conversion. This is
  the single most important correctness property of the whole plan and Codex
  flagged it unprompted.
- **Refusing to let discovery accidentally trigger a broad index rebuild.**
  Correctly identifies that `core.indexer`'s `rebuild` can "do more than
  identify new files" and gates on that — shows it actually looked at
  `core/indexer/` rather than assuming uniform `--dry-run` support everywhere.
- **Declining to treat the three repos as one filesystem.** Keeping
  `academic_notes/` (nested repo), `academic-hub/` (vault), and
  `academic-rag-model/` (code) as separately-reported roots, with no implicit
  cross-repo sync, matches `docs/WORKTREE_WORKFLOW.md`'s explicit statement
  that worktrees "do not populate or isolate the separate academic_notes/...
  repositories."
- **Honest process framing.** Named the routing override explicitly, didn't
  pretend the linked Git-workflow spec was approved policy, and kept the
  response read-only as asked. No scope creep, no silent escalation.

### Where the reasoning falls short

1. **Missed the one hard project rule that directly governs step 3/6.**
   `academic-rag-model/CLAUDE.md` states plainly that any step needing a
   human decision "produces an interactive Artifact by default, not a JSON
   or Markdown file to hand-edit," and names `offering_links.py`'s review
   Artifact as the reference implementation. Codex's open questions ask
   *from scratch* whether the review surface should be "terminal prompts...,
   a saved approval queue, or both" — treating a settled convention as an
   open design axis. This isn't a nitpick: it's the exact decision the
   codebase already made, with working code to point to. A plan that doesn't
   find it will get built the wrong way and then redone.

2. **Didn't look for — or at least didn't cite — directly relevant existing
   tools.** `tools/active_work.py` and `tools/git_workflow.py` already do
   read-only, cross-worktree Git status/overlap reporting (branch state,
   dirty files, merge-base divergence) — a working slice of Codex's step 1.
   `tools/reconcile_needs_manual.py` is an existing, documented precedent for
   *exactly* the "bridge two pipelines' outputs without having them call each
   other, regenerate a worklist instead of hand-editing one" pattern Codex
   is reinventing for step 2/5. Citing and extending these would have made
   the plan concretely buildable instead of describing the shape of a
   solution without naming its parts. This is the main cost of Codex running
   without Claude's persisted project memory: a correctly-reasoned plan that
   doesn't know what already exists tends to re-derive existing work rather
   than extend it.

3. **"Daily, no agent" requirement is stated but not actually designed
   around.** The user's prompt says "ideally this check could be run without
   invoking an agent and could be run daily." Codex's step 6 acknowledges the
   tension (a scheduled run can't safely apply anything needing judgment) but
   stops at naming the tension rather than resolving it. A plan at this level
   should commit to an answer: discovery-only cron, writing a dated report
   artifact a human or a *next* agent session reads — not leave "should it be
   discovery-only or pre-approved-subset" dangling as an open question when
   the user already told Codex which of those (a review step, not silent
   application) they wanted ("after checking with the user which of the
   fixes should be applied right then"). The user's own prompt partially
   answers one of Codex's six questions; re-asking it suggests the prompt
   wasn't re-read closely during the open-questions pass.

4. **No mention of idempotency/report-diffing mechanics beyond "save a dated
   report."** Given `reconcile_needs_manual.py` and
   `discover_journal_articles`'s worklist already solve "don't re-report
   something already reviewed," the plan should specify *how* re-scans avoid
   re-surfacing a declined-by-the-user item as new every day — e.g., a
   decision ledger keyed by file hash/path with a `declined`/`deferred`
   state, not just the dated snapshot Codex proposes (which would re-ask
   about everything the user skipped yesterday, training the user to ignore
   the daily report).

5. **Scope of "fixes" is underspecified in a way that matters for safety.**
   Step 4 says "metadata repair where existing checks support it" without
   naming which checks, and conflates read-only discovery commands
   (`--dry-run`) with mutating ones in the same sentence ("Likely operations
   include note transcription, textbook conversion and its follow-up steps,
   Markdown indexing, and metadata repair"). A plan destined for daily
   unattended execution should enumerate, per pipeline, which specific
   subcommand is discovery-safe vs. mutating, not leave that inventory as a
   "before implementation" follow-up. Deferring the inventory is reasonable;
   deferring *naming the risk of not having it yet* is not — nothing in the
   plan flags that steps 1-6 are provisional until that inventory exists.

6. **No cost/runtime budget for the daily scan itself.** Walking the full
   corpus daily (PDFs, transcriptions, index) has its own cost — especially
   if "discovery" calls into a pipeline's `--dry-run` rather than a cheaper
   direct filesystem diff. The plan doesn't distinguish "stat-based diff
   against a manifest" (cheap, safe to run daily unattended) from "invoke
   each pipeline's dry-run mode" (same order of cost as a partial real run
   for some pipelines). This matters directly for the "no agent, daily" goal:
   a scan that's too slow or expensive stops being something a cron job can
   run.

### Net assessment
As an architecture-dry-run artifact, this is a credible mid-level plan: safe
defaults, correct risk ordering, no overreach. It would not have been
rejected in review, but it would have come back with exactly the six items
above, most of which trace to the same root cause — the plan was reasoned
from the prompt and a surface read of pipeline READMEs, not from the
project's accumulated design decisions (CLAUDE.md conventions, existing
cross-pipeline tools, prior Artifact-review precedent). That's the gap the
routing convention is actually about: not that Codex can't reason about
architecture, but that architecture decisions in this repo are
path-dependent on context Codex doesn't carry between sessions and didn't
fully mine in a single pass.

---

## 3. Improvements for the plan itself

Concrete changes to fold into whichever agent implements this next:

1. **Review/decision surface: use an interactive Artifact, not a prompt or
   file.** Replace step 3/6's open question with a committed design: the
   orchestrator's discovery pass writes findings into an Artifact-backed
   review page (checkbox/accept-skip per finding or finding-group, grouped by
   pipeline and cost tier — free/local vs. paid/cloud), modeled directly on
   `core/indexer/offering_links.py`'s review Artifact. Accepted items get
   written to a resolve/apply step the same way `offering_links.py` already
   separates proposal from application. This removes an entire open question
   and reuses tested machinery instead of inventing a new review UI.

2. **Build step 1 on `tools/git_workflow.py`, don't re-derive it.** Add the
   two missing roots (`academic-hub/`'s nested state and `academic_notes/`)
   to that module's existing `Worktree`/`dirty_files`/`is_ancestor` helpers
   rather than writing parallel Git-status code. If `academic-hub/` isn't a
   separate repo (confirm this — it may be a subtree of the monorepo rather
   than its own `.git`), the status report for it is a hub-resources content
   diff, not a Git-branch diff, and the plan should say which of the two it
   means per root.

3. **Decision ledger, not just a dated report.** Persist findings keyed by a
   stable identity (source file path + content hash, not just path, since
   notes/PDFs get renamed) with a status: `new` / `pending-review` /
   `accepted` / `declined` / `deferred` / `applied`. Daily discovery updates
   this ledger rather than overwriting a snapshot; the review Artifact reads
   from it. This directly fixes critique #4 (re-asking about declined items)
   and gives the "scheduled run with no one present" case (critique #3) a
   real answer: the cron job updates the ledger and the Artifact; a human (or
   the next interactive session) reviews accumulated `pending-review` entries
   whenever they next look, instead of the orchestrator needing to decide
   in-the-moment what to do with no one watching.

4. **Per-pipeline capability table before writing any orchestrator code.**
   Make Codex's deferred "inventory" step 0, not a prerequisite mentioned in
   passing: for each of `transcribe_notes`, `convert_textbook`,
   `convert_essays`, `convert_journal_articles`, `postprocess_notes`, and
   `core/indexer`'s `rebuild`/`retag`/`chunk`/`duplicate_check`, record (a)
   does it have a non-mutating discovery/dry-run mode, (b) can it be scoped
   to an explicit file list vs. only a full-corpus batch, (c) is it
   free/local or paid/cloud, (d) expected output path(s) it writes on apply.
   Anything that's full-batch-only or lacks a dry-run is a named follow-up
   ("add `--dry-run` to X") rather than something the orchestrator works
   around implicitly — this turns Codex's vaguest step (4) into something
   testable.

5. **Make discovery itself cheap by default.** Discovery's first pass should
   be a filesystem/manifest diff (source file list vs. recorded
   processed-output list, reusing `discover_journal_articles`'s manifest
   pattern and `core/indexer`'s existing card/index records as the "already
   processed" side of the diff) rather than invoking each pipeline's
   `--dry-run`. Reserve actual pipeline dry-runs for a second, opt-in,
   heavier pass (e.g., weekly or on-demand) if the manifest diff alone proves
   insufficient. This is what makes "run daily, no agent" actually cheap
   enough to be true.

6. **Resolve the scheduling mechanism explicitly, and check it against this
   session's own constraints.** "No agent invoked" plus "daily" plus
   "Windows" (per this repo's environment) points at Windows Task Scheduler
   or a cron-equivalent calling a plain Python entry point directly — not an
   agent-dispatched job. State that choice in the plan rather than leaving
   "add scheduled operation" as a deferred step 6 with no mechanism named.
   Separately, note for whoever schedules it: this is unrelated to this
   session's own `ScheduleWakeup`/cron tooling, which schedules *agent* turns,
   not plain scripts — don't conflate the two when implementing.

7. **Name the write boundary per repo explicitly in the design doc, not just
   in prose.** State plainly: `academic-rag-model/` — orchestrator code and
   ledger live here; `academic-hub/` — the orchestrator writes generated
   frontmatter/index artifacts here only on explicit per-item acceptance,
   never a bulk commit; `academic_notes/` — read/report only in v1 (it's a
   separately-synced nested repo with its own Fit-plugin sync constraints;
   don't let the orchestrator's "apply fixes" step touch it until that sync
   interaction is separately designed). This forecloses the "where should
   reports and pending decisions live" open question by giving each repo one
   job.

8. **Carry forward, don't re-ask, the one open question Codex raised that
   the user's prompt didn't already answer**: *"Are paid API/cloud
   operations eligible for later batch approval, or does each book require
   its own approval?"* This is the one genuinely open item in Codex's list —
   everything else either restates a project convention (Q2, Q5) or was
   already answered in the user's prompt (Q1, by "checking with the user
   which of the fixes should be applied right then"). Whoever writes the
   real spec should ask the user this one directly rather than re-surfacing
   all six.

---

## 4. Follow-up: review of Codex's design doc

Codex responded to section 3 and produced
[`docs/superpowers/specs/academic_hub/2026-10-07-corpus-health-orchestrator-design.md`](../superpowers/specs/academic_hub/2026-10-07-corpus-health-orchestrator-design.md)
(status: DRAFT, no implementation authorized). This section checks whether
that design actually resolves section 3's items, then separately assesses
whether Codex's design *process* — not just this one artifact — is now
sufficient for architecture work in this repo.

### 4.1 Disposition of each prior item

All eight numbered improvements and all six critique points from section 3
are resolved in the design doc, most of them thoroughly:

- **Review surface (critique #1, improvement #1):** resolved, with a
  deliberate and correctly-justified deviation. The design doc names the
  project's Artifact-by-default convention explicitly, then records that the
  user clarified the real requirement is a standalone, no-agent-required
  local page — which a Claude Artifact structurally cannot be, since
  rendering one requires this agent. The "Local interactive review page"
  section designs a loopback-only HTTP server with per-run tokens, origin
  validation, and no cross-origin API as the local analogue, and calls out
  that it is explicitly *not* a Claude Artifact. This is the right call, made
  for the right reason, not a convention it missed.
- **Reuse `tools/git_workflow.py` / `tools/active_work.py` (improvement #2):**
  resolved. The design doc also corrects an open assumption from section 3 —
  it confirms `academic-hub/` is *not* a separate Git repository (it's
  tracked inside the outer monorepo), which section 3 had flagged as
  something to "confirm... it may be a subtree." Codex verified it this
  time rather than asserting it.
- **Decision ledger with stable identity (improvement #3):** resolved, and
  more complete than what was asked for — fingerprint-based identity
  (survives renames), explicit `new -> pending_review ->
  accepted|declined|deferred -> applied` transitions, vanished-source
  handling, and acceptance invalidation on fingerprint/destination/parameter
  change.
- **Per-pipeline capability inventory as step 0 (improvement #4):** resolved
  — it's rollout phase 1, with a concrete table of operations to assess and
  an explicit rule that an operation without safe preview or scope is simply
  not callable until that gap is closed.
- **Cheap manifest-first discovery (improvement #5):** resolved — the cheap
  pass is enumeration/metadata/manifest/index-card based, content-hashes only
  new/changed candidates, and defers pipeline dry-runs to an opt-in deeper
  pass.
- **Name the scheduling mechanism (improvement #6):** resolved — Windows Task
  Scheduler invoking the entry point directly, discovery-only for the first
  rollout, explicitly not agent-dispatched.
- **Per-repo write boundary table (improvement #7):** resolved, with a table
  that also defers `academic_notes/` writes entirely to a later version
  pending sync-process coordination — correctly treating that as an open
  engineering problem rather than hand-waving it.
- **Narrow the open questions (improvement #8):** resolved. The design doc's
  four open decisions are all genuinely unresolved (cloud-approval
  granularity carried forward verbatim; notes-repo write timing; which
  Markdown categories need frontmatter; decline-retention policy) — none of
  them restate a settled convention or something the original prompt already
  answered.
- **"Daily, no agent" designed around, not just named (critique #3):**
  resolved — the four-phase workflow and the scheduling section both commit
  to an answer: scheduled runs refresh pending state only and never treat
  absence of a reviewer as approval.
- **Idempotency / re-asking about declined items (critique #4):** resolved
  by the same ledger design as improvement #3.
- **Discovery-safe vs. mutating operations conflated (critique #5):**
  resolved — "Applying accepted work" revalidates fingerprint, destination,
  and cost category immediately before invocation, and blocks any operation
  whose only implementation can't be scoped or validated.
- **Scan cost budget (critique #6):** resolved as well as a design doc can
  at this stage — it commits to measuring and reporting duration, files
  considered, and fingerprinting cost, and gates the expensive path behind
  that measurement rather than assuming a number up front. Reasonable; an
  actual budget has to come from the discovery prototype, not the design.

### 4.2 Gaps the design doc still has

Two concrete technical gaps, plus one process/scope concern, survive into
this draft:

1. **Concurrent writers outside the orchestrator's own lock.** "Apply" checks
   "no conflicting orchestrator run is active," but says nothing about a
   *manually*-run pipeline invocation (a human or another agent running
   `convert_textbook` directly, say, while the orchestrator's apply step
   also targets it) or about Obsidian Git sync running mid-write against
   `academic-hub/`. `WORKTREE_WORKFLOW.md` already states shared corpus/index
   writes "need one assigned writer and coordination with sync processes
   such as Obsidian Git sync" — the design doc cites this for
   `academic_notes/` but its lock design (section "Repository boundaries")
   only defends against *other orchestrator runs*, not against a concurrent
   manual pipeline invocation targeting the same output path. This needs a
   concrete mechanism (e.g., a lock file convention pipelines themselves
   check, or at minimum a documented "don't run X by hand while the
   orchestrator apply step is active" rule) before phase 5.
2. **`academic_notes/` sync noise is a known, specific hazard this draft
   doesn't name.** Per this session's standing project notes, the tablet's
   Direct Git Sync plugin stamps `.gitignore` from each device's local
   config on every load, so that file is not a stable shared source of
   truth, and the Fit sync plugin hard-blocks syncing its own `main.js`/
   `styles.css`. A `git_state` finding over the live `academic_notes/`
   checkout will see `.gitignore` churn and plugin-file sync blocks as
   ordinary dirty/divergent state unless it's told to discount them. The
   design doc's `git_state` finding kind should explicitly except known
   device-local sync artifacts in that repository rather than surface them
   as drift every day.
3. **Proportionality.** The original ask was "a single script" to replace ad
   hoc agent refreshes. This draft specs a loopback HTTP server with a
   token-authenticated decision API, a versioned ledger with fingerprint
   invalidation and lock semantics, a six-pipeline capability inventory, and
   a six-phase rollout — before anything ships. The Rollout section does
   sequence this reasonably and each phase is individually small, but the
   design doc never states that early phases are independently useful (e.g.,
   phase 2's discovery prototype is already a complete, valuable dry-run
   reporting tool on its own, with no ledger or server needed to get value
   from it today). Worth asking Codex to say so explicitly, so "approve the
   full spec before any implementation" (the doc's own closing line) doesn't
   become the default framing when phase 2 alone is worth shipping and using
   immediately.

None of these are severe enough to send the doc back; they're exactly the
scope of finding a second review pass should produce on an already-solid
draft, not evidence the first pass missed something major.

### 4.3 Is Codex's design process sufficient?

On this exercise: yes, conditionally. The gap between the plan (section 1)
and the design doc (this section) is large and in the right direction — it
went from "re-derive the shape of a known pattern from a prompt and package
READMEs" to "find the existing building blocks, verify an assumption instead
of flagging it, and commit to concrete policies instead of leaving them as
open questions." That jump happened because Codex was handed a specific,
itemized critique to work against, not because its first pass already had
that depth. That's the real signal: Codex's *correction* process — given
targeted feedback, each cited gap gets closed concretely rather than
hand-waved — is reliable. Its unprompted first-pass depth on a cold
architecture question is not yet at that level, and the proportionality gap
in 4.2 suggests the correction process optimizes for "address every named
critique" rather than "step back and ask if the overall shape still matches
the original ask" — a second-order check a plan should apply to itself
without being told to.

Practically, this supports the user's standing routing convention rather
than overturning it: Codex is well-suited to *executing against* an
itemized architectural critique or spec, which is most of what "code
maintenance, tests, and Git mechanics" plus well-specified feature work
actually requires. It is not yet demonstrated to produce first-pass
architecture at this depth unprompted — which is exactly the case for
keeping new designs routed through a Claude review pass before
implementation, as happened here, rather than treating this dry run as
grounds to change the default.

### 4.4 Review of the proposed `AGENTS.md` rules

The six rules Codex proposed are a reasonable and appropriately generalized
distillation of section 3/4.2 — they're phrased as durable process rules,
not hard-coded to this one orchestrator, which is the right level of
abstraction for `AGENTS.md`. Suggested revisions before adding them:

1. **Rule 1 (search before proposing) — make the search list concrete.** As
   written, "search for existing tools, specs, status docs, and conventions"
   is easy to satisfy with one shallow grep. Name the actual locations this
   repo uses: `tools/`, `docs/superpowers/{specs,plans}/`,
   `docs/status/<package>/`, and `docs/trackers/academic_hub_to_do.md`. The
   tracker matters specifically: this session's to-do list just gained a
   "Project Steering" item that explicitly has to stay distinct from this
   orchestrator — exactly the kind of adjacent, already-planned work a
   search should surface before proposing something that collides or
   duplicates it.
2. **Rule 4 (unattended workflows) — keep the generalization, it's good.** Add
   one clause: when a project convention exists for the human-decision
   surface (e.g., the interactive-Artifact-by-default rule), either follow
   it or state explicitly why the execution mode makes it inapplicable and
   what replaces it — i.e., require the justified-substitution move Codex
   made correctly this time (4.1, review surface) rather than assuming it
   will recur without being named as the expected behavior.
3. **New rule — proportionality.** None of the six rules check whether the
   proposed design's complexity matches the scope of the original request.
   Add: *"State plainly when a design introduces new infrastructure (a
   server, a persistent store, locking, a multi-phase rollout) beyond what a
   minimal version of the request would need, and identify which early
   phase(s) already deliver usable value on their own, rather than gating
   all value behind full-spec approval."* This is the one gap in this round
   (4.2.3) that the other six rules don't cover, and it's a repeatable
   failure mode independent of this particular orchestrator.

Rules 2, 3, 5, and 6 need no changes — each maps directly to a section 3/4.1
item that this design doc shows Codex can now close out concretely.
