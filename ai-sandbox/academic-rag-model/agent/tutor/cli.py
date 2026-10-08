"""cli.py -- the command surface the live IDE agent calls every turn
(spec §3.2). JSON on stdout, exit 0 when ok else 2. Run as
`python -m agent.tutor.cli --hub-root H --course C --problem-set PS <command> ...`."""
from __future__ import annotations

import argparse
import json
import os
import sys

from agent.tutor import audit as audit_mod
from agent.tutor import prep
from agent.tutor.fsm import INTENTS, IllegalTransition
from agent.tutor.packet import PacketError
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RatingRejected
from agent.tutor.session import Session

_DEFAULT_HUB = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "academic-hub"))


def _text(args) -> str:
    if getattr(args, "text_file", None):
        with open(args.text_file, "r", encoding="utf-8") as f:
            return f.read()
    if getattr(args, "text", None) is not None:
        return args.text
    raise ValueError("provide --text or --text-file")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Socratic tutor session gate.")
    p.add_argument("--hub-root", default=_DEFAULT_HUB)
    p.add_argument("--course", required=True)
    p.add_argument("--problem-set", required=True)
    p.add_argument("--session", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("prep-collect")
    c.add_argument("--problem-set-file", required=True)
    c.add_argument("--question-ref", action="append", required=True)
    c.add_argument("--hints-file")
    c.add_argument("--solutions-file")
    c.add_argument("--force", action="store_true")
    sub.add_parser("prep-submit")
    sub.add_parser("start")

    s = sub.add_parser("student")
    s.add_argument("--intent", required=True, choices=sorted(INTENTS))
    s.add_argument("--text")
    s.add_argument("--text-file")
    s.add_argument("--misconception", action="append", default=[])
    s.add_argument("--admits-gap", nargs="?", const="all", default=None)

    sy = sub.add_parser("say")
    sy.add_argument("--text")
    sy.add_argument("--text-file")

    d = sub.add_parser("define")
    d.add_argument("term")
    sd = sub.add_parser("sealed")
    sd.add_argument("kind", choices=["hint", "solution"])
    v = sub.add_parser("verdict")
    v.add_argument("--assessment", required=True)
    v.add_argument("--note", default="")
    m = sub.add_parser("misconception")
    m.add_argument("tag")
    m.add_argument("--axis", default="all")
    m.add_argument("--resolved", action="store_true")
    cp = sub.add_parser("close-part")
    cp.add_argument("--ratings-file", required=True)
    e = sub.add_parser("end")
    e.add_argument("--big-picture-file", required=True)
    sub.add_parser("audit")
    sub.add_parser("bootstrap")
    return p


def _dispatch(args, paths: TutorPaths) -> dict:
    if args.cmd == "prep-collect":
        from core.env.gemini_utils import get_gemini_client, load_dotenv_override
        from agent.rag.rag_agent import retrieve_passages
        load_dotenv_override()
        client = get_gemini_client()
        if client is None:
            raise SystemExit(1)
        retrieve = lambda q: retrieve_passages([paths.hub_root], q, client, course=paths.course)
        return prep.collect(paths, args.problem_set_file, args.question_ref, retrieve,
                            hints_file=args.hints_file, solutions_file=args.solutions_file, force=args.force)
    if args.cmd == "prep-submit":
        return prep.submit(paths)
    if args.cmd == "bootstrap":
        template = _read(os.path.join(os.path.dirname(__file__), "bootstrap_prompt.md"))
        for key, value in (("{PYTHON}", sys.executable), ("{HUB_ROOT}", paths.hub_root),
                           ("{COURSE}", paths.course), ("{PROBLEM_SET}", paths.problem_set)):
            template = template.replace(key, value)
        return {"ok": True, "_raw": template}
    if args.cmd == "start":
        return Session.start(paths).view()
    session = Session.open(paths, args.session)
    if args.cmd == "student":
        miscs = []
        for item in args.misconception:
            tag, _, axis = item.partition(":")
            miscs.append((tag, axis or "all"))
        return session.student(args.intent, _text(args), misconceptions=miscs, admits_gap=args.admits_gap)
    if args.cmd == "say":
        return session.say(_text(args))
    if args.cmd == "define":
        return session.define(args.term)
    if args.cmd == "sealed":
        return session.sealed(args.kind)
    if args.cmd == "verdict":
        return session.verdict(args.assessment, args.note)
    if args.cmd == "misconception":
        return session.misconception(args.tag, args.axis, args.resolved)
    if args.cmd == "close-part":
        return session.close_part(json.loads(_read(args.ratings_file)))
    if args.cmd == "end":
        return session.end(_read(args.big_picture_file))
    if args.cmd == "audit":
        findings = [f.to_dict() for f in audit_mod.audit(session.log.load(), session.packet)]
        return {"ok": True, "findings": findings}
    raise ValueError(f"unknown command {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _build_parser().parse_args(argv)
    paths = TutorPaths(args.hub_root, args.course, args.problem_set)
    try:
        result = _dispatch(args, paths)
    except (IllegalTransition, RatingRejected, PacketError, ValueError, FileExistsError, OSError) as err:
        result = {"ok": False, "error": str(err)}
    if "_raw" in result:
        print(result["_raw"])
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
