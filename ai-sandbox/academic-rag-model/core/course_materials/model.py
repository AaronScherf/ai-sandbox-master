"""Material records and the per-course catalog that holds them. Pure data: no file reads here."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath

ROLES = ("syllabus", "instructor", "student_notes", "recitation", "problem_set", "exam", "textbook", "other")
FORMATS = ("slides", "handwritten", "typeset", "excalidraw", "chapter")
DECIDABLE = ("role", "format", "offering", "book", "date", "order")
# Who stands behind a file. Class material is ground truth; mixing up roles inside `class` costs little, while
# mistaking a student's notes for class material (or the reverse) changes what the evidence is worth.
AUTHORITY = {"syllabus": "class", "instructor": "class", "recitation": "class", "problem_set": "class", "exam": "class",
             "textbook": "reference", "student_notes": "student", "other": "unknown"}
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
    def authority(self) -> str:
        return AUTHORITY.get(self.role, "unknown")

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
    excluded: list[str] = field(default_factory=list)  # files the owner excluded (a duplicate, an unrelated file)
    misses: set = field(default_factory=set, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._by_path = {m.path: m for m in self.materials}
        self._excluded = set(self.excluded)

    def is_excluded(self, path: str) -> bool:
        norm = normalize(path)
        return norm is not None and (norm in self._excluded or rag_twin(norm) in self._excluded)

    def lookup(self, path: str) -> Material | None:
        """The material at `path` (either hub root, either slash), its .rag twin, or the nearest catalogued ancestor
        folder whose materials all share one role, book and offering (so a book's front matter maps to the book)."""
        norm = normalize(path)
        if norm is None or self.is_excluded(norm):
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
                "unknown_decisions": list(self.unknown_decisions), "excluded": list(self.excluded)}

    @classmethod
    def from_json(cls, data: dict, source: str = "catalog") -> Catalog:
        try:
            return cls(course=data["course"], materials=[Material(**m) for m in data["materials"]],
                       unknown_decisions=list(data.get("unknown_decisions", [])),
                       excluded=list(data.get("excluded", [])))
        except (KeyError, TypeError) as exc:
            raise CatalogError(f"{source}: not a course-materials catalog ({exc})") from exc
