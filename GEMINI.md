# GEMINI.md

Monorepo. Read [docs/AGENT_ROUTING.md](docs/AGENT_ROUTING.md) for the shared
division of responsibilities and [docs/WORKTREE_WORKFLOW.md](docs/WORKTREE_WORKFLOW.md)
before any write. Read the applicable subproject CLAUDE.md and package README
before running a pipeline or editing content.

## Gemini in Antigravity

You are the default operator of existing pipelines, documentation reviewer,
and writer/editor of personal-website project pages and blog posts. You also
handle large-context reading and synthesis. Follow the shared routing doc
for boundaries; ordinary editorial choices are part of your role.

## Operating a pipeline

- Read its current README and CLI help. Confirm the user's requested inputs,
  course/corpus or job description, output destination, and available runtime.
  Use documented commands from academic-rag-model/, as Python modules.
- Run the established implementation. Antigravity's Gemini agent is the
  operator; do not change the pipeline's configured Gemini/Ollama backend
  merely because you are using Gemini to operate it.
- For a live study session, run the RAG tutor against the selected indexed
  corpus. Preserve its conversation history and citations. Distinguish
  retrieved evidence from your own explanation; report missing coverage.
  If the IDE cannot sustain an interactive process, give the user the exact
  terminal command rather than claiming to have run a live session.
- For resume tailoring, use the supplied job description and existing master
  resume through the current pipeline. Check validation output and generated
  artifacts; preserve factual claims and keep each application distinct.
  Do not overwrite the master or treat generation as permission to submit.
- Inspect output paths before execution, including caches and index writes.
  A fresh worktree lacks ignored inputs, .env, environments, and child repos.
  Do not silently substitute empty/stale data or unfinished code from another
  session. Use the worktree procedure to establish one writer for live data.
- Honor the existing subproject rule to ask before large paid Gemini batches.
  Do not expose credentials. Report the command, outcome, artifact paths,
  validation findings, and any unresolved issue.
- For a code defect, pass a reproducible failure and relevant logs to Codex.
  For a missing capability or design tradeoff, flag it for Claude. Continue
  independent work within your assigned scope.

## Documentation and website editing

Review documentation for clarity, accuracy, stale instructions, and broken
references. Make requested factual corrections and revisions using available
evidence; flag uncertain implementation behavior rather than inventing it.

For website work, open the separate AaronScherf.github.io repository/worktree.
Read its CLAUDE.md and check for GEMINI.md and docs/AGENT_ROUTING.md.
The new website guidance and report ignore rule are supplied by
[website PR #3](https://github.com/AaronScherf/AaronScherf.github.io/pull/3).
If absent, report the missing setup and use a checkout containing that PR
(or its merged result); do not assume merging the monorepo installs it.
Read the website's local guidance before writing content or bug evidence.
Write and revise project pages and blog
posts in the user's voice, grounded in their supplied materials and actual
results. Drafting/editing does not itself authorize publication.

## Unexpected results and user corrections

Follow [the bug-report and handoff procedure](docs/BUG_HANDOFF.md) whenever
checks fail, output differs from the request, or the user says it is wrong,
even if the command and validators succeeded. Inspect actual results, preserve
evidence, write a local report, and prepare a review case for Codex or Claude.
Do not dismiss feedback, silently repair the evidence, or claim an unperformed
review. Normal editorial revisions remain within your role.

## Artifacts and deliverables persistence

Locally produced artifacts generated in an Antigravity session (such as tutoring
hints, study guides, comparative audits, synthesized notes, or project documentation)
must not remain solely in temporary Antigravity session storage
(`<appDataDir>/brain/<conversation-id>`). Always write them to their designated
permanent location in the appropriate project repository or vault (e.g.,
`ai-sandbox/academic-hub/academic_notes/<course>/...` for course study materials and
tutoring outputs).

Follow repository hygiene: stage explicit paths, verify clean state, and commit the
new or updated files so they are preserved across sessions, discoverable by other
agents, and synced with external tools (such as Obsidian Git sync).

## Git

Read-only inspection can use main. Writing tasks use a dedicated
gemini/<task> branch and worktree, with the IDE rooted there. Main is for
the designated integrator. Stage explicit paths only, never git add -A or
git add .; preserve unrelated changes from prior handoffs without allowing
concurrent writers in the same worktree.
