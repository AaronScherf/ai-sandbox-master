"""Task cards: what an agent is asked to produce, and how its answer is read back."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from .sources import Passage


class ResultError(ValueError):
    """The agent's result block could not be read; the message says why, in plain words."""


@dataclass
class Task:
    id: str
    stage: str
    subject: dict
    instructions: str
    context: str
    passages: list[Passage] = field(default_factory=list)


def render_card(task: Task) -> str:
    parts = [
        f"# Task {task.id}   (stage: {task.stage})",
        "",
        "## Instructions",
        task.instructions.strip(),
        "",
        "## Subject",
        task.context.strip(),
        "",
        "## Offered passages",
    ]
    if not task.passages:
        parts.append("(none: say so in your result rather than inventing a source)")
    for p in task.passages:
        parts += [f"### {p.id}  [source: {p.source} | ref: {p.ref}]", p.text.strip(), ""]
    parts += ["## Result", "Write only the YAML mapping, inside the fence below.", "```yaml", "```", ""]
    return "\n".join(parts)


_FENCE = re.compile(r"```(?:yaml|yml)?[ \t]*\r?\n(.*?)```", re.DOTALL)


def extract_result(card_text: str) -> dict | None:
    """The YAML mapping the agent wrote under '## Result', or None if the block is empty.

    Anything before '## Result' (instructions, passages) and after the block (a bounce note) is ignored."""
    start = card_text.rfind("\n## Result")
    if start == -1:
        raise ResultError("no '## Result' heading on the card")
    region = card_text[start + len("\n## Result"):]
    nxt = region.find("\n## ")
    if nxt != -1:
        region = region[:nxt]
    blocks = _FENCE.findall(region)
    if not blocks:
        raise ResultError("no YAML block under '## Result' (keep the ```yaml fence and write inside it)")
    if len(blocks) > 1:
        raise ResultError(f"expected exactly one YAML block under '## Result', found {len(blocks)}")
    return parse_result_text(blocks[0])


def parse_result_text(text: str) -> dict | None:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ResultError(f"invalid YAML in the result block: {str(exc).splitlines()[0]}") from exc
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ResultError("the result must be a YAML mapping (key: value), not a list or a single value")
    return data


def result_from_response(response: str) -> dict | None:
    """Read a model's reply: the first fenced block if it used one, else the whole reply as YAML."""
    match = _FENCE.search(response or "")
    return parse_result_text(match.group(1) if match else (response or ""))
