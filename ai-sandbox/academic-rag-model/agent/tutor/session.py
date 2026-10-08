"""session.py -- ties the FSM, lint, ratings, packet and persistence together
(spec §3.2). Stateless: every method replays events.jsonl, so a CLI process
can exit between calls and state is identical on reload."""
from __future__ import annotations

import os
import re
from datetime import datetime

from agent.tutor import fsm
from agent.tutor.events import Event, EventLog
from agent.tutor.fsm import (
    AWAITING_ADVANCE, LAUNCH, SYNTHESIS, VERIFIED, WORKING, IllegalTransition,
    FsmState, replay, student_event,
)
from agent.tutor.lint import lint_message
from agent.tutor.packet import Packet, load_packet, read_sealed, sealed_section
from agent.tutor.paths import TutorPaths
from agent.tutor.profile import load_profile, open_gaps, save_profile, update_profile
from agent.tutor.ratings import validate_close_part
from agent.tutor.render import write_session_docs

_GUIDANCE = {
    LAUNCH: "Send ONLY the launch text via say. No hints, setup or roadmap. Then wait for the student.",
    SYNTHESIS: "All parts are closed. Write the big-picture synthesis and call end.",
    VERIFIED: "Confirm correctness without extending the solution. Call close-part, then say a check-in "
              "asking whether they have lingering questions or are ready to move on. Do not mention the next part.",
    AWAITING_ADVANCE: "Wait for the student. Answer their questions under the normal Socratic rules. "
                      "Never mention the next part until they confirm.",
}
_WORKING_GUIDANCE = {
    0: "Level 0: give minimal evaluative feedback on what the student wrote; ask what they are thinking. "
       "No hints, no proof technique, no leading sub-questions.",
    1: "Level 1: Socratic check only (what intuition or definition applies?). No direction yet.",
    2: "Level 2: a targeted nudge about analytical direction is allowed; still do not name a proof technique "
       "the student has not named.",
    3: "Level 3 (last resort): intermediate steps allowed. Keep them minimal; never quote the sealed solution.",
}


class Session:
    def __init__(self, paths: TutorPaths, session_id: str, packet: Packet):
        self.paths, self.session_id, self.packet = paths, session_id, packet
        self.dir = os.path.join(paths.sessions_dir, session_id)
        self.log = EventLog(os.path.join(self.dir, "events.jsonl"))
        self._hints, self._solution = read_sealed(paths.packet_dir)

    # ---- construction -------------------------------------------------
    @staticmethod
    def _is_open(paths: TutorPaths, sid: str) -> bool:
        events = EventLog(os.path.join(paths.sessions_dir, sid, "events.jsonl")).load()
        return bool(events) and not any(e.type == "session_end" for e in events)

    @classmethod
    def _latest_open(cls, paths: TutorPaths) -> str | None:
        if not os.path.isdir(paths.sessions_dir):
            return None
        for sid in sorted(os.listdir(paths.sessions_dir), reverse=True):
            if cls._is_open(paths, sid):
                return sid
        return None

    @classmethod
    def start(cls, paths: TutorPaths, now: datetime | None = None) -> "Session":
        packet = load_packet(paths)
        sid = cls._latest_open(paths)
        if sid is None:
            base = (now or datetime.now()).strftime("%Y-%m-%d-%H%M")
            sid, n = base, 1
            while os.path.exists(os.path.join(paths.sessions_dir, sid)):
                n += 1
                sid = f"{base}-{n}"
            session = cls(paths, sid, packet)
            session.log.append("session_start", part=packet.parts[0].part_id, state=LAUNCH,
                               data={"problem_set": paths.problem_set})
        else:
            session = cls(paths, sid, packet)
        session._write_prior_gaps()
        return session

    @classmethod
    def open(cls, paths: TutorPaths, session_id: str | None = None) -> "Session":
        packet = load_packet(paths)
        sid = session_id or cls._latest_open(paths)
        if sid is None:
            raise ValueError("no open session; run start first")
        return cls(paths, sid, packet)

    # ---- helpers ------------------------------------------------------
    def _prior_gaps(self) -> list[str]:
        tags = {t for p in self.packet.parts for t in p.concept_tags}
        return [g for g in open_gaps(load_profile(self.paths.profile_json)) if g in tags]

    def _write_prior_gaps(self) -> None:
        gaps = self._prior_gaps()
        text = "# Prior gaps (informational; never a source of hints)\n\n" + (
            "\n".join(f"- `{g}`" for g in gaps) if gaps else "- None") + "\n"
        with open(os.path.join(self.paths.packet_dir, "prior_gaps.md"), "w", encoding="utf-8") as f:
            f.write(text)

    def _fsm(self, events: list[Event] | None = None) -> FsmState:
        return replay(self.log.load() if events is None else events, len(self.packet.parts))

    def _guidance(self, s: FsmState) -> str:
        return _WORKING_GUIDANCE[s.hint_level] if s.state == WORKING else _GUIDANCE.get(s.state, "Session finished.")

    def view(self) -> dict:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        out = {"ok": True, "session": self.session_id, "state": s.state, "part_id": part.part_id,
               "part_index": s.part_index, "n_parts": len(self.packet.parts), "hint_level": s.hint_level,
               "guidance": self._guidance(s), "prior_gaps": self._prior_gaps()}
        if s.state == LAUNCH:
            out["launch_text"] = part.launch_text()
        return out

    @staticmethod
    def _closed(events: list[Event], part_id: str) -> bool:
        return any(e.type == "close_part" and e.part == part_id for e in events)

    # ---- commands -----------------------------------------------------
    def student(self, intent: str, text: str, misconceptions=(), admits_gap: str | None = None) -> dict:
        """misconceptions: iterable of (tag, axis) pairs, axis in conceptual|rigor|directness|all."""
        if not (text or "").strip():
            raise ValueError("student text is empty; log the student's verbatim message")
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        if intent == "confirm_advance" and s.state in (VERIFIED, AWAITING_ADVANCE) and not self._closed(events, part.part_id):
            raise IllegalTransition(f"call close-part for {part.part_id} before the student can advance")
        new, info = student_event(s, intent, len(self.packet.parts))
        part_id = self.packet.parts[new.part_index].part_id
        data = dict(info)
        if admits_gap:
            data.update(admits_gap=True, gap_axis=admits_gap)
        self.log.append("student", part=part_id, state=new.state, hint_level=new.hint_level,
                        intent=intent, text=text, data=data)
        for tag, axis in misconceptions:
            self.log.append("misconception", part=part_id, state=new.state, hint_level=new.hint_level,
                            data={"tag": tag, "axis": axis})
        return {**self.view(), "hint_capped": info["hint_capped"]}

    def say(self, text: str) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        part_events = [e for e in events if e.part == part.part_id]
        student_text = " ".join(e.text or "" for e in part_events if e.type == "student")
        allowed = [part.launch_text()] if s.state == LAUNCH else []
        last_student = next((e for e in reversed(events) if e.type == "student"), None)
        after_define = bool(last_student and last_student.intent == "define_request")
        if after_define:
            for e in reversed(events):
                if e.type == "define":
                    allowed.append(e.data["definition"])
                    break
                if e.type == "student":
                    break
        forbidden = []
        nxt = s.part_index + 1
        if s.state in (VERIFIED, AWAITING_ADVANCE) and nxt < len(self.packet.parts):
            n = self.packet.parts[nxt]
            forbidden = [rf"\b{re.escape(n.part_id)}\b"] + ([rf"\b{re.escape(n.label)}\b"] if n.label else [])
        solution = sealed_section(self._solution, part.part_id) or ""
        violations = lint_message(
            text, state=s.state, hint_level=s.hint_level, student_text=student_text, statement=part.statement,
            sealed_solution=solution, allowed_exact=allowed, after_define=after_define, forbidden_patterns=forbidden,
        )
        if violations:
            self.log.append("lint_reject", part=part.part_id, state=s.state, hint_level=s.hint_level, text=text,
                            data={"violations": [v.to_dict() for v in violations]})
            return {"ok": False, "violations": [v.to_dict() for v in violations],
                    "message": "Revise the draft and call say again. Send nothing to the student until it returns ok."}
        checkin = s.state == VERIFIED
        new = fsm.checkin_event(s) if checkin else s
        self.log.append("tutor_say", part=part.part_id, state=new.state, hint_level=new.hint_level, text=text,
                        data={"checkin": checkin})
        return {**self.view(), "send": text}

    def define(self, term: str) -> dict:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        for key, definition in self.packet.glossary.items():
            if key.lower() == term.strip().lower():
                self.log.append("define", part=part.part_id, state=s.state, hint_level=s.hint_level,
                                data={"term": key, "definition": definition})
                return {"ok": True, "term": key, "definition": definition}
        return {"ok": False, "error": f"no glossary entry for {term!r}",
                "terms": sorted(self.packet.glossary)}

    def sealed(self, kind: str) -> dict:
        if kind not in ("hint", "solution"):
            return {"ok": False, "error": "kind must be 'hint' or 'solution'"}
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        attempted = any(e.type == "student" and e.part == part.part_id and e.intent == "attempt" for e in events)
        if not attempted or s.state == LAUNCH:
            return {"ok": False, "error": "sealed content is released only after the student has logged an attempt on this part"}
        text = sealed_section(self._hints if kind == "hint" else self._solution, part.part_id)
        self.log.append("sealed", part=part.part_id, state=s.state, hint_level=s.hint_level, data={"kind": kind})
        return {"ok": True, "kind": kind, "part_id": part.part_id, "text": text,
                "warning": "internal verification only: never quote, summarize or outline this to the student"}

    def verdict(self, assessment: str, note: str = "") -> dict:
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        if not any(e.type == "student" and e.part == part.part_id and e.intent == "attempt" for e in events):
            raise IllegalTransition("record a student attempt before giving a verdict")
        new = fsm.verdict_event(s, assessment)
        self.log.append("verdict", part=part.part_id, state=new.state, hint_level=new.hint_level, text=note or None,
                        data={"assessment": assessment})
        return self.view()

    def misconception(self, tag: str, axis: str = "all", resolved: bool = False) -> dict:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        self.log.append("misconception_resolved" if resolved else "misconception", part=part.part_id,
                        state=s.state, hint_level=s.hint_level, data={"tag": tag, "axis": axis})
        return {"ok": True}

    def close_part(self, ratings: dict) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        if s.state not in (VERIFIED, AWAITING_ADVANCE):
            raise IllegalTransition(f"close-part is only valid once the part is verified (state is {s.state})")
        if self._closed(events, part.part_id):
            raise IllegalTransition(f"{part.part_id} is already closed")
        validate_close_part(ratings, [e for e in events if e.part == part.part_id])
        self.log.append("close_part", part=part.part_id, state=s.state, hint_level=s.hint_level,
                        data={"ratings": ratings})
        return self.view()

    def end(self, big_picture: str) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        if s.state != SYNTHESIS:
            raise IllegalTransition(f"cannot end from state {s.state}; finish and close every part first")
        missing = [p.part_id for p in self.packet.parts if not self._closed(events, p.part_id)]
        if missing:
            raise IllegalTransition(f"parts not closed: {missing}")
        last = self.packet.parts[-1].part_id
        self.log.append("synthesis", part=last, state=SYNTHESIS, text=big_picture)
        self.log.append("session_end", part=last, state=fsm.DONE)
        events = self.log.load()
        date = self.session_id[:10]
        transcript, summary = write_session_docs(self.dir, events, self.packet, big_picture, self._prior_gaps(), date)
        profile = update_profile(load_profile(self.paths.profile_json), session_id=self.session_id, date=date,
                                 events=events, packet=self.packet)
        save_profile(self.paths.profile_json, self.paths.profile_md, profile)
        return {"ok": True, "transcript": transcript, "summary": summary, "profile": self.paths.profile_json}
