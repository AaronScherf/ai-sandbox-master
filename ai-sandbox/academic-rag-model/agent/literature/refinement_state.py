"""Refinement status for records eligible for reporting and database builds."""
from .refine_grain import PROMPT_VERSION


def refinement_state(record: dict) -> str:
    value = (record.get("extractor") or {}).get("grain_refine_version")
    return "current" if value == PROMPT_VERSION else "older" if value else "missing"


def unrefined(records, ids):
    older, missing = [], []
    for fid in ids:
        record = records.read(fid, "a")
        if record is None:
            continue
        state = refinement_state(record)
        if state == "older":
            older.append(fid)
        elif state == "missing":
            missing.append(fid)
    return older, missing


def report(records, ids):
    older, missing = unrefined(records, ids)
    pending = older + missing
    print(f"records not refined under {PROMPT_VERSION}: {len(pending)} (older: {len(older)}, never: {len(missing)})")
    if pending:
        print("  " + ", ".join(pending[:20]) + (f" and {len(pending) - 20} more" if len(pending) > 20 else ""))
    return older, missing
