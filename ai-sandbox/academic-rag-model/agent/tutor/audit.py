# agent/tutor/audit.py  (replace the whole file)
"""audit.py -- re-lints a finished (or in-progress) session from its log (v1 spec §7,
v1.1 §10). The stand-in for the hard file-access wall the user declined: drift
becomes visible even when it was not blocked. UNANSWERED_STUDENT_TURN is a proxy for
'the agent replied without calling say' because the CLI cannot observe the chat.
It never decides whether an answer is correct."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor import fsm
from agent.tutor.events import Event
from agent.tutor.ledger import build_ledger
from agent.tutor.packet import Packet
from agent.tutor.ratings import RATINGS, ceiling
from agent.tutor.skip import mentions_skip

_CONFIRM_WORDS = re.compile(r"move on|next|ready|continue|go ahead|yes|\bok\b|okay|sure|proceed|done|good", re.I)
_STUCK_WORDS = re.compile(r"stuck|help|hint|don't know|do not know|not sure|no idea|lost|confus", re.I)


def _mention(part) -> re.Pattern:
    alts = [rf"\b{re.escape(part.part_id)}\b"]
    if part.label:
        alts.append(re.escape(part.label) + r"(?!\d|\.\d)")
        tail = part.label.split()[-1]
        if any(ch.isdigit() for ch in tail):
            alts.append(rf"(?<![\d.]){re.escape(tail)}(?!\d)")
    return re.compile("|".join(alts), re.I)


@dataclass(frozen=True)
class Finding:
    code: str
    event_id: int
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "event_id": self.event_id, "detail": self.detail}


def audit(events: list[Event], packet: Packet) -> list[Finding]:
    found: list[Finding] = []
    prev_part, prev_level = None, 0
    pending: Event | None = None
    move_ok = False
    for e in events:
        mover = e.type == "student" and (e.intent in ("confirm_advance", "revisit") or e.data.get("skip_ended"))
        if e.part and prev_part and e.part != prev_part:
            if not (mover or move_ok):
                found.append(Finding("ADVANCE_WITHOUT_CONFIRM", e.id, f"moved from {prev_part} to {e.part} without a student confirm_advance, revisit or second skip request"))
            move_ok = False
        if mover and e.data.get("skip_ended"):
            move_ok = True                                  # the next event is logged under the new part
        if e.part and e.part == prev_part and e.hint_level > prev_level:
            ok = e.type == "student" and e.intent in ("stuck", "hint_request") and e.hint_level - prev_level == 1
            if not ok:
                found.append(Finding("HINT_JUMP", e.id, f"hint level rose {prev_level}->{e.hint_level} without a single-step student request"))
        if e.part:
            prev_part, prev_level = e.part, e.hint_level
        if e.type == "sealed":          # v1 logs only
            attempted = any(x.type == "student" and x.part == e.part and x.intent == "attempt" and x.id < e.id for x in events)
            if not attempted:
                found.append(Finding("SEALED_EARLY", e.id, "sealed content released before any student attempt on this part"))
        if e.type == "verify_release":
            pc = packet.claims.get(e.part) if packet.claims else None
            if pc is not None:
                before = [x for x in events if x.part == e.part and x.id < e.id]
                if not build_ledger(pc, before).covered:
                    found.append(Finding("VERIFY_WITHOUT_COVERAGE", e.id, "the solution was released before a route was covered"))
        if e.type == "part_status":
            if e.data.get("skip_requests", 2) < 2:
                found.append(Finding("SKIP_TOO_EARLY", e.id, f"{e.part} was parked after fewer than two skip requests"))
            first = next((x for x in events if x.type == "student" and x.part == e.part and x.data.get("skip") and x.id < e.id
                          and x.data.get("skip_count") == 1), None)
            ending = next((x for x in reversed(events) if x.type == "student" and x.id < e.id and x.data.get("skip_ended")), None)
            if first is not None and ending is not None and not any(
                    x.type == "tutor_say" and first.id < x.id < ending.id for x in events):
                found.append(Finding("SKIP_WITHOUT_NUDGE", e.id, "no tutor reply between the first and the ending skip request"))
        if e.type == "student" and e.state in (fsm.WORKING, fsm.LAUNCH) and not e.data.get("skip") \
                and e.intent not in ("confirm_advance", "define_request", "revisit") and mentions_skip(e.text):
            found.append(Finding("SKIP_PHRASE_UNCOUNTED", e.id, "the message mentions skipping or moving on but was not counted as a skip request"))
        if e.type == "tutor_say":
            try:
                before = fsm.replay([x for x in events if x.id < e.id], len(packet.parts))
            except fsm.IllegalTransition:
                before = None
            if before is not None:
                if e.data.get("checkin") or before.state == fsm.SYNTHESIS:
                    for i in fsm.offerable(before):
                        p = packet.parts[i]
                        if not _mention(p).search(e.text or ""):
                            found.append(Finding("REVISIT_OFFER_MISSING", e.id, f"the message did not offer to go back to {p.label or p.part_id}"))
                if before.state == fsm.WORKING:
                    for i in before.queue:
                        if _mention(packet.parts[i]).search(e.text or ""):
                            found.append(Finding("REVISIT_MID_PART", e.id, f"{packet.parts[i].label or packet.parts[i].part_id} was brought up while another part was being worked"))
                            break
        if e.type == "establish":
            found.append(Finding("MANUAL_OVERRIDE", e.id, f"claim {e.data.get('claim')} was established manually (quote: {e.data.get('quote')!r})"))
        if e.type in ("misconception", "misconception_resolved") and e.data.get("manual"):
            found.append(Finding("MANUAL_OVERRIDE", e.id, f"{e.type.replace('_', ' ')} '{e.data.get('tag')}' was entered manually (quote: {e.data.get('quote')!r})"))
        if e.type == "student":
            if e.intent == "confirm_advance" and not _CONFIRM_WORDS.search(e.text or ""):
                found.append(Finding("INTENT_MISMATCH", e.id, "labelled confirm_advance but the text does not ask to move on"))
            if e.intent in ("stuck", "hint_request") and not _STUCK_WORDS.search(e.text or ""):
                found.append(Finding("INTENT_MISMATCH", e.id, f"labelled {e.intent} but the text does not ask for help"))
            if pending is not None:
                found.append(Finding("UNANSWERED_STUDENT_TURN", pending.id, "no tutor say before the next student turn"))
            pending = None if e.state == "SYNTHESIS" else e
        elif e.type == "tutor_say":
            pending = None
        elif e.type == "close_part":
            part_events = [x for x in events if x.part == e.part and x.id < e.id]
            for axis, r in e.data["ratings"].items():
                cap, _ = ceiling(part_events, axis)
                if RATINGS.index(r["rating"]) > RATINGS.index(cap):
                    found.append(Finding("RATING_OVER_CEILING", e.id, f"{axis}: {r['rating']} exceeds ceiling {cap}"))
    if pending is not None and any(x.type == "session_end" for x in events):
        found.append(Finding("UNANSWERED_STUDENT_TURN", pending.id, "session ended with an unanswered student turn"))
    return found
