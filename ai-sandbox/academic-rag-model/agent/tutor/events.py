"""events.py -- append-only JSONL session log; the source of truth for a
tutoring session (spec §6). Each event records the part and FSM state as
they are AFTER the event, so any log can be replayed through fsm.replay()."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class Event:
    id: int
    ts: str
    type: str
    part: str | None = None
    state: str | None = None
    hint_level: int = 0
    intent: str | None = None
    text: str | None = None
    data: dict = field(default_factory=dict)


class EventLog:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> list[Event]:
        if not os.path.exists(self.path):
            return []
        events = []
        with open(self.path, "r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(Event(**json.loads(line)))
                except (json.JSONDecodeError, TypeError) as err:
                    raise ValueError(f"{self.path}: corrupt event on line {n}: {err}") from err
        return events

    def append(self, type: str, **fields) -> Event:
        events = self.load()
        next_id = max((e.id for e in events), default=0) + 1
        event = Event(
            id=next_id, ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            type=type, **fields,
        )
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event
