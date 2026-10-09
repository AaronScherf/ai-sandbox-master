# agent/tutor/ledger.py
"""ledger.py -- which claims the student has established, which pitfalls they
hit, and whether a route is complete (spec §4). Pure functions over the event
log: the same events always give the same ledger, so a CLI restart cannot
change it."""
from __future__ import annotations

from dataclasses import dataclass

from agent.tutor.claims import Claim, PartClaims
from agent.tutor.events import Event

IGNORED_INTENTS = frozenset({"confirm_advance", "define_request"})


@dataclass
class PartLedger:
    established: list
    manual: list
    pitfalls_hit: list
    route_progress: dict
    covered_route: str | None
    final_answer_ok: bool

    @property
    def covered(self) -> bool:
        return self.covered_route is not None and self.final_answer_ok


def build_ledger(pc: PartClaims, part_events: list[Event], extra_student_text: str | None = None) -> PartLedger:
    sequence = []
    for e in part_events:
        if e.type == "student" and e.intent not in IGNORED_INTENTS:
            sequence.append(("text", e.text or ""))
        elif e.type == "establish":
            sequence.append(("claim", e.data["claim"]))
    if extra_student_text is not None:
        sequence.append(("text", extra_student_text))
    established, manual, hit = [], [], []
    final_ok = pc.final_answer is None
    for kind, value in sequence:
        if kind == "claim":
            if value not in established:
                established.append(value)
                manual.append(value)
            continue
        for c in pc.claims:
            if c.id not in established and c.recognizer.matches(value):
                established.append(c.id)
        for p in pc.pitfalls:
            if p.id not in hit and p.recognizer.matches(value):
                hit.append(p.id)
        if pc.final_answer is not None and pc.final_answer.matches(value):
            final_ok = True
    progress = {r: (sum(1 for c in ids if c in established), len(ids)) for r, ids in pc.routes.items()}
    covered = next((r for r, (n, total) in progress.items() if n == total), None)
    return PartLedger(established, manual, hit, progress, covered, final_ok)


def next_claim(pc: PartClaims, ledger: PartLedger) -> Claim | None:
    if ledger.covered_route is not None:
        return None
    best = max(pc.routes, key=lambda r: ledger.route_progress[r][0])   # max() keeps the first on ties
    by_id = {c.id: c for c in pc.claims}
    for cid in pc.routes[best]:
        if cid not in ledger.established:
            return by_id[cid]
    return None
