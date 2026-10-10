# agent/tutor/lint.py  (replace the whole file)
"""lint.py -- checks on a tutor draft before it is sent (v1 spec §4, v1.1 §6) and
on glossary definitions at prep time. v1.1 adds claim disclosure (a draft may not
match the recognizer of a claim the student has not reached) and the question
form. A false positive costs one revision; a false negative costs a leak."""
from __future__ import annotations

import re
from dataclasses import dataclass

from agent.tutor.claims import tokenize
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
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOP = {"that", "this", "with", "from", "have", "been", "were", "will", "would", "could", "should", "what",
         "when", "where", "which", "there", "their", "them", "then", "than", "into", "your", "about", "also",
         "just", "like", "does", "think", "said", "because", "these", "those", "every", "being"}
MAX_FORM_WORDS = 60
STATEMENT_RUN = 6


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


def _statement_run_positions(tokens: list[str], statement_tokens: list[str], n: int = STATEMENT_RUN) -> set[int]:
    runs = {tuple(statement_tokens[i:i + n]) for i in range(len(statement_tokens) - n + 1)}
    positions: set[int] = set()
    for i in range(len(tokens) - n + 1):
        if tuple(tokens[i:i + n]) in runs:
            positions.update(range(i, i + n))
    return positions


def _content_words(text: str) -> set[str]:
    return {t for t in tokenize(text) if len(t) >= 4 and t not in _STOP}


# Words a content-free warm sentence may use (besides words the student wrote).
_WARM = {"thanks", "thank", "trying", "tried", "fair", "good", "great", "okay", "glad", "tricky", "tough", "hard",
         "common", "normal", "worries", "sense", "understand", "started", "start", "together", "step", "help",
         "difficult", "honest", "honestly", "totally", "really", "happy"}
MAX_WARM_WORDS = 14


def _is_warm(sentence: str, last_student_text: str) -> bool:
    if len(sentence.split()) > MAX_WARM_WORDS:
        return False
    return _content_words(sentence) <= (_WARM | _content_words(last_student_text))


def check_form(text: str, last_student_text: str, max_words: int = MAX_FORM_WORDS) -> str | None:
    """The question form (v1.1 §6): at most one question, a word cap, and at most one other
    sentence which must restate the student's own words; one extra short sentence is allowed when it
    carries no content beyond a small warm vocabulary and the student's words. Returns the reason or None."""
    if text.count("?") > 1:
        return "ask at most one question"
    if len(text.split()) > max_words:
        return f"use at most {max_words} words"
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    statements = [s for s in sentences if not s.endswith("?")]
    student_words = _content_words(last_student_text)
    restating = [s for s in statements if len(_content_words(s) & student_words) >= 2]
    rest = [s for s in statements if s not in restating]
    warm = [s for s in rest if _is_warm(s, last_student_text)]
    bad = [s for s in rest if s not in warm]
    if len(restating) + len(bad) > 1 or len(warm) > 1:
        return "use at most one non-question sentence, plus one short warm sentence with no content"
    if bad:
        return ("the one non-question sentence must restate or acknowledge the student's own words "
                "(share at least two content words with their last message)")
    return None


def lint_message(
    text: str, *, state: str, hint_level: int, student_text: str = "", statement: str = "",
    sealed_solution: str = "", allowed_exact=(), after_define: bool = False, forbidden_patterns=(),
    blocked_claims: dict | None = None, form: bool = False, last_student_text: str = "",
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
    if sealed_solution and _ngrams(text) & _ngrams(sealed_solution):
        found.append(Violation("SEALED_OVERLAP", "draft repeats a phrase from the sealed solution"))
    if blocked_claims:
        tokens = tokenize(text)
        copied = _statement_run_positions(tokens, tokenize(statement))
        for cid, rec in blocked_claims.items():
            if rec.matches_tokens(tokens, masked=copied):
                found.append(Violation("REVEALS_CLAIM", f"introduces an idea the student has not reached (claim {cid})"))
    if state == WORKING and hint_level < 3 and len(_SUBQ_LINE.findall(text)) >= 2:
        found.append(Violation("SUBQUESTION_LIST", "leading sub-question list before the student proposed a plan"))
    if form:
        shown = text
        if after_define:      # the glossary definition is verbatim packet text, so it needs no echo of the student
            for a in allowed_exact:
                shown = shown.replace(a, " ")
        reason = check_form(shown, last_student_text)
        if reason:
            found.append(Violation("QUESTION_FORM", reason))
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
