# tests/agent/tutor/skip_support.py
import datetime

from agent.tutor.paths import TutorPaths
from agent.tutor.sample_packet import write_sample_packet
from agent.tutor.session import Session

NOW = datetime.datetime(2026, 10, 9, 10, 0)
DEV, PROF, MAST = "Developing / Needs Review", "Proficient", "Mastered"
M1 = "the probabilities of everything in the set sum to 1"
M2 = "walking away is whatever is left over when nothing else is chosen"
M3 = "so it is one minus the sum of the others"
N1 = "all the non-positive numbers are indifferent to each other"
N2 = "so any representing function is flat up to zero and then strictly increasing"
N3 = "a flat then increasing function cannot be concave"
CHECK_Q1 = [{"step": 1, "status": "confirmed", "quote": M3}, {"step": 2, "status": "confirmed", "quote": M2}]
CHECK_Q2 = [{"step": 1, "status": "confirmed", "quote": N1}, {"step": 2, "status": "confirmed", "quote": N2},
            {"step": 3, "status": "confirmed", "quote": N3}]
CHECKIN = "Right. Do you have any lingering questions, or are you ready to move on?"
CHECKIN_OFFER = "Right. Do you have any lingering questions, or would you like to go back to Question 1 first?"
NUDGE = "What is the first thing you would try here?"


def make(tmp):
    paths = TutorPaths(tmp, "microecon", "homework_4")
    write_sample_packet(paths)
    return paths, Session.start(paths, now=NOW)


def codes(result):
    return {v["code"] for v in result.get("violations", [])}


def cover_q1(s):
    s.turn("attempt", M2)
    return s.turn("attempt", M3)


def cover_q2(s):
    s.turn("attempt", N1)
    s.turn("attempt", N2)
    return s.turn("attempt", N3)


def park_q1(s, with_attempt=False):
    """Skip q1 (two requests). Leaves the session in q2/LAUNCH. Returns the last brief."""
    if with_attempt:
        s.turn("attempt", M2)                      # recognizer match -> a real attempt
    s.turn("other", "I would rather skip this one", skip=True)
    s.say(NUDGE)
    return s.turn("other", "please, skip it, I want to move on", skip=True)


def close_q1(s):
    cover_q1(s)
    s.verify()
    return s.verify(CHECK_Q1)


def close_q2(s):
    cover_q2(s)
    s.verify()
    return s.verify(CHECK_Q2)


Q = "What makes you say that?"


def close_q1_said(s):
    """Like close_q1 but with a tutor reply after every student turn, so the audit sees an honest flow."""
    s.turn("attempt", M2)
    s.say(Q)
    s.turn("attempt", M3)
    s.verify()
    return s.verify(CHECK_Q1)


def close_q2_said(s):
    for text in (N1, N2):
        s.turn("attempt", text)
        s.say(Q)
    s.turn("attempt", N3)
    s.verify()
    return s.verify(CHECK_Q2)
