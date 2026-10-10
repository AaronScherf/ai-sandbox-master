# agent/tutor/session.py  (replace the whole file)
"""session.py -- ties the FSM, ledger, lint, ratings, packet and persistence together
(v1.1 §4-§7). Stateless: every method replays events.jsonl, so a CLI process can exit
between calls and state is identical on reload."""
from __future__ import annotations

import os
import re
from datetime import datetime

from agent.tutor import fsm
from agent.tutor.claims import AXES_ALL, tokenize
from agent.tutor.events import Event, EventLog
from agent.tutor.fsm import (
    AWAITING_ADVANCE, LAUNCH, PAUSED, SYNTHESIS, VERIFIED, WORKING, FsmState, IllegalTransition, fresh_index,
    offerable, replay, status_of, student_event,
)
from agent.tutor.ledger import IGNORED_INTENTS, build_ledger, next_claim
from agent.tutor.lint import Violation, lint_message
from agent.tutor.packet import Packet, load_packet, read_solution, sealed_section
from agent.tutor.paths import TutorPaths
from agent.tutor.profile import load_profile, open_gaps, save_profile, update_profile
from agent.tutor.ratings import build_ratings
from agent.tutor.render import write_session_docs
from agent.tutor.skip import counts_as_skip, is_real_attempt

CHECK_STATUSES = ("confirmed", "missing", "wrong")

_NEXT = {
    LAUNCH: ["say (send the launch line)", "turn (once the student replies)"],
    WORKING: ["turn (the student's next message)", "say (your reply)", "verify (only when verify_available is true)"],
    VERIFIED: ["say (the check-in question)"],
    AWAITING_ADVANCE: ["turn (the student's reply)", "say (answer a question)"],
    SYNTHESIS: ["say (closing message)", "end --big-picture-file F"],
    fsm.PAUSED: ["start (resume)", "start --fresh"],
}
_LEVEL_RULES = {
    0: "Level 0: no hints. Ask what the student is thinking.",
    1: "Level 1: a Socratic check only (what definition or intuition applies?). No direction yet.",
    2: "Level 2: you may point at the object to think about (see object_terms) but not the relation or computation.",
    3: "Level 3 (last resort): you may state the next claim (next_claim_text) and nothing beyond it.",
}


class Refused(ValueError):
    """A command the gate will not run now; carries the legal next commands."""

    def __init__(self, message: str, next_commands):
        super().__init__(message)
        self.next_commands = list(next_commands)


def _norm(text: str | None) -> str:
    return " ".join((text or "").split())


MIN_QUOTE_TOKENS = 3
MAX_ACK_WORDS = 20


def _quote_ok(quote: str | None, texts: list[str]) -> bool:
    """A quote must appear in the student's own words and carry real content: at least MIN_QUOTE_TOKENS
    words, or be the student's whole (shorter) message. `texts` are whitespace-normalized student messages."""
    q = _norm(quote)
    if not q or not any(q in t for t in texts):
        return False
    return len(tokenize(q)) >= MIN_QUOTE_TOKENS or q in texts


def split_steps(section: str) -> list[str]:
    lines = section.splitlines()
    heading = re.compile(r"^#{3,}\s")
    if any(heading.match(l) for l in lines):
        steps, cur = [], []
        for line in lines:
            if heading.match(line) and cur:
                steps.append("\n".join(cur).strip())
                cur = [line]
            else:
                cur.append(line)
        steps.append("\n".join(cur).strip())
        return [s for s in steps if s]
    return [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]


def _parked(packet, indices, s=None):
    return [{"part_id": packet.parts[i].part_id, "label": packet.parts[i].label or packet.parts[i].part_id,
             "status": (status_of(s, i) if s is not None else None)} for i in indices]


def _mention(part) -> re.Pattern:
    """Matches the part by id, by label, or by the number at the end of its label ("1.2")."""
    alts = [rf"\b{re.escape(part.part_id)}\b"]
    if part.label:
        alts.append(re.escape(part.label) + r"(?!\d|\.\d)")
        tail = part.label.split()[-1]
        if any(ch.isdigit() for ch in tail):
            alts.append(rf"(?<![\d.]){re.escape(tail)}(?!\d)")
    return re.compile("|".join(alts), re.I)


class Session:
    def __init__(self, paths: TutorPaths, session_id: str, packet: Packet):
        self.paths, self.session_id, self.packet = paths, session_id, packet
        self.dir = os.path.join(paths.sessions_dir, session_id)
        self.log = EventLog(os.path.join(self.dir, "events.jsonl"))
        self._solution = read_solution(paths.packet_dir)

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
    def start(cls, paths: TutorPaths, now: datetime | None = None, fresh: bool = False) -> "Session":
        packet = load_packet(paths)
        sid = cls._latest_open(paths)
        if sid is not None and fresh:
            cls(paths, sid, packet)._end_partial()
            sid = None
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
            s = session._fsm()
            if s.state == fsm.PAUSED:
                back = fsm.resume_event(s)
                session.log.append("resumed", part=packet.parts[s.part_index].part_id, state=back.state,
                                   hint_level=back.hint_level)
        session._write_prior_gaps()
        return session

    @classmethod
    def open(cls, paths: TutorPaths, session_id: str | None = None) -> "Session":
        packet = load_packet(paths)
        sid = session_id or cls._latest_open(paths)
        if sid is None:
            raise ValueError("no open session; run start first")
        return cls(paths, sid, packet)

    @staticmethod
    def latest_session_id(paths: TutorPaths) -> str | None:
        """Newest session directory with a log, open or finished (the audit is most useful after `end`)."""
        if not os.path.isdir(paths.sessions_dir):
            return None
        ids = sorted(d for d in os.listdir(paths.sessions_dir)
                     if os.path.exists(os.path.join(paths.sessions_dir, d, "events.jsonl")))
        return ids[-1] if ids else None

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

    @staticmethod
    def _require_live(s: FsmState) -> None:
        if s.state == fsm.DONE:
            raise Refused("session has ended; start a new session", ["start"])
        if s.state == fsm.PAUSED:
            raise Refused("session is paused; run start to resume it, or start --fresh to begin a new one",
                          ["start", "start --fresh"])

    @staticmethod
    def _part_events(events: list[Event], part_id: str) -> list[Event]:
        return [e for e in events if e.part == part_id]

    @staticmethod
    def _closed(events: list[Event], part_id: str) -> bool:
        return any(e.type == "close_part" and e.part == part_id for e in events)

    @staticmethod
    def _released(pe: list[Event]) -> bool:
        return any(e.type == "verify_release" for e in pe)

    @staticmethod
    def _unresolved(pe: list[Event]) -> list[Event]:
        resolved = {e.data["tag"] for e in pe if e.type == "misconception_resolved"}
        seen, out = set(), []
        for e in pe:
            tag = e.data.get("tag") if e.type == "misconception" else None
            if tag and tag not in resolved and tag not in seen:
                out.append(e)
                seen.add(tag)
        return out

    @staticmethod
    def _attempt_no(pe: list[Event]) -> int:
        return 1 + sum(1 for e in pe if e.type == "student" and e.intent == "revisit")

    def _form_active(self, s: FsmState, pe: list[Event]) -> bool:
        return s.state == WORKING and (s.hint_level <= 1 or (self._released(pe) and s.hint_level < 3))

    def _rules(self, s: FsmState, ledger, unresolved: list[Event], form: bool, extra=()) -> str:
        return " ".join([self._rules_base(s, ledger, unresolved, form), *extra])

    def _rules_base(self, s: FsmState, ledger, unresolved: list[Event], form: bool) -> str:
        if s.state == LAUNCH:
            return "Send launch_text through say, then wait for the student."
        if s.state == SYNTHESIS:
            return "All parts are closed. Write the big-picture synthesis and run end."
        if s.state == VERIFIED:
            return ("The part is closed. Say the check-in: ask whether they have lingering questions or are ready to "
                    "move on. Do not mention the next part.")
        if s.state == AWAITING_ADVANCE:
            return ("Answer any question briefly under the usual rules. Do not mention the next part until the "
                    "student asks to move on.")
        bits = []
        if unresolved:
            bits.append("First surface the slip Socratically with the repair_question in pitfalls_hit; do not state the correction.")
        bits.append(_LEVEL_RULES[s.hint_level])
        if form:
            bits.append("Reply with at most ONE question (60 words max) plus at most one sentence restating the "
                        "student's own words; introduce no idea the student has not said.")
        if ledger.covered:
            bits.append("Every claim on a route is established: call verify.")
        return " ".join(bits)

    def _brief(self, events: list[Event] | None = None, definition: str | None = None) -> dict:
        events = self.log.load() if events is None else events
        s = self._fsm(events)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        ledger = build_ledger(pc, pe)
        unresolved = self._unresolved(pe)
        by_tag = {p.tag: p for p in pc.pitfalls}
        last_student = next((e for e in reversed(events) if e.type == "student"), None)
        answered = last_student is not None and any(e.type == "tutor_say" and e.id > last_student.id for e in events)
        extra = []
        nudge = (s.state == WORKING and s.skip_requests == 1 and last_student is not None
                 and last_student.data.get("skip") and not answered)
        if nudge:
            extra.append("The student asked to skip. Do NOT agree or move on, and do not mention the next question. "
                         "Reply with ONE question that invites them to try a first step. If they ask again, the "
                         "part is parked and can be revisited later.")
        parked_now = None
        if s.state == LAUNCH and last_student is not None and last_student.data.get("skip_ended") and not answered:
            idx = next(i for i, p in enumerate(self.packet.parts) if p.part_id == last_student.part)
            parked_now = _parked(self.packet, [idx], s)[0]
            extra.append("The previous question is parked. Send launch_text through say; you may put ONE short "
                         "sentence (max 20 words, no question, no content) before it saying the earlier question "
                         "can be revisited later.")
        offer = list(offerable(s))
        if offer:
            names = ", ".join(self.packet.parts[i].label or self.packet.parts[i].part_id for i in offer)
            extra.append(f"Parked earlier: {names}. Your message must also offer to go back to "
                         f"{'it' if len(offer) == 1 else 'them'} (name it); do not name the next question.")
        if s.state in (AWAITING_ADVANCE, SYNTHESIS) and s.queue:
            extra.append("If the student wants to go back, run turn --intent revisit --part <part_id> (a parked part "
                         "from revisit_options). If they want to move on, label it confirm_advance."
                         if s.state == AWAITING_ADVANCE else
                         "Offer the parked parts once more in the closing message; if the student declines, run end.")
        attempt_no = self._attempt_no(pe)
        if s.state == WORKING and attempt_no > 1:
            extra.append(f"This is a revisit (attempt {attempt_no}); the earlier work still counts. Hint level is "
                         f"restored to {s.hint_level}.")
        out = {
            "ok": True, "session": self.session_id, "state": s.state, "part_id": part.part_id,
            "label": part.label or part.part_id, "part_index": s.part_index, "n_parts": len(self.packet.parts),
            "hint_level": s.hint_level, "statement": part.statement, "chat_statement": part.chat_statement,
            "claims_established": ledger.established,
            "route_coverage": {r: f"{n}/{total}" for r, (n, total) in ledger.route_progress.items()},
            "pitfalls_hit": [{"tag": e.data["tag"],
                              "repair_question": by_tag[e.data["tag"]].repair_question if e.data["tag"] in by_tag else None}
                             for e in unresolved],
            "verify_available": s.state == WORKING and ledger.covered,
            "solution_released": self._released(pe),
            "rules": self._rules(s, ledger, unresolved, self._form_active(s, pe), extra),
            "next": _NEXT.get(s.state, []), "prior_gaps": self._prior_gaps(),
        }
        if events and events[-1].type == "resumed":
            out["resumed"] = True
        out["skip_requests"] = s.skip_requests
        out["attempt"] = attempt_no
        out["deferred_queue"] = _parked(self.packet, s.queue, s)
        if offer:
            out["revisit_offer"] = _parked(self.packet, offer, s)
        if s.state in (AWAITING_ADVANCE, SYNTHESIS) and s.queue:
            out["revisit_options"] = _parked(self.packet, s.queue, s)
        if parked_now:
            out["parked"] = parked_now
        if s.state == LAUNCH:
            out["launch_text"] = part.launch_text()
        nxt = next_claim(pc, ledger)
        if s.state == WORKING and nxt is not None:
            if s.hint_level == 2:
                out["object_terms"] = list(nxt.object_terms)
            if s.hint_level >= 3:
                out["next_claim_text"] = nxt.text
        if definition:
            out["definition"] = definition
        return out

    def view(self) -> dict:
        return self._brief()

    # ---- turn ---------------------------------------------------------
    def turn(self, intent: str, text: str, *, admits_gap: str | None = None, establish: str | None = None,
             establish_quote: str | None = None, flag_slip: str | None = None, slip_quote: str | None = None,
             resolve: str | None = None, resolve_quote: str | None = None, define_term: str | None = None, skip: bool = False,
             revisit_part: str | None = None) -> dict:
        if not (text or "").strip():
            raise ValueError("student text is empty; pass the student's verbatim message")
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        virtual = None if intent in IGNORED_INTENTS else text
        prev = build_ledger(pc, pe)
        now = build_ledger(pc, pe, extra_student_text=virtual)
        newly = [c for c in now.established if c not in prev.established]
        new_pitfalls = [p.id for p in pc.pitfalls if p.id in now.pitfalls_hit and p.id not in prev.pitfalls_hit]
        skip_now = counts_as_skip(intent, text, skip, s.state in (LAUNCH, WORKING))
        real = is_real_attempt(intent, text, bool(newly or new_pitfalls), admits_gap is not None)
        target = self._resolve_revisit(s, intent, revisit_part)

        manual = any(x is not None for x in (establish, flag_slip, resolve))
        if manual and intent == "confirm_advance":
            raise ValueError("manual establish / flag-slip / resolve cannot be combined with confirm_advance")
        texts = [_norm(e.text) for e in pe if e.type == "student"] + [_norm(text)]
        quote_ok = lambda q: _quote_ok(q, texts)
        if admits_gap is not None and admits_gap not in AXES_ALL:
            raise ValueError(f"--admits-gap must be one of {list(AXES_ALL)}, got {admits_gap!r}")
        if flag_slip is not None and (flag_slip.partition(":")[2] or "all") not in AXES_ALL:
            raise ValueError(f"--flag-slip axis must be one of {list(AXES_ALL)}")
        if establish is not None:
            if establish not in {c.id for c in pc.claims}:
                raise ValueError(f"unknown claim id {establish!r}; known ids: {sorted(c.id for c in pc.claims)}")
            if not quote_ok(establish_quote):
                raise ValueError("--establish needs --establish-quote: at least 3 words the student actually wrote in this part (or their whole message if it is shorter)")
        if flag_slip is not None and not quote_ok(slip_quote):
            raise ValueError("--flag-slip needs --slip-quote: at least 3 words the student actually wrote in this part (or their whole message if it is shorter)")
        if resolve is not None:
            if resolve not in {e.data["tag"] for e in self._unresolved(pe)}:
                raise ValueError(f"no unresolved misconception tagged {resolve!r}")
            if not quote_ok(resolve_quote):
                raise ValueError("--resolve needs --resolve-quote: at least 3 words the student actually wrote in this part (or their whole message if it is shorter)")

        try:
            new, info = student_event(s, intent, len(self.packet.parts), bool(newly),
                                      skip=skip_now, real_attempt=real, revisit=target)
        except IllegalTransition as err:
            extra = " Run verify first; a clean verify closes the part." if s.state == WORKING and prev.covered else ""
            raise Refused(str(err) + extra, _NEXT.get(s.state, [])) from err

        part_id = part.part_id if info.get("skip_ended") else self.packet.parts[new.part_index].part_id
        data = dict(info)
        data["made_progress"] = bool(newly)
        data["established"] = newly
        data["real_attempt"] = real
        if skip_now:
            data["skip"] = True
        if target is not None:
            data["revisit"] = target
            data["revisit_part"] = self.packet.parts[target].part_id
        if admits_gap:
            data.update(admits_gap=True, gap_axis=admits_gap)
        student_ev = self.log.append("student", part=part_id, state=new.state, hint_level=new.hint_level,
                                     intent=intent, text=text, data=data)
        if part_id == part.part_id:
            common = dict(part=part_id, state=new.state, hint_level=new.hint_level)
            for p in pc.pitfalls:
                if p.id in now.pitfalls_hit and p.id not in prev.pitfalls_hit and virtual is not None:
                    self.log.append("misconception", data={"tag": p.tag, "axis": p.axis, "pitfall": p.id,
                                                           "msg": student_ev.id}, **common)
            if establish is not None:
                self.log.append("establish", data={"claim": establish, "quote": establish_quote}, **common)
            if flag_slip is not None:
                tag, _, axis = flag_slip.partition(":")
                self.log.append("misconception", data={"tag": tag, "axis": axis or "all", "manual": True,
                                                       "quote": slip_quote, "msg": student_ev.id}, **common)
            if resolve is not None:
                self.log.append("misconception_resolved", data={"tag": resolve, "axis": "all", "manual": True,
                                                                "quote": resolve_quote}, **common)
            self._auto_resolve(part, pc, new)
            if info.get("skip_ended"):
                self.log.append("part_status", part=part.part_id, state=new.state, hint_level=s.hint_level,
                                data={"status": info["part_status"], "attempt": self._attempt_no(pe),
                                      "real_attempt": info["had_real_attempt"], "skip_requests": info["skip_count"]})

        definition, definition_error = None, None
        if define_term:
            for key, d in self.packet.glossary.items():
                if key.lower() == define_term.strip().lower():
                    definition = d
                    self.log.append("define", part=part_id, state=new.state, hint_level=new.hint_level,
                                    data={"term": key, "definition": d})
                    break
            else:
                definition_error = f"no glossary entry for {define_term!r}"
        brief = self._brief(definition=definition)
        if definition_error:
            brief["definition_error"] = definition_error
            brief["terms"] = sorted(self.packet.glossary)
        return brief

    def _resolve_revisit(self, s: FsmState, intent: str, ref: str | None) -> int | None:
        if intent != "revisit":
            if ref:
                raise ValueError("--part is only used with --intent revisit")
            return None
        if s.state not in (AWAITING_ADVANCE, SYNTHESIS):
            return None                                   # the FSM explains why
        names = ", ".join(f"{p['part_id']} ({p['label']})" for p in _parked(self.packet, s.queue))
        if not s.queue:
            raise Refused("no parts are parked, so there is nothing to go back to", _NEXT.get(s.state, []))
        if ref is None:
            if len(s.queue) == 1:
                return s.queue[0]
            raise Refused(f"several parts are parked: {names}; pass --part with one of these ids",
                          ["turn --intent revisit --part <part_id> --stdin"])
        key = _norm(ref).lower()
        for i in s.queue:
            p = self.packet.parts[i]
            label = (p.label or "").lower()
            if key in (p.part_id.lower(), label, label.rsplit(" ", 1)[-1]):
                return i
        raise Refused(f"{ref!r} is not a parked part; parked: {names}", ["turn --intent revisit --part <part_id> --stdin"])

    def _auto_resolve(self, part, pc, st: FsmState) -> None:
        pe = self._part_events(self.log.load(), part.part_id)
        by_tag = {p.tag: p for p in pc.pitfalls}
        for e in self._unresolved(pe):
            p = by_tag.get(e.data["tag"])
            msg = e.data.get("msg")
            if p is None or not p.resolved_by or msg is None:
                continue
            after = build_ledger(pc, [x for x in pe if x.id >= msg])
            if p.resolved_by in after.established:
                self.log.append("misconception_resolved", part=part.part_id, state=st.state, hint_level=st.hint_level,
                                data={"tag": p.tag, "axis": p.axis, "auto": True})

    # ---- say ----------------------------------------------------------
    def say(self, text: str, check: bool = False) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        ledger = build_ledger(pc, pe)
        student_text = " ".join(e.text or "" for e in pe if e.type == "student")
        last_student = next((e for e in reversed(events) if e.type == "student"), None)
        last_text = (last_student.text or "") if last_student else ""
        allowed = [part.launch_text()] if s.state == LAUNCH else []
        after_define = bool(last_student and last_student.intent == "define_request")
        if after_define:
            for e in reversed(events):
                if e.type == "define":
                    allowed.append(e.data["definition"])
                    break
                if e.type == "student":
                    break
        nxt_index = fsm.fresh_index(s)
        nudge = bool(last_student and last_student.data.get("skip") and not last_student.data.get("skip_ended")
                     and s.state == WORKING and not any(e.type == "tutor_say" and e.id > last_student.id for e in events))
        forbidden = []
        if (s.state in (VERIFIED, AWAITING_ADVANCE) or nudge) and nxt_index < len(self.packet.parts):
            n = self.packet.parts[nxt_index]
            forbidden = [rf"\b{re.escape(n.part_id)}\b"] + ([rf"\b{re.escape(n.label)}\b"] if n.label else [])
        blocked = {}
        if s.state == WORKING:
            nc = next_claim(pc, ledger)
            for c in pc.claims:
                if c.id in ledger.established or (s.hint_level >= 3 and nc is not None and c.id == nc.id):
                    continue
                blocked[c.id] = c.recognizer
        offer_parts = [self.packet.parts[i] for i in fsm.offerable(s)]
        must = [(p.label or p.part_id, _mention(p)) for p in offer_parts]
        queued = [(self.packet.parts[i].label or self.packet.parts[i].part_id, _mention(self.packet.parts[i])) for i in s.queue]
        ack_issues: list[Violation] = []
        if s.state == LAUNCH and last_student and last_student.data.get("skip_ended"):
            ack_issues = self._ack_issues(text, part, last_student.part)
            if not ack_issues and _norm(text) != _norm(part.launch_text()) and _norm(text).endswith(_norm(part.launch_text())):
                allowed.append(text)
        violations = lint_message(
            text, state=s.state, hint_level=s.hint_level, student_text=student_text, statement=part.statement,
            sealed_solution=sealed_section(self._solution, part.part_id) or "", allowed_exact=allowed,
            after_define=after_define, forbidden_patterns=forbidden, blocked_claims=blocked,
            form=self._form_active(s, pe), last_student_text=last_text,
            skip_nudge=nudge, must_mention=must, queued_patterns=queued,
        ) + ack_issues
        if violations:
            payload = [v.to_dict() for v in violations]
            if not check:
                self.log.append("lint_reject", part=part.part_id, state=s.state, hint_level=s.hint_level, text=text,
                                data={"violations": payload})
            return {"ok": False, "violations": payload,
                    "message": "Revise the draft and call say again. Send nothing to the student until it returns ok."}
        if check:
            return {"ok": True, "checked": True}
        checkin = s.state == VERIFIED
        new = fsm.checkin_event(s) if checkin else s
        self.log.append("tutor_say", part=part.part_id, state=new.state, hint_level=new.hint_level, text=text,
                        data={"checkin": checkin, "offer": [p.part_id for p in offer_parts]})
        return {**self._brief(), "send": text}

    def _ack_issues(self, text: str, part, parked_id: str) -> list[Violation]:
        launch, full = _norm(part.launch_text()), _norm(text)
        if not full.endswith(launch) or full == launch:
            return []                                              # plain LAUNCH_NOT_VERBATIM handles it
        prefix = full[: len(full) - len(launch)].strip()
        issues: list[Violation] = []
        if len(prefix.split()) > MAX_ACK_WORDS:
            issues.append(Violation("LAUNCH_ACK", f"keep the acknowledgement to {MAX_ACK_WORDS} words"))
        if "?" in prefix:
            issues.append(Violation("LAUNCH_ACK", "the acknowledgement must not be a question"))
        old = next(p for p in self.packet.parts if p.part_id == parked_id)
        old_pc = self.packet.claims[old.part_id]
        old_ledger = build_ledger(old_pc, self._part_events(self.log.load(), old.part_id))
        blocked = {c.id: c.recognizer for c in old_pc.claims if c.id not in old_ledger.established}
        issues += lint_message(prefix, state=WORKING, hint_level=0, statement=old.statement,
                               sealed_solution=sealed_section(self._solution, old.part_id) or "", blocked_claims=blocked)
        return issues

    # ---- verify -------------------------------------------------------
    def _validate_check(self, check, n_steps: int, pe: list[Event]) -> list[dict]:
        if not isinstance(check, list) or not check:
            raise ValueError("the check file must be a non-empty JSON list of {step, status, quote, note}")
        texts = [_norm(e.text) for e in pe if e.type == "student"]
        seen, entries = [], []
        for item in check:
            if not isinstance(item, dict):
                raise ValueError("each check entry must be an object")
            step, status = item.get("step"), item.get("status")
            if not isinstance(step, int) or isinstance(step, bool) or not 1 <= step <= n_steps:
                raise ValueError(f"step must be an integer from 1 to {n_steps}")
            if step in seen:
                raise ValueError(f"step {step} appears more than once")
            if status not in CHECK_STATUSES:
                raise ValueError(f"step {step}: status must be one of {list(CHECK_STATUSES)}")
            quote, note = _norm(item.get("quote")), _norm(item.get("note"))
            if status == "confirmed":
                if not _quote_ok(quote, texts):
                    raise ValueError(f"step {step}: a confirmed step needs a quote of at least 3 words (or their whole message) that appears in this part's student messages")
            elif not note:
                raise ValueError(f"step {step}: a {status} step needs a note about the student's step")
            axis = item.get("axis", "rigor")
            if axis not in AXES_ALL:
                raise ValueError(f"step {step}: axis must be one of {list(AXES_ALL)}")
            entry = {"step": step, "status": status, "quote": quote, "note": note, "axis": axis}
            if item.get("tag"):
                entry["tag"] = str(item["tag"])
            seen.append(step)
            entries.append(entry)
        missing = sorted(set(range(1, n_steps + 1)) - set(seen))
        if missing:
            raise ValueError(f"missing check entries for steps {missing}")
        return sorted(entries, key=lambda e: e["step"])

    def verify(self, check=None, downgrades: dict | None = None) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        pc = self.packet.claims[part.part_id]
        pe = self._part_events(events, part.part_id)
        if s.state != WORKING:
            raise Refused(f"verify is only valid while the part is being worked (state is {s.state})", _NEXT.get(s.state, []))
        ledger = build_ledger(pc, pe)
        if not ledger.covered:
            raise Refused("verify is available only when every claim on one route has been established by the student "
                          "(recognized in their messages, or established with a quote)", ["turn", "say"])
        released = self._released(pe)
        steps = split_steps(sealed_section(self._solution, part.part_id) or "")
        if check is None:
            if released:
                raise Refused("the solution was already released for this part; submit your step check with "
                              "verify --check-file", ["verify --check-file F"])
            self.log.append("verify_release", part=part.part_id, state=s.state, hint_level=s.hint_level)
            return {"ok": True, "released": True,
                    "steps": [{"n": i + 1, "text": t} for i, t in enumerate(steps)],
                    "instructions": ("For EVERY step write one entry {step, status: confirmed|missing|wrong, quote, note}. "
                                     "A confirmed step needs a quote of the student's own words from this part; a "
                                     "missing or wrong step needs a note about the student's step (not the solution). "
                                     "Do not quote or outline these steps to the student.")}
        if not released:
            raise Refused("run verify without --check-file first to receive the solution steps", ["verify"])
        entries = self._validate_check(check, len(steps), pe)
        defects = [e for e in entries if e["status"] != "confirmed"]
        common = dict(part=part.part_id, hint_level=s.hint_level)
        confirmed = {e["step"] for e in entries if e["status"] == "confirmed"}
        for e in self._unresolved(pe):      # a step left open earlier and now confirmed needs no manual resolve
            m = re.fullmatch(r"defect-step-(\d+)", e.data["tag"])
            if m and int(m.group(1)) in confirmed:
                self.log.append("misconception_resolved", state=WORKING,
                                data={"tag": e.data["tag"], "axis": e.data.get("axis", "all"), "auto": True}, **common)
        pe = self._part_events(self.log.load(), part.part_id)
        unresolved = [e.data["tag"] for e in self._unresolved(pe)]
        if not defects and not unresolved:
            ratings = build_ratings(pe, downgrades)            # may raise before anything is logged
            self.log.append("verify", state=VERIFIED, data={"clean": True, "check": entries}, **common)
            self.log.append("close_part", state=VERIFIED, data={"ratings": ratings, "attempt": self._attempt_no(pe)}, **common)
            return {**self._brief(), "closed": True}
        self.log.append("verify", state=WORKING, data={"clean": False, "check": entries}, **common)
        for d in defects:
            tag = d.get("tag") or f"defect-step-{d['step']}"
            self.log.append("defect", state=WORKING, data={"step": d["step"], "status": d["status"], "note": d["note"],
                                                           "quote": d["quote"]}, **common)
            self.log.append("misconception", state=WORKING, data={"tag": tag, "axis": d["axis"], "defect": True}, **common)
        unresolved_now = [e.data["tag"] for e in self._unresolved(self._part_events(self.log.load(), part.part_id))]
        return {**self._brief(), "closed": False, "defects": defects, "unresolved": unresolved_now}

    # ---- end ----------------------------------------------------------
    def _render_partial(self, note: str) -> dict:
        events = self.log.load()
        date = self.session_id[:10]
        transcript, summary = write_session_docs(self.dir, events, self.packet, note, self._prior_gaps(), date)
        profile = update_profile(load_profile(self.paths.profile_json), session_id=self.session_id, date=date,
                                 events=events, packet=self.packet)
        save_profile(self.paths.profile_json, self.paths.profile_md, profile)
        return {"transcript": transcript, "summary": summary, "profile": self.paths.profile_json}

    def pause(self) -> dict:
        s = self._fsm()
        self._require_live(s)
        part = self.packet.parts[s.part_index]
        self.log.append("paused", part=part.part_id, state=fsm.PAUSED, hint_level=s.hint_level)
        return {"ok": True, "paused": True, **self._render_partial("Session paused before every part was covered."),
                "next": ["start (resume)", "start --fresh"]}

    def _end_partial(self) -> None:
        s = self._fsm()
        part = self.packet.parts[s.part_index]
        self.log.append("session_end", part=part.part_id, state=fsm.DONE, data={"partial": True})
        self._render_partial("Session ended before every part was covered.")

    def end(self, big_picture: str) -> dict:
        events = self.log.load()
        s = self._fsm(events)
        self._require_live(s)
        if s.state != SYNTHESIS:
            raise Refused(f"cannot end from state {s.state}; finish and close every part first", _NEXT.get(s.state, []))
        parked = set(s.queue)
        missing = [p.part_id for i, p in enumerate(self.packet.parts) if not self._closed(events, p.part_id) and i not in parked]
        if missing:
            raise Refused(f"parts not closed: {missing}", ["verify"])
        last_say = next((e for e in reversed(events) if e.type == "tutor_say"), None)
        if parked and not (last_say and last_say.state == SYNTHESIS and last_say.data.get("offer")):
            names = ", ".join(self.packet.parts[i].label or self.packet.parts[i].part_id for i in s.queue)
            raise Refused(f"parked parts remain ({names}); say a closing message that offers to go back to them, "
                          "then run end", ["say (closing message offering the parked parts)"])
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
