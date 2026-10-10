# agent/tutor/cli.py  (replace the whole file)
"""cli.py -- the command surface the live IDE agent calls every turn (v1.1 §5).
JSON on stdout, exit 0 when ok else 2. Run as
`python -m agent.tutor.cli --hub-root H --course C --problem-set PS <command> ...`."""
from __future__ import annotations

import argparse
import json
import os
import sys

from agent.tutor import audit as audit_mod
from agent.tutor import prep
from agent.tutor.fsm import INTENTS
from agent.tutor.packet import PacketError
from agent.tutor.paths import TutorPaths
from agent.tutor.ratings import RATINGS
from agent.tutor.session import Refused, Session

_RAG_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DEFAULT_HUB = os.path.normpath(os.path.join(_RAG_DIR, "..", "academic-hub"))
_RATING_ALIASES = {"developing": RATINGS[0], "proficient": RATINGS[1], "mastered": RATINGS[2]}
_RETRY = ["fix the arguments named in the error and retry the same command"]


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def _text(args) -> str:
    if getattr(args, "stdin", False):
        return sys.stdin.read().rstrip("\r\n")
    if getattr(args, "text_file", None):
        return _read(args.text_file).rstrip("\r\n")
    if getattr(args, "text", None) is not None:
        return args.text
    raise ValueError("provide --stdin, --text-file or --text")


def _downgrades(items, why):
    out = {}
    for item in items or []:
        axis, sep, rating = item.partition("=")
        if not sep:
            raise ValueError(f"--downgrade expects axis=rating, got {item!r}")
        if not why:
            raise ValueError("--downgrade needs --why: the reason for lowering the rating")
        out[axis.strip()] = (_RATING_ALIASES.get(rating.strip().lower(), rating.strip()), why)
    return out


def _add_text_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--text-file")
    p.add_argument("--text")


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

    t = sub.add_parser("turn")
    t.add_argument("--intent", required=True, choices=sorted(INTENTS))
    _add_text_args(t)
    t.add_argument("--admits-gap", nargs="?", const="all", default=None)
    t.add_argument("--define")
    t.add_argument("--establish")
    t.add_argument("--establish-quote")
    t.add_argument("--flag-slip")
    t.add_argument("--slip-quote")
    t.add_argument("--resolve")
    t.add_argument("--resolve-quote")
    t.add_argument("--skip", action="store_true")
    t.add_argument("--part")

    sy = sub.add_parser("say")
    _add_text_args(sy)
    sy.add_argument("--check", action="store_true")

    v = sub.add_parser("verify")
    v.add_argument("--check-file")
    v.add_argument("--downgrade", action="append", default=[])
    v.add_argument("--why")

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
        for key, value in (("{PYTHON}", sys.executable), ("{RAG_DIR}", _RAG_DIR), ("{HUB_ROOT}", paths.hub_root),
                           ("{COURSE}", paths.course), ("{PROBLEM_SET}", paths.problem_set)):
            template = template.replace(key, value)
        return {"ok": True, "_raw": template}
    if args.cmd == "start":
        return Session.start(paths).view()
    if args.cmd == "audit":
        session = Session.open(paths, args.session or Session.latest_session_id(paths))
        return {"ok": True, "findings": [f.to_dict() for f in audit_mod.audit(session.log.load(), session.packet)]}
    session = Session.open(paths, args.session)
    if args.cmd == "turn":
        return session.turn(
            args.intent, _text(args), admits_gap=args.admits_gap, establish=args.establish,
            establish_quote=args.establish_quote, flag_slip=args.flag_slip, slip_quote=args.slip_quote,
            resolve=args.resolve, resolve_quote=args.resolve_quote, define_term=args.define,
            skip=args.skip, revisit_part=args.part,
        )
    if args.cmd == "say":
        return session.say(_text(args), check=args.check)
    if args.cmd == "verify":
        check = json.loads(_read(args.check_file)) if args.check_file else None
        return session.verify(check, _downgrades(args.downgrade, args.why))
    if args.cmd == "end":
        return session.end(_read(args.big_picture_file))
    raise ValueError(f"unknown command {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stdin):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = _build_parser().parse_args(argv)
    paths = TutorPaths(args.hub_root, args.course, args.problem_set)
    try:
        result = _dispatch(args, paths)
    except Refused as err:
        result = {"ok": False, "error": str(err), "next": err.next_commands}
    except (PacketError, ValueError, FileExistsError, OSError) as err:
        result = {"ok": False, "error": str(err), "next": list(_RETRY)}
    if "_raw" in result:
        print(result["_raw"])
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
