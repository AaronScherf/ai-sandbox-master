# Course-agnostic Concept Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the concept-graph pipeline run on econometrics (and any later course) by classifying each course file's role and format from several signals, and having the concept graph read that catalog instead of hard-coded microecon paths.

**Architecture:** A new shared package `core/course_materials/` turns a course's converted files into a `Catalog` of `Material` records (role, format, offering, date, book). It does this by weighted votes from frontmatter, PDF page shape, index cards, content and path words. Owner decisions are stored next to the generated catalog and always win. `agent/concept_graph` maps materials to citation keys and builds the seed card by role. Course wording moves into each graph repo's `site.yaml` and `vocab.yaml`.

**Tech Stack:** Python 3.13, pypdf (already in `requirements.txt`), pydantic v2 (existing schema), pytest.

**Spec:** `ai-sandbox/academic-rag-model/docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md`

## Global Constraints

- Work only in the worktree `C:/Users/theaa/ai-sandbox-master/.worktrees/claude-concept-graph-generalize`, branch `claude/concept-graph-generalize`. All paths below are relative to its `ai-sandbox/academic-rag-model/`.
- Python: `PY=C:/Users/theaa/ai-sandbox-master/ai-sandbox/academic-rag-model/.venv/Scripts/python.exe` (worktrees have no venv). Run every command from `ai-sandbox/academic-rag-model/` in the worktree.
- `core/course_materials/` makes no model or network calls.
- No new dependencies.
- Do not modify `core/env/` or `core/indexer/`. Only import from them.
- Stage explicit paths only (never `git add -A` / `git add .`). Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Match the surrounding style: lines up to about 120 characters, short docstrings, `from __future__ import annotations`.
- Real hub writes (`academic-hub/.index/materials/`) happen only in Task 10. Tests use `tmp_path` fixture trees.
- Signal weights (spec): decisive 10, strong 3, medium 2, weak 1. Flag when the top role scores below 3 or leads the runner-up by less than 2.

**Refinements to the spec made while planning.** Task 9 also records each of these in the spec.
1. A landscape source PDF votes `instructor` at **strong** (3), not weak. Microecon's prior decks have no other role signal, so at weak every one would be flagged. Recitation decks still get flagged, because their `ta`/`recitation` path word plus recitation wording ties the score.
2. The spec's `review`/`resolve` commands become `flagged` and `decide`, following the `offering_links` pattern. `flagged` prints JSON rows for Claude to load into the review Artifact. `decide` applies one decision. Claude builds the Artifact at review time (Task 10), and nothing in code calls it.
3. A decision may be keyed by a **directory** (`academic_notes/<course>/<folder>/`), which applies it to every file under that folder. Without this, the microecon book keys would need one decision per chapter file.
4. A path missing from the catalog gets a **path-only classification** (`classify_path`), not a flat `other`. It is still counted in `Catalog.misses` and reported by `collect`.
5. Instructor material keys as `slides` unless its format is `handwritten`, which keys as `notes`.
6. The student-notes cap is 30 dates, not 20: econometrics already has 23 lecture dates.

## Review Focus

1. **A course whose source PDFs are not on disk** (e.g. `academic_resources/` not synced). Classification must not crash. The PDF signal records `pdf unavailable` and abstains. *Test: Task 3 `test_missing_source_pdfs_abstain_without_crashing`.*
2. **Windows paths with backslashes and spaces from retrieval** (`C:\...\academic_notes\econometrics\lecture_notes\processed_outputs\Econometrics 2026-09-09 10.11.39.excalidraw.rag.md`). These must look up the same material as the forward-slash form. *Test: Task 1 `test_lookup_accepts_backslashes_and_resources_root`.*
3. **CRLF line endings in a converted file's frontmatter.** These must still be parsed, so `source_excalidraw`/`source_pdf` are not lost. *Test: Task 3 `test_crlf_frontmatter_is_read`.*
4. **Two lecture notes on the same date** (econometrics has two notes each on 2026-10-07 and 2026-10-14). Both must reach the seed card. *Test: Task 6 `test_two_lecture_notes_on_one_date_are_both_offered`.*
5. **A corrupt or foreign-format index-card file** (`.index/<course>.json`). It belongs to another pipeline, so it costs only the card signal and never the run. *Test: Task 3 `test_a_corrupt_index_card_file_only_loses_that_signal`.*

---

### Task 1: Material and Catalog model

**Files:**
- Create: `core/course_materials/__init__.py`
- Create: `core/course_materials/model.py`
- Test: `tests/core/course_materials/test_cm_model.py`

**Interfaces:**
- Produces:
  - `ROLES: tuple[str, ...]`, `FORMATS: tuple[str, ...]`, `DECIDABLE: tuple[str, ...]`
  - `class CatalogError(ValueError)`
  - `normalize(path: str) -> str | None`: the hub-relative posix path under `academic_notes/`
  - `rag_twin(path: str) -> str`
  - `@dataclass Material(path, role="other", format="typeset", offering=None, date=None, book=None, order=[1_000_000, "", ""], confidence=0.0, flagged=True, evidence=[], decided_by="rules")` with property `stem`
  - `@dataclass Catalog(course: str, materials: list[Material], unknown_decisions: list[str] = [])` with:
    - `.lookup(path) -> Material | None`
    - `.flagged() -> list[Material]`
    - `.by_role(role, offering=None) -> list[Material]`
    - `.offerings() -> list[str]`
    - `.book_keys() -> list[str]`
    - `.misses: set[str]`
    - `.to_json() -> dict`
    - `Catalog.from_json(data, source="catalog") -> Catalog`

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/course_materials/test_cm_model.py
import pytest

from core.course_materials.model import Catalog, CatalogError, Material, normalize, rag_twin

N = "academic_notes/econometrics"


def test_normalize_maps_either_root_to_a_hub_relative_notes_path():
    assert normalize("C:/hub/academic_notes/econometrics/syllabus/a.md") == f"{N}/syllabus/a.md"
    assert normalize("academic_resources/econometrics/textbooks/x.md") == f"{N}/textbooks/x.md"
    assert normalize("C:/somewhere/else/a.md") is None
    assert normalize("") is None


def test_rag_twin_swaps_both_ways():
    assert rag_twin("a/X.excalidraw.md") == "a/X.excalidraw.rag.md"
    assert rag_twin("a/X.excalidraw.rag.md") == "a/X.excalidraw.md"


def test_stem_drops_rag_and_md_suffixes():
    assert Material(path=f"{N}/lecture_notes/processed_outputs/E 2026-09-09.excalidraw.rag.md").stem == "E 2026-09-09.excalidraw"
    assert Material(path=f"{N}/professor_notes/processed_outputs/092126.md").stem == "092126"
    assert Material(path="").stem == ""


def catalog():
    return Catalog(course="econometrics", materials=[
        Material(path=f"{N}/professor_notes/processed_outputs/slides2.md", role="instructor", format="slides", order=[1_000_000, "", "slides2"]),
        Material(path=f"{N}/professor_notes/processed_outputs/slides1.md", role="instructor", format="slides", order=[1_000_000, "", "slides1"]),
        Material(path=f"{N}/class_2024/Slides/processed_outputs/1.Intro.md", role="instructor", format="slides", offering="2024"),
        Material(path=f"{N}/textbooks/processed_outputs/Hansen_2022/chapters/01_intro.rag.md", role="textbook", format="chapter", book="hansen"),
        Material(path=f"{N}/textbooks/processed_outputs/Hansen_2022/chapters/02_ols.rag.md", role="textbook", format="chapter", book="hansen"),
        Material(path=f"{N}/lecture_notes/processed_outputs/E 2026-09-09.excalidraw.rag.md", role="student_notes", format="excalidraw", flagged=False),
        Material(path=f"{N}/mixed/a.md", role="recitation"),
        Material(path=f"{N}/mixed/b.md", role="problem_set"),
    ])


def test_lookup_exact_twin_and_misses():
    c = catalog()
    assert c.lookup(f"C:/hub/{N}/professor_notes/processed_outputs/slides1.md").stem == "slides1"
    assert c.lookup(f"{N}/lecture_notes/processed_outputs/E 2026-09-09.excalidraw.md").role == "student_notes"
    assert c.lookup("C:/elsewhere/a.md") is None
    assert c.lookup(f"{N}/nowhere/x.md") is None
    assert f"{N}/nowhere/x.md" in c.misses and "C:/elsewhere/a.md" not in c.misses


def test_lookup_accepts_backslashes_and_resources_root():
    c = catalog()
    win = "C:\\hub\\academic_notes\\econometrics\\lecture_notes\\processed_outputs\\E 2026-09-09.excalidraw.rag.md"
    assert c.lookup(win).role == "student_notes"
    assert c.lookup("academic_resources/econometrics/professor_notes/processed_outputs/slides2.md").stem == "slides2"


def test_lookup_falls_back_to_the_nearest_ancestor_only_when_it_is_uniform():
    c = catalog()
    front = c.lookup(f"{N}/textbooks/processed_outputs/Hansen_2022/Hansen_2022.rag.md")
    assert front is not None and front.book == "hansen"
    assert c.lookup(f"{N}/mixed/c.md") is None


def test_by_role_filters_offering_and_sorts_by_order():
    c = catalog()
    assert [m.stem for m in c.by_role("instructor")] == ["slides1", "slides2"]
    assert [m.stem for m in c.by_role("instructor", offering="2024")] == ["1.Intro"]
    assert c.offerings() == ["2024"] and c.book_keys() == ["hansen"]
    assert {m.role for m in c.flagged()} == {"instructor", "textbook", "recitation", "problem_set"}


def test_json_round_trip_and_bad_data():
    c = catalog()
    again = Catalog.from_json(c.to_json())
    assert [m.path for m in again.materials] == [m.path for m in c.materials]
    assert "misses" not in c.to_json()
    with pytest.raises(CatalogError, match="catalog"):
        Catalog.from_json({"materials": []})
    with pytest.raises(CatalogError):
        Catalog.from_json({"course": "x", "materials": [{"nope": 1}]})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/core/course_materials/test_cm_model.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.course_materials'`

- [ ] **Step 3: Implement**

```python
# core/course_materials/__init__.py
"""What each converted file in a course is (role, format, offering), decided once per course. See
docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md."""
from .model import DECIDABLE, FORMATS, ROLES, Catalog, CatalogError, Material, normalize, rag_twin  # noqa: F401
```

```python
# core/course_materials/model.py
"""Material records and the per-course catalog that holds them. Pure data: no file reads here."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath

ROLES = ("syllabus", "instructor", "student_notes", "recitation", "problem_set", "exam", "textbook", "other")
FORMATS = ("slides", "handwritten", "typeset", "excalidraw", "chapter")
DECIDABLE = ("role", "format", "offering", "book", "date", "order")
_ROOTS = ("academic_notes", "academic_resources")


class CatalogError(ValueError):
    """A catalog or decisions file that cannot be read, or a decision that cannot be recorded."""


def normalize(path: str) -> str | None:
    """Hub-relative posix path under academic_notes/ for a path under either hub root; None if it has neither."""
    parts = (path or "").replace("\\", "/").split("/")
    idx = max((i for i, p in enumerate(parts) if p in _ROOTS), default=None)
    if idx is None:
        return None
    return "/".join(["academic_notes", *parts[idx + 1:]])


def rag_twin(path: str) -> str:
    """X.md <-> X.rag.md: the two converted forms of one source file."""
    if path.endswith(".rag.md"):
        return path[: -len(".rag.md")] + ".md"
    if path.endswith(".md"):
        return path[: -len(".md")] + ".rag.md"
    return path


@dataclass
class Material:
    path: str
    role: str = "other"
    format: str = "typeset"
    offering: str | None = None
    date: str | None = None
    book: str | None = None
    order: list = field(default_factory=lambda: [1_000_000, "", ""])
    confidence: float = 0.0
    flagged: bool = True
    evidence: list = field(default_factory=list)
    decided_by: str = "rules"

    @property
    def stem(self) -> str:
        name = PurePosixPath(self.path).name
        for suffix in (".rag.md", ".md"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name


@dataclass
class Catalog:
    course: str
    materials: list[Material]
    unknown_decisions: list[str] = field(default_factory=list)
    misses: set = field(default_factory=set, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._by_path = {m.path: m for m in self.materials}

    def lookup(self, path: str) -> Material | None:
        """The material at `path` (either hub root, either slash), its .rag twin, or the nearest catalogued ancestor
        folder whose materials all share one role, book and offering (so a book's front matter maps to the book)."""
        norm = normalize(path)
        if norm is None:
            return None
        for candidate in (norm, rag_twin(norm)):
            if candidate in self._by_path:
                return self._by_path[candidate]
        parts = norm.split("/")
        for depth in range(len(parts) - 1, 2, -1):  # parts[:3] is academic_notes/<course>/<top folder>
            prefix = "/".join(parts[:depth]) + "/"
            under = [m for m in self.materials if m.path.startswith(prefix)]
            if under:
                if len({(m.role, m.book, m.offering) for m in under}) == 1:
                    return under[0]
                break
        self.misses.add(norm)
        return None

    def flagged(self) -> list[Material]:
        return [m for m in self.materials if m.flagged]

    def by_role(self, role: str, offering: str | None = None) -> list[Material]:
        return sorted((m for m in self.materials if m.role == role and m.offering == offering),
                      key=lambda m: tuple(m.order))

    def offerings(self) -> list[str]:
        return sorted({m.offering for m in self.materials if m.offering})

    def book_keys(self) -> list[str]:
        return sorted({m.book for m in self.materials if m.book})

    def to_json(self) -> dict:
        return {"course": self.course, "materials": [asdict(m) for m in self.materials],
                "unknown_decisions": list(self.unknown_decisions)}

    @classmethod
    def from_json(cls, data: dict, source: str = "catalog") -> Catalog:
        try:
            return cls(course=data["course"], materials=[Material(**m) for m in data["materials"]],
                       unknown_decisions=list(data.get("unknown_decisions", [])))
        except (KeyError, TypeError) as exc:
            raise CatalogError(f"{source}: not a course-materials catalog ({exc})") from exc
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/core/course_materials/test_cm_model.py -q`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/course_materials/__init__.py core/course_materials/model.py tests/core/course_materials/test_cm_model.py
git commit -m "feat(course_materials): material and catalog model

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Signals and the vote combiner

**Files:**
- Create: `core/course_materials/signals.py`
- Create: `tests/core/course_materials/cm_helpers.py`
- Test: `tests/core/course_materials/test_cm_signals.py`

**Interfaces:**
- Consumes: nothing from Task 1 except the package.
- Produces:
  - `DECISIVE=10, STRONG=3, MEDIUM=2, WEAK=1`, `FLAG_BELOW=3`, `FLAG_MARGIN=2`
  - `@dataclass(frozen=True) Vote(signal: str, field: str, value: str, weight: int)`
  - `@dataclass Facts(path: str, frontmatter: dict, body: str, card_doc_type: str | None = None, pdf_shape: str | None = None)`
  - `@dataclass Decision(role: str, format: str, confidence: float, flagged: bool, votes: list[Vote])`
  - `pdf_shape(pdf_path: Path, pages: int = 3) -> str`: returns `"landscape"`, `"portrait"` or `"unavailable"`
  - `decide(facts: Facts) -> Decision`
  - Test helper `make_pdf(path: Path, width: float, height: float, rotate: int = 0) -> Path` in `cm_helpers.py`

- [ ] **Step 1: Write the test helper and failing tests**

```python
# tests/core/course_materials/cm_helpers.py
"""Fixture helpers for course_materials tests: blank PDFs of a given page shape, and small course trees."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

LANDSCAPE, PORTRAIT = (792, 612), (612, 792)


def make_pdf(path: Path, width: float, height: float, rotate: int = 0) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=width, height=height)
    if rotate:
        page.rotate(rotate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        writer.write(fh)
    return path


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
```

```python
# tests/core/course_materials/test_cm_signals.py
from cm_helpers import LANDSCAPE, PORTRAIT, make_pdf

from core.course_materials.signals import Facts, decide, pdf_shape

N = "academic_notes/demo"


def facts(path, fm=None, body="", card=None, shape=None):
    return Facts(path=f"{N}/{path}", frontmatter=fm or {}, body=body, card_doc_type=card, pdf_shape=shape)


def test_pdf_shape_reads_orientation_and_rotation_and_abstains_on_bad_files(tmp_path):
    assert pdf_shape(make_pdf(tmp_path / "l.pdf", *LANDSCAPE)) == "landscape"
    assert pdf_shape(make_pdf(tmp_path / "p.pdf", *PORTRAIT)) == "portrait"
    assert pdf_shape(make_pdf(tmp_path / "r.pdf", *PORTRAIT, rotate=90)) == "landscape"
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf")
    assert pdf_shape(tmp_path / "bad.pdf") == "unavailable"
    assert pdf_shape(tmp_path / "missing.pdf") == "unavailable"


def test_an_excalidraw_source_is_decisive_student_notes():
    d = decide(facts("x/processed_outputs/a.md", fm={"source_excalidraw": "a.excalidraw.md"}, body="exam exam midterm"))
    assert (d.role, d.format, d.flagged) == ("student_notes", "excalidraw", False)


def test_the_excalidraw_file_name_alone_is_a_medium_vote():
    d = decide(facts("x/E 2026-09-09 10.00.00.excalidraw.rag.md"))
    assert (d.role, d.format) == ("student_notes", "excalidraw") and d.flagged


def test_a_chapters_layout_is_a_decisive_textbook_under_any_folder_name():
    d = decide(facts("reading/processed_outputs/Greene_2018/chapters/03_ols.rag.md"))
    assert (d.role, d.format, d.flagged) == ("textbook", "chapter", False)
    front = decide(facts("textbooks/processed_outputs/Greene_2018/Greene_2018.rag.md"))
    assert front.role == "textbook" and front.flagged is False


def test_a_landscape_deck_is_instructor_slides_without_any_path_hint():
    d = decide(facts("misc/processed_outputs/week1.md", shape="landscape"))
    assert (d.role, d.format, d.flagged) == ("instructor", "slides", False)


def test_a_landscape_recitation_deck_ties_and_is_flagged():
    d = decide(facts("ta_sessions/processed_outputs/r1.md", shape="landscape", body="Recitation 1: review"))
    assert d.flagged


def test_a_portrait_scan_in_a_professor_folder_is_handwritten_and_flagged():
    body = "<!-- page 1 -->\n\nSept 21\n\nAssumptions 7.1\n(1) iid\n\n<!-- page 2 -->\n\nY = Xb + e\n"
    d = decide(facts("professor_notes/processed_outputs/092126.md", shape="portrait", body=body))
    assert (d.role, d.format, d.flagged) == ("instructor", "handwritten", True)


def test_a_portrait_document_with_headings_and_long_lines_is_typeset():
    body = "# Problem Set 3\n\n" + ("This is a long typeset line of the problem statement that goes on. " * 2 + "\n") * 6
    body += "\nProblem 1\n(a) x\n\nProblem 2\n(b) y\n"
    d = decide(facts("stuff/processed_outputs/week3.md", shape="portrait", body=body))
    assert (d.role, d.format) == ("problem_set", "typeset")


def test_index_card_doc_type_is_a_strong_role_vote():
    d = decide(facts("ta_notes/processed_outputs/n1.md", card="ta_notes"))
    assert d.role == "recitation" and d.flagged is False


def test_syllabus_wording_and_path_words():
    body = "Office hours: Tuesday. Grading: homework 40%. Course description: econometrics."
    d = decide(facts("syllabus/processed_outputs/s.md", body=body))
    assert d.role == "syllabus" and d.flagged is False


def test_nothing_known_is_other_and_flagged_with_evidence_of_the_pdf_state():
    d = decide(facts("x/processed_outputs/y.md", shape="unavailable"))
    assert (d.role, d.flagged) == ("other", True)
    assert any(v.signal == "pdf unavailable" for v in d.votes)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/core/course_materials/test_cm_signals.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.course_materials.signals'`

- [ ] **Step 3: Implement**

```python
# core/course_materials/signals.py
"""Evidence about one converted file, as weighted votes for its role and format. `decide` adds them up.

No signal is trusted alone except where the evidence is unambiguous (an Excalidraw source, a converted textbook's
chapters/ layout); folder and file names are only weak votes. No model calls."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from core.env.academic_hub_paths import TEXTBOOK_FOLDER_NAMES

DECISIVE, STRONG, MEDIUM, WEAK = 10, 3, 2, 1
FLAG_BELOW, FLAG_MARGIN = 3, 2

logging.getLogger("pypdf").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Vote:
    signal: str
    field: str  # "role" or "format"
    value: str
    weight: int  # 0 = evidence only


@dataclass
class Facts:
    path: str  # hub-relative, academic_notes/<course>/...
    frontmatter: dict
    body: str
    card_doc_type: str | None = None
    pdf_shape: str | None = None  # landscape, portrait, unavailable; None when no source PDF is named


@dataclass
class Decision:
    role: str
    format: str
    confidence: float
    flagged: bool
    votes: list[Vote] = field(default_factory=list)


def pdf_shape(pdf_path: Path, pages: int = 3) -> str:
    """Majority page orientation of the first pages, rotation applied."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        land = port = 0
        for page in reader.pages[:pages]:
            w, h = float(page.mediabox.width), float(page.mediabox.height)
            if int(page.get("/Rotate", 0) or 0) % 180 == 90:
                w, h = h, w
            if w > h * 1.1:
                land += 1
            else:
                port += 1
    except Exception:  # pypdf raises many types for damaged files; a missing shape only costs this signal
        return "unavailable"
    if land + port == 0:
        return "unavailable"
    return "landscape" if land > port else "portrait"


def excalidraw_signal(f: Facts) -> list[Vote]:
    if "source_excalidraw" in f.frontmatter:
        return [Vote("excalidraw source", "format", "excalidraw", DECISIVE),
                Vote("excalidraw source", "role", "student_notes", DECISIVE)]
    if ".excalidraw." in PurePosixPath(f.path).name:
        return [Vote("excalidraw file name", "format", "excalidraw", MEDIUM),
                Vote("excalidraw file name", "role", "student_notes", MEDIUM)]
    return []


_CHAPTER_FILE = re.compile(r"^\d+_")


def textbook_signal(f: Facts) -> list[Vote]:
    parts = f.path.split("/")
    chapter = len(parts) >= 2 and parts[-2] == "chapters" and bool(_CHAPTER_FILE.match(parts[-1]))
    if f.card_doc_type == "textbook" or chapter:
        return [Vote("textbook layout", "format", "chapter", DECISIVE), Vote("textbook layout", "role", "textbook", DECISIVE)]
    if any(p in TEXTBOOK_FOLDER_NAMES for p in parts[:-1]):
        return [Vote("textbook folder", "format", "chapter", STRONG), Vote("textbook folder", "role", "textbook", STRONG)]
    return []


def pdf_signal(f: Facts) -> list[Vote]:
    if f.pdf_shape == "landscape":
        # Lecture slides are by far the commonest landscape PDF; recitation and TA decks carry their own signals.
        return [Vote("pdf landscape", "format", "slides", STRONG), Vote("pdf landscape", "role", "instructor", STRONG)]
    if f.pdf_shape in ("portrait", "unavailable"):
        return [Vote(f"pdf {f.pdf_shape}", "format", f.pdf_shape, 0)]
    return []


_CARD_VOTES = {"problem_set": ("role", "problem_set"), "ta_notes": ("role", "recitation"),
               "syllabus": ("role", "syllabus"), "handwritten_notes": ("format", "handwritten"),
               "lecture_notes": ("role", "student_notes"), "excalidraw_notes": ("role", "student_notes")}


def card_signal(f: Facts) -> list[Vote]:
    hit = _CARD_VOTES.get(f.card_doc_type or "")
    return [Vote(f"index card {f.card_doc_type}", hit[0], hit[1], STRONG)] if hit else []


_CONTENT = (
    ("syllabus", re.compile(r"(?i)\b(office hours|grading|course (?:description|objectives|outline)|"
                            r"learning (?:outcomes|objectives)|required (?:texts?|readings?))\b"), 2),
    ("problem_set", re.compile(r"(?im)^\W*(?:problem|question|exercise)\s*\d+"), 2),
    ("exam", re.compile(r"(?i)\b(?:midterm|final exam|exam)\b"), 2),
    ("recitation", re.compile(r"(?i)\b(?:recitation|ta session|section notes)\b"), 1),
)


def content_signal(f: Facts, head: int = 6000) -> list[Vote]:
    text = f.body[:head]
    return [Vote(f"content: {role} wording", "role", role, MEDIUM)
            for role, pattern, need in _CONTENT if len(pattern.findall(text)) >= need]


_PATH_WORDS = {
    "professor": ("role", "instructor"), "prof": ("role", "instructor"), "instructor": ("role", "instructor"),
    "proof": ("role", "instructor"), "proofs": ("role", "instructor"),
    "slides": ("format", "slides"), "slide": ("format", "slides"), "handwritten": ("format", "handwritten"),
    "ta": ("role", "recitation"), "recitation": ("role", "recitation"), "recitations": ("role", "recitation"),
    "hw": ("role", "problem_set"), "homework": ("role", "problem_set"), "homeworks": ("role", "problem_set"),
    "problem": ("role", "problem_set"), "problems": ("role", "problem_set"), "pset": ("role", "problem_set"),
    "solution": ("role", "problem_set"), "solutions": ("role", "problem_set"),
    "exam": ("role", "exam"), "exams": ("role", "exam"), "midterm": ("role", "exam"),
    "syllabus": ("role", "syllabus"),
}
_WORD = re.compile(r"[a-z]+")


def path_signal(f: Facts) -> list[Vote]:
    below_course = f.path.split("/", 2)[-1].lower()
    words = sorted(set(_WORD.findall(below_course)) & set(_PATH_WORDS))
    return [Vote(f"path word '{w}'", *_PATH_WORDS[w], WEAK) for w in words]


_HEADING_LINE = re.compile(r"(?m)^#{1,3}\s")


def format_fallback(f: Facts) -> list[Vote]:
    """When nothing names a format: a portrait scan with few headings and short lines reads as handwriting."""
    if f.pdf_shape == "portrait":
        lines = sorted(len(ln) for ln in f.body.splitlines() if ln.strip())
        pages = max(f.body.count("<!-- page "), 1)
        if lines and lines[len(lines) // 2] < 60 and len(_HEADING_LINE.findall(f.body)) < pages / 2:
            return [Vote("portrait scan, few headings", "format", "handwritten", WEAK)]
    return [Vote("default", "format", "typeset", WEAK)]


SIGNALS = (excalidraw_signal, textbook_signal, pdf_signal, card_signal, content_signal, path_signal)


def _tally(votes: list[Vote], field_name: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for v in votes:
        if v.field == field_name and v.weight > 0:
            scores[v.value] = scores.get(v.value, 0) + v.weight
    return scores


def decide(f: Facts) -> Decision:
    votes = [v for signal in SIGNALS for v in signal(f)]
    if not any(v.field == "format" and v.weight > 0 for v in votes):
        votes += format_fallback(f)
    ranked = sorted(_tally(votes, "role").items(), key=lambda kv: (-kv[1], kv[0]))
    role, top = ranked[0] if ranked else ("other", 0)
    runner = ranked[1][1] if len(ranked) > 1 else 0
    formats = _tally(votes, "format")
    fmt = sorted(formats.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if formats else "typeset"
    margin = top - runner
    return Decision(role=role, format=fmt, confidence=float(margin),
                    flagged=top < FLAG_BELOW or margin < FLAG_MARGIN, votes=votes)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/core/course_materials/test_cm_signals.py -q`
Expected: PASS (11 tests). If `test_a_landscape_recitation_deck_ties_and_is_flagged` fails, check the scores: instructor 3 (landscape) against recitation 1 (`ta`) + 2 (content) = 3. That's a margin of 0, which is flagged.

- [ ] **Step 5: Commit**

```bash
git add core/course_materials/signals.py tests/core/course_materials/cm_helpers.py tests/core/course_materials/test_cm_signals.py
git commit -m "feat(course_materials): weighted signals for role and format

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Classifying a course, decisions, and the stored catalog

**Files:**
- Create: `core/course_materials/classify.py`
- Modify: `core/course_materials/__init__.py` (add the exports below)
- Test: `tests/core/course_materials/test_cm_classify.py`

**Interfaces:**
- Consumes:
  - `Material`, `Catalog`, `CatalogError`, `normalize`, `rag_twin`, `DECIDABLE`, `ROLES`, `FORMATS` (Task 1)
  - `Facts`, `decide`, `pdf_shape` (Task 2)
- Produces:
  - `GENERATED_DIRS: frozenset[str]`
  - `catalog_path(hub_root, course) -> Path`, `decisions_path(hub_root, course) -> Path`
  - `discover(hub_root, course) -> list[Path]`
  - `date_from_stem(stem: str) -> str | None`
  - `classify_file(hub_root, path: Path, cards: dict | None = None) -> Material`
  - `classify_path(path: str) -> Material`: path-only, no file reads
  - `load_decisions(hub_root, course) -> dict[str, dict]`
  - `record_decision(hub_root, course, path: str, **fields) -> str`: returns the key used; a directory key ends in `/`
  - `classify_course(hub_root, course, *, write: bool = True) -> Catalog`
  - `load_catalog(hub_root, course, *, refresh: str = "if_stale") -> Catalog`, where `refresh` is `"if_stale"`, `"always"` or `"never"`

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/course_materials/test_cm_classify.py
import json
import os

import pytest
from cm_helpers import LANDSCAPE, PORTRAIT, make_pdf, write

from core.course_materials import (Catalog, CatalogError, classify_course, classify_path, date_from_stem, load_catalog,
                                   record_decision)
from core.course_materials.classify import catalog_path, decisions_path

COURSE = "demo"
N = f"academic_notes/{COURSE}"


def build_course(tmp_path, with_pdfs=True):
    """A course whose folder names follow no convention: the classifier must lean on content, PDFs and layout."""
    hub = tmp_path / "hub"
    notes, res = hub / "academic_notes" / COURSE, hub / "academic_resources" / COURSE

    def converted(rel, body, pdf_rel=None, shape=None, extra=""):
        fm = f"---\nsource_pdf: academic_resources/{COURSE}/{pdf_rel}\n{extra}---\n\n" if pdf_rel else ""
        if pdf_rel and with_pdfs:
            make_pdf(res / pdf_rel, *shape)
        return write(notes / rel, fm + body)

    converted("misc/processed_outputs/week1.md", "# Intro\n\nDefinition 1 A thing\n", "misc/week1.pdf", LANDSCAPE)
    converted("stuff/processed_outputs/week3.md", "Problem 1\n(a) x\n\nProblem 2\n(b) y\n", "stuff/week3.pdf", PORTRAIT)
    converted("professor_notes/processed_outputs/092126.md",
              "<!-- page 1 -->\n\nSept 21\n\nAssumptions 7.1\n(1) iid\n", "professor_notes/092126.pdf", PORTRAIT)
    scene = "---\n\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n\n---\n==Switch to EXCALIDRAW VIEW==\n"
    write(notes / "notes" / "Demo 2026-09-09 10.00.00.excalidraw.md", scene)
    exc = "---\nsource_excalidraw: Demo 2026-09-09 10.00.00.excalidraw.md\n---\n\n"
    write(notes / "notes/processed_outputs/Demo 2026-09-09 10.00.00.excalidraw.md", exc + "chunk\n")
    write(notes / "notes/processed_outputs/Demo 2026-09-09 10.00.00.excalidraw.rag.md", exc + "### Expanded\n")
    write(notes / "reading/processed_outputs/Greene_Econometric_Analysis_2018/chapters/01_intro.rag.md", "# Intro\n")
    write(notes / "reading/processed_outputs/Greene_Econometric_Analysis_2018/chapters/02_ols.rag.md", "# OLS\n")
    converted("class_2023/deck/processed_outputs/1.Intro.md", "# Intro\n", "class_2023/deck/1.Intro.pdf", LANDSCAPE)
    write(res / "class_2023" / ".notes_subset.json", json.dumps({"label": "2023"}))
    write(notes / "summaries/guide.md", "# A generated study guide\n")
    return hub


def by_stem(catalog):
    return {m.stem: m for m in catalog.materials}


def test_classifies_a_course_with_unconventional_names(tmp_path):
    cat = by_stem(classify_course(build_course(tmp_path), COURSE))
    assert (cat["week1"].role, cat["week1"].format, cat["week1"].flagged) == ("instructor", "slides", False)
    assert cat["week3"].role == "problem_set"
    assert (cat["092126"].role, cat["092126"].format, cat["092126"].date) == ("instructor", "handwritten", "2026-09-21")
    assert cat["092126"].flagged
    assert (cat["01_intro"].role, cat["01_intro"].book) == ("textbook", "greene")
    assert cat["1.Intro"].offering == "2023" and cat["1.Intro"].role == "instructor"
    assert "week1" in cat and cat["week1"].offering is None


def test_one_record_per_source_preferring_rag_and_raw_scenes_and_generated_dirs_skipped(tmp_path):
    paths = [m.path for m in classify_course(build_course(tmp_path), COURSE).materials]
    excal = [p for p in paths if "Demo 2026-09-09" in p]
    assert excal == [f"{N}/notes/processed_outputs/Demo 2026-09-09 10.00.00.excalidraw.rag.md"]
    assert not any("summaries" in p for p in paths)


def test_the_catalog_is_written_and_reloaded(tmp_path):
    hub = build_course(tmp_path)
    classify_course(hub, COURSE)
    assert catalog_path(hub, COURSE).is_file()
    again = load_catalog(hub, COURSE, refresh="never")
    assert isinstance(again, Catalog) and len(again.materials) == 7


def test_decisions_win_survive_reclassification_and_can_exclude(tmp_path):
    hub = build_course(tmp_path)
    record_decision(hub, COURSE, f"{N}/stuff/processed_outputs/week3.md", role="exam")
    record_decision(hub, COURSE, f"{N}/misc/processed_outputs/week1.md", exclude=True)
    cat = by_stem(classify_course(hub, COURSE))
    assert (cat["week3"].role, cat["week3"].flagged, cat["week3"].decided_by) == ("exam", False, "review")
    assert "week1" not in cat
    assert json.loads(decisions_path(hub, COURSE).read_text(encoding="utf-8"))[f"{N}/stuff/processed_outputs/week3.md"] == {"role": "exam"}


def test_a_folder_decision_applies_to_everything_under_it(tmp_path):
    hub = build_course(tmp_path)
    key = record_decision(hub, COURSE, f"{N}/reading/processed_outputs/Greene_Econometric_Analysis_2018", book="greene-ea")
    assert key.endswith("/")
    cat = by_stem(classify_course(hub, COURSE))
    assert cat["01_intro"].book == cat["02_ols"].book == "greene-ea"


def test_decisions_for_missing_files_are_reported_and_kept(tmp_path):
    hub = build_course(tmp_path)
    record_decision(hub, COURSE, f"{N}/gone/old.md", role="exam")
    assert classify_course(hub, COURSE).unknown_decisions == [f"{N}/gone/old.md"]
    assert f"{N}/gone/old.md" in json.loads(decisions_path(hub, COURSE).read_text(encoding="utf-8"))


def test_bad_decisions_are_refused(tmp_path):
    hub = build_course(tmp_path)
    with pytest.raises(ValueError):
        record_decision(hub, COURSE, f"{N}/misc/processed_outputs/week1.md", role="lecturer")
    with pytest.raises(ValueError):
        record_decision(hub, COURSE, f"{N}/misc/processed_outputs/week1.md", colour="blue")
    with pytest.raises(CatalogError):
        record_decision(hub, COURSE, "C:/not/in/the/hub.md", role="exam")


def test_load_catalog_rebuilds_when_a_file_or_the_decisions_change(tmp_path):
    hub = build_course(tmp_path)
    classify_course(hub, COURSE)
    built = catalog_path(hub, COURSE).stat().st_mtime
    new = write(hub / N / "misc/processed_outputs/week2.md", "# More\n")
    os.utime(new, (built + 10, built + 10))
    assert "week2" in by_stem(load_catalog(hub, COURSE))
    assert "week2" in by_stem(load_catalog(hub, COURSE, refresh="never"))


def test_corrupt_catalog_and_decisions_raise_naming_the_file(tmp_path):
    hub = build_course(tmp_path)
    classify_course(hub, COURSE)
    catalog_path(hub, COURSE).write_text("{not json", encoding="utf-8")
    with pytest.raises(CatalogError, match=r"demo\.json"):
        load_catalog(hub, COURSE, refresh="never")
    decisions_path(hub, COURSE).write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(CatalogError, match="decisions"):
        classify_course(hub, COURSE)


def test_missing_source_pdfs_abstain_without_crashing(tmp_path):
    cat = by_stem(classify_course(build_course(tmp_path, with_pdfs=False), COURSE))
    assert any(e[0] == "pdf unavailable" for e in cat["week1"].evidence)
    assert cat["week1"].flagged


def test_crlf_frontmatter_is_read(tmp_path):
    hub = tmp_path / "hub"
    text = "---\r\nsource_excalidraw: a.excalidraw.md\r\n---\r\n\r\nbody\r\n"
    (hub / N / "x").mkdir(parents=True)
    (hub / N / "x" / "a.md").write_bytes(text.encode("utf-8"))
    assert classify_course(hub, COURSE).materials[0].role == "student_notes"


def test_index_cards_vote_and_a_corrupt_card_file_only_loses_that_signal(tmp_path):
    hub = build_course(tmp_path)
    write(hub / N / "loose/processed_outputs/n1.md", "plain text\n")
    cards = [{"path": f"academic_resources/{COURSE}/loose/processed_outputs/n1.md", "doc_type": "ta_notes"}]
    write(hub / ".index" / f"{COURSE}.json", json.dumps(cards))
    assert by_stem(classify_course(hub, COURSE))["n1"].role == "recitation"


def test_a_corrupt_index_card_file_only_loses_that_signal(tmp_path):
    hub = build_course(tmp_path)
    write(hub / ".index" / f"{COURSE}.json", "{broken")
    assert by_stem(classify_course(hub, COURSE))["week1"].role == "instructor"


def test_a_missing_course_folder_gives_an_empty_catalog_and_writes_nothing(tmp_path):
    cat = classify_course(tmp_path / "hub", "nope")
    assert cat.materials == [] and not (tmp_path / "hub" / ".index").exists()


def test_classify_path_needs_no_files():
    m = classify_path("C:/hub/academic_notes/microecon/textbooks/processed_outputs/Press_MT_2011/chapters/01_x.rag.md")
    assert (m.role, m.book) == ("textbook", "press")
    assert classify_path("").role == "other"


def test_dates_from_iso_and_mmddyy_stems():
    assert date_from_stem("Econometrics 2026-09-09 10.11.39.excalidraw") == "2026-09-09"
    assert date_from_stem("092126") == "2026-09-21"
    assert date_from_stem("133126") is None and date_from_stem("slides1") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/core/course_materials/test_cm_classify.py -q`
Expected: FAIL with `ImportError: cannot import name 'classify_course'`

- [ ] **Step 3: Implement**

```python
# core/course_materials/classify.py
"""Build, store and reload a course's material catalog, with the owner's decisions applied on top."""
from __future__ import annotations

import json
import re
from pathlib import Path

from core.env.academic_hub_paths import find_containing_offering_label, to_resources_root
from core.env.frontmatter import parse_frontmatter

from .model import DECIDABLE, FORMATS, ROLES, Catalog, CatalogError, Material, normalize, rag_twin
from .signals import Facts, decide, pdf_shape

# Folders other pipelines write into a course (study guides, guide plans, tutoring logs): outputs, not materials.
GENERATED_DIRS = frozenset({"summaries", "guide_plans", "tutoring"})
_RAW_SCENE = re.compile(r"(?m)^excalidraw-plugin:")
_ISO_DATE = re.compile(r"20\d\d-\d\d-\d\d")
_MMDDYY = re.compile(r"^(\d\d)(\d\d)(\d\d)$")
_LEADING_NUMBER = re.compile(r"^(\d{1,3})[._ \-]")
_HEAD_CHARS = 20000


def catalog_path(hub_root, course: str) -> Path:
    return Path(hub_root) / ".index" / "materials" / f"{course}.json"


def decisions_path(hub_root, course: str) -> Path:
    return Path(hub_root) / ".index" / "materials" / f"{course}.decisions.json"


def _course_dir(hub_root, course: str) -> Path:
    return Path(hub_root) / "academic_notes" / course


def _read(path: Path, limit: int = _HEAD_CHARS) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n")[:limit]


def discover(hub_root, course: str) -> list[Path]:
    """Every converted .md in the course: one per source (the .rag.md when both exist), without raw Excalidraw
    scene files or other pipelines' output folders."""
    base = _course_dir(hub_root, course)
    found: dict[str, Path] = {}
    for f in sorted(base.rglob("*.md")):
        if set(f.relative_to(base).parts[:-1]) & GENERATED_DIRS:
            continue
        key = str(f)[: -len(".rag.md")] if f.name.endswith(".rag.md") else str(f)[: -len(".md")]
        if key in found and not f.name.endswith(".rag.md"):
            continue
        found[key] = f
    return [f for f in found.values() if not _RAW_SCENE.search(_read(f, 400))]


def date_from_stem(stem: str) -> str | None:
    m = _ISO_DATE.search(stem)
    if m:
        return m.group(0)
    m = _MMDDYY.match(stem)
    if m and 1 <= int(m.group(1)) <= 12 and 1 <= int(m.group(2)) <= 31:
        return f"20{m.group(3)}-{m.group(1)}-{m.group(2)}"
    return None


def _order(stem: str, date: str | None) -> list:
    m = _LEADING_NUMBER.match(stem)
    return [int(m.group(1)) if m else 1_000_000, date or "", stem.lower()]


def _book(path: str) -> str:
    """Short key for a textbook: the first word of its folder, e.g. Hansen_ECONOMETRICS_2022 -> hansen."""
    parts = path.split("/")
    if "chapters" in parts:
        folder = parts[parts.index("chapters") - 1]
    elif "processed_outputs" in parts and parts.index("processed_outputs") + 2 < len(parts):
        folder = parts[parts.index("processed_outputs") + 1]
    else:
        folder = parts[-2] if len(parts) > 1 else "book"
    return re.sub(r"[^a-z0-9]", "", re.split(r"[_\s\-]+", folder.strip())[0].lower()) or "book"


def _cards(hub_root, course: str) -> dict[str, str]:
    """Index-card doc_type by normalised path. The index belongs to another pipeline: a bad file only costs this signal."""
    p = Path(hub_root) / ".index" / f"{course}.json"
    try:
        cards = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
    except ValueError:
        return {}
    out: dict[str, str] = {}
    for c in cards if isinstance(cards, list) else []:
        if not isinstance(c, dict) or not c.get("doc_type"):
            continue
        for key in (c.get("path"), c.get("rag_md_path")):
            norm = normalize(key or "")
            if norm:
                out[norm] = c["doc_type"]
    return out


def _source_pdf(hub_root, frontmatter: dict) -> Path | None:
    raw = (frontmatter.get("source_pdf") or "").strip().strip('"')
    if not raw.lower().endswith(".pdf"):
        return None
    p = Path(raw)
    return p if p.is_absolute() else Path(hub_root) / raw


def _offering(path: Path) -> str | None:
    try:
        return find_containing_offering_label(to_resources_root(str(path)))
    except ValueError:
        return None


def _material(norm: str, facts: Facts, offering: str | None) -> Material:
    d = decide(facts)
    stem = Material(path=norm).stem
    date = date_from_stem(stem)
    return Material(path=norm, role=d.role, format=d.format, offering=offering, date=date,
                    book=_book(norm) if d.role == "textbook" else None, order=_order(stem, date),
                    confidence=d.confidence, flagged=d.flagged,
                    evidence=[[v.signal, v.field, v.value, v.weight] for v in d.votes])


def classify_file(hub_root, path: Path, cards: dict | None = None) -> Material:
    norm = normalize(str(path)) or str(path).replace("\\", "/")
    fm, body = parse_frontmatter(_read(path)) if path.is_file() else ({}, "")
    pdf = _source_pdf(hub_root, fm)
    facts = Facts(path=norm, frontmatter=fm, body=body, card_doc_type=(cards or {}).get(norm),
                  pdf_shape=pdf_shape(pdf) if pdf else None)
    return _material(norm, facts, _offering(path))


def classify_path(path: str) -> Material:
    """Path-only classification for a path that is not in the catalog: no file read, no offering."""
    norm = normalize(path) or (path or "").replace("\\", "/")
    return _material(norm, Facts(path=norm, frontmatter={}, body=""), None)


def load_decisions(hub_root, course: str) -> dict[str, dict]:
    p = decisions_path(hub_root, course)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CatalogError(f"decisions file is not valid JSON: {p} ({exc})") from exc
    if not isinstance(data, dict):
        raise CatalogError(f"decisions file must be a JSON object keyed by path: {p}")
    return data


def record_decision(hub_root, course: str, path: str, **fields) -> str:
    """Store the owner's decision for one file, or for every file under a folder. Returns the key used."""
    norm = normalize(path)
    if norm is None:
        raise CatalogError(f"not a path under the hub's academic_notes/ or academic_resources/: {path}")
    unknown = sorted(set(fields) - set(DECIDABLE) - {"exclude"})
    if unknown:
        raise ValueError(f"unknown decision field(s) {unknown}; allowed: {[*DECIDABLE, 'exclude']}")
    if fields.get("role") is not None and fields["role"] not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if fields.get("format") is not None and fields["format"] not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    key = norm.rstrip("/") + "/" if (Path(hub_root) / norm).is_dir() else norm
    data = load_decisions(hub_root, course)
    data[key] = {**data.get(key, {}), **{k: v for k, v in fields.items() if v is not None and v is not False}}
    p = decisions_path(hub_root, course)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return key


def _decision_for(path: str, decisions: dict) -> dict:
    """Folder decisions from the outermost in, then the file's own (or its .rag twin's)."""
    merged: dict = {}
    for key in sorted((k for k in decisions if k.endswith("/") and path.startswith(k)), key=len):
        merged.update(decisions[key])
    merged.update(decisions.get(path) or decisions.get(rag_twin(path)) or {})
    return merged


def _apply(m: Material, decision: dict) -> None:
    for key in DECIDABLE:
        if key in decision:
            setattr(m, key, decision[key])
    if m.role == "textbook" and not m.book:
        m.book = _book(m.path)
    m.flagged, m.decided_by = False, "review"


def classify_course(hub_root, course: str, *, write: bool = True) -> Catalog:
    if not _course_dir(hub_root, course).is_dir():
        return Catalog(course=course, materials=[])
    decisions = load_decisions(hub_root, course)
    cards = _cards(hub_root, course)
    files = discover(hub_root, course)
    materials: list[Material] = []
    for f in files:
        m = classify_file(hub_root, f, cards)
        decision = _decision_for(m.path, decisions)
        if decision.get("exclude"):
            continue
        if decision:
            _apply(m, decision)
        materials.append(m)
    seen = {p for p in (normalize(str(f)) for f in files) if p}
    seen |= {rag_twin(p) for p in seen}
    unknown = sorted(k for k in decisions
                     if not (any(p.startswith(k) for p in seen) if k.endswith("/") else k in seen))
    catalog = Catalog(course=course, materials=materials, unknown_decisions=unknown)
    if write:
        p = catalog_path(hub_root, course)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(catalog.to_json(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return catalog


def _stale(hub_root, course: str) -> bool:
    p = catalog_path(hub_root, course)
    if not p.is_file():
        return True
    built = p.stat().st_mtime
    d = decisions_path(hub_root, course)
    if d.is_file() and d.stat().st_mtime > built:
        return True
    return any(f.stat().st_mtime > built for f in _course_dir(hub_root, course).rglob("*.md"))


def load_catalog(hub_root, course: str, *, refresh: str = "if_stale") -> Catalog:
    """The stored catalog, rebuilt first when missing or older than the course's files or decisions."""
    if refresh == "always" or (refresh == "if_stale" and _stale(hub_root, course)):
        return classify_course(hub_root, course)
    p = catalog_path(hub_root, course)
    if not p.is_file():
        raise CatalogError(f"no catalog for {course}: run python -m core.course_materials.cli --course {course} classify")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CatalogError(f"catalog is not valid JSON: {p} ({exc})") from exc
    return Catalog.from_json(data, source=str(p))
```

Note on `test_load_catalog_rebuilds_when_a_file_or_the_decisions_change`: `refresh="never"` after a rebuild returns the rebuilt catalog, because `load_catalog` wrote it.

```python
# core/course_materials/__init__.py  (replace the import line)
from .classify import (classify_course, classify_file, classify_path, date_from_stem, load_catalog,  # noqa: F401
                       load_decisions, record_decision)
from .model import DECIDABLE, FORMATS, ROLES, Catalog, CatalogError, Material, normalize, rag_twin  # noqa: F401
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/core/course_materials -q`
Expected: PASS (all of Tasks 1-3)

- [ ] **Step 5: Commit**

```bash
git add core/course_materials/classify.py core/course_materials/__init__.py tests/core/course_materials/test_cm_classify.py
git commit -m "feat(course_materials): classify a course, store the catalog, apply owner decisions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Course-materials command line

**Files:**
- Create: `core/course_materials/cli.py`
- Test: `tests/core/course_materials/test_cm_cli.py`

**Interfaces:**
- Consumes: `classify_course`, `load_catalog`, `record_decision`, `ROLES`, `FORMATS`, `CatalogError`, `Catalog` (Tasks 1-3)
- Produces:
  - `main(argv: list[str] | None = None) -> int`
  - `summarize(catalog: Catalog) -> str`
  - Commands:
    - `classify`
    - `flagged`: JSON list of `{path, role, format, offering, book, confidence, evidence}`
    - `decide PATH [--role R] [--format F] [--offering L] [--book K] [--date D] [--exclude]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/course_materials/test_cm_cli.py
import json

from test_cm_classify import COURSE, N, build_course

from core.course_materials.cli import main


def run(capsys, hub, *args):
    code = main(["--hub-root", str(hub), "--course", COURSE, *args])
    return code, capsys.readouterr()


def test_classify_prints_counts_and_flagged_files_with_their_evidence(tmp_path, capsys):
    code, out = run(capsys, build_course(tmp_path), "classify")
    assert code == 0
    assert "demo: 7 materials" in out.out
    assert "instructor:" in out.out and "flagged (" in out.out
    assert "092126.md" in out.out and "path word 'professor'" in out.out


def test_flagged_prints_json_rows(tmp_path, capsys):
    hub = build_course(tmp_path)
    run(capsys, hub, "classify")
    code, out = run(capsys, hub, "flagged")
    rows = json.loads(out.out)
    assert code == 0 and any(r["path"].endswith("092126.md") for r in rows)
    assert set(rows[0]) == {"path", "role", "format", "offering", "book", "confidence", "evidence"}


def test_decide_records_and_bad_values_exit_one(tmp_path, capsys):
    hub = build_course(tmp_path)
    code, out = run(capsys, hub, "decide", f"{N}/professor_notes/processed_outputs/092126.md", "--role", "instructor")
    assert code == 0 and "recorded" in out.out
    _, out = run(capsys, hub, "flagged")
    assert not any(r["path"].endswith("092126.md") for r in json.loads(out.out))
    code, out = run(capsys, hub, "decide", "C:/elsewhere/x.md", "--role", "exam")
    assert code == 1 and "error:" in out.err
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/core/course_materials/test_cm_cli.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.course_materials.cli'`

- [ ] **Step 3: Implement**

```python
# core/course_materials/cli.py
"""Classify a course's materials, list the files that need the owner's eye, and record decisions.

  python -m core.course_materials.cli --hub-root <academic-hub> --course <course> classify
  python -m core.course_materials.cli --hub-root <academic-hub> --course <course> flagged
  python -m core.course_materials.cli --hub-root <academic-hub> --course <course> decide <path> --role instructor
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from .classify import classify_course, load_catalog, record_decision
from .model import FORMATS, ROLES, Catalog, CatalogError


def _why(evidence: list) -> str:
    return "; ".join(f"{signal} {field_}={value} +{weight}" for signal, field_, value, weight in evidence if weight)


def summarize(catalog: Catalog) -> str:
    lines = [f"{catalog.course}: {len(catalog.materials)} materials"]
    for role in ROLES:
        group = [m for m in catalog.materials if m.role == role]
        if group:
            formats = Counter(m.format for m in group)
            lines.append(f"  {role}: {len(group)} (" + ", ".join(f"{k} {v}" for k, v in sorted(formats.items())) + ")")
    for label in catalog.offerings():
        lines.append(f"  offering {label}: {sum(m.offering == label for m in catalog.materials)}")
    flagged = catalog.flagged()
    lines.append(f"flagged ({len(flagged)}):")
    lines += [f"  {m.path} -> {m.role}/{m.format} (margin {m.confidence:g}): {_why(m.evidence)}" for m in flagged]
    if catalog.unknown_decisions:
        lines.append(f"decisions for files that no longer exist ({len(catalog.unknown_decisions)}, kept):")
        lines += [f"  {p}" for p in catalog.unknown_decisions]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="course_materials", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hub-root", required=True, help="the academic-hub folder")
    p.add_argument("--course", required=True, help="course folder name under academic_notes/")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("classify", help="build or refresh the catalog and print a summary")
    sub.add_parser("flagged", help="print the flagged materials as JSON rows (for the review page)")
    d = sub.add_parser("decide", help="record the owner's decision for one file or folder")
    d.add_argument("path", help="hub-relative or absolute path; a folder applies to everything under it")
    d.add_argument("--role", choices=ROLES)
    d.add_argument("--format", choices=FORMATS)
    d.add_argument("--offering")
    d.add_argument("--book")
    d.add_argument("--date")
    d.add_argument("--exclude", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "classify":
            print(summarize(classify_course(args.hub_root, args.course)))
        elif args.cmd == "flagged":
            rows = [{"path": m.path, "role": m.role, "format": m.format, "offering": m.offering, "book": m.book,
                     "confidence": m.confidence, "evidence": m.evidence}
                    for m in load_catalog(args.hub_root, args.course).flagged()]
            print(json.dumps(rows, indent=1, ensure_ascii=False))
        else:
            key = record_decision(args.hub_root, args.course, args.path, role=args.role, format=args.format,
                                  offering=args.offering, book=args.book, date=args.date, exclude=args.exclude)
            print(f"recorded decision for {key}")
    except (CatalogError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/core/course_materials -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/course_materials/cli.py tests/core/course_materials/test_cm_cli.py
git commit -m "feat(course_materials): classify, flagged and decide commands

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Concept-graph citation keys from the catalog

**Files:**
- Modify: `agent/concept_graph/sources.py` (replace the hard-coded classification, lines 9-76)
- Modify: `agent/concept_graph/retrieval.py:20-35` (IndexRetriever), `:47-58` (LexicalRetriever init), `:95` (lexical call), `:146-155` (factory)
- Modify tests:
  - `tests/agent/concept_graph/test_cg_sources.py` (rewrite)
  - `tests/agent/concept_graph/test_cg_sources_refs.py:9` (`"rubinstein"` → `"rubenstein"`)
  - `tests/agent/concept_graph/test_cg_retrieval.py:24` (`"mwg"` → `"press"`, plus a catalog test)

**Interfaces:**
- Consumes: `Catalog`, `Material`, `classify_path`, `date_from_stem`, `normalize` from `core.course_materials`
- Produces:
  - `source_key(m: Material) -> str`
  - `classify_passage(path: str, citation: str = "", catalog: Catalog | None = None) -> tuple[str, str]`
  - `IndexRetriever(hub_root, course, client, catalog=None)`
  - `LexicalRetriever(hub_root, course, max_per_file=3, catalog=None)`
  - `make_resilient_retriever(hub_root, course, notify=None, catalog=None)`

- [ ] **Step 1: Write the failing tests**

Replace `tests/agent/concept_graph/test_cg_sources.py` with:

```python
from agent.concept_graph.sources import Passage, classify_passage, source_key
from core.course_materials import Catalog, Material

HUB = "C:/hub/academic-hub/academic_notes/microecon"
N = "academic_notes/microecon"


def test_without_a_catalog_paths_are_classified_by_their_own_shape():
    rub = f"{HUB}/textbooks/processed_outputs/Rubenstein_Lecture_Notes_2026/chapters/02_preferences.rag.md"
    assert classify_passage(rub, "§2.1 Preference relations, p. 12") == ("rubenstein", "ch. 2, §2.1 Preference relations, p. 12")
    assert classify_passage(f"{HUB}/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_x.rag.md") == ("press", "ch. 1")
    assert classify_passage(f"{HUB}/lecture_notes/processed_outputs/Microeconomics 2026-09-15 10.15.55.excalidraw.rag.md") == ("lecture", "2026-09-15")
    assert classify_passage(f"{HUB}/professor_notes/processed_outputs/2.Utility_Maximization_1.md") == ("slides", "Utility Maximization 1")
    assert classify_passage(f"{HUB}/problem_sets/processed_outputs/Homework_2.md") == ("hw", "Homework_2")
    assert classify_passage(f"{HUB}/summaries/study_guide.md") == ("other", "study_guide")


def test_ref_is_never_empty():
    for path in ("", "x.md", "C:/a/b/.md", "C:/hub/textbooks/Rubenstein_X/chapters/readme.rag.md"):
        source, ref = classify_passage(path, "")
        assert source and ref


def test_passage_exposes_its_offered_citation():
    p = Passage(id="P1", source="mwg", ref="ch. 1", text="t", path="p")
    assert p.offered == ("mwg", "ch. 1")


def test_the_catalog_decides_book_keys_offerings_and_handwritten_notes():
    cat = Catalog(course="microecon", materials=[
        Material(path=f"{N}/textbooks/processed_outputs/Press_MT_2011/chapters/01_x.rag.md", role="textbook", format="chapter", book="mwg"),
        Material(path=f"{N}/2024_class/Post lecture notes/processed_outputs/7.Consumer_Choice_2.md", role="instructor",
                 format="slides", offering="2024"),
        Material(path=f"{N}/2025_class/Homeworks/Solutions/processed_outputs/HW3_Sol.md", role="problem_set", offering="2025"),
        Material(path=f"{N}/2025_class/processed_outputs/Micro_I_Recitation_Notes.md", role="recitation", offering="2025"),
        Material(path=f"{N}/professor_notes/processed_outputs/092126.md", role="instructor", format="handwritten", date="2026-09-21"),
    ])
    assert classify_passage(f"{HUB}/textbooks/processed_outputs/Press_MT_2011/chapters/01_x.rag.md", "", cat) == ("mwg", "ch. 1")
    assert classify_passage(f"{HUB}/textbooks/processed_outputs/Press_MT_2011/Press_MT_2011.rag.md", "", cat)[0] == "mwg"
    assert classify_passage(f"{HUB}/2024_class/Post lecture notes/processed_outputs/7.Consumer_Choice_2.md", "", cat) == ("slides-2024", "Consumer Choice 2")
    assert classify_passage(f"{HUB}/2025_class/Homeworks/Solutions/processed_outputs/HW3_Sol.md", "", cat) == ("hw-2025", "HW3_Sol")
    assert classify_passage(f"{HUB}/2025_class/processed_outputs/Micro_I_Recitation_Notes.md", "", cat) == ("recitation-2025", "Micro I Recitation Notes")
    assert classify_passage(f"{HUB}/professor_notes/processed_outputs/092126.md", "", cat) == ("notes", "2026-09-21")


def test_a_path_the_catalog_lacks_is_classified_alone_and_remembered_as_a_miss():
    cat = Catalog(course="microecon", materials=[])
    assert classify_passage(f"{HUB}/problem_sets/processed_outputs/Homework_2.md", "", cat) == ("hw", "Homework_2")
    assert f"{N}/problem_sets/processed_outputs/Homework_2.md" in cat.misses


def test_source_key_rules():
    assert source_key(Material(path="x", role="instructor", format="slides")) == "slides"
    assert source_key(Material(path="x", role="instructor", format="typeset")) == "slides"
    assert source_key(Material(path="x", role="instructor", format="handwritten", offering="2024")) == "notes-2024"
    assert source_key(Material(path="x", role="textbook", book="hansen", offering="2024")) == "hansen"
    assert source_key(Material(path="x", role="syllabus")) == "syllabus"
```

In `tests/agent/concept_graph/test_cg_sources_refs.py`, change `assert source == "rubinstein"` to `assert source == "rubenstein"`.

In `tests/agent/concept_graph/test_cg_retrieval.py`, change the last assertion to expect `("press", "ch. 1, §1.B, p. 5", "body text")`, and append:

```python
def test_index_retriever_uses_the_catalog_for_book_keys(monkeypatch):
    from core.course_materials import Catalog, Material

    path = "C:/hub/academic_notes/microecon/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md"

    def retrieve_passages(roots, query, client, course=None, top_k=6, **kw):
        return [SimpleNamespace(path=path, citation="", text="t")]

    fake = types.ModuleType("agent.rag.rag_agent")
    fake.retrieve_passages = retrieve_passages
    monkeypatch.setitem(sys.modules, "agent.rag.rag_agent", fake)
    cat = Catalog(course="microecon", materials=[Material(
        path="academic_notes/microecon/textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md",
        role="textbook", format="chapter", book="mwg")])
    got = IndexRetriever("C:/hub", "microecon", object(), catalog=cat).retrieve("q", 1)
    assert (got[0].source, got[0].ref) == ("mwg", "ch. 1")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/agent/concept_graph/test_cg_sources.py tests/agent/concept_graph/test_cg_sources_refs.py tests/agent/concept_graph/test_cg_retrieval.py -q`
Expected: FAIL (`cannot import name 'source_key'`; old keys)

- [ ] **Step 3: Implement**

Replace `agent/concept_graph/sources.py` with:

```python
"""Retrieved passages and the citation keys they are offered under.

A passage's key comes from what its file is (core.course_materials): a textbook by its book key, instructor slides
or notes, the student's lecture notes, and so on, with an earlier offering's label as a suffix."""
from __future__ import annotations

import re

from core.agent_tasks.tasks import Passage  # noqa: F401  (re-exported: the very object core defines)
from core.course_materials import Catalog, Material, classify_path, date_from_stem, normalize

_CHAPTER = re.compile(r"/chapters/(\d+)_")
_PAGE = re.compile(r",?\s*(p\. ?[\d\-–]+)$")
_ROLE_KEYS = {"student_notes": "lecture", "recitation": "recitation", "problem_set": "hw", "exam": "exam",
              "syllabus": "syllabus"}


def _clean_citation(citation: str, limit: int = 110) -> str:
    """A citation that is safe to copy back exactly: one line, no markdown emphasis, bounded length."""
    text = re.sub(r"\s+", " ", (citation or "").replace("*", "").replace("`", "").replace("#", "")).strip()
    text = re.sub(r"\s*:\s*", " - ", text)  # a colon inside a plain YAML value would make it invalid
    page = _PAGE.search(text)
    tail = f", {page.group(1)}" if page else ""
    head = text[: page.start()] if page else text
    if len(head) + len(tail) > limit:
        head = head[: max(limit - len(tail) - 1, 10)].rstrip() + "…"
    return head + tail


def _chapter_ref(path: str, stem: str, citation: str) -> str:
    m = _CHAPTER.search(path)
    base = f"ch. {int(m.group(1))}" if m else (stem or "unknown")
    citation = _clean_citation(citation)
    return f"{base}, {citation}" if citation else base


def _deck_title(stem: str) -> str:
    return re.sub(r"^\d+\.\s*", "", stem).replace("_", " ").strip() or stem


def source_key(m: Material) -> str:
    if m.role == "textbook":
        return m.book or "book"
    if m.role == "instructor":
        key = "notes" if m.format == "handwritten" else "slides"
    else:
        key = _ROLE_KEYS.get(m.role, "other")
    return f"{key}-{m.offering}" if m.offering else key


def classify_passage(path: str, citation: str = "", catalog: Catalog | None = None) -> tuple[str, str]:
    """Map a retrieved passage's file path (and rendered citation) to the (source, ref) pair a card offers.

    The ref is always built from `path` itself (a book's front matter found through its folder still cites its own
    file); the catalog only says what kind of file it is. The ref is never empty."""
    m = (catalog.lookup(path) if catalog is not None else None) or classify_path(path)
    p = normalize(path) or (path or "").replace("\\", "/")
    stem = Material(path=p).stem
    date = date_from_stem(stem)
    if m.role == "textbook":
        ref = _chapter_ref(p, stem, citation)
    elif m.role == "student_notes":
        ref = date or stem
    elif m.role == "instructor":
        ref = (date or _deck_title(stem)) if m.format == "handwritten" else _deck_title(stem)
    elif m.role == "recitation":
        ref = _deck_title(stem) or date or stem
    else:
        ref = stem
    return source_key(m), ref or "unknown"
```

In `agent/concept_graph/retrieval.py`:
- `IndexRetriever.__init__(self, hub_root: str, course: str, client, catalog=None)`: store `self.catalog = catalog`. The call becomes `classify_passage(r.path, r.citation, self.catalog)`.
- `LexicalRetriever.__init__(self, hub_root: str, course: str, max_per_file: int = 3, catalog=None)`: store `self.catalog`. The call becomes `classify_passage(path, _render_citation(c), self.catalog)`.
- In the factory:

```python
def make_resilient_retriever(hub_root: str, course: str, notify: Callable[[str], None] | None = None,
                             catalog=None) -> ResilientRetriever:
    ...
            backends.append((label, IndexRetriever(hub_root, course, make_gemini_client(env), catalog=catalog)))
    ...
    backends.append(("keyword", LexicalRetriever(hub_root, course, catalog=catalog)))
```

- [ ] **Step 4: Run the concept-graph tests**

Run: `$PY -m pytest tests/agent/concept_graph -q`
Expected:
- `test_cg_sources*`, `test_cg_retrieval*` and `test_cg_fill_robustness` pass.
- Seed tests that pass `textbook_chapters={"mwg": ...}`, or that expect `slides-2024` from a fixture without markers, may now fail. Task 6 rewrites those, so note them and move on.
- Any other failure means a broken key mapping. Fix it before committing.

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/sources.py agent/concept_graph/retrieval.py tests/agent/concept_graph/test_cg_sources.py tests/agent/concept_graph/test_cg_sources_refs.py tests/agent/concept_graph/test_cg_retrieval.py
git commit -m "feat(concept_graph): citation keys from the course-materials catalog

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Seed evidence by role

**Files:**
- Modify: `agent/concept_graph/stages/seed.py`:
  - lines 28-30 (`_STATEMENT`)
  - 134-165 (`statement_anchors`)
  - 188-283 (`outline_context`, rewritten)
  - 299-308 (`make_tasks` signature and call)
  - imports at lines 8-16
- Modify tests:
  - `tests/agent/concept_graph/test_cg_seed_outline.py` (lines 105-112, 169-179, plus new tests)
- Test (new): `tests/agent/concept_graph/test_cg_seed_catalog.py`

**Interfaces:**
- Consumes:
  - `classify_passage`, `source_key` (Task 5)
  - `load_catalog`, `Catalog`, `record_decision` (Task 3)
- Produces:
  - `outline_context(hub_root, course, *, config=None, catalog=None, max_chars=12000) -> tuple[str, list[Passage]]`
  - `make_tasks(store, retriever=None, *, hub_root=None, course=None, redo=False, catalog=None, **_ignored)`
  - `ROLE_CAPS = {"instructor": 30, "student_notes": 30, "recitation": 8, "prior": 15}`

- [ ] **Step 1: Write the failing tests**

In `tests/agent/concept_graph/test_cg_seed_outline.py`:
- In `test_textbook_section_headings_appear_only_for_configured_chapters`, change `{"mwg": [1]}` to `{"press": [1]}`.
- Replace `test_outline_offers_earlier_years_post_lecture_slides_under_their_own_source` with:

```python
def test_outline_offers_earlier_offerings_slides_under_their_own_source(tmp_path):
    from pypdf import PdfWriter

    hub = rich_hub(tmp_path)
    for year, folder in (("2024", "Post lecture notes"), ("2025", "Post-Lecture Notes")):
        res = hub / "academic_resources" / "microecon" / f"{year}_class"
        (res / folder).mkdir(parents=True)
        (res / ".notes_subset.json").write_text('{"label": "%s"}' % year, encoding="utf-8")
        writer = PdfWriter()
        writer.add_blank_page(width=792, height=612)
        with open(res / folder / "8.Production.pdf", "wb") as fh:
            writer.write(fh)
        d = hub / "academic_notes" / "microecon" / f"{year}_class" / folder / "processed_outputs"
        d.mkdir(parents=True)
        (d / "8.Production.md").write_text(
            f"---\nsource_pdf: academic_resources/microecon/{year}_class/{folder}/8.Production.pdf\n---\n\n"
            "Production\n\nDefinition\nA production set is a set of feasible input-output plans\n", encoding="utf-8")
    context, passages = seed.outline_context(str(hub), "microecon")
    assert {p.source for p in passages if p.source.endswith(("2024", "2025"))} == {"slides-2024", "slides-2025"}
    assert any(p.source == "slides-2025" and p.ref == "Production" for p in passages)
    assert "2024 offering slide sets (in order): Production" in context
```

Create `tests/agent/concept_graph/test_cg_seed_catalog.py`:

```python
"""Seed evidence built from the course-materials catalog: headings, instructor notes, caps, decisions."""
from agent.concept_graph.schema import SeedConfig
from agent.concept_graph.stages import seed
from core.course_materials import record_decision

ECON = "econometrics"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def econ_hub(tmp_path):
    hub = tmp_path / "hub"
    n = hub / "academic_notes" / ECON
    write(n / "professor_notes/processed_outputs/slides2.md",
          "# Properties of OLS\n\n# Gauss Markov Theorem\n\n**Assumption 4.**\nE[e|X] = 0 holds here\n\n# Omitted variables bias\n")
    write(n / "professor_notes/processed_outputs/092126.md",
          "<!-- page 1 -->\n\nSept 21\n\nAssumptions 7.1 $n = \\text{sample size}$.\n\n(1) iid\n")
    for stamp, text in (("10.19.22", "# Delta method\n"), ("14.16.17", "# Wald test\n")):
        write(n / f"lecture_notes/processed_outputs/Econometrics 2026-10-07 {stamp}.excalidraw.rag.md",
              "---\nsource_excalidraw: x\n---\n\n" + text)
    write(n / "ta_notes/processed_outputs/TA1.md", "Recitation 1\n\n# Matrix algebra review\n")
    return hub


def test_slide_headings_and_numbered_assumptions_reach_the_card(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    text = "\n".join(p.text for p in passages)
    assert "Gauss Markov Theorem" in text and "Omitted variables bias" in text
    assert "Assumption 4 E[e|X] = 0 holds here" in text
    assert "Assumptions 7.1 $n" in text


def test_dated_instructor_notes_join_the_lecture_timeline(tmp_path):
    hub = econ_hub(tmp_path)
    record_decision(hub, ECON, f"academic_notes/{ECON}/professor_notes/processed_outputs/092126.md",
                    role="instructor", format="handwritten")
    context, passages = seed.outline_context(str(hub), ECON)
    assert "2026-09-21" in context.split("Lecture dates with notes: ")[1].splitlines()[0]
    assert any(p.source == "notes" and p.ref == "2026-09-21" for p in passages)


def test_two_lecture_notes_on_one_date_are_both_offered(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    lecture = [p for p in passages if p.source == "lecture" and p.ref == "2026-10-07"]
    assert len(lecture) == 1 and "Delta method" in lecture[0].text and "Wald test" in lecture[0].text


def test_recitation_material_offers_headings_only(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    rec = [p for p in passages if p.source == "recitation"]
    assert rec and "Matrix algebra review" in rec[0].text


def test_role_caps_limit_instructor_passages(tmp_path, monkeypatch):
    hub = econ_hub(tmp_path)
    for i in range(5):
        write(hub / "academic_notes" / ECON / f"professor_notes/processed_outputs/{i}.Deck.md", f"# Topic {i}\n")
    monkeypatch.setitem(seed.ROLE_CAPS, "instructor", 2)
    _, passages = seed.outline_context(str(hub), ECON)
    assert len([p for p in passages if p.source in ("slides", "notes")]) == 2


def test_a_book_key_decision_scopes_textbook_chapters(tmp_path):
    hub = tmp_path / "hub"
    book = hub / "academic_notes" / ECON / "textbooks/processed_outputs/Hansen_ECONOMETRICS_2022"
    write(book / "chapters/01_intro.rag.md", "# Intro\n\n## 1.1 What is econometrics\n")
    write(book / "chapters/04_least_squares.rag.md", "# Least squares\n\n## 4.2 Projection\n")
    record_decision(hub, ECON, str(book), book="hansen22")
    _, passages = seed.outline_context(str(hub), ECON, config=SeedConfig(textbook_chapters={"hansen22": [4]}))
    joined = "\n".join(p.text for p in passages)
    assert "4.2 Projection" in joined and "1.1 What is econometrics" not in joined
    assert {p.source for p in passages} == {"hansen22"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/agent/concept_graph/test_cg_seed_catalog.py tests/agent/concept_graph/test_cg_seed_outline.py -q`
Expected: FAIL (no headings in slide passages, no `ROLE_CAPS`, old offering wording)

- [ ] **Step 3: Implement**

In `seed.py`, change the imports:

```python
from core.course_materials import Catalog, load_catalog

from ..ipguard import check_meta, check_prose
from ..schema import SLUG, SeedConfig
from ..sources import Passage, classify_passage
```

Replace `_STATEMENT`:

```python
_STATEMENT = re.compile(
    r"^[\s*_#>\-]*(definitions?|theorems?|axioms?|lemmas?|propositions?|corollar(?:y|ies)|assumptions?|"
    r"propert(?:y|ies)|postulates?)(\s+\d[\d.]*)?\b[\s:.\-–—]*(.*)$",
    re.IGNORECASE)
```

In `statement_anchors`, replace the body of the loop from `parts = ...` up to `anchor = ...`:

```python
        rest = m.group(3).strip(" *_#>:-")
        parts = [rest] if rest else []
        j = i + 1
        while len(" ".join(parts)) < 60 and j < len(lines) and len(parts) < 3:
            nxt = lines[j]
            j += 1
            if not nxt or nxt.startswith("<!--"):
                continue
            if nxt.startswith("#") or _STATEMENT.match(nxt):
                break
            parts.append(nxt)
        if not parts:
            continue
        label = m.group(1).capitalize() + (m.group(2) or "").rstrip(".")
        anchor = re.sub(r"\s+", " ", " ".join([label, *parts])).strip()[:width]
```

Replace `outline_context`, and add `ROLE_CAPS` and `_evidence` above it:

```python
# Upper bounds on passages per kind of material, so a large role (34 TA notes) cannot crowd out the slides.
ROLE_CAPS = {"instructor": 30, "student_notes": 30, "recitation": 8, "prior": 15}
_CHAPTER_FILE = re.compile(r"/chapters/(\d+)_[^/]*$")


def _evidence(text: str, *, statements: int, headings: int) -> str:
    parts = []
    anchors = statement_anchors(text, limit=statements)
    if anchors:
        parts.append("Statements:\n" + _bullets(anchors))
    heads = section_headings(text, limit=headings) if headings else []
    if heads:
        parts.append("Section headings:\n" + _bullets(heads))
    return "\n\n".join(parts)


def outline_context(hub_root: str, course: str, *, config: SeedConfig | None = None, catalog: Catalog | None = None,
                    max_chars: int = 12000) -> tuple[str, list[Passage]]:
    """Describe the course from its files only (no model, no embedding), by what each file is.

    Offered passages: the syllabus excerpt (contact details removed); the statements and section headings of the
    instructor's slides and notes and of the lecture notes; recitation headings; each textbook's contents and the
    headings of the chapters the config puts in scope; earlier offerings' slide statements. The context text carries
    the lecture dates and teaching order and points to the passages."""
    config = config or SeedConfig()
    catalog = catalog if catalog is not None else load_catalog(hub_root, course)
    hub = Path(hub_root)
    lines: list[str] = []
    passages: list[Passage] = []

    def read(m) -> str:
        return (hub / m.path).read_text(encoding="utf-8", errors="ignore")

    def add(m, text: str, ref: str | None = None) -> None:
        source, default_ref = classify_passage(m.path, "", catalog)
        passages.append(Passage(id="", source=source, ref=ref or default_ref, text=text, path=str(hub / m.path)))

    seen_text: set[str] = set()
    for m in catalog.by_role("syllabus"):
        text = _clean_syllabus(read(m))[:3000].strip()
        if text and text not in seen_text:
            seen_text.add(text)
            add(m, text)

    titles: list[str] = []
    lecture_dates: set[str] = set()
    for m in catalog.by_role("instructor")[: ROLE_CAPS["instructor"]]:
        label = classify_passage(m.path, "", catalog)[1]
        evidence = _evidence(read(m), statements=25, headings=20)
        handwritten = m.format == "handwritten"
        if evidence:
            add(m, ("Found in the instructor's notes of " + label if handwritten else "Found in these slides") + ":\n\n" + evidence)
        if handwritten and m.date:
            lecture_dates.add(m.date)
        if label not in titles:
            titles.append(label)

    by_date: dict[str, list] = {}
    for m in catalog.by_role("student_notes"):
        if m.date:
            by_date.setdefault(m.date, []).append(m)
    for date in sorted(by_date)[: ROLE_CAPS["student_notes"]]:
        evidence = "\n\n".join(e for e in (_evidence(read(m), statements=12, headings=12) for m in by_date[date]) if e)
        if evidence:
            add(by_date[date][0], f"Found in the lecture notes of {date}:\n\n{evidence}", ref=date)
    lecture_dates |= set(by_date)

    for m in catalog.by_role("recitation")[: ROLE_CAPS["recitation"]]:
        heads = section_headings(read(m), limit=15)
        if heads:
            add(m, "Section headings:\n" + _bullets(heads))

    by_name = {k.lower(): v for k, v in config.textbook_chapters.items()}
    books: dict[str, list] = {}
    for m in catalog.by_role("textbook"):
        books.setdefault(m.book or "book", []).append(m)
    for key in sorted(books):
        chapters = sorted(((int(c.group(1)), m) for m in books[key] if (c := _CHAPTER_FILE.search(m.path))
                           and int(c.group(1)) > 0), key=lambda pair: (pair[0], pair[1].path))
        if not chapters:
            continue
        folder = chapters[0][1].path.split("/")[-3].lower()
        wanted = set(config.textbook_chapters.get(key) or by_name.get(key.lower()) or by_name.get(folder) or [])
        titles_toc = []
        for number, m in chapters:
            titles_toc.append(f"{number}. {_title(m.stem)}")
            if number in wanted:
                heads = section_headings(read(m))
                if heads:
                    add(m, f"Section headings of chapter {number} ({_title(m.stem)}):\n" + _bullets(heads),
                        ref=f"ch. {number} section headings")
        add(chapters[0][1], "\n".join(titles_toc), ref="table of contents")

    prior_lines: list[str] = []
    for label in catalog.offerings():
        decks: list[str] = []
        for m in [x for x in catalog.by_role("instructor", offering=label) if x.format == "slides"][: ROLE_CAPS["prior"]]:
            title = classify_passage(m.path, "", catalog)[1]
            anchors = statement_anchors(read(m))
            if anchors:
                add(m, f"Statements found in the {label} offering slides:\n" + _bullets(anchors))
            if title not in decks:
                decks.append(title)
        if decks:
            prior_lines += [f"{label} offering slide sets (in order): " + "; ".join(decks), ""]

    if lecture_dates:
        lines += ["Lecture dates with notes: " + ", ".join(sorted(lecture_dates)), ""]
    if titles:
        lines += ["Instructor slides and notes (in course order): " + "; ".join(titles), ""]
    lines += prior_lines
    lines += ["The syllabus excerpt, what was found in the instructor's slides and notes and in the lecture notes, and "
              "the textbook contents and section headings are under 'Offered passages' below."]
    context = "\n".join(lines).strip()
    if len(context) > max_chars:
        context = context[:max_chars] + "\n[context truncated]"
    return context, passages
```

In `make_tasks`, add `catalog: Catalog | None = None` before `**_ignored`, and pass it through: `context, passages = outline_context(hub_root, course, config=config, catalog=catalog)`.

Then delete `_DATE` (line 24) if nothing else references it. `slide_key` was local to the old `outline_context` and goes with it. Check with `grep -n "_DATE\|slide_key" agent/concept_graph/stages/seed.py`, which should print nothing.

- [ ] **Step 4: Run all concept-graph tests**

Run: `$PY -m pytest tests/agent/concept_graph -q`
Expected: PASS, except `tests/agent/concept_graph/test_cg_stage_seed.py:192`, which looks for a context line starting `Professor slide sets`. Change it to `Instructor slides and notes`, and update any other assertion on old wording the same way. Do not change the code back.

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/stages/seed.py tests/agent/concept_graph/test_cg_seed_outline.py tests/agent/concept_graph/test_cg_seed_catalog.py
git commit -m "feat(concept_graph): seed evidence by material role, with slide headings and caps

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Subject, kind descriptions, and a course-neutral scaffold

**Files:**
- Modify: `agent/concept_graph/schema.py:103-112` (`Vocab`, `Site`), and its imports (add `model_validator`)
- Modify: `agent/concept_graph/store.py:200-209` (`add_vocab`)
- Modify: `agent/concept_graph/stages/fill.py:13-14, 56-68`
- Modify: `agent/concept_graph/stages/seed.py`:
  - `KIND_HELP` (line 34)
  - `INSTRUCTIONS` lines 68-69
  - `make_tasks` lines 316-318
- Modify: `agent/concept_graph/scaffold.py:34-38, 117-118, 134-150`
- Modify: `agent/concept_graph/cli.py:99-107, 233-237`
- Test (new): `tests/agent/concept_graph/test_cg_course_wording.py`

**Interfaces:**
- Consumes: `load_catalog` (Task 3)
- Produces:
  - `Site.subject: str = "this course"`
  - `Vocab.kind_help: dict[str, str]` (excluded from dumps); `kinds` accepts names or `{name, help}`
  - `scaffold(root, repo, holder, year, with_sample=False, contact=None, fetch_text=None, *, title="Concept graph", subject="this course", book_keys=())`
  - CLI `scaffold --title --subject [--hub-root --course]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/concept_graph/test_cg_course_wording.py
"""Course wording lives in the graph repo's config, not in code."""
import yaml

from agent.concept_graph.schema import Site, Vocab
from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.stages import fill, seed
from agent.concept_graph.store import GraphStore
from cg_helpers import FakeRetriever, copy_sample


def test_site_subject_defaults_and_vocab_accepts_kind_descriptions():
    assert Site().subject == "this course"
    v = Vocab.model_validate({"kinds": ["theorem", {"name": "estimator", "help": "a rule mapping data to an estimate"}],
                              "topics": []})
    assert v.kinds == ["theorem", "estimator"] and v.kind_help == {"estimator": "a rule mapping data to an estimate"}
    assert "kind_help" not in v.model_dump()


def test_add_vocab_does_not_duplicate_a_described_kind(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    path = store.root / "config" / "vocab.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["kinds"].append({"name": "estimator", "help": "h"})
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    store.add_vocab(kinds=["estimator"])
    kinds = yaml.safe_load(path.read_text(encoding="utf-8"))["kinds"]
    assert sum(1 for k in kinds if k == "estimator" or (isinstance(k, dict) and k.get("name") == "estimator")) == 1


def test_fill_card_names_the_subject(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    site = store.root / "config" / "site.yaml"
    site.write_text(site.read_text(encoding="utf-8") + "subject: graduate econometrics\n", encoding="utf-8")
    task = fill.make_tasks(store, FakeRetriever(), nodes=[store.read_all().nodes[0].id], redo=True)[0]
    assert "studying graduate econometrics" in task.instructions and "{subject}" not in task.instructions
    assert "microeconomic" not in task.instructions.lower()


def test_seed_card_prefers_the_vocab_files_kind_help_and_names_the_subject(tmp_path):
    root = tmp_path / "g"
    scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license",
             title="Econometrics concept graph", subject="graduate econometrics")
    (root / "config" / "vocab.yaml").write_text(
        "kinds: [theorem, {name: estimator, help: a rule that maps a sample to an estimate}]\ntopics: [ols]\n", encoding="utf-8")
    hub = tmp_path / "hub"
    (hub / "academic_notes" / "econometrics" / "syllabus").mkdir(parents=True)
    task = seed.make_tasks(GraphStore(root), None, hub_root=str(hub), course="econometrics")[0]
    assert "- estimator: a rule that maps a sample to an estimate" in task.context
    assert "Subject: graduate econometrics" in task.context
    assert "(sets, relations, orders)" not in task.instructions


def test_scaffold_uses_title_subject_and_book_keys(tmp_path):
    root = tmp_path / "g"
    scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license",
             title="Econometrics concept graph", subject="graduate econometrics", book_keys=["hansen", "hayashi"])
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Econometrics concept graph") and "graduate econometrics" in readme
    assert "microeconomic" not in readme.lower()
    site = yaml.safe_load((root / "config/site.yaml").read_text(encoding="utf-8"))
    assert site["title"] == "Econometrics concept graph" and site["subject"] == "graduate econometrics"
    assert "Source keys: hansen, hayashi" in (root / "config/seed.yaml").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/agent/concept_graph/test_cg_course_wording.py -q`
Expected: FAIL (`Site` has no `subject`, `scaffold()` got an unexpected keyword `title`, ...)

- [ ] **Step 3: Implement**

`schema.py`. Add `model_validator` to the pydantic import, then:

```python
class Vocab(_Model):
    """config/vocab.yaml. A kind is a name, or {name, help} where help explains it on the seed card."""

    kinds: list[str]
    topics: list[str]
    kind_help: dict[str, str] = Field(default_factory=dict, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _split_described_kinds(cls, data):
        if isinstance(data, dict) and isinstance(data.get("kinds"), list):
            names, helps = [], dict(data.get("kind_help") or {})
            for k in data["kinds"]:
                if isinstance(k, dict):
                    names.append(k.get("name"))
                    if k.get("help"):
                        helps[k.get("name")] = k["help"]
                else:
                    names.append(k)
            data = {**data, "kinds": names, "kind_help": helps}
        return data


class Site(_Model):
    """config/site.yaml: the only per-site settings, shipped into the public page, so validated like the rest."""

    title: str = "Concept graph"
    subject: str = "this course"
    repo: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
```

`store.py` `add_vocab`. Compare by name:

```python
        for key, wanted in (("kinds", kinds), ("topics", topics)):
            present = {e.get("name") if isinstance(e, dict) else e for e in data[key]}
            for entry in wanted:
                if entry not in present:
                    data[key].append(entry)
                    present.add(entry)
```

`fill.py`:
- Make line 14 `Explain this concept for a student studying {subject}, using the offered passages as your source.`
- In `make_tasks`, compute `subject = graph.site.get("subject") or "this course"`.
- Pass `instructions=INSTRUCTIONS.replace("{subject}", subject)` (use `replace`, not `format`: the text contains `{source: ..., ref: ...}`).

`seed.py`:
- Replace INSTRUCTIONS lines 68-69 with:
  ```
  - Follow the order the course teaches (slide-set order and lecture dates) where it differs from the textbooks'. If
    the course relies on background mathematics or other prerequisites, give it a first section, however brief.
  ```
- Add to `KIND_HELP`:
  ```python
      "estimator": "a rule that turns a sample into an estimate (OLS, IV, maximum likelihood)",
      "assumption": "a condition placed on the data-generating process (exogeneity, homoskedasticity, iid sampling)",
      "test": "a hypothesis test or test procedure (Wald, likelihood ratio, t test)",
      "statistic": "a quantity computed from the sample (a t statistic, R squared, a residual)",
      "distribution": "a probability distribution or limiting law (normal, chi-squared)",
      "result": "an asymptotic or finite-sample property of an estimator or statistic (consistency, unbiasedness)",
  ```
- In `make_tasks`:
  ```python
  kinds = [f"- {k}: {graph.vocab.kind_help.get(k) or KIND_HELP.get(k, '(no description)')}" for k in graph.vocab.kinds]
  ```
  and the body starts:
  ```python
  f"Course: {course}", f"Subject: {graph.site.get('subject') or 'this course'}", "",
  ```

`scaffold.py`:
- README becomes:

```python
README = """# {title}

An interactive study aid: a map of the key concepts in {subject}, showing how the ideas connect, which results imply
or are equivalent to which, and under what conditions.
...
"""
```

(Keep the rest of the README unchanged.)
- Make the `SEED_TEMPLATE` comment line `# Source keys: {book_keys}.   Example:  textbook_chapters: {first_key: [1, 2, 3]}`.
- Change the signature and body:

```python
def scaffold(root: Path, repo: str, holder: str, year: int, with_sample: bool = False,
             contact: str | None = None, fetch_text=None, *, title: str = "Concept graph",
             subject: str = "this course", book_keys=()) -> list[str]:
    ...
    keys = list(book_keys)
    seed_text = (SEED_TEMPLATE.replace("{book_keys}", ", ".join(keys) or
                                       "run `python -m core.course_materials.cli --course <course> classify` to list them")
                 .replace("{first_key", "{" + (keys[0] if keys else "book")))
    ...
        "README.md": README.format(owner=owner, name=name, title=title, subject=subject),
        "config/seed.yaml": seed_text,
        "config/site.yaml": f"title: {title}\nsubject: {subject}\nrepo: {repo}\n",
```

Quote `title`/`subject` in site.yaml if they contain `:`. Use `yaml.safe_dump({"title": title, "subject": subject, "repo": repo}, sort_keys=False)` instead of the f-string.

`cli.py` scaffold parser:

```python
    sc.add_argument("--title", default="Concept graph", help="page and README title")
    sc.add_argument("--subject", default="this course", help="what the course is, e.g. 'graduate econometrics'")
    sc.add_argument("--hub-root", help="with --course: list the course's textbook keys in seed.yaml")
    sc.add_argument("--course")
```

and in `_cmd_scaffold`:

```python
    book_keys = ()
    if args.hub_root and args.course:
        from core.course_materials import load_catalog
        book_keys = load_catalog(args.hub_root, args.course).book_keys()
    created = scaffold_mod.scaffold(args.graph_repo, args.repo, args.holder, dt.date.today().year,
                                    with_sample=args.with_sample, contact=args.contact,
                                    title=args.title, subject=args.subject, book_keys=book_keys)
```

- [ ] **Step 4: Run all concept-graph tests**

Run: `$PY -m pytest tests/agent/concept_graph -q`
Expected: PASS. `test_cg_compat_golden.py` must still pass, because `kind_help` is excluded from dumps. If it fails on `site`, check whether `subject` now appears in `graph.site` in the build output. If it does and the golden test compares the site block, update the golden file in the same commit and say so in the message.

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/schema.py agent/concept_graph/store.py agent/concept_graph/stages/fill.py agent/concept_graph/stages/seed.py agent/concept_graph/scaffold.py agent/concept_graph/cli.py tests/agent/concept_graph/test_cg_course_wording.py
git commit -m "feat(concept_graph): course subject, described kinds, course-neutral scaffold

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: One catalog per run, the seed gate, and miss reporting

**Files:**
- Modify: `agent/concept_graph/cli.py`:
  - `_default_retriever` (118-121)
  - `_collect_run` (124-138)
  - `_cmd_collect` (153-164)
  - staged parser (244-252)
- Test (new): `tests/agent/concept_graph/test_cg_cli_catalog.py`

**Interfaces:**
- Consumes:
  - `load_catalog`, `Catalog`, `record_decision` (Task 3)
  - `seed.make_tasks(..., catalog=)` (Task 6)
  - `make_resilient_retriever(..., catalog=)` (Task 5)
- Produces:
  - `--allow-unreviewed` on `collect`/`api`
  - `args.catalog`, set before the retriever factory is called

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent/concept_graph/test_cg_cli_catalog.py
from agent.concept_graph import cli
from agent.concept_graph.scaffold import scaffold
from core.course_materials import record_decision


def setup(tmp_path):
    graph = tmp_path / "graph"
    scaffold(graph, "someone/g", "Some One", 2026, fetch_text=lambda url: "license")
    hub = tmp_path / "hub"
    s = hub / "academic_notes" / "demo" / "syllabus" / "processed_outputs" / "Syllabus.md"
    s.parent.mkdir(parents=True)
    s.write_text("Topics: regression.\n", encoding="utf-8")  # path word only: flagged
    return graph, hub


def args(graph, hub, *extra):
    return ["--graph-repo", str(graph), "collect", "seed", "--hub-root", str(hub), "--course", "demo",
            "--work-dir", str(hub.parent / "work"), *extra]


def test_seed_stops_while_materials_are_flagged_and_names_them(tmp_path, capsys):
    graph, hub = setup(tmp_path)
    assert cli.main(args(graph, hub)) == 1
    err = capsys.readouterr().err
    assert "flagged" in err and "Syllabus.md" in err and "--allow-unreviewed" in err


def test_seed_runs_once_reviewed_or_when_allowed(tmp_path, capsys):
    graph, hub = setup(tmp_path)
    assert cli.main(args(graph, hub, "--allow-unreviewed")) == 0
    record_decision(hub, "demo", "academic_notes/demo/syllabus/processed_outputs/Syllabus.md", role="syllabus")
    assert cli.main(args(graph, hub, "--run-id", "seed-2")) == 0
    assert "Topics: regression." in (hub.parent / "work" / "seed-2" / "cards" / "seed.md").read_text(encoding="utf-8")


def test_the_retriever_factory_receives_the_runs_catalog(tmp_path):
    graph, hub = setup(tmp_path)
    seen = {}

    def factory(a):
        seen["catalog"] = a.catalog
        raise RuntimeError("stop here")

    cli.main(["--graph-repo", str(graph), "collect", "fill", "--hub-root", str(hub), "--course", "demo",
              "--work-dir", str(tmp_path / "work")], retriever_factory=factory)
    assert seen["catalog"] is not None and seen["catalog"].course == "demo"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/agent/concept_graph/test_cg_cli_catalog.py -q`
Expected: FAIL (`unrecognized arguments: --allow-unreviewed`; no `a.catalog`)

- [ ] **Step 3: Implement**

```python
def _catalog(args):
    """The course's material catalog for this run, or None without --hub-root/--course or a course folder."""
    if not (args.hub_root and args.course and (Path(args.hub_root) / "academic_notes" / args.course).is_dir()):
        return None
    return load_catalog(args.hub_root, args.course)


def _default_retriever(args):
    if not args.hub_root or not args.course:
        raise ValueError("retrieval needs --hub-root and --course")
    return make_resilient_retriever(args.hub_root, args.course, catalog=args.catalog)


def _collect_run(args):
    store = GraphStore(args.graph_repo)
    args.catalog = _catalog(args)
    if args.stage == "seed" and args.catalog is not None and args.catalog.flagged() and not args.allow_unreviewed:
        names = "\n  ".join(m.path for m in args.catalog.flagged())
        raise ValueError(f"{len(args.catalog.flagged())} course file(s) are flagged for review; decide them with "
                         f"python -m core.course_materials.cli --hub-root {args.hub_root} --course {args.course} decide "
                         f"<path> --role ... (or pass --allow-unreviewed):\n  {names}")
    retriever = None if args.stage == "seed" else args.retriever_factory(args)
    ...  # unchanged orphan handling
    run = drivers.collect(args.stage, store, retriever, _work_root(args), run_id=args.run_id, section=args.section,
                          nodes=nodes, redo=redo, top_k=top_k, hub_root=args.hub_root, course=args.course,
                          catalog=args.catalog)
    return store, run
```

In `_cmd_collect`, after the run line:

```python
    catalog = getattr(args, "catalog", None)
    if catalog is not None and catalog.misses:
        print(f"note: {len(catalog.misses)} retrieved file(s) are not in the course catalog (classified by path only); "
              "re-run course_materials classify if they are new:")
        for path in sorted(catalog.misses):
            print("   ", path)
```

Do the same in `_cmd_api` after its report. Add to the `staged` parser:

```python
    staged.add_argument("--allow-unreviewed", action="store_true",
                        help="seed even while some course files are flagged for review")
```

Add `from core.course_materials import load_catalog` to the imports.

The `CatalogError` raised by a corrupt catalog is a `ValueError`, so `main` already reports it and exits 1.

- [ ] **Step 4: Run all concept-graph and course-materials tests**

Run: `$PY -m pytest tests/agent/concept_graph tests/core/course_materials -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/concept_graph/cli.py tests/agent/concept_graph/test_cg_cli_catalog.py
git commit -m "feat(concept_graph): one catalog per run, seed waits for review, report catalog misses

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Documentation and spec refinements

**Files:**
- Create: `core/course_materials/README.md`
- Modify: `agent/concept_graph/README.md`. Grep for the `Seed config` section, the `Source keys:` line (around line 132) and the `scaffold` usage. Edit only those.
- Modify: `docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md` (the refinements listed under Global Constraints)

- [ ] **Step 1: Write `core/course_materials/README.md`**

Cover:
- What it is (one paragraph).
- The roles and formats tables.
- The signals table with weights and the flag rule.
- Where the catalog and decisions live.
- The three commands, with one example each.
- How the review Artifact is used:
  - `flagged` rows go into the page's `db`.
  - Each confirmed row is applied with `decide`.
  - A folder path decides every file under it.
- The public API (`classify_course`, `load_catalog`, `Catalog.lookup`, `record_decision`, `classify_path`).

Keep it under about 120 lines.

- [ ] **Step 2: Update the concept-graph README**

- The source-keys line becomes: textbook book keys from the catalog, `slides`, `notes`, `lecture`, `recitation`, `hw`, `exam`, `syllabus`, `other`, with `-<offering>` for earlier offerings.
- The seed-config section: `textbook_chapters` is keyed by book key (from `course_materials classify`) or the book's folder name.
- Add `site.yaml` `subject`.
- Add the `{name, help}` form of `vocab.yaml` kinds.
- Add `collect seed` stopping on flagged files, plus `--allow-unreviewed`.
- Add `scaffold --title --subject --hub-root --course`.

- [ ] **Step 3: Record the planning refinements in the spec**

Edit the spec:
- **Signals:** landscape role vote is strong.
- **Commands:** `flagged`/`decide`, and the review Artifact built by Claude from `flagged`.
- **Storage:** folder decisions.
- **Citation keys:** a path missing from the catalog is classified alone and reported; instructor `typeset` keys as `slides`.
- **Seed evidence:** student-notes cap 30.

- [ ] **Step 4: Run the full suite**

Run: `$PY tools/run_tests_chunked.py`
Expected: all chunks pass. Paste the summary line into the commit message body.

- [ ] **Step 5: Commit**

```bash
git add core/course_materials/README.md agent/concept_graph/README.md docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md
git commit -m "docs: course_materials README, concept-graph README and spec refinements

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Real-data verification on microecon and econometrics (no model calls)

This task writes to the live hub's `.index/materials/` and runs from one session only. `HUB=C:/Users/theaa/ai-sandbox-master/ai-sandbox/academic-hub`. Put scratch output in the session scratchpad.

- [ ] **Step 1: Classify microecon and review the result**

Run: `$PY -m core.course_materials.cli --hub-root $HUB --course microecon classify`
Expected:
- The professor decks and the 2024/2025 post-lecture decks are `instructor`/`slides`.
- Excalidraw notes are `student_notes`.
- The three books are `textbook`.
- Few files are flagged.

For each misclassification, tune the weight or word list in `signals.py` only when the cause is systematic (it would hit any course). Add a failing test in `test_cm_signals.py` first. Otherwise leave it for review.

- [ ] **Step 2: Record microecon's book keys and other decisions**

```bash
$PY -m core.course_materials.cli --hub-root $HUB --course microecon decide academic_notes/microecon/textbooks/processed_outputs/Rubenstein_Lecture_Notes_in_Microeconomic_Theory_2026 --book rubinstein
$PY -m core.course_materials.cli --hub-root $HUB --course microecon decide academic_notes/microecon/textbooks/processed_outputs/Press_Microeconomic_Theory_2011 --book mwg
$PY -m core.course_materials.cli --hub-root $HUB --course microecon decide academic_notes/microecon/textbooks/processed_outputs/Ok_Real_Analysis_with_Economic_Applications_2026 --book ok
```

Resolve any remaining flagged microecon files through the review page (Step 4's flow).

- [ ] **Step 3: Microecon seed-card regression**

1. Copy the microecon graph repo to the scratchpad: `cp -r C:/Users/theaa/microecon-concept-graph <scratch>/mg-main` and `<scratch>/mg-branch`.
2. Generate the old card from the main checkout's code: `cd C:/Users/theaa/ai-sandbox-master/ai-sandbox/academic-rag-model && $PY -m agent.concept_graph.cli --graph-repo <scratch>/mg-main collect seed --redo --hub-root $HUB --course microecon --work-dir <scratch>/work-main --run-id seed-main`
3. Generate the new card from the worktree with the same arguments, using `<scratch>/mg-branch` and `<scratch>/work-branch`.
4. `diff <scratch>/work-main/seed-main/cards/seed.md <scratch>/work-branch/seed-branch/cards/seed.md`

Expected differences, and nothing else:
- prior-year keys (`slides-pre-2024` → `slides-2024`, `proofs-*` → `slides-*`)
- added `Section headings:` blocks
- `Subject:` line
- the reworded context lines

Any lost slide, lecture date or textbook is a bug. Fix it with a test before continuing.

- [ ] **Step 4: Classify econometrics and run the review page**

Run: `$PY -m core.course_materials.cli --hub-root $HUB --course econometrics classify`, then `... flagged > <scratch>/econ-flagged.json`.

Build the review Artifact:
1. Load the `artifact-design` and `artifact-capabilities` skills first.
2. Make one row per flagged file, grouped by folder, showing its evidence.
3. Give each row a role select, a format select, Confirm, Exclude, and an "apply to whole folder" toggle.
4. Store decisions in a `db` collection `decisions`, with one document per path: `{path, role, format, exclude, folder}`.

Publish it and send the owner the link. When they say they're done:
1. Read the collection with `ArtifactData`.
2. Apply each row: `decide <path or folder>/ --role ... --format ...` (or `--exclude`).
3. Re-run `classify` until `flagged (0)`.

- [ ] **Step 5: Set up the econometrics graph locally and dry-run seed**

1. Scaffold locally only, with no GitHub repo yet. Ask the owner before creating one:
   ```bash
   $PY -m agent.concept_graph.cli --graph-repo C:/Users/theaa/econometrics-concept-graph scaffold --repo AaronScherf/econometrics-concept-graph --holder "Aaron Scherf" --title "Econometrics concept graph" --subject "graduate econometrics" --hub-root $HUB --course econometrics
   ```
2. Draft `config/seed.yaml` with the owner:
   - `scope`
   - `must_include`: the OLS assumptions, Gauss-Markov, consistency, asymptotic normality, LLN, CLT, Slutsky, delta method, Wald test, omitted variable bias, MLE
   - `textbook_chapters`: Hansen chapters in scope
   - `min_nodes_per_section`
3. Draft `config/vocab.yaml` kinds with `{name, help}` entries for the econometric kinds.
4. Run `$PY -m agent.concept_graph.cli --graph-repo C:/Users/theaa/econometrics-concept-graph collect seed --hub-root $HUB --course econometrics --run-id seed-econ-dry`, and check the card for:
   - the dated instructor notes in `Lecture dates with notes`
   - slide headings (`Gauss Markov Theorem`, `Omitted variables bias`)
   - `hansen`/`cameron`/`hayashi`/`stock` keys
   - `2024 offering slide sets`
   - at most 8 recitation passages

   Stop here. Handing the prompt to Gemini (the Antigravity relay) is the owner's step.

- [ ] **Step 6: Status doc, memory, and landing request**

1. Write `docs/status/agent/concept_graph/2026-10-19-course-agnostic-status.md` with:
   - what shipped
   - the microecon diff result
   - econometrics flagged counts before and after review
   - weight changes, if any
   - the deferred edge-vocabulary checks from the spec
2. Update the memory file `project_concept_graph.md` and its MEMORY.md line.
3. Commit the status doc on the branch. Run `$PY -m tools.land_branch check --full` and ask the owner to land, per `docs/WORKTREE_WORKFLOW.md`.

Two things need the owner's call, not this branch:
- the live hub's new `.index/materials/*.json` files (whether to commit them)
- the microecon graph repo's `site.yaml` `subject` line (it lives in another repo)
