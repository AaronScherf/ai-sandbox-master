# AGENTS.md

Monorepo. Work happens in `ai-sandbox/academic-rag-model/` (Python
pipelines) or `ai-sandbox/academic-hub/` (the content vault they populate);
each has its own `CLAUDE.md` with commands, scope, and gotchas that apply
regardless of which agent is running — read the relevant one before editing
there. See `docs/AGENT_ROUTING.md` for the full multi-agent convention.

## What Codex is for in this workspace

Routine, well-specified, mechanical work: git mechanics (rebase,
cherry-pick, branch cleanup), running/fixing unit tests, lint/format passes,
maintenance script execution, dependency bumps, boilerplate.
Using existing pipelines for study or resume tailoring, documentation review,
and website writing defaults to Gemini; see the shared routing convention.
If a task turns out to need
a design decision mid-way, stop and flag for Claude rather than deciding it
inline.

Running an existing pipeline on workspace materials, when requested by the
user, authorizes its documented API calls and the data transfers they require;
keep calls within the requested inputs and options, and ask only if the run
would materially expand that scope.

## Codex completion updates

- After a long-running code task or multi-stage implementation, summarize the
  completed work and the current project status. Include the verification
  results and any remaining tasks or gates; reporting only that tests finished
  is not enough.
- End each user-facing response with a concise question about next steps. When
  work remains, recommend the most useful next action; when no follow-up is
  apparent, ask whether the user wants to continue with another task or stop.

## Planning and architecture work

When explicitly asked to plan or design a project change:

- Before proposing architecture, read the relevant subproject guidance and
  package README, then search for existing tools, specs, status docs, and
  conventions that solve part of the problem — concretely, check `tools/`,
  `docs/superpowers/{specs,plans}/`, `docs/status/<package>/`, and
  `docs/trackers/academic_hub_to_do.md` for adjacent or already-planned work,
  not just the package you're extending. Name the relevant files and
  distinguish verified behavior from assumptions.
- Turn the request into explicit requirements and constraints first. Don't
  re-ask questions the user or project rules have already answered; reserve
  open questions for decisions that remain genuinely unresolved.
- For workflows spanning tools or pipelines, make a capability table covering
  discovery, scope, side effects and cost, outputs, idempotency, and
  verification. Identify unsupported behavior as a prerequisite instead of
  assuming it exists.
- For scheduled or unattended workflows, specify the actual execution
  mechanism, scan cost, persistent state, retry behavior, and what happens
  when no human is available. Separate internal machine state from the human
  review surface, and verify that the proposed interface can be used by the
  requested execution mode. When a project convention already governs the
  human-decision surface (e.g., the interactive-Artifact-by-default rule in
  `academic-rag-model/CLAUDE.md`), follow it, or state explicitly why the
  execution mode makes it inapplicable and what replaces it — don't treat a
  settled convention as an open design axis.
- Define stable identity and state transitions for recurring findings.
  Explain how changed inputs invalidate prior decisions and how declined or
  deferred items avoid recurring as new alerts.
- Map every repository and write destination. Verify which paths share a
  Git repository, which are nested or external checkouts, and how sync
  processes affect writes. Never infer that a directory is a separate
  repository from its name or role.
- State plainly when a design introduces new infrastructure (a server, a
  persistent store, locking, a multi-phase rollout) beyond what a minimal
  version of the request would need, and identify which early phase(s)
  already deliver usable value on their own, rather than gating all value
  behind full-spec approval.

## Git

Before any write, follow [the worktree procedure](docs/WORKTREE_WORKFLOW.md).
Use a dedicated `codex/<task>` branch and worktree; launch the session there
and keep shell and IDE edits inside it. Main is for the designated integrator.

Stage explicit task paths only, never `git add -A` / `git add .`.
Preserve unrelated changes encountered during handoff; their presence does
not authorize concurrent writers in this worktree.

## Bug report intake

Follow [reviewer responsibilities](docs/BUG_HANDOFF.md#reviewer-responsibilities).

## Private API pipeline runs

The user has authorized running existing study, resume, and other personal
pipelines with their own configured API credentials when the requested source
files and generated outputs stay within their local workspace/repositories.
For these requests, sending only the necessary user-provided or locally held
source material to the configured personal API is within scope; do not ask
again for that same authorization. Keep generated files in the requested local
destination. This standing authorization does not cover publishing source
material or outputs to a public repository/service, sending them to a different
person's account, or using unrelated sources or credentials. Follow any
platform-level approval or data-handling controls that still apply.
