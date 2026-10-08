"""lint.py -- conservative lexical checks on a tutor draft before it is sent
(spec §4) and on glossary definitions at prep time (spec §3.1). A false
positive costs one revision; a false negative costs a leak, so rules lean
strict. Cannot catch paraphrased strategy hints (spec §11)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor.fsm import LAUNCH, VERIFIED, WORKING


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str

    def to_dict(self) -> dict:
        return {"code": self.code, "detail": self.detail}


TECHNIQUES = {
    "contradiction": re.compile(r"contradiction|reductio|for the sake of", re.I),
    "contrapositive": re.compile(r"contraposit", re.I),
    "induction": re.compile(r"\binduct(?:ion|ive)\b", re.I),
    "construction": re.compile(r"\bconstruct(?:ion|ive)?\b|counterexample", re.I),
}
_MATH = re.compile(r"\$([^$]+)\$")
_LATEX_CMD = re.compile(r"\\[A-Za-z]+")
_GREEK = re.compile(r"[α-ωΑ-Ω]")
_LETTER = re.compile(r"(?<![A-Za-z\\])[A-Za-z](?![A-Za-z])")
_COMMON_LETTERS = {"a", "A", "I"}
_UNICODE_FOR_LATEX = {
    "\\succeq": "≽", "\\succ": "≻", "\\preceq": "≼", "\\prec": "≺", "\\in": "∈", "\\cup": "∪", "\\cap": "∩",
    "\\gamma": "γ", "\\Gamma": "Γ", "\\lambda": "λ", "\\Lambda": "Λ", "\\mu": "μ", "\\sigma": "σ",
    "\\epsilon": "ε", "\\delta": "δ", "\\Delta": "Δ", "\\alpha": "α", "\\beta": "β", "\\theta": "θ",
}
_SUBQ_LINE = re.compile(r"^\s*(?:\d+[.)]|[A-Za-z][.)]|[-*•])\s+.*\?\s*$", re.M)
_LATEX_IN_CHAT = re.compile(r"\$|\\\(|\\\[|\\[A-Za-z]{2,}")
_CHECKIN = re.compile(r"lingering|any questions|ready to move on|move on", re.I)
_BACKREF = re.compile(r"\b(?:part|question|problem)\s+\d", re.I)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def extract_symbols(statement: str) -> set[str]:
    symbols: set[str] = set()
    for math in _MATH.findall(statement):
        symbols.update(_LATEX_CMD.findall(math))
        symbols.update(_GREEK.findall(math))
        symbols.update(l for l in _LETTER.findall(math) if l not in _COMMON_LETTERS)
    symbols.update(_GREEK.findall(statement))
    return symbols


def symbol_hits(text: str, symbols: set[str]) -> list[str]:
    hits = []
    for sym in sorted(symbols):
        if sym.startswith("\\"):
            if sym in text or _UNICODE_FOR_LATEX.get(sym, "\0") in text:
                hits.append(sym)
        elif len(sym) > 1 or not sym.isascii():
            if sym in text:
                hits.append(sym)
        elif re.search(rf"(?<![A-Za-z]){re.escape(sym)}(?![A-Za-z])", text):
            hits.append(sym)
    return hits


def _ngrams(text: str, n: int = 6) -> set[tuple]:
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def lint_message(
    text: str, *, state: str, hint_level: int, student_text: str = "", statement: str = "",
    sealed_solution: str = "", allowed_exact=(), after_define: bool = False, forbidden_patterns=(),
) -> list[Violation]:
    if _normalize(text) in {_normalize(a) for a in allowed_exact}:
        return []
    found: list[Violation] = []
    if state == LAUNCH:
        found.append(Violation("LAUNCH_NOT_VERBATIM", "In LAUNCH send exactly the launch text, nothing added or changed."))
    if hint_level < 3:
        for name, rx in TECHNIQUES.items():
            if rx.search(text) and not rx.search(student_text):
                found.append(Violation("TECHNIQUE", f"names the proof technique '{name}' before the student did"))
    if after_define:
        hits = symbol_hits(text, extract_symbols(statement))
        if hits:
            found.append(Violation("NOTATION_BRIDGE", f"a definition answer must not use the problem's notation: {hits}"))
    if sealed_solution and len(_ngrams(text) & _ngrams(sealed_solution)) >= 2:
        found.append(Violation("SEALED_OVERLAP", "draft repeats a phrase from the sealed solution"))
    if state == WORKING and hint_level < 3 and len(_SUBQ_LINE.findall(text)) >= 2:
        found.append(Violation("SUBQUESTION_LIST", "leading sub-question list before the student proposed a plan"))
    if state == VERIFIED and not (_CHECKIN.search(text) and "?" in text):
        found.append(Violation("CHECKIN_MISSING", "ask whether they have lingering questions or are ready to move on"))
    for pattern in forbidden_patterns:
        if re.search(pattern, text, re.I):
            found.append(Violation("NEXT_PART_REFERENCE", "do not mention the next part before the student confirms advancing"))
            break
    if _LATEX_IN_CHAT.search(text):
        found.append(Violation("LATEX_IN_CHAT", "use Unicode math (≽, ≤, λ, ℝ) in chat; keep LaTeX for vault files"))
    return found


def lint_glossary(glossary: dict[str, str], statements: list[str]) -> list[Violation]:
    found: list[Violation] = []
    for term, definition in glossary.items():
        if _BACKREF.search(definition):
            found.append(Violation("GLOSSARY_BACKREF", f"{term!r}: definition refers to a part/question number"))
        for statement in statements:
            if term.lower() in statement.lower():
                hits = symbol_hits(definition, extract_symbols(statement))
                if hits:
                    found.append(Violation("GLOSSARY_NOTATION", f"{term!r}: definition uses the problem's notation {hits}"))
                    break
    return found
