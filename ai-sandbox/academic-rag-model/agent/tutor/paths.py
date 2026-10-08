"""paths.py -- where the Socratic tutor keeps everything in the vault
(spec: docs/superpowers/specs/2026-10-08-socratic-tutor-pipeline-design.md §3.1, §6)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TutorPaths:
    hub_root: str
    course: str
    problem_set: str

    @property
    def tutoring_dir(self) -> str:
        return os.path.join(self.hub_root, "academic_notes", self.course, "tutoring")

    @property
    def problem_set_dir(self) -> str:
        return os.path.join(self.tutoring_dir, self.problem_set)

    @property
    def packet_dir(self) -> str:
        return os.path.join(self.problem_set_dir, "packet")

    @property
    def sessions_dir(self) -> str:
        return os.path.join(self.problem_set_dir, "sessions")

    @property
    def profile_json(self) -> str:
        return os.path.join(self.tutoring_dir, "learner_profile.json")

    @property
    def profile_md(self) -> str:
        return os.path.join(self.tutoring_dir, "learner_profile.md")
