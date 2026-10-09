# Socratic Tutor Pipeline: Status Summary

Package: `agent/tutor/`. Spec: `docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md`. Plan: `docs/superpowers/plans/2026-10-08-socratic-tutor-pipeline.md`. Branch: `claude/socratic-tutor`.

## What shipped

The v1 session gate from the spec, implemented task by task with a test watched failing before each module:

- `events.py`, `paths.py`: append-only JSONL log (corruption raises with file and line) and vault layout.
- `fsm.py`: pure state machine and hint-level gating (level 3 needs two failed attempts at level 2).
- `ratings.py`: evidence-capped tri-axial rating; ratings above the ceiling are rejected, evidence must be an event id or a real student quote.
- `lint.py`: tutor-message lint (named techniques, notation bridging, sealed-solution phrases, leading sub-question lists, next-part mentions, LaTeX in chat) and glossary lint.
- `packet.py`, `prep.py`, `sample_packet.py`: packet model, validation, content hash marker (CRLF-insensitive), `prep-collect` / `prep-submit`.
- `render.py`, `profile.py`: transcript and four-part summary; versioned learner-gap profile.
- `session.py`, `audit.py`, `cli.py`, `bootstrap_prompt.md`: the stateless session, the audit, the command surface, and the agent's operating contract.
- Routing: `academic-rag-model/CLAUDE.md`, `docs/AGENT_ROUTING.md`, `agent/rag/README.md` and the package map now say which tutor to use for what.

Tests: `python -m pytest tests/agent/tutor -q` -> 97 passed. `tests/agent/tutor/test_tutor_regression.py` replays the five HW4 deviations; disabling the technique rule, the rating ceiling or the sealed-overlap rule each makes the matching test fail.

## Not validated

- No live Antigravity run yet. Whether Antigravity's workflow and shell-permission settings let the agent run the CLI every turn, and whether it follows the contract, is the open validation.
- `prep-collect` (Gemini query embedding for retrieval) has no automated test; `prep.collect` is tested with an injected `retrieve`.
- Lint thresholds (technique lexicon, two shared six-word phrases for sealed overlap) are tuned on fixtures only; the first real prep and session should add false-positive and false-negative cases.

## Known limits

Soft wall only: direct reads of `packet/sealed/` are undetectable, and `audit` flags the symptom (a reply with no `say`), not the read. Lexical lint cannot catch a paraphrased strategy hint. Intent labels are the agent's.

## What's next

1. Real prep plus a first live HW session on Antigravity; fold the findings back into lint cases and the bootstrap prompt.
2. Disentangle naming between this package and `agent/rag/` (pending to-do "Socratic Tutor vs RAG Tutor Disentanglement" in `docs/trackers/academic_hub_to_do.md`).
3. Spec §10.1: topic/timeframe review and study-guide walkthrough modes (new packet sources, configurable FSM states).
4. Spec §10.2: learning-progress tracker built on `learner_profile.json` (`schema_version` 1).
