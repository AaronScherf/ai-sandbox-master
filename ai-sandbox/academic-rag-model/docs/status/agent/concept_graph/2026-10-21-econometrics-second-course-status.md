# Concept graph: econometrics, the second course, status 2026-10-21

Supersedes the "Open" list of `2026-10-19-course-agnostic-status.md`. That doc covers classifying the course and the
first seed. This one covers drafting the econometrics graph to completion, what went wrong along the way, and the
lessons for the next course.

## State

- Graph repo `C:\Users\theaa\econometrics-concept-graph` (GitHub `AaronScherf/econometrics-concept-graph`, **private**),
  main @ `f4361b7`. 112 concepts, 135 edges. Every edge has a critic verdict, and every item is still `proposed`.
- Public page: a separate repo, `AaronScherf/econometrics-concept-graph-site` (Pages from `main` root), live at
  <https://aaronscherf.github.io/econometrics-concept-graph-site/>. Site commit `be098b6` holds the page built at
  `f4361b7`.
- **Next:** the owner verifies items on the page. Nothing else is queued.

## How the graph was drafted (2026-10-20 to 2026-10-21)

| Step | By | Result |
|---|---|---|
| Seed, then fill, link, critic and corrections | Gemini (seed), Codex | 84 concepts, 80 edges (graph `c2d4082`) |
| Independent critic pass 1 | Claude | 78 supports, 2 weak. 28 of 80 edges were `applies_to`/`uses` |
| Two new edge types, `defined_via` and `assumption_of` | Claude | monorepo `07c4c01`. 5 edges retyped by hand |
| Relink with the new types | Gemini | 20 edges. Claude then removed 2 superseded `implies` edges that closed a four-node cycle |
| Additive seed (`seed --redo`) | Gemini | 7 concepts, mostly assumption-level (strict exogeneity, full column rank, random sampling, ...) |
| Link of the 7 new concepts | Gemini | 15 edges |
| Exogeneity split | Claude | narrowed `exogeneity` to the per-observation condition; removed 4 edges that needed strict exogeneity |
| Critic pass 2 | Claude | 38 supports (less blind: Claude had reviewed or written most of them) |
| External syllabus gap check | Claude | 21 concepts, 8 connections, entered as reviewer proposals |
| Fill and link of the 21 | Gemini | all 21 explained from the corpus; 17 edges |
| Critic of the 25 new edges | Codex | 14 supports, 9 weak, 2 unsupported |
| Retype of the flagged edges | Claude | 9 retyped or reworded, 1 rejected (`size-of-a-test--defined_via--power-of-a-test`) |
| Link of the 2 orphaned concepts, then critic of the last 11 edges | Gemini, Codex | 2 edges; 7 supports, 4 weak (judgment calls left to the owner) |
| Rebuild and publish | Claude, owner pushed | graph `f4361b7`, site `be098b6` |

## Lessons for the next course

1. **The corpus seed under-covers, so check against the syllabus.** The additive seed found 7 concepts, almost all
   assumptions. A manual comparison of the syllabus reading list with the node list then found 21 more, which the
   corpus covers well enough to fill all of them. They include a whole syllabus topic: dynamic causal effects
   (Stock-Watson 16), with none of its concepts in the graph. Make the gap check a standard step after the first
   fill and link. List the syllabus's assigned sections, compare them with the node names, and enter the gaps as
   reviewer proposals. A schema-version-2 review file with `add_node` and `add_edge` decisions, applied with
   `apply-review`, works for an agent as well as a person. The concepts land as `proposed` with
   `provenance.driver: reviewer`.
2. **A statistics course needs more edge types than a theory course.** The microecon vocabulary left about a third of
   econometrics edges as `applies_to`/`uses`. In econometrics, the line between a theorem's premise and a condition
   an estimator imposes matters (`hypothesis_of` vs `assumption_of`), and so does defining a concept versus computing
   it (`defined_via` vs `computed_from`). Even with the two new types, a fresh link run still used loose types for about a
   third of its edges (6 of 17 on the gap-check concepts), so link instructions must name the specific types first
   and critics should grade a loose type `weak` when a specific one fits. Run the edge-vocabulary check (count loose types and type fan-out) after the first link of
   every new course.
3. **Link only adds edges.** A relink with better types leaves the old edge next to its replacement, and two
   superseded `implies` edges formed a cycle. After any relink, look for node pairs joined by two edges, then remove
   and tombstone the stale one (`store.remove_item` plus `store.add_rejected`).
4. **One concept can hide two strengths of an assumption.** `exogeneity` carried both the per-observation condition
   and strict exogeneity, and edges that hold only for the stronger one. Critic notes of the form "needs the stronger
   version" mean the node should be split, not that the edge is wrong.
5. **Critic bookkeeping.** Each edge has one critic slot, and `collect critic --redo` overwrites all of them. Run
   `collect critic` without `--redo` after each drafting round; it picks up only edges with no verdict. Retyping an
   edge clears its verdict (the id changes), so every retype needs one more small critic round.
6. **Keep the critic independent of the drafter.** The rotation that worked: Gemini drafts (seed, fill, link), Codex
   critiques, and Claude reviews branches, designs vocabulary changes and retypes. Whoever proposed or retyped an
   item does not critique it. Errors concentrate in late, thinly sourced edges. The first pass flagged 3% of edges,
   while the gap-check edges had 44% flagged as weak or unsupported.
7. **Name similarity can merge distinct concepts.** "Distributed lag model" was merged into "Autoregressive
   distributed lag model": the token overlap is 3 of 4, and `similar_names` treats 0.75 as the same concept. The
   workaround was a distinct name (`distributed-lag-regression-model`). See Open.
8. **Rejecting an edge can orphan a concept.** `validate` warns, and `collect link --node <id> --redo` on the
   orphans fixes it.
9. **Publishing uses two repos.** The graph YAML and review history stay private, and the built page is copied into a
   public site repo. Two things go wrong:
   - `config/site.yaml` `repo:` must name the **public** site repo, or Submit review opens an issue form that
     reviewers cannot see. It now does, so `apply-review --from-issues` reads the site repo.
   - Landing graph commits does not refresh the page. The site still showed the `c2d4082` graph (84 concepts,
     80 edges) when the graph had 112 and 135. Run `build` after each landing round, copy `index.html` into the site repo and push. The owner
     does the push: the auto-mode classifier blocks Claude from pushing to the public repo.
10. **Operational traps (Windows).** PowerShell `Set-Content -Encoding utf8` writes a BOM, which the review-file
    loader rejects ("Unexpected UTF-8 BOM"); write JSON from Python or with `UTF8Encoding($false)`. The task produced
    19 graph worktrees in two days, so retire each one as soon as its branch lands. One worktree directory stayed
    locked by another process after `git worktree remove` unregistered it.

## Open

- **No retype or supersede command.** The retypes, the removal of superseded edges and the exogeneity split were done
  with throwaway scripts on `GraphStore`'s private `_files`/`_load`/`_save`. A `retype` command (new type, target or
  condition; clears the verdict; records provenance) and a `reject-edge` command would make this repeatable.
- **`similar_names` false merge** (lesson 7). A candidate rule: two names that differ by a non-generic word that is
  itself a technical qualifier (`autoregressive`, `cumulative`, `partial`, ...) are different concepts. The
  `QUALIFIERS` set in `proposals.py` is the place to add them; mirror the change in `viewer/logic.js`.
- **No publish helper.** A `publish --site-repo PATH` that builds, copies `index.html` and commits (leaving the push to
  the owner) would prevent a stale public page.
- **The syllabus check is manual.** A `collect gaps` stage could put the syllabus reading list and the node list on one
  card and ask for missing concepts as review-file proposals.
- The 4 weak verdicts from the last critic round (OLS variance `defined_on` OLS, multicollinearity `applies_to` OLS,
  Granger test `uses` F test, dynamic multiplier `defined_on` the distributed lag model) are left for the owner.
- One leftover, unregistered directory: `.worktrees/codex-econometrics-edge-corrections`, locked by a running process.
  Delete it once that process (likely an open terminal or IDE window) is closed.
