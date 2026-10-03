"""CLI/orchestration for the optional summary-enhancement pipeline.

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" \
        --topic "Likelihood ratio test" [--output PATH] [--model M] [--force] [--dry-run]

Writes one enhanced Markdown file next to the guide (never over the guide,
never outside <corpus>/academic_notes/). Never runs git. Spec:
docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from agent.summary_enhance.llm import DEFAULT_MODEL, GeminiClient, LLMClient
from agent.summary_enhance.prompt import build_prompt
from agent.summary_enhance.render import render
from agent.summary_enhance.schema import RESPONSE_SCHEMA, Enhanced, parse_enhanced
from agent.summary_enhance.source_loader import GuideInput, SourceError, load_guide
from agent.summary_enhance.validate import validate
from core.env.gemini_utils import get_gemini_client, load_dotenv_override

EXIT_OK, EXIT_NO_CLIENT, EXIT_INPUT, EXIT_INVALID, EXIT_LLM, EXIT_WRITE = 0, 1, 2, 3, 4, 5


class OutputError(Exception):
    pass


def resolve_output(guide: GuideInput, output: str | None, force: bool) -> Path:
    default = guide.path.with_name(f"{guide.path.stem}.enhanced.md")
    out = Path(output).resolve() if output else default
    vault = (guide.root / "academic_notes").resolve()
    if out.suffix.lower() != ".md":
        raise OutputError(f"output must be a .md file: {out}")
    if not out.is_relative_to(vault):
        raise OutputError(f"output must be inside {vault} (generated guides stay in the private notes vault): {out}")
    if out == guide.path:
        raise OutputError("output would overwrite the original guide")
    if out.exists() and not force:
        raise OutputError(f"{out} already exists; pass --force to replace it")
    return out


def _generate(llm: LLMClient, guide: GuideInput, topics: list[str]) -> tuple[Enhanced | None, list[str]]:
    """Up to two attempts; the second prompt carries the first attempt's errors.
    Returns (enhanced, []) on success or (None, errors) after the retry fails.
    LLM exceptions propagate."""
    valid_labels = {s.label for s in guide.sources}
    errors: list[str] = []
    for _ in range(2):
        prompt = build_prompt(guide, topics, errors=errors or None)
        data = llm.generate_structured(prompt, RESPONSE_SCHEMA)
        try:
            enhanced = parse_enhanced(data)
        except ValueError as err:
            errors = [f"malformed response: {err}"]
            continue
        errors = validate(enhanced, valid_labels, topics)
        if not errors:
            return enhanced, []
    return None, errors


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _save_recovery(out: Path, enhanced: Enhanced, text: str | None) -> None:
    """The paid call already succeeded; keep its result (inside the vault, next to the
    intended output) when the final write fails, e.g. Obsidian/sync holds the file open."""
    try:
        if text is not None:
            rec = out.with_name(out.stem + ".recovered.md")
            rec.write_text(text, encoding="utf-8", newline="\n")
        else:
            rec = out.with_name(out.stem + ".recovered.json")
            rec.write_text(json.dumps(asdict(enhanced), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"The model result was saved to {rec}")
    except Exception as err:
        print(f"WARNING: could not save a recovery copy either: {err}")


def _load_env(env_file: str | None) -> None:
    """Default: ai-sandbox/.env relative to the code. A worktree has no .env
    (it is git-ignored), so --env-file lets it inherit the main checkout's."""
    if env_file is None:
        load_dotenv_override()
        return
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)


def run(guide_path: str, *, topics: list[str], output: str | None = None, model: str | None = None,
        force: bool = False, dry_run: bool = False, llm: LLMClient | None = None,
        env_file: str | None = None) -> int:
    try:
        guide = load_guide(guide_path)
        out = resolve_output(guide, output, force)
        if env_file is not None and not Path(env_file).is_file():
            raise OutputError(f"--env-file not found: {env_file}")
    except (SourceError, OutputError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT

    if dry_run:
        prompt = build_prompt(guide, topics)
        print(f"DRY RUN: {len(guide.sources)} chunks, prompt {len(prompt)} characters, "
              f"model {model or DEFAULT_MODEL}, topics {topics or '(model-chosen)'}")
        print(f"DRY RUN: would write {out}")
        return EXIT_OK

    if llm is None:
        _load_env(env_file)
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return EXIT_NO_CLIENT
        llm = GeminiClient(client, model or DEFAULT_MODEL)

    try:
        enhanced, errors = _generate(llm, guide, topics)
    except Exception as err:  # network/API failure after the client's own retries
        print(f"ERROR: model call failed: {err}")
        return EXIT_LLM
    if enhanced is None:
        print("ERROR: model output failed validation twice; nothing written:")
        for e in errors:
            print(f"  - {e}")
        return EXIT_INVALID

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    text: str | None = None
    try:
        text = render(guide, enhanced, model=llm.model, generated_at=generated_at)
        _atomic_write(out, text)
    except Exception as err:
        print(f"ERROR: could not write {out}: {err}")
        _save_recovery(out, enhanced, text)
        return EXIT_WRITE
    print(f"Wrote {out}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("guide", help="path to an existing RAG-generated summary (.md)")
    p.add_argument("--topic", action="append", default=[], help="section title; repeat per topic")
    p.add_argument("--output", help="explicit output .md path (must be inside academic_notes/)")
    p.add_argument("--model", help=f"Gemini model id (default {DEFAULT_MODEL})")
    p.add_argument("--env-file", help="load PAID_GEMINI_KEY from this .env (e.g. the main checkout's) "
                                      "instead of ai-sandbox/.env next to the code")
    p.add_argument("--force", action="store_true", help="replace an existing enhanced file")
    p.add_argument("--dry-run", action="store_true", help="show size/destination; no API call")
    args = p.parse_args(argv)
    return run(args.guide, topics=args.topic, output=args.output, model=args.model,
               force=args.force, dry_run=args.dry_run, env_file=args.env_file)


if __name__ == "__main__":
    sys.exit(main())
