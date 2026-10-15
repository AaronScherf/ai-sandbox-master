"""The ready-to-paste prompt that goes with a run of task cards.

`collect` prints it and writes it to the run folder as PROMPT.md, so the person relaying the run to an agent (for
example Gemini in Antigravity) pastes one block instead of someone writing it each time. It names the stage and shows
the first line of a card's instructions, so an agent that was given the wrong run can tell."""
from __future__ import annotations

from .work import Run

COMMON = """\
- Write in your own words. Never mention the passages, the sources, or what they do or do not cover.
- Copy every citation's source and ref exactly from the offered passages; do not invent or reformat them.
- Close every $ in LaTeX. Put any value that contains a colon in double quotes."""

STEPS = {
    "seed": """\
- This is an additive seed: add only the concepts that are missing; never repeat an existing node or section.
- Meet every section's minimum node count stated on the card, with real concepts from the passages (definitions,
  axioms, theorems, properties, standard examples), not padding.
- Use only the kinds, topics and section ids the card lists.""",
    "fill": """\
- Fill gist, explanation, an optional example, and `formal` (LaTeX) where the concept has a formal statement.
- If the card carries an owner's request for the concept, cover it.""",
    "link": """\
- Propose only edges the offered passages support, from or to the card's node, using only the edge types the card lists.
- Prefer connections to concepts in other sections as well as the same section; edges that already exist are skipped.
- `condition` is required for implies and iff. Avoid definitional cycles. An empty edge list is allowed when nothing is
  supported.""",
    "summary": """\
- Write one cohesive paragraph of at most 110 words about how this section's concepts fit together and why they
  matter for what follows. Do not list the concepts one by one.
- Describe the ideas themselves; never mention the passages, the sources, or the lectures.""",
    "critic": """\
- Judge only whether the cited passages support the claim as stated, including its direction and any condition.
- Give a verdict of supports, weak or unsupported, and a one-sentence note. Do not edit the claim or its citations.
- Be strict with implies and iff claims: check the direction and that the condition is actually given.""",
}

STAGE_NOUN = {"seed": "SEED", "fill": "FILL", "link": "LINK", "critic": "CRITIC", "summary": "SUMMARY"}


def _first_instruction(run: Run) -> str:
    """The first sentence of the first card's instructions, to let the agent confirm it has the right run."""
    for entry in run.tasks:
        path = run.card_path(entry["id"])
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        marker = "## Instructions"
        if marker in text:
            body = text.split(marker, 1)[1].strip().splitlines()
            if body:
                line = body[0].strip()
                return line if len(line) <= 140 else line[:137].rstrip() + "..."
    return ""


def agent_prompt(run: Run, *, submit_hint: str | None = None) -> str:
    stage = run.stage
    noun = STAGE_NOUN.get(stage, stage.upper())
    count = len(run.tasks)
    first = _first_instruction(run)
    check = (f'\nCheck first: this is a {noun} run. Open any one card; the first line under "## Instructions" should be:\n'
             f'  "{first}"\nIf it is not, you were given the wrong run: stop and tell me.\n') if first else ""
    steps = STEPS.get(stage, "- Follow each card's instructions.")
    return f"""\
Run the concept-graph {noun} run {run.run_id} ({count} card{"s" if count != 1 else ""}).
Run dir: {run.root}
{check}
For every card in the cards folder of the run dir:
1. Open the card and follow its "## Instructions" exactly; the card is the authority for this task.
2. Use only the offered passages as evidence.
{steps}
{COMMON}

Fill the YAML under "## Result" in each card. Do not run submit yourself; tell me when you are done.
{submit_hint or ""}""".rstrip() + "\n"
