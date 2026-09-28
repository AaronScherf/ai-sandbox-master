"""
merge_resumes.py
Ongoing multi-source resume merge (spec §12, Revision 7): processes every
new/changed file in resume-manager/source_resumes/ (PDF via extract.py's
local primitives, DOCX via mammoth), asks the local Ollama model to spot
content not already in resume_master.yaml, and merges everything it finds
back into resume_master.yaml. Additions only -- never rewrites or improves
an existing bullet's wording, even when a source phrases the same fact
better, so a merge re-run never silently changes wording already
hand-tuned in the master. The master should accept as much content as a
source offers; the only reason to reject something is that it is already
present.

**No traceability gate** (removed 2026-09-27 per explicit direction):
an earlier revision verified every proposed addition against the source
file's own raw text via schema.py's `verify_entry_fields()` (the same
substring check convert_resume.py runs at bootstrap) and dropped anything
that failed. That gate was removed -- it was rejecting genuine content
whenever the LLM paraphrased instead of quoting verbatim, and traceability
was never the intended filter; duplicate detection is. The one real gap
this surfaced (an entry returned with zero bullets because the model's
single large response ran out of attention before generating them) is
handled instead by `_backfill_bullets()`, a targeted follow-up call scoped
to just that one role's raw text. Two more content types the model can
surface are merged the same non-gated way: `new_field_updates_by_id` fills
in a currently-blank field (e.g. a thesis title) on an existing entry, and
`new_skills_by_category` appends skills not already present anywhere in
the master's Skills section.

**Existing blank fields need a deterministic backfill pass too, not just
new entries** (confirmed 2026-09-27, real re-run against a master that
already had 5 blank-bullets work_experience entries and one education
entry with a still-blank thesis from an earlier run): the main comparison
call does not reliably re-propose content for an entry it can already see
in `_build_master_context()` -- it simply omits the entry from its
response, silently, with nothing to flag. This isn't fixable by trusting
the same single call harder; `merge_one_source()` runs an unconditional
second pass after the main call, independent of what that call returned,
backfilling every work_experience entry with empty bullets
(`_backfill_bullets()`) and every education entry with a blank field
(`_backfill_education_fields()`) against this source's raw text. Also
fixed in the same pass: the field-update code now rejects a *proposed new
value* that is itself a placeholder (the model sometimes answers a blank
field with the literal text "Not specified" instead of omitting it) --
writing that in would just swap one placeholder spelling for another.

**Backfill calls send an excerpt, not the whole document** (confirmed
2026-09-27: the process got killed mid-run for exhausting system memory).
`call_ollama()` sizes Ollama's context window to fit the whole prompt it's
given, and a single `merge_one_source()` run can make ~10+ backfill calls
(one per still-blank entry/field) -- every one of them was passing the
entire source document as `raw_text`, even though each only needs the few
hundred characters describing one role or institution. `_excerpt_around()`
windows `raw_text` to a fixed-size excerpt starting at the target entry's
own name, falling back to the full text if the name isn't found in it.

**Duplicate detection is not LLM-judgment-only** (corrected after the
first real run, 2026-09-26): the local model's own "is this already in
the master" comparison was not reliable enough alone -- a real run
duplicated 3 USAID work_experience entries, 2 education entries, and 2
publications, each because a different source resume phrased the same
role/institution/title slightly differently and the LLM didn't recognize
it as already present. `_find_duplicate()` adds a deterministic
`rapidfuzz.fuzz.ratio` check (threshold 85, calibrated against those
exact real duplicate pairs) in front of every addition, as defense in
depth alongside the LLM's own judgment -- the same "flag, never trust a
single judgment alone" posture this project already applies elsewhere
(e.g. §3 step 4's traceability check, still used by convert_resume.py's
one-time bootstrap, which is unaffected by this file's change).

Deliberately does NOT route through normalize.py's section/line-shape
parser (unlike convert_resume.py's one-time bootstrap, spec §3): this is
an LLM comparison task ("does the master already say this?"), not a
full-document extraction task, so a source document's own layout never
needs to be fully understood, only compared against.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from rapidfuzz import fuzz

from common.ollama_utils import call_ollama
from resume_manager.extract import DefectivePageError, extract_resume_text
from resume_manager.llm_yaml import parse_llm_yaml
from resume_manager.markdown_sync import export_to_markdown
from resume_manager.schema import MISSING_VALUE_PLACEHOLDERS, assign_ids
from resume_manager.tailor import RESUMEMANAGER_OLLAMA_MODEL, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS

_IGNORED_FILENAMES = {"desktop.ini"}
_SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
_MANIFEST_FILENAME = ".processed_manifest.json"

# Fuzzy-match duplicate guard (added 2026-09-26, deterministic defense in
# depth alongside the LLM's own novelty judgment). A real merge run
# confirmed the LLM alone isn't reliable here: it duplicated 3 USAID
# roles, 2 education entries, and 2 publications, each time because a
# different source resume phrased the same role/institution/title
# slightly differently and the LLM didn't recognize it as already
# present. Calibrated against those exact real duplicate pairs (93.8-100
# similarity) versus a genuinely different entry (38.9) -- 85 sits well
# inside the gap between them, matching the same rapidfuzz.fuzz.ratio
# primitive normalize.py's match_section_header() already uses (§3),
# just a stricter threshold since a false-positive "this is a duplicate"
# is a lost real addition, not a merely-inconvenient one.
_DUPLICATE_SIMILARITY_THRESHOLD = 85
_DUPLICATE_REVIEW_THRESHOLD = 75

# Compound signal for awards/publications specifically (added 2026-09-26
# after a real slip-through): "Donald M. Payne Fellow" vs "Donald M. Payne
# International Development Fellow" -- the same real $100,000 fellowship,
# same 05/2017 date -- only scored 62.9 name similarity, under the
# name-only threshold above, and was wrongly added as a second entry. An
# exact date match is a strong independent signal, so it's paired with a
# much lower name-similarity bar. Calibrated against that real pair (62.9)
# against the closest genuinely-different pairs in the actual master that
# happen to share a generic word like "Fellow"/"Scholar" (44.4, 45.3) --
# 55 sits in the gap between them.
_DUPLICATE_SAME_DATE_SIMILARITY_THRESHOLD = 55

# Education-specific secondary signal (added 2026-09-26 after a real
# slip-through): "Mercer University Bachelor in Finance and Economics" vs
# "Mercer University B.B.A. with Honors, Summa Cum Laude, GPA: 3.91" --
# the same real degree (same institution, same 3.91 GPA) -- only scored
# 48.7 combined institution+degree similarity, which is actually LOWER
# than some genuinely different institution pairs that happen to both say
# "Master of Science in ..." (52-56 in the real master) -- lowering the
# combined-text threshold to catch 48.7 would create false positives
# there instead of fixing this. Institution name alone is a far more
# specific signal (100 for the real duplicate pair vs 32.7-36.4 for
# genuinely different institutions in the real master), so it's compared
# on its own, at a high bar, paired with an exact GPA match.
_EDUCATION_INSTITUTION_SIMILARITY_THRESHOLD = 90


def _find_duplicate(candidate_text: str, existing_texts: list[str]) -> str | None:
    """Returns the first existing text `candidate_text` is a likely
    duplicate of (fuzzy ratio >= _DUPLICATE_SIMILARITY_THRESHOLD), or None
    if it looks genuinely new against every one of `existing_texts`."""
    for existing in existing_texts:
        if fuzz.ratio(candidate_text, existing) >= _DUPLICATE_SIMILARITY_THRESHOLD:
            return existing
    return None


def _find_near_duplicate(candidate_text: str, existing_texts: list[str]) -> tuple[str, float] | None:
    """Return the strongest review-band match without changing auto-drop behavior."""
    matches = [
        (existing, fuzz.ratio(candidate_text, existing))
        for existing in existing_texts
    ]
    matches = [
        (existing, score) for existing, score in matches
        if _DUPLICATE_REVIEW_THRESHOLD <= score < _DUPLICATE_SIMILARITY_THRESHOLD
    ]
    return max(matches, key=lambda item: item[1]) if matches else None


def _find_duplicate_by_name_and_date(
    candidate_text: str, candidate_date: str, existing: list[tuple[str, str]],
) -> str | None:
    """Like `_find_duplicate`, but for awards/publications: also treats an
    exact date match plus only moderate name similarity
    (>= _DUPLICATE_SAME_DATE_SIMILARITY_THRESHOLD) as a duplicate, not just
    a high name similarity on its own. `existing` is a list of (text,
    date) pairs from the master's current awards or publications."""
    for text, date in existing:
        threshold = _DUPLICATE_SIMILARITY_THRESHOLD
        if candidate_date and date and candidate_date == date:
            threshold = _DUPLICATE_SAME_DATE_SIMILARITY_THRESHOLD
        if fuzz.ratio(candidate_text, text) >= threshold:
            return text
    return None


def _find_duplicate_education(candidate: dict, existing_entries: list[dict]) -> str | None:
    """Education-specific duplicate check: the usual institution+degree
    combined-text check first, then a second, more targeted signal --
    institution name alone (a far more specific comparison than the
    combined text) at a high bar, paired with an exact GPA match when
    both are real (non-placeholder) values."""
    signature = f"{candidate.get('institution', '')} {candidate.get('degree', '')}"
    existing_signatures = [f"{e['institution']} {e['degree']}" for e in existing_entries]
    duplicate = _find_duplicate(signature, existing_signatures)
    if duplicate:
        return duplicate

    candidate_gpa = str(candidate.get("gpa") or "").strip()
    if not candidate_gpa or candidate_gpa.lower() in MISSING_VALUE_PLACEHOLDERS:
        return None
    for entry in existing_entries:
        existing_gpa = str(entry.get("gpa") or "").strip()
        if not existing_gpa or existing_gpa.lower() in MISSING_VALUE_PLACEHOLDERS:
            continue
        if existing_gpa != candidate_gpa:
            continue
        if fuzz.ratio(candidate.get("institution", ""), entry.get("institution", "")) >= (
            _EDUCATION_INSTITUTION_SIMILARITY_THRESHOLD
        ):
            return f"{entry['institution']} {entry['degree']}"
    return None

_DEFAULT_RESUME_MANAGER_DIR = (
    Path(__file__).resolve().parent.parent.parent / "research" / "independent-research"
    / "projects" / "resume-manager"
)

_MERGE_SYSTEM_PROMPT = """You are comparing one additional resume/CV document against the existing entries of a master resume, to find content in the additional document that is genuinely NEW -- not already captured in the master, even if the master phrases it slightly differently.
CRITICAL RULES:
1. You will be given the master's existing Work Experience, Education, Awards, Publications, and Skills (each with an id where applicable) followed by the full raw text of one additional document.
2. Do NOT flag something as new merely because it is worded differently from how the master already states the same fact -- only genuinely new information counts.
3. A new bullet describing work under an org/role or institution/degree that ALREADY has an entry in the master goes under new_bullets_by_id, keyed by that existing entry's id. Include EVERY such bullet, not just the first one or two -- if the role has ten bullets in the document and the master only already has three of them, all seven missing ones belong here.
4. A role/org with no matching entry in the master at all is an entirely new entry: return it under new_work_experience with org, role, location, start_date, end_date, and bullets. Include EVERY bullet describing that role's responsibilities and achievements, verbatim from the document -- an entry with an empty or partial bullets list is much less useful than a complete one, so do not stop partway through.
5. Similarly, an institution/degree not in the master goes under new_education (institution, degree, gpa, location, start_date, end_date, thesis); a new award goes under new_awards (name, description, date); a new publication goes under new_publications (title, date, venue, link). Use the literal text "Not specified" for any field the additional document doesn't state -- never guess a value.
6. If an EXISTING entry (work experience or education) is missing a field in the master (its current value is "Not specified" or blank) and this document states that field's real value (e.g. a thesis title, a GPA, a location), return it under new_field_updates_by_id, keyed by that entry's id, mapping the field name to the real value. Never propose an update for a field that already has a real value in the master -- only fill in genuinely blank ones.
7. A skill/tool/technology not already listed anywhere in the master's Skills goes under new_skills_by_category, keyed by the category name it belongs under (reuse an existing category name if this document's own grouping matches one, otherwise a short new category name), each mapping to a list of new skill strings.
8. Do NOT rewrite, improve, or replace the wording of anything already in the master -- only report new content, verbatim from the additional document's own text.
9. Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences -- use an empty list/mapping for any category with nothing new:
new_bullets_by_id:
  <existing-id>: [new bullet text, ...]
new_work_experience: [{org: str, role: str, location: str, start_date: str, end_date: str, bullets: [str]}]
new_education: [{institution: str, degree: str, gpa: str, location: str, start_date: str, end_date: str, thesis: str}]
new_awards: [{name: str, description: str, date: str}]
new_publications: [{title: str, date: str, venue: str, link: str}]
new_field_updates_by_id:
  <existing-id>: {field_name: real value}
new_skills_by_category:
  <category name>: [new skill, ...]"""

_BACKFILL_BULLETS_SYSTEM_PROMPT = """You previously identified a work experience entry below with no bullet points included. Extract EVERY bullet point describing this specific role's responsibilities and achievements, verbatim from the text -- do not summarize, paraphrase, or omit any of them.
Output ONLY valid YAML in exactly this shape, no commentary, no markdown code fences:
bullets: [bullet one, bullet two, ...]"""

_BACKFILL_FIELD_SYSTEM_PROMPT = """You previously identified an education entry below with one or more blank fields. State the real value for each listed field, verbatim from the text, if the text states it -- use the literal text "Not specified" for any field the text doesn't state.
Output ONLY valid YAML, no commentary, no markdown code fences, with one line per blank field listed below, using each field's own exact name as its YAML key (not the word "field_name" or "value" -- those are not real field names)."""


def _discover_unprocessed_files(source_dir: str, manifest: dict[str, float]) -> list[str]:
    """Lists every supported file directly under `source_dir` whose mtime
    doesn't match the manifest's recorded value for it -- new files and
    changed files both count, an unchanged file is skipped so a re-run
    doesn't repeat a ~5-30-minute Ollama call (spec §4's timing evidence)
    on content already processed."""
    if not os.path.isdir(source_dir):
        return []
    unprocessed = []
    for name in sorted(os.listdir(source_dir)):
        if name.startswith(".") or name in _IGNORED_FILENAMES:
            continue
        if os.path.splitext(name)[1].lower() not in _SUPPORTED_EXTENSIONS:
            continue
        path = os.path.join(source_dir, name)
        if manifest.get(name) == os.path.getmtime(path):
            continue
        unprocessed.append(name)
    return unprocessed


def _load_manifest(source_dir: str) -> dict[str, float]:
    path = os.path.join(source_dir, _MANIFEST_FILENAME)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(source_dir: str, manifest: dict[str, float]) -> None:
    with open(os.path.join(source_dir, _MANIFEST_FILENAME), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def _extract_raw_text(path: str) -> str | None:
    """Returns raw text for a .pdf (extract.py's local primitive, same as
    convert_resume.py) or .docx (mammoth -- already a project dependency,
    first used in resume_manager here, same "already a dependency, new
    context" precedent as rapidfuzz, spec §2/§12), or None for an
    unsupported extension. `mammoth` is imported locally, matching this
    project's existing convention for it (essays/convert_essays.py) since
    it's a library call this project doesn't unit-test directly."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_resume_text(path)
    if ext == ".docx":
        import mammoth

        with open(path, "rb") as f:
            result = mammoth.convert_to_markdown(f)
        return result.value
    return None


def _build_master_context(master: dict) -> str:
    """Lists the master's existing content (id, key identifying fields,
    and bullets where applicable) so the LLM comparison call knows what's
    already captured -- never the source document's own text, which is
    passed separately."""
    lines: list[str] = []
    lines.append("EXISTING WORK EXPERIENCE:")
    for entry in master.get("work_experience") or []:
        lines.append(f"id: {entry['id']}\norg: {entry['org']}\nrole: {entry['role']}\nbullets:")
        for bullet in entry.get("bullets") or []:
            lines.append(f"  - {bullet}")
    lines.append("\nEXISTING EDUCATION:")
    for entry in master.get("education") or []:
        lines.append(f"id: {entry['id']}\ninstitution: {entry['institution']}\ndegree: {entry['degree']}")
        for field in ("gpa", "location", "start_date", "end_date", "thesis"):
            value = str(entry.get(field) or "").strip()
            if not value or value.lower() in MISSING_VALUE_PLACEHOLDERS:
                lines.append(f"{field}: (blank -- fill in under new_field_updates_by_id if this document states it)")
            else:
                lines.append(f"{field}: {value}")
    lines.append("\nEXISTING AWARDS:")
    for entry in master.get("awards") or []:
        lines.append(f"- {entry.get('name')}")
    lines.append("\nEXISTING PUBLICATIONS:")
    for entry in master.get("publications") or []:
        lines.append(f"- {entry.get('title')}")
    lines.append("\nEXISTING SKILLS:")
    for entry in master.get("skills") or []:
        lines.append(f"{entry.get('category')}: {', '.join(entry.get('items') or [])}")
    return "\n".join(lines)


_BACKFILL_EXCERPT_WINDOW_CHARS = 2500


def _excerpt_around(raw_text: str, needle: str, window: int = _BACKFILL_EXCERPT_WINDOW_CHARS) -> str:
    """Returns up to `window` characters of `raw_text` starting at
    `needle`'s first case-insensitive occurrence, or the full `raw_text`
    if `needle` isn't found in it at all (a safe fallback -- the backfill
    calls this feeds simply get their original, pre-excerpt behavior back
    in that case, never a worse outcome).

    Real, confirmed memory/time problem this fixes (2026-09-27):
    `call_ollama()` sizes Ollama's context window to fit the whole prompt
    it's given (`_estimate_num_ctx()`, `common/ollama_utils.py` -- itself
    an earlier fix for Ollama silently truncating an oversized prompt).
    `_backfill_bullets()` and `_backfill_education_fields()` run one
    targeted follow-up call per still-blank entry -- up to ~10+ in a
    single `merge_one_source()` run against a real resume -- and every
    one of them was passing the *entire* source document as `raw_text`,
    even though each call only needs the few hundred characters
    describing one specific role or institution. That repeatedly forced
    Ollama to allocate a context sized for the whole document on calls
    that only needed a small slice of it, real enough to exhaust system
    memory and get the process killed mid-run. A real resume lists each
    job/degree as a compact, contiguous block (confirmed against the
    resume that surfaced this: a whole education entry, including its
    thesis line, fit in ~250 characters), so a generous fixed window
    following the entry's own name comfortably covers it without needing
    to parse the document's structure."""
    lowered = raw_text.lower()
    start = lowered.find(needle.lower())
    if start == -1:
        return raw_text
    return raw_text[start:start + window]


def _backfill_bullets(org: str, role: str, raw_text: str, model: str) -> list[str]:
    """Real, confirmed gap this fixes (2026-09-26): a single large
    comparison call sometimes proposes a brand-new work_experience entry
    with an empty bullets list -- not because the source document lacks
    bullets for that role (confirmed it doesn't, in the real case that
    surfaced this), but because the model runs out of attention/output
    budget after generating a lot of other new content in the same
    response. A separate, narrowly-scoped follow-up call -- "list every
    bullet for this one already-identified role" -- is a much easier task
    for the same small local model to get right than doing it as part of
    one large comparison in a single pass. Returns an empty list (never
    raises) if the call fails or the response is malformed, mirroring
    this project's existing never-crash-on-a-bad-LLM-response contract.
    Sends `raw_text` windowed to an excerpt around `org` (see
    `_excerpt_around()`) rather than the whole document, to keep this
    narrowly-scoped call's context -- and the memory Ollama allocates for
    it -- proportional to what it actually needs."""
    excerpt = _excerpt_around(raw_text, org)
    prompt = f"{_BACKFILL_BULLETS_SYSTEM_PROMPT}\n\n### ROLE: {role} at {org}\n\n### TEXT:\n{excerpt}"
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return []
    parsed = parse_llm_yaml(result)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("bullets"), list):
        return []
    return [b for b in parsed["bullets"] if isinstance(b, str) and b.strip()]


def _backfill_education_fields(
    institution: str, degree: str, blank_fields: list[str], raw_text: str, model: str,
) -> dict[str, str]:
    """Mirrors `_backfill_bullets()`'s targeted-follow-up-call pattern for
    a different, equally real gap (confirmed 2026-09-27, real case: a
    thesis title the source document states but the main comparison call
    didn't surface): the main call doesn't reliably re-propose a real
    value for an existing education entry's blank field even when
    `_build_master_context()` marks that field as blank in the prompt --
    same "don't trust a single judgment call" posture as the bullets
    backfill. Drops any field the model couldn't find a real value for
    (it's told to use the literal "Not specified" placeholder in that
    case, filtered out here) rather than writing that placeholder text
    into the field. Never raises; returns {} on any failure.

    **Real, confirmed prompt bug this guards against (2026-09-27):** an
    earlier version of the system prompt showed the output shape as the
    generic template `{field_name}: {value}` -- the model echoed that
    literally (a response shaped `field_name: thesis\\nvalue: <the real
    thesis text>` for every field) instead of substituting each field's
    real name as the YAML key, even though it had correctly found every
    value from the raw text. The example below is built from
    `blank_fields` itself so the model always sees its own real target
    keys, the same fix that already made `_backfill_bullets()`'s prompt
    work (its example uses the literal key "bullets", never a
    placeholder name).

    Sends `raw_text` windowed to an excerpt around `institution` (see
    `_excerpt_around()`) rather than the whole document, for the same
    memory/context-size reason as `_backfill_bullets()`."""
    example = "\n".join(f"{field}: <the real value, or \"Not specified\">" for field in blank_fields)
    excerpt = _excerpt_around(raw_text, institution)
    prompt = (
        f"{_BACKFILL_FIELD_SYSTEM_PROMPT}\n\nExample shape for these exact fields:\n{example}"
        f"\n\n### ENTRY: {degree} at {institution}"
        f"\n### BLANK FIELDS: {', '.join(blank_fields)}\n\n### TEXT:\n{excerpt}"
    )
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return {}
    parsed = parse_llm_yaml(result)
    if not isinstance(parsed, dict):
        return {}
    return {
        field: value.strip()
        for field, value in parsed.items()
        if field in blank_fields and isinstance(value, str) and value.strip()
        and value.strip().lower() not in MISSING_VALUE_PLACEHOLDERS
    }


def merge_one_source(
    master: dict, raw_text: str, model: str = RESUMEMANAGER_OLLAMA_MODEL,
) -> tuple[list[str], list[str]]:
    """Runs one LLM comparison call for `raw_text` against `master`'s
    current content and applies the result directly onto `master`
    (mutated in place). Returns (applied, flagged) -- human-readable
    descriptions of what was added and what was skipped and why, for the
    merge report (spec §12 step 7). An unreachable/timed-out Ollama call
    or malformed response applies nothing and returns a single flagged
    message describing why, mirroring tailor_resume()'s and
    generate_clarifying_questions()'s existing never-crash-on-a-bad-LLM-
    response contract (spec §8, §11).

    **No traceability gate** (removed 2026-09-27, confirmed real
    preference: "there should not be any reason to filter... unless there
    is a duplicate"). The exact-substring `verify_entry_fields()` check
    this module originally ran here (mirroring convert_resume.py's
    bootstrap-time check, spec §3 step 4) turned out to reject a lot of
    genuine content: the LLM rarely quotes multi-sentence bullets 100%
    verbatim, so a legitimate paraphrase-level difference was enough to
    fail an exact-match check built for a very different context
    (deterministic, non-LLM bootstrap extraction, where verbatim
    traceability is actually guaranteed by construction). Fuzzy-match
    duplicate detection (`_find_duplicate*`, still the one active filter)
    stays -- it addresses a different, still-real problem (recognizing
    the same fact stated differently isn't a case of "new" at all)."""
    prompt = (
        f"{_MERGE_SYSTEM_PROMPT}\n\n### EXISTING MASTER CONTENT:\n{_build_master_context(master)}"
        f"\n\n### ADDITIONAL DOCUMENT TEXT:\n{raw_text}"
    )
    result = call_ollama(prompt, model, RESUMEMANAGER_OLLAMA_TIMEOUT_SECONDS)
    if not isinstance(result, str):
        return [], ["Ollama call failed, timed out, or was unreachable -- nothing merged from this source."]
    parsed = parse_llm_yaml(result)
    if not isinstance(parsed, dict):
        return [], ["LLM response was not valid YAML -- nothing merged from this source."]

    applied: list[str] = []
    flagged: list[str] = []

    work_experience_by_id = {e["id"]: e for e in master.get("work_experience") or []}
    education_by_id = {e["id"]: e for e in master.get("education") or []}

    new_bullets_by_id = parsed.get("new_bullets_by_id")
    if isinstance(new_bullets_by_id, dict):
        for entry_id, bullets in new_bullets_by_id.items():
            # Real, confirmed slip (2026-09-26): the LLM sometimes writes
            # an id with underscores ("university_of_california_berkeley_1")
            # instead of the master's actual hyphenated id -- an exact-
            # match lookup silently lost 4 otherwise-good new bullets to
            # this formatting mismatch alone. Tries the id as given first,
            # falling back to a hyphen-normalized form.
            normalized_id = entry_id.replace("_", "-") if isinstance(entry_id, str) else entry_id
            target = (
                work_experience_by_id.get(entry_id) or education_by_id.get(entry_id)
                or work_experience_by_id.get(normalized_id) or education_by_id.get(normalized_id)
            )
            if target is None:
                flagged.append(f"new_bullets_by_id referenced unknown id '{entry_id}' -- skipped")
                continue
            if not isinstance(bullets, list):
                flagged.append(f"new_bullets_by_id['{entry_id}'] was not a list -- skipped")
                continue
            for bullet in bullets:
                duplicate = _find_duplicate(bullet, target.get("bullets") or [])
                if duplicate:
                    flagged.append(
                        f"bullet for '{entry_id}' looks like a duplicate of an existing bullet, dropped: "
                        f"{bullet!r} (matches {duplicate!r})"
                    )
                    continue
                near_duplicate = _find_near_duplicate(bullet, target.get("bullets") or [])
                if near_duplicate:
                    existing, score = near_duplicate
                    flagged.append(
                        f"bullet for '{entry_id}' is a possible near-duplicate ({score:.2f}% similarity), "
                        f"added for review: {bullet!r} (matches {existing!r})"
                    )
                target.setdefault("bullets", []).append(bullet)
                applied.append(f"added bullet to '{entry_id}': {bullet!r}")

    # Real, confirmed gap (2026-09-27): re-running a merge against a master
    # that already has a blank-bullets entry (e.g. from an earlier run made
    # before `_backfill_bullets()` existed) is not reliably caught by the
    # main comparison call above -- the model sees the entry already listed
    # in EXISTING WORK EXPERIENCE and doesn't reliably re-propose its
    # bullets under new_bullets_by_id, even though `_build_master_context()`
    # shows its bullets list as empty. Rather than trust the single
    # judgment call to notice this (the same "flag, never trust a single
    # judgment alone" posture used for duplicate detection), every
    # still-empty entry gets its own deterministic, targeted backfill
    # attempt against this source's raw text.
    for entry in master.get("work_experience") or []:
        if entry.get("bullets"):
            continue
        backfilled = _backfill_bullets(entry.get("org", ""), entry.get("role", ""), raw_text, model)
        if backfilled:
            entry["bullets"] = backfilled
            applied.append(
                f"backfilled {len(backfilled)} bullet(s) for existing entry "
                f"'{entry.get('org')} — {entry.get('role')}' (id {entry.get('id')}), which had none"
            )

    # Same gap, same fix, for education fields (confirmed 2026-09-27, real
    # case: a thesis title the model didn't re-propose for an existing
    # entry across two full re-runs of the main comparison call).
    for entry in master.get("education") or []:
        blank_fields = [
            field for field in ("gpa", "location", "start_date", "end_date", "thesis")
            if str(entry.get(field) or "").strip().lower() in MISSING_VALUE_PLACEHOLDERS
            or not str(entry.get(field) or "").strip()
        ]
        if not blank_fields:
            continue
        backfilled_fields = _backfill_education_fields(
            entry.get("institution", ""), entry.get("degree", ""), blank_fields, raw_text, model,
        )
        for field, value in backfilled_fields.items():
            entry[field] = value
            applied.append(
                f"backfilled '{entry.get('id')}.{field}': {value!r} (existing entry had it blank)"
            )

    existing_ids = set(work_experience_by_id) | set(education_by_id)

    we_signatures = [f"{e['org']} {e['role']}" for e in master.get("work_experience") or []]
    new_work_experience = []
    for candidate in parsed.get("new_work_experience") or []:
        if not isinstance(candidate, dict):
            continue
        signature = f"{candidate.get('org', '')} {candidate.get('role', '')}"
        duplicate = _find_duplicate(signature, we_signatures)
        if duplicate:
            flagged.append(
                f"new work_experience entry looks like a duplicate of an existing entry, dropped: "
                f"'{signature}' (matches '{duplicate}')"
            )
            continue
        new_work_experience.append(candidate)
        we_signatures.append(signature)
    if new_work_experience:
        for entry in new_work_experience:
            if not entry.get("bullets"):
                backfilled = _backfill_bullets(entry.get("org", ""), entry.get("role", ""), raw_text, model)
                if backfilled:
                    entry["bullets"] = backfilled
                    applied.append(
                        f"backfilled {len(backfilled)} bullet(s) for new entry "
                        f"'{entry.get('org')} — {entry.get('role')}' (initially returned with none)"
                    )
                else:
                    flagged.append(
                        f"new entry '{entry.get('org')} — {entry.get('role')}' still has no bullets "
                        f"after a backfill attempt"
                    )
        assign_ids(new_work_experience, "org", existing_ids=existing_ids)
        for entry in new_work_experience:
            applied.append(f"added new work_experience entry '{entry['org']} — {entry['role']}' (id {entry['id']})")
        master.setdefault("work_experience", []).extend(new_work_experience)
        existing_ids |= {e["id"] for e in new_work_experience}

    existing_education = list(master.get("education") or [])
    new_education = []
    for candidate in parsed.get("new_education") or []:
        if not isinstance(candidate, dict):
            continue
        signature = f"{candidate.get('institution', '')} {candidate.get('degree', '')}"
        duplicate = _find_duplicate_education(candidate, existing_education)
        if duplicate:
            flagged.append(
                f"new education entry looks like a duplicate of an existing entry, dropped: "
                f"'{signature}' (matches '{duplicate}')"
            )
            continue
        new_education.append(candidate)
        existing_education.append(candidate)
    if new_education:
        assign_ids(new_education, "institution", existing_ids=existing_ids)
        for entry in new_education:
            applied.append(f"added new education entry '{entry['institution']}' (id {entry['id']})")
        master.setdefault("education", []).extend(new_education)

    existing_awards = [(e.get("name", ""), e.get("date", "")) for e in master.get("awards") or []]
    for candidate in parsed.get("new_awards") or []:
        if not isinstance(candidate, dict):
            continue
        name, date = candidate.get("name", ""), candidate.get("date", "")
        duplicate = _find_duplicate_by_name_and_date(name, date, existing_awards)
        if duplicate:
            flagged.append(f"new award looks like a duplicate of '{duplicate}', dropped: '{name}'")
            continue
        master.setdefault("awards", []).append(candidate)
        applied.append(f"added new award '{name}'")
        existing_awards.append((name, date))

    existing_publications = [(e.get("title", ""), e.get("date", "")) for e in master.get("publications") or []]
    for candidate in parsed.get("new_publications") or []:
        if not isinstance(candidate, dict):
            continue
        title, date = candidate.get("title", ""), candidate.get("date", "")
        duplicate = _find_duplicate_by_name_and_date(title, date, existing_publications)
        if duplicate:
            flagged.append(f"new publication looks like a duplicate of '{duplicate}', dropped: '{title}'")
            continue
        master.setdefault("publications", []).append(candidate)
        applied.append(f"added new publication '{title}'")
        existing_publications.append((title, date))

    new_field_updates_by_id = parsed.get("new_field_updates_by_id")
    if isinstance(new_field_updates_by_id, dict):
        for entry_id, updates in new_field_updates_by_id.items():
            normalized_id = entry_id.replace("_", "-") if isinstance(entry_id, str) else entry_id
            target = (
                work_experience_by_id.get(entry_id) or education_by_id.get(entry_id)
                or work_experience_by_id.get(normalized_id) or education_by_id.get(normalized_id)
            )
            if target is None:
                flagged.append(f"new_field_updates_by_id referenced unknown id '{entry_id}' -- skipped")
                continue
            if not isinstance(updates, dict):
                flagged.append(f"new_field_updates_by_id['{entry_id}'] was not a mapping -- skipped")
                continue
            for field, value in updates.items():
                if not isinstance(value, str) or not value.strip():
                    continue
                value = value.strip()
                # Real, confirmed slip (2026-09-27): the model sometimes
                # proposes the literal placeholder text itself (e.g.
                # "Not specified") as the "real value" for a field the
                # source document doesn't actually state -- writing that
                # in would just replace one placeholder spelling with
                # another, so it's rejected the same as an empty value.
                if value.lower() in MISSING_VALUE_PLACEHOLDERS:
                    continue
                current_value = str(target.get(field) or "").strip()
                if current_value and current_value.lower() not in MISSING_VALUE_PLACEHOLDERS:
                    flagged.append(
                        f"field update for '{entry_id}.{field}' skipped -- already has a real value "
                        f"({current_value!r}); only genuinely blank fields get filled in"
                    )
                    continue
                target[field] = value
                applied.append(f"filled in '{entry_id}.{field}': {value!r}")

    new_skills_by_category = parsed.get("new_skills_by_category")
    if isinstance(new_skills_by_category, dict):
        existing_categories_by_name = {c["category"]: c for c in master.get("skills") or []}
        # Cross-category item ownership (real, confirmed root cause,
        # 2026-09-28 layout report): the category-name match above is a
        # weak signal on its own -- "Computer Programming" vs. the real
        # master's existing "Computer Programming and Artificial
        # Intelligence" scores only 58.8% by fuzz.ratio, well under
        # _DUPLICATE_SIMILARITY_THRESHOLD, so a differently-worded
        # category for the same underlying skills creates a second
        # category instead of matching. The real master ended up with 13
        # skill categories, several exact item-for-item duplicates, this
        # way. Tracking which category (if any) already owns each item --
        # not just the one category a name-match just picked -- catches
        # the duplication regardless of what the new category is named.
        item_owner_by_lower: dict[str, str] = {
            item.lower(): category["category"]
            for category in master.get("skills") or []
            for item in category.get("items") or []
            if isinstance(item, str)
        }
        for category_name, items in new_skills_by_category.items():
            if not isinstance(items, list) or not isinstance(category_name, str):
                continue
            target_category = None
            for existing_name, category in existing_categories_by_name.items():
                if fuzz.ratio(category_name, existing_name) >= _DUPLICATE_SIMILARITY_THRESHOLD:
                    target_category = category
                    break
            is_new_category = target_category is None
            if target_category is None:
                target_category = {"category": category_name, "items": []}
            added_items = []
            for item in items:
                if not isinstance(item, str) or not item.strip():
                    continue
                item = item.strip()
                item_lower = item.lower()
                owner = item_owner_by_lower.get(item_lower)
                if owner == target_category["category"]:
                    continue  # already exactly here -- ordinary no-op, not worth flagging
                if owner is not None:
                    flagged.append(
                        f"skill '{item}' already listed under '{owner}' -- not duplicated into '{target_category['category']}'"
                    )
                    continue
                target_category.setdefault("items", []).append(item)
                item_owner_by_lower[item_lower] = target_category["category"]
                added_items.append(item)
            if is_new_category and added_items:
                # Only create the new category if it actually gained a
                # genuinely new item -- an empty near-duplicate category
                # (every proposed item already lived elsewhere) would just
                # be more of the same sprawl this check exists to prevent.
                master.setdefault("skills", []).append(target_category)
                existing_categories_by_name[category_name] = target_category
            if added_items:
                applied.append(f"added {len(added_items)} skill(s) to '{target_category['category']}': {added_items}")

    return applied, flagged


def merge_source_resumes(
    source_dir: str, master_path: str, model: str = RESUMEMANAGER_OLLAMA_MODEL,
) -> str:
    """Runs the full merge (spec §12) and returns a one-line status
    message. Writes the updated `resume_master.yaml`, a merge report
    (`resume_master.merge_report.txt`, alongside it) recording what was
    added/flagged per source file, and the processed-files manifest --
    all after *every* file processed (not just once at the end): each
    file can cost a real, slow (~5-30-minute) Ollama call, so a crash or
    kill partway through a multi-file run leaves everything up to that
    point durably saved, and a re-run picks up from there via the
    manifest rather than starting over. Nothing is written at all if
    there was no unprocessed source file to begin with. A source file
    that fails extraction (corrupt, password-protected, an unsupported
    format) is skipped with a note in the report rather than aborting the
    whole run."""
    with open(master_path, encoding="utf-8") as f:
        master = yaml.safe_load(f)
    manifest = _load_manifest(source_dir)
    files_to_process = _discover_unprocessed_files(source_dir, manifest)
    if not files_to_process:
        return "No new or changed source files to merge."

    report_path = os.path.join(os.path.dirname(master_path), "resume_master.merge_report.txt")
    master_md_path = os.path.join(os.path.dirname(master_path), "resume_master.md")

    def _persist() -> None:
        # Real gap this closes (2026-09-26): each of the (up to
        # ~5-30-minute) Ollama calls below used to only get written to
        # disk after every file in this run finished -- a kill or crash
        # partway through lost all progress, including files that had
        # already gotten a real LLM response, forcing a full re-run from
        # scratch. Writing after every file means a re-run picks up where
        # it left off instead (the manifest already reflects the files
        # that finished).
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(master, f, sort_keys=False, allow_unicode=True)
        # Also refresh resume_master.md (spec §14) so its embedded hash
        # always matches the just-written YAML -- a hand-edit sync
        # (sync_master_md.py) started right after this run sees a fresh,
        # non-stale base to diff against.
        with open(master_md_path, "w", encoding="utf-8") as f:
            f.write(export_to_markdown(master, embed_hash=True))
        _save_manifest(source_dir, manifest)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines) + "\n")

    report_lines: list[str] = []
    for name in files_to_process:
        path = os.path.join(source_dir, name)
        report_lines.append(f"## {name}")
        try:
            raw_text = _extract_raw_text(path)
        except DefectivePageError as err:
            report_lines.append(f"- skipped: extraction failed ({err})")
            manifest[name] = os.path.getmtime(path)
            _persist()
            continue
        if raw_text is None:
            report_lines.append("- skipped: unsupported file type")
            manifest[name] = os.path.getmtime(path)
            _persist()
            continue

        applied, flagged = merge_one_source(master, raw_text, model)
        report_lines.extend(f"- {line}" for line in applied)
        report_lines.extend(f"- FLAGGED: {line}" for line in flagged)
        if not applied and not flagged:
            report_lines.append("- nothing new found")
        manifest[name] = os.path.getmtime(path)
        _persist()

    return f"Processed {len(files_to_process)} source file(s). Wrote {master_path} and {report_path}."


def main() -> None:
    resume_manager_dir = str(_DEFAULT_RESUME_MANAGER_DIR)
    source_dir = os.path.join(resume_manager_dir, "source_resumes")
    master_path = os.path.join(resume_manager_dir, "resume_master.yaml")
    print(merge_source_resumes(source_dir, master_path))


if __name__ == "__main__":
    main()
