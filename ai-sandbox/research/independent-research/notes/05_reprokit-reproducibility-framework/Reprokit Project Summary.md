# Reprokit Project Summary

*Group F (new). Written 2026-11-05 from: the framework design spec (`docs/superpowers/specs/2026-10-31-reproducible-research-framework-design.md`, with its 2026-11-03 addendum), the core plan (`plans/2026-10-31-reprokit-core-plan.md`), the v0.3 handoff (`plans/2026-11-03-reprokit-v03-handoff.md`), the Pipeline Review in this folder's parent, the `reprokit` CHANGELOG (including the v0.3 branch), and the reprokit items in `academic-rag-model/docs/trackers/academic_hub_to_do.md`. The docs are in `ai-sandbox/research/independent-research/docs/superpowers/`, not in `academic-rag-model`; the only rag-model files that mention reprokit are the to-do tracker and a repo-hygiene handoff. There is no separate "status doc". Status here comes from the Pipeline Review, the CHANGELOG and the tracker. "(inference)" marks my own reading.*

## What it is
`reprokit` is a standalone MIT-licensed Python repo (`C:\Users\theaa\reprokit`, GitHub `AaronScherf/reprokit`) that holds the schemas, validators, a small CLI and a copier template for reproducible research repos. `compound-shocks-panel` (`C:\Users\theaa\compound-shocks-panel`, GitHub `AaronScherf/compound-shocks-panel`) is the first project built on it, and the test case. The design's intent: any outsider should be able to reproduce a study with one command, adapt it to another country or source, and see what a run did, without hidden coupling to the monorepo.

## The spec (design, 2026-10-31)
- **15 goals:** reproduce, adapt, compare, standalone, plug-and-play libraries, restricted data stays restricted, agent-accessible, cost-transparent, rights-safe, fits a meta-structure (3ie taxonomy), knows what it is for, plans end products, communicates as it goes, adaptable to future project kinds, derivable for other audiences.
- **Project kinds:** study repo, library repo, evidence/desk repo. Interactive-app and consulting-corpus kinds are designed for but not built.
- **Shared standard:** data descriptors, role-based inputs with one adapter per role, step graph, run manifest, a two-tier harmonization record (cosmetic changes are logged; structural ones block the run until written up), verification states, compute and agent profiles, an `AGENTS.md`, locked environments, and a project charter (`project.yaml`) with purpose, confidentiality class, audiences and deliverables.
- **Phases 0 to 16.** Schemas, template and validators come first, then the pilot, then Sudan, then review, then the taxonomy and communication hooks.
- **Anti-goals:** sprawling overlapping systems, hidden monorepo coupling, hard-coded paths, silent cross-source substitution, and a replication that needs an undeclared paid subscription.
- Owner decision recorded in the spec: no OSF project hub (OSF stops accepting new projects 2026-11-16).

## The core plan (2026-10-31)
Plan 1 of 3, covering reprokit itself in ten tasks: bootstrap, loader and schema validation, charter cross-field rules, descriptor and run-config schemas, harmonization gate, run manifest, compute and agent profiles, CLI, the copier template, and a clean-room check and release prep. Plan 2 is the Project 02 pilot; plan 3 is communication, derivative rules and the future-kind check. Constraints worth knowing: Python 3.11+, uv lockfile, tests under 30 seconds, no secrets, a warn-and-confirm rule for any spend over $1, role directories instead of hard-coded filenames, and modules kept near 150 lines or fewer.

## Status as of 2026-11-05
| Item | State |
|---|---|
| `reprokit` v0.1.0, v0.2.0 | Released 2026-10-31 (tagged) |
| `compound-shocks-panel` v0.1.0 to v0.1.2 | Built on reprokit v0.2.0; both countries reproduced byte for byte in fresh clones (one machine); CI passes on Windows and Linux |
| Phase A pipeline review (2026-11-03) | Strong on mechanical reproducibility and honest labelling; weak on claim validation, number drift, newcomer orientation and cheap proof of a clean run |
| `reprokit` v0.3.0 | Built on branch `codex/reprokit-v03-validate`, last commit `18edf92` (2026-11-05 20:43). A local `v0.3.0` tag exists. The CHANGELOG still says "Unreleased" and says the tag is only usable after you approve and publish. I did not check whether the tag has been pushed |
| Outside reproduction attempt | Deferred by decision on 2026-11-03, until the project holds data worth reproducing |
| Spec phases 12 to 16 | Not attempted (taxonomy hooks blocked on the 3ie taxonomy, `comms/`, derivative test, future-kind check) |

### What v0.3.0 adds (from the CHANGELOG)
- `reprokit quick-check`: runs a made-up-data check in under 60 seconds and explains PASS or FAIL. A PASS confirms the setup, not the research results.
- `write_run_summary` produces `RUN_SUMMARY.md` from measured per-step time, peak memory and output SHA-256 values, so no run figures are typed by hand.
- `validate` flags blank or placeholder licence terms and unverified access text on sources marked checked, and descriptor schema 0.2.0 checks coverage against the configured period and requires a verification note. The note check confirms text exists; it does not prove the claim.
- Charter schema 0.2.0 requires a `quick_check` line when a deliverable has a build. Schema 0.1.0 files still validate, with a notice.
- Template: rewritten README, working placeholder `quick_check.py`, starter unit test, Windows and Linux CI.

### The 10 items in the v0.3 handoff, against what the CHANGELOG shows
| # | Handoff item | In the v0.3 CHANGELOG? |
|---|---|---|
| 1 | `validate` checks claims, not just shape | Yes (licence/access placeholders, coverage, verification note) |
| 2 | Run card generated from the run | Yes (`RUN_SUMMARY.md`) |
| 3 | `smoke` command under 60 seconds | Yes (`quick-check`) |
| 5 | Measured cost against `compute.yaml` | Partly: measured time and memory are recorded; I didn't see a comparison to `compute.yaml` in the changelog |
| 4, 6, 7, 8, 9, 10 | Path drift, harmonization stub and second-source section, exploratory purpose, narrated `reproduce`, tested `pip` path, no empty scaffolding | Not mentioned (inference: not yet done) |

## Open work that touches other documents
Both are in the to-do tracker, added 2026-11-03:
1. Resolve five unverified licence fields in the `compound-shocks-panel` descriptors (PRMN, CHIRPS twice, IOM DTM, COD-PS). The v0.3 `validate` will fail on exactly these.
2. Adopt the v0.3 quick check and run summary in `compound-shocks-panel`, bump the pinned `reprokit`, and release it with item 1 as `v0.1.3` or `v0.2.0`.

A third tracker item (2026-11-02) evaluates splitting the monorepo, with reprokit and compound-shocks-panel as the first examples of independent repos.

## Decisions on record
- The original spec text is not edited; changes go in its addendum.
- The Somalia displacement flow and the Sudan stock stay separate.
- The `compound-shocks-panel` repo is changed only to bump the pinned reprokit version, and only if you ask.
- Tagging, pushing and releasing reprokit need your explicit approval.
- Phase B research work is out of scope for the framework.

## Open questions in the Pipeline Review
1. Which of the first three recommendations to do first (the review's order: claim checking, then generated numbers, then the smoke test; v0.3 appears to have done all three).
2. Amend the design doc with the second-source-type note, or keep it as the original intent (the addendum already records it).
3. Whether to attempt an outside reproduction before the next project.
