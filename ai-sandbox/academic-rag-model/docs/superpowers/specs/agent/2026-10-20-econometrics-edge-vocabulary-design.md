# Econometrics concept-graph edge vocabulary: decision record

Date: 2026-10-20. Status: proposed design decision; implementation has not started.

**Decision:** Add five narrowly defined relation types to the shared graph
package (`uses`, `applies_to`, `estimates`, `computed_from`, `variant_of`),
render any stated condition in every edge sentence, and repair the
econometrics edges with passage-level checks. This is a design decision by
Codex under the owner's explicit request, not an owner approval of individual
graph claims. The owner was asked to choose between extending shared types
and omitting inexpressible links; no preference was received before this
record was completed, so the recommended extension is the stated assumption.

## Request and boundaries

The first econometrics LINK pass produced 74 proposed edges. An independent
CRITIC pass classified 33 as supported, 24 as weak, and 17 as unsupported.
The owner wants accurate, well-supported, complete connections, with a design
decision about the relation vocabulary before the edge corrections are made.
This document decides the vocabulary and correction method; it does not
approve graph content, rewrite YAML, or publish a graph.

Requirements:

1. A rendered edge sentence must truthfully state the type, direction, and
   qualifications of the relationship. Its explanation and exact citations
   must support that same claim.
2. Preserve useful econometrics connections among methods, estimators,
   population targets, tests, and theorems without calling an association a
   taxonomy, domain, theorem hypothesis, or logical implication.
3. Preserve the existing microeconomics graph and the shared pipeline's
   review semantics. Drafted edges stay `proposed`; only owner review can
   set `verified`.
4. Show a condition wherever it changes whether the edge holds. A condition
   in YAML that readers do not see in the sentence does not qualify it.
5. Keep the viewer's prerequisite mode honest: an optional application is
   not a conceptual prerequisite merely because it has an arrow.
6. Make replacements traceable by old and new edge ID, and rerun independent
   criticism after changing a claim. Structural validation alone is not
   evidence that a claim is correct.

The repositories are distinct: shared code/specs/tests are in
`ai-sandbox-master/ai-sandbox/academic-rag-model`; econometrics YAML and the
built page are in the separate `econometrics-concept-graph` Git repository;
private task cards are under `academic-hub/.agent_work/concept_graph` in the
monorepo workspace. Worktree isolation is required for every writer. The
econometrics graph's `main` and `origin/main` remain at FILL commit
`3d8edc9`; Gemini LINK `83ce98b` and Codex CRITIC `bfda550` are unmerged
stacked commits; the 41-edge correction inventory is `e7bb466` on
`codex/econometrics-critic`. None of the 74 edges is owner-verified.

## Evidence checked

- The core [concept-graph design](2026-10-09-concept-graph-design.md) fixes
  nine edge types and says `component_of` is a condition in a bundle,
  `defined_on` is an object on a set/relation, `hypothesis_of` is a theorem
  premise/input, and `yields` connects a theorem to its conclusion.
- The [course-agnostic design](2026-10-19-course-agnostic-concept-graph-design.md)
  explicitly deferred this check until an econometrics FILL/LINK run, naming
  `uses`/`applies` and `special_case_of` as possibilities. Its predicted
  tool-centred structure now has live evidence.
- The graph repository's `docs/econometrics-link-corrections-20261019.md`
  at commit `e7bb466` lists each of the 41 flagged edge IDs and a proposed semantic correction.
  That inventory reflects the critic's judgments; each replacement still
  needs a passage-level evidence check.
- Reading `schema.py`, `stages/common.py`, `stages/link.py`, `validate.py`,
  `proposals.py`, `viewer/logic.js`, and `viewer/app.js` confirms these
  behaviors: edge types are code constants; the Python and JavaScript
  sentence renderers hardcode them; the viewer hardcodes styles, proposal
  choices, and prerequisite directions; structural validation does not judge
  evidence; and `condition` is absent from the displayed sentence for
  `has_property`, `defined_on`, `component_of`, `hypothesis_of`, and `yields`.
- Directly reading the stacked graph gives 80 nodes and 74 edges. The
  independent critic flagged 15 of 19 `defined_on`, 9 of 12 `hypothesis_of`,
  4 of 5 `component_of`, 5 of 16 `is_a`, 4 of 9 `yields`, and all 4
  `has_property` edges. It supported all 8 `implies` and the one `iff` edge.
  A manual lower-bound classification finds 19 of the flagged links trying to
  state an input/proof/application relationship with another type (10
  input/proof cases, 9 applications). The tool-node degrees are low despite
  their importance: weak law 2, central limit theorem 2, Slutsky 1,
  continuous mapping 2, delta method 2, and linear projection 2, whereas
  OLS has 13 incident edges, most flagged. `martingale-difference-sequence`
  and `p-value` were orphaned at critic-stage validation. These are observed
  counts and classifications, not proof that every critic verdict is correct.
- A read-only check of the graph repo's main checkout found an untracked
  `reviews/applied/2026-10-19-aaronscherf.json` containing three node-reject
  decisions and no edge decisions. Its node IDs are absent from the current
  80-node branch. Preserve this other session's file and recheck graph/review
  state before a later migration; its presence is not authorization to apply
  or reinterpret those decisions.

## Capability and side-effect map

| Step | Current capability and scope | Side effects / cost | Output, repeatability, and check |
|---|---|---|---|
| Inspect | `GraphStore.read_all` and edge inventory read YAML in the graph worktree. | Read-only; no API cost. | Stable list of IDs, types, verdicts; compare to source YAML. |
| Collect evidence | `collect link`/`collect critic` retrieve course passages. The preferred index backend makes a Gemini query-embedding call; lexical fallback uses the local index. | Writes private cards in a run directory; embedding calls can cost quota/money. No collect is needed for this design decision. | Run ID and offered passages; collect/submit are idempotent for already-applied cards, while `--redo` is explicit. |
| Draft or replace | `submit link` adds proposed edges after shape, citation, and cycle checks; current review UI proposes edges. Neither changes verified edges. | Graph YAML write in its assigned worktree; no automatic publication. | Proposed edge IDs; validate catches structural problems, critic and owner review check meaning. |
| Critic | `collect critic` gives a blind claim and fresh passages, then submit records a verdict. | Private cards plus critic fields in graph YAML; possible embedding calls. | One verdict per proposed edge; a changed edge needs a new/redo critic, never reuse a stale `supports`. |
| Validate/build | `validate` checks IDs, endpoints, types, conditions, and cycles. `build` writes `build/graph.json` and `index.html`. | Validate is read-only; build writes only the graph checkout; no API cost. | Zero errors and a rendered page, but neither proves econometric truth. |
| Owner review | Existing self-contained graph page records accept/reject/edit decisions and `apply-review` applies them. | Review files/YAML writes only after an owner decision; GitHub issue submission is a separate publication step. | Only accepted/edited claims become `verified`; stale edits produce conflicts. |

## Design alternatives

**Keep the nine types and omit mismatches.** This minimizes shared-code work
and protects the original ontology. It would remove or leave unlinked many
legitimate tool/target/application relationships that the course-agnostic
design predicted; the 41 flags show the issue is systematic. Even this choice
still needs a viewer fix for hidden conditions and evidence-based YAML repair.

**Extend the shared types narrowly (selected).** This adds code, viewer labels, and
tests for a few semantics that recur in the 41 flagged edges. It keeps the
old types' meanings unchanged and makes useful relationships visible.
The risk is an overlarge legend or vague catch-all types, so every new type
needs a precise sentence, direction, prerequisite behavior, and example of
what it must *not* mean. Five additive types are the selected limit for the
first release; do not add another merely to preserve an old edge count.

## Selected relation semantics

The selected initial vocabulary for the recurring patterns has
five additive types. Each type has an optional `condition`; if present, it
is rendered. A relation is still omitted when its exact claim lacks evidence.

| Type | Sentence and direction | Prerequisite behavior | Valid example / boundary |
|---|---|---|---|
| `uses` | “A uses B” (`A -> B`) for an essential input to a calculation, test, or derivation in the stated context. | A needs B within that context. | An LM test uses the restricted score; do not use it merely because two topics appear together. |
| `applies_to` | “A applies to B” (`A -> B`) for a nonexclusive theorem, technique, or test application. | No prerequisite edge: B does not generally require A, nor A this particular B. | Cross-validation applies to OLS fits; do not imply OLS defines cross-validation. |
| `estimates` | “A estimates B” (`A -> B`) for a sample-based rule and its population target. | A needs B to explain its target. | QMLE estimates a pseudo-true parameter under stated regularity; a model alone is not an estimator. |
| `computed_from` | “A is computed from B” (`A -> B`) for a formula-level dependency. | A needs B. | Robust standard errors are computed from a sandwich covariance estimate; do not treat the scalar errors as the matrix. |
| `variant_of` | “A is a variant of B” (`A -> B`) for a modified objective or transformation that preserves a recognizable method lineage without strict subtype identity. | A needs B. | Ridge is a penalized least-squares variant of OLS; this does not assert ridge **is** OLS. |

Existing `is_a`, `defined_on`, `component_of`, `hypothesis_of`, `yields`,
`implies`, and `iff` retain their current semantic restrictions. In
particular, `variant_of` does not replace `is_a` for true taxonomy, and
`applies_to` does not license a false theorem conclusion. No new generic
`related_to` type is proposed. The original spec's possible
`special_case_of` is deferred: zero-penalty coincidence of OLS and ridge or
lasso is a parameter case, not evidence that ridge/lasso is taxonomically
OLS; `variant_of` states the relevant relation directly.

For theorem-to-conclusion cases, prefer a specific `result` node and the
existing `yields` type when the result is educationally important: for
example, “OLS is BLUE under Gauss–Markov assumptions” and “the LR statistic
has a chi-square null limit under Wilks regularity.” A broad theorem ->
estimator/test edge stays out of the graph until its conclusion can be
stated. A result node requires its own explanation and citations through the
normal proposed-node review path.

Illustrative migrations, pending exact passage checks:

| Current claim | Better proposed claim | Why |
|---|---|---|
| `cross-validation--defined_on--ordinary-least-squares` | `cross-validation--applies_to--ordinary-least-squares` | OLS is one estimator that held-out evaluation can assess. |
| `ridge-regression--is_a--ordinary-least-squares` | `ridge-regression--variant_of--ordinary-least-squares` | Penalizing squared loss changes the estimator; it is not OLS. |
| `ordinary-least-squares--defined_on--linear-projection` | `ordinary-least-squares--estimates--linear-projection`, if the target node explicitly covers its coefficients; otherwise add a projection-coefficient target node. | Population projection coefficients are a target, not a domain. |
| `heteroskedasticity-robust-standard-errors--is_a--sandwich-variance` | `heteroskedasticity-robust-standard-errors--computed_from--sandwich-variance` | Standard errors are taken from a covariance estimate's diagonal. |
| `score--component_of--lagrange-multiplier-test` | `lagrange-multiplier-test--uses--score` | The restricted score is part of the test statistic. |
| `ordinary-least-squares--has_property--unbiasedness` | Same ID with a displayed exogeneity/rank condition. | The relationship is conditional, and the current viewer hides that fact. |
| `gauss-markov-theorem--yields--ordinary-least-squares` | `gauss-markov-theorem--yields--<conditional-ols-blue-result>` | The theorem concludes a property of OLS; the result node must be drafted and reviewed first. |

## Condition display and compatibility

Keep the current `condition` field and its required status for `implies` and
`iff`. Preserve `is_a`'s “that also: …” differentiator meaning. For every
other existing or new type, append a visible “, when: …” clause whenever
`condition` is nonempty. Match this behavior in Python task-card sentences
and JavaScript viewer sentences, including the node connection list and edge
heading. Do not globally require conditions for `has_property`: some
properties are unconditional. Require the author/critic to state and verify
one wherever the particular claim is conditional.

The new types must be additive and global to the shared package, not a
course-specific `vocab.yaml` entry. The viewer legend/proposal form, link
instructions, schema constants, validators, sentence renderers, and
prerequisite traversal all need the same semantics. Existing graph YAML
must still load and render unchanged. The microeconomics sample graph is a
regression fixture; its existing edge IDs and sentences should not change
except when they carry a previously hidden explicit condition.

## Correction and review lifecycle

1. Implement and test the shared vocabulary and condition-display behavior
   in a dedicated monorepo worktree. Land it before using the new types in
   graph data, so the deployed builder and viewer can read them.
2. In a separate graph-repo worktree based on the committed LINK/CRITIC
   stack, check each of the 41 old claims against the exact citation passage.
   Preflight the graph main checkout and pending reviews for owner decisions
   or endpoint changes since this decision record.
   Remove or replace an inaccurate proposed edge. A changed source, type,
   or target gets a new ID; a changed explanation/condition invalidates the
   old critic verdict. Changed citations also require a fresh critic even
   though the current review hash covers only editable text fields. Keep
   every replacement `proposed`. The current review UI edits only condition
   and explanation on an existing edge, so a type/direction replacement must
   be made in the graph worktree before owner review.
3. Do not force a replacement for every old edge. Some relationships need a
   new result node, a corrected source node, more evidence, or no link.
   Specifically audit the likelihood-principle node's gist before using it
   in new edges. Count every removal and unresolved edge in a migration
   report so the graph's apparent completeness is not overstated.
4. Run structural validation, build a local page, compare all changed
   displayed sentences with YAML, independently critic the new claims, and
   audit the originally supported 33 for the same relation-label misuse.
   Resolve or explicitly defer any remaining weak/unsupported claims before
   asking the owner to verify them in the existing interactive review page.

Old edge IDs must remain traceable in the migration report and Git history.
The current `data/rejected.yaml` is an owner-decision tombstone; do not write
agent supersessions there as if the owner had rejected them. Since ordinary
`collect link` does not redo touched nodes and explicit `--redo` can recreate
old drafts, the first correction release can avoid another link sweep and
list superseded IDs in its audit. A reusable machine-readable supersession
registry is a later prerequisite **if** automatic link redrafting is planned;
it is not required to make this first reviewed graph useful.

| Current state | Next state after a correction | Authority and audit |
|---|---|---|
| Proposed old edge with wrong type/direction | Removed from active YAML; old ID and reason in the migration report. | Agent correction requested by owner, not an owner rejection or verification. |
| Proposed replacement edge or new result node | Proposed, with fresh citation check and no inherited critic verdict. | Independent critic, then owner's interactive review. |
| Verified edge/node | Unchanged by automated correction. | Only an explicit owner review decision may edit/reject it. |
| Owner-rejected ID | Remains in `data/rejected.yaml`. | Existing tombstone prevents ordinary re-proposal. |

The smallest usable release is the shared type/display change followed by
one evidence-checked correction pass on the econometrics graph and a local
viewer preview. It needs no new service, database, scheduler, or generic
agent-run infrastructure. Extra relation types, automated supersession
tracking, and new course migrations can wait until a later release.

## Acceptance evidence and limits

- Unit tests: old and new sentence wording (including conditions), edge
  type acceptance, reviewer proposal UI parity, and prerequisite direction
  for every new type; existing microeconomics tests still pass.
- Fixture integration: build and validate a small mixed graph with both old
  and new types, check that filters/legend/selection work, and ensure no
  new type accidentally enters the logical or definitional cycle checks.
- Live graph: all replacement edges structurally validate; inspect each
  changed sentence, citation, critic result, and page rendering. Record
  per-edge dispositions and the remaining orphan count.
- Owner gate: `proposed` remains distinct from `verified`. Passing tests,
  validation, and a critic pass are not owner acceptance or publication.

No implementation, live corrected graph, or owner review is claimed by
this decision record.
