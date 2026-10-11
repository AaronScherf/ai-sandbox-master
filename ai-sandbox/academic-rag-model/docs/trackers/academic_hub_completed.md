# Completed academic-hub tasks

This note keeps completed items from [the active to-do tracker](academic_hub_to_do.md).

When a task is complete, record its completion date under a `## YYYY-MM-DD` heading and move its entire `TODO-####` bullet here, including any continuation lines. Preserve its ID and original added date. Remove that bullet from the active tracker in the same reviewed Git change so the two notes stay in sync. Marking an item `done` in the local project-steering review page excludes it from recommendations, but does not move or delete its tracker text.

Do not infer completion from a commit or from a missing bullet. Check the item's actual outcome before archiving it.

## 2026-10-10

- <!-- TODO-0055 --> Paragraph-level splitting fallback for oversized sections: in `sections.py`, split oversized sections by paragraph boundaries when individual markdown sections exceed the TTS chunk limit, preventing oversized audio parts. (added 2026-10-04)
  - Completed 2026-10-10: oversized raw sections split at narration's paragraph/code-block boundaries; episode grouping enforces the target maximum when a boundary exists. `tests/audio_generator/test_sections.py` (16 passed) and the audio-generator suite (89 passed) verify the behavior. A single indivisible paragraph or post-narration expansion can still exceed the target; no live audio rerun was performed.
- <!-- TODO-0058 --> Flaky timing assertion under parallel test runs: `tests/audio_generator/test_audio_generator_pipeline.py::TestRunPipelineNotesEpisodes::test_episode_synthesis_is_dispatched_concurrently_not_one_at_a_time` asserts a wall-clock duration under 0.3s to prove synthesis calls run concurrently. It failed once at 0.36s when the full suite ran under `pytest-xdist -n auto`; it passes reliably alone and in a serial run. Found while measuring `pytest-xdist` for the agent git workflow's landing gate (`ai-sandbox/academic-rag-model/docs/superpowers/plans/2026-10-06-agent-git-workflow.md`, Task 6); not yet fixed since it's outside that work's package. Fix: replace the wall-clock threshold with a deterministic signal (e.g. recorded start/end timestamps on the mocked synthesis calls, asserting they overlap) so the test doesn't depend on machine load, or raise the threshold with a comment explaining why. (added 2026-10-07)
  - Completed in f7062e9: the test now verifies overlapping synthesis calls with a three-worker barrier. Focused, parallel, and full-suite checks passed.
