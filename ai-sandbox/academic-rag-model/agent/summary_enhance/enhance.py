# agent/summary_enhance/enhance.py
"""CLI/orchestration for the optional summary-enhancement pipeline (v2).

    python -m agent.summary_enhance.enhance <guide.md> --topic "Wald test" \
        --topic "Likelihood ratio test" [--worked-example] [--min-words N] \
        [--output PATH] [--model M] [--env-file PATH] [--force] [--dry-run]

Per run: an optional planning call (no --topic), one synthesis call per topic, and
(with --worked-example) one code-execution call per topic. Writes one enhanced
Markdown file next to the guide (never over the guide, never outside
<corpus>/academic_notes/). Never runs git. Specs:
docs/superpowers/specs/agent/2026-10-03-summary-enhancement-design.md (v1) and
docs/superpowers/specs/agent/2026-10-03-summary-enhancement-v2-design.md.
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
from agent.summary_enhance.prompt import (
    build_plan_prompt, build_topic_prompt, build_worked_example_prompt,
)
from agent.summary_enhance.render import render
from agent.summary_enhance.schema import (
    PLAN_SCHEMA, TOPIC_SCHEMA, Enhanced, Topic, parse_plan, parse_topic,
)
from agent.summary_enhance.source_loader import GuideInput, SourceError, load_guide
from agent.summary_enhance.validate import validate_plan, validate_topic, validate_worked_example
from core.env.gemini_utils import get_gemini_client, load_dotenv_override

EXIT_OK, EXIT_NO_CLIENT, EXIT_INPUT, EXIT_INVALID, EXIT_LLM, EXIT_WRITE = 0, 1, 2, 3, 4, 5
DEFAULT_MIN_WORDS = 1400


class OutputError(Exception):
    pass


class GenerationFailed(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


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


def _with_retry(make_prompt, call, check):
    """Up to two attempts; the second prompt carries the first attempt's errors.
    make_prompt(errors|None) -> str; call(prompt) -> raw; check(raw) -> (result, errors).
    A ValueError from the client (truncated, empty, not JSON) counts as an unusable
    response and is retried; any other exception propagates."""
    errors: list[str] | None = None
    for _ in range(2):
        try:
            raw = call(make_prompt(errors))
        except ValueError as err:
            errors = [f"model response unusable: {err}"]
            continue
        result, errors = check(raw)
        if not errors:
            return result
    raise GenerationFailed(errors or ["no attempt succeeded"])


def _plan_topics(llm: LLMClient, guide: GuideInput) -> list[str]:
    def check(data):
        try:
            titles = parse_plan(data)
        except ValueError as err:
            return None, [f"malformed plan: {err}"]
        return titles, validate_plan(titles)

    return _with_retry(lambda errs: build_plan_prompt(guide, errs),
                       lambda p: llm.generate_structured(p, PLAN_SCHEMA), check)


def _synthesize(llm: LLMClient, guide: GuideInput, title: str, others: list[str], min_words: int) -> Topic:
    labels = {s.label for s in guide.sources}

    def check(data):
        try:
            topic = parse_topic(data)
        except ValueError as err:
            return None, [f"malformed topic: {err}"]
        errors = validate_topic(topic, labels, title, min_words)
        topic.title = title  # render the requested spelling
        return topic, errors

    return _with_retry(lambda errs: build_topic_prompt(guide, title, others, min_words, errs),
                       lambda p: llm.generate_structured(p, TOPIC_SCHEMA), check)


def _grounded_text(topic: Topic) -> str:
    return "\n\n".join(b.text.strip() for s in topic.sections for b in s.blocks if b.type == "grounded")


def _worked_example(llm: LLMClient, topic: Topic) -> str:
    grounded = _grounded_text(topic)

    def check(text):
        text = text.strip()
        return text, validate_worked_example(text)

    return _with_retry(lambda errs: build_worked_example_prompt(topic.title, grounded, errs),
                       lambda p: llm.generate_text(p, code_execution=True), check)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _save_recovery(out: Path, enhanced: Enhanced, text: str | None) -> None:
    """The paid calls already succeeded; keep their result (inside the vault, next to the
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


def _planned_calls(topics: list[str], worked_example: bool) -> str:
    if topics:
        n = len(topics) * (2 if worked_example else 1)
        return f"{n} calls ({len(topics)} topics{', each with a worked example' if worked_example else ''})"
    extra = " + 1 worked-example call per topic" if worked_example else ""
    return f"1 planning call + 1 call per planned topic (3-8){extra}"


def run(guide_path: str, *, topics: list[str], output: str | None = None, model: str | None = None,
        force: bool = False, dry_run: bool = False, llm: LLMClient | None = None,
        env_file: str | None = None, worked_example: bool = False,
        min_words: int = DEFAULT_MIN_WORDS) -> int:
    try:
        if min_words < 1:
            raise OutputError(f"--min-words must be a positive integer, got {min_words}")
        guide = load_guide(guide_path)
        out = resolve_output(guide, output, force)
        if env_file is not None and not Path(env_file).is_file():
            raise OutputError(f"--env-file not found: {env_file}")
    except (SourceError, OutputError) as err:
        print(f"ERROR: {err}")
        return EXIT_INPUT

    if dry_run:
        sample = (build_topic_prompt(guide, topics[0], topics[1:], min_words) if topics
                  else build_plan_prompt(guide))
        print(f"DRY RUN: {len(guide.sources)} chunks, about {len(sample)} prompt characters per call, "
              f"model {model or DEFAULT_MODEL}, {_planned_calls(topics, worked_example)}, "
              f"topics {topics or '(model-chosen)'}, min {min_words} words per topic")
        print(f"DRY RUN: would write {out}")
        return EXIT_OK

    if llm is None:
        _load_env(env_file)
        client = get_gemini_client("PAID_GEMINI_KEY")
        if client is None:
            return EXIT_NO_CLIENT
        llm = GeminiClient(client, model or DEFAULT_MODEL)

    try:
        titles = list(topics) or _plan_topics(llm, guide)
        done: list[Topic] = []
        for i, title in enumerate(titles):
            others = [t for j, t in enumerate(titles) if j != i]
            topic = _synthesize(llm, guide, title, others, min_words)
            if worked_example:
                topic.worked_example = _worked_example(llm, topic)
            done.append(topic)
    except GenerationFailed as err:
        print("ERROR: model output failed validation twice; nothing written:")
        for e in err.errors:
            print(f"  - {e}")
        return EXIT_INVALID
    except Exception as err:  # network/API failure after the client's own retries
        print(f"ERROR: model call failed: {err}")
        return EXIT_LLM

    enhanced = Enhanced(done)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    text: str | None = None
    try:
        text = render(guide, enhanced, model=llm.model, generated_at=generated_at,
                      worked_example=worked_example, min_words=min_words)
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
    p.add_argument("--topic", action="append", default=[],
                   help="section title; repeat per topic (omit to let the model plan the topics)")
    p.add_argument("--worked-example", action="store_true",
                   help="add a computed worked example per topic (code-execution call)")
    p.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS,
                   help=f"minimum words per topic (default {DEFAULT_MIN_WORDS})")
    p.add_argument("--output", help="explicit output .md path (must be inside academic_notes/)")
    p.add_argument("--model", help=f"Gemini model id (default {DEFAULT_MODEL})")
    p.add_argument("--env-file", help="load PAID_GEMINI_KEY from this .env (e.g. the main checkout's) "
                                      "instead of ai-sandbox/.env next to the code")
    p.add_argument("--force", action="store_true", help="replace an existing enhanced file")
    p.add_argument("--dry-run", action="store_true", help="show size/destination/call count; no API call")
    args = p.parse_args(argv)
    return run(args.guide, topics=args.topic, output=args.output, model=args.model,
               force=args.force, dry_run=args.dry_run, env_file=args.env_file,
               worked_example=args.worked_example, min_words=args.min_words)


if __name__ == "__main__":
    sys.exit(main())
