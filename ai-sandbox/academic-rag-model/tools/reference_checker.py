"""Conservative, read-only bibliographic checks against DOI registration agencies.

Run: python -m tools.reference_checker references.md --format markdown
     python -m tools.reference_checker references.json --format json
JSON input may be a list of citation strings or objects with citation and identifier.
The default response cache is gitignored. DOI/arXiv ids go to registries;
references without an identifier send an extracted title or at most 200
characters of citation text to Crossref for candidate search. Source files stay local.
The AUTHOR_YEAR guard sends up to four registered author family names and a
three-year publication window to Crossref, and the DOI and OpenAlex author IDs
to OpenAlex; it sends no note text, abstracts, email, or user name. OpenAlex can
split one person into two author IDs and hide a sibling; Crossref is a second net.
For a low-scoring cited title, the checker sends at most 200 characters of the
cited title to Crossref and OpenAlex, plus cited surnames to Crossref. No note
body or personal identifier is sent with that search.

Known limitation: when one table reference contains multiple DOIs, each DOI may
inherit the same citation. This can misclassify a dataset DOI using paper authors;
review such rows manually and prefer separate DOI rows in the input.

Identity-to-tier mapping:
- SAME_WORK is CONFIRMED when an explicit title scores >= 0.92 and the cited
  year is within one year of any registered year, or when its title scores
  >= 0.5 and the cited year matches a registered year exactly.
- SAME_WORK with no title in the citation or linked reference list is
  AUTHOR_YEAR only when every cited surname is registered, the cited year
  matches exactly, Crossref registered the DOI, and a complete same-team
  search finds no sibling. Otherwise it is PLAUSIBLE.
- SAME_WORK with a cited title scoring below 0.5 is TITLE_WRONG only after
  successful Crossref and OpenAlex searches find no matching cited title;
  a found title or unavailable search remains REVIEW.
- AMBIGUOUS maps to REVIEW.
- WRONG_WORK, NOT_FOUND, UNCHECKED, and UNRESOLVED retain their identity as
  their tier.
- DOI aggregation ranks CONFIRMED < AUTHOR_YEAR < PLAUSIBLE < UNCHECKED < UNRESOLVED <
  REVIEW (= AMBIGUOUS) < TITLE_WRONG < NOT_FOUND < WRONG_WORK.

The legacy classification field remains for one release. Its mapping is
unchanged: MATCH means SAME_WORK with text_fidelity ["OK"], MISMATCH means
WRONG_WORK, PARTIAL means another resolved DOI identity, NO_IDENTIFIER means
an identifier-free or URL-only row, and NOT_FOUND means the registry reports
that the DOI does not exist. Registry lookup failures remain UNRESOLVED.
"""
from __future__ import annotations

import argparse
import difflib
import email.utils
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.git_workflow import git_common_dir


def shared_project_root(cwd: Path | None = None) -> Path:
    """Find the main checkout's project through the repository's common git dir."""
    return git_common_dir(cwd or Path(__file__).resolve().parents[1]).parent / "ai-sandbox/academic-rag-model"


DEFAULT_CACHE = shared_project_root() / ".reference_checker_cache"

TIER_RANK = {"CONFIRMED": 0, "AUTHOR_YEAR": 1, "DESCRIBED": 1, "PLAUSIBLE": 2, "UNCHECKED": 3,
             "UNRESOLVED": 4, "REVIEW": 5, "AMBIGUOUS": 5, "TITLE_WRONG": 6, "TITLE_MISSING": 6,
             "NOT_FOUND": 7, "WRONG_WORK": 8}
SAME_TEAM_VERSION_TITLE_THRESHOLD = 0.8

USER_AGENT = "ReferenceChecker/1.0 (bibliographic metadata validation)"
DOI = re.compile(r"10\.\d{4,9}/[^\s\]\[{}\"']+", re.I)
ARXIV = re.compile(r"(?:arxiv(?:\.org/(?:abs|pdf)/|:|\s+))(\d{4}\.\d{4,5}(?:v\d+)?|[a-z.\-]+/\d{7}(?:v\d+)?)", re.I)
URL = re.compile(r"https?://[^\s\])]+", re.I)
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
LINK = re.compile(r"\[([^]]+)\]\((https?://(?:[^()]|\([^()]*\))*)\)(?=\s|$|[.,;:)*])")
SOURCE_TAG = re.compile(r"\s*\*{0,2}\[(?:VERIFIED|UNVERIFIED|ABSTRACT-ONLY)\]\*{0,2}", re.I)


def clean_citation(value: str) -> str:
    return SOURCE_TAG.sub("", value).strip()


def clean_identifier(value: str) -> str:
    """Keep balanced DOI parentheses, including Wiley SICI, and trim prose punctuation."""
    value = urllib.parse.unquote(html.unescape(value.strip()))
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    while value and value[-1] in ".,;:!?)]>`*_":
        end = value[-1]
        if end == ")" and value.count(")") <= value.count("("):
            break
        if end == ">" and value.count(">") <= value.count("<"):
            break
        if end == "]" and value.count("]") <= value.count("["):
            break
        value = value[:-1]
    return value


def identifiers(text: str) -> tuple[str, str]:
    doi = DOI.search(text)
    if doi:
        return "doi", clean_identifier(doi.group())
    arxiv = ARXIV.search(text)
    if arxiv:
        return "arxiv", arxiv.group(1)
    url = URL.search(text)
    return ("url", url.group().rstrip(".,;:!?")) if url else ("", "")


def extract(text: str) -> list[dict]:
    """One row per reference; prefer the full citation directly below a link."""
    rows = []
    # Hugo publication pages cite their own title in the leading YAML block.
    # Keep this case separate from body references, whose title rules differ.
    front = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.S)
    if front:
        title = doi = ""
        doi_line = 0
        for number, raw in enumerate(front.group(1).splitlines(), 2):
            field = re.match(r"^(title|doi):\s*(.*?)\s*$", raw, re.I)
            if field:
                value = field.group(2).strip().strip("\"'")
                if field.group(1).lower() == "title":
                    title = value
                else:
                    doi, doi_line = value, number
        if DOI.search(doi):
            rows.append({"citation": title, "identifier": clean_identifier(DOI.search(doi).group()),
                         "kind": "doi", "line": doi_line, "front_matter_title": title})
        body = text[front.end():]
        offset = text[:front.end()].count("\n")
        for row in extract(body):
            if "line" in row:
                row["line"] += offset
            rows.append(row)
        return rows
    markdown_document = bool(re.search(r"^#{1,6}\s", text, re.M))
    lines = text.splitlines()
    reference_headings = [i for i, line in enumerate(lines)
                          if re.match(r"^#{1,6}\s+.*\b(?:references|bibliography)\b", line, re.I)]
    in_references = False
    reference_level = 0
    literature_title = ""
    literature_authors = ""
    literature_year = ""
    for index, raw in enumerate(lines):
        line = raw.strip()
        heading = re.match(r"^(#+)\s", line)
        if heading:
            if index in reference_headings:
                in_references, reference_level = True, len(heading.group(1))
            elif in_references and len(heading.group(1)) <= reference_level:
                in_references = False
            paper_heading = re.match(
                r"^#{1,6}\s+<a\s+id=[\"']paper-\d+[\"']\s*>\s*</a>\s*\d+\.\s*(.+?)\s*$",
                line, re.I,
            )
            literature_title = html.unescape(paper_heading.group(1)).strip() if paper_heading else ""
            literature_authors = ""
            literature_year = ""
            continue
        if not line:
            continue
        authors_match = re.match(r"^[-*+]\s+\*\*Authors?:\*\*\s*(.+)$", line, re.I)
        if authors_match and literature_title:
            literature_authors = re.sub(r"\s*\(\d+\s+authors?\s+total\)\s*$", "", authors_match.group(1), flags=re.I)
            continue
        year_match = re.match(r"^[-*+]\s+\*\*Publication Year:\*\*\s*((?:19|20)\d{2})\b", line, re.I)
        if year_match and literature_title:
            literature_year = year_match.group(1)
            continue
        bullet = bool(re.match(r"(?:[-*+]\s+|\d+[.)]\s+)", line))
        table = line.startswith("|") and not re.match(r"^\|?\s*[-:| ]+\|", line)
        if reference_headings and not in_references and not line.startswith("|") and not LINK.search(line):
            continue
        if markdown_document and not (bullet or table):
            continue
        if markdown_document and not reference_headings and not (table or (bullet and (LINK.search(line) or DOI.search(line)))):
            continue
        if table:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            author_year = re.compile(r"\b[A-Z][\w'’.-]*(?:\s+[A-Z][\w'’.-]*){0,4}\s*\((?:19|20)\d{2}\)")
            citation = next((re.sub(r"<br\s*/?>", ". ", cell, flags=re.I).strip(" *`_") for cell in cells
                             if author_year.search(DOI.sub("", cell))), "")
            if not citation:
                citation = next((re.sub(r"<br\s*/?>", ". ", cell, flags=re.I).strip(" *`_") for cell in cells
                                 if YEAR.search(DOI.sub("", cell)) and not re.fullmatch(r"[\d. /-]+", cell)), "")
            if not citation:
                citation = re.sub(r"[*`]", "", cells[0]).strip()
            seen = set()
            doi_matches = list(DOI.finditer(line))
            for doi_index, match in enumerate(doi_matches):
                ident = clean_identifier(match.group())
                if ident.lower() not in seen:
                    prior = line[doi_matches[doi_index - 1].end() if doi_index else 0:match.start()]
                    prior = LINK.sub(lambda m: m.group(1), prior)
                    candidate = ""
                    for part in re.split(r"\s*\|\s*", prior):
                        part = re.sub(r"<br\s*/?>", ". ", part, flags=re.I)
                        part = LINK.sub(lambda m: m.group(1), part)
                        found_author_year = author_year.search(DOI.sub("", part))
                        if found_author_year:
                            candidate = re.sub(r"\[[^]]*$", "", part).replace("**", "").strip(" |*`_. ")
                            break
                    link_text = next((link.group(1) for link in LINK.finditer(line)
                                      if ident.lower() in link.group(2).lower()), "")
                    selected = candidate or (citation if author_year.search(citation) else "") or link_text or citation
                    rows.append({"citation": clean_citation(selected),
                                 "identifier": ident, "kind": "doi", "line": index + 1,
                                 "descriptive_link": bool(link_text and selected == link_text)})
                    seen.add(ident.lower())
            if not seen:
                for link in LINK.finditer(line):
                    kind, ident = identifiers(link.group(2))
                    if kind:
                        rows.append({"citation": clean_citation(citation), "identifier": ident, "kind": kind, "line": index + 1})
            continue
        links = list(LINK.finditer(line))
        if links:
            for link_index, link in enumerate(links):
                kind, ident = identifiers(link.group(2))
                if not kind:
                    continue
                citation = link.group(1)
                if (re.match(r"^[-*+]\s+\*\*DOI\s*/\s*Link:\*\*", line, re.I)
                        and literature_title and literature_authors and literature_year):
                    citation = f"{literature_authors} ({literature_year}). {literature_title}"
                end = links[link_index + 1].start() if link_index + 1 < len(links) else len(line)
                suffix = line[link.end():end].lstrip(" —–-:")
                # Only text before the next link may elaborate this DOI.
                if YEAR.search(suffix) and re.match(r"[A-ZÀ-ÖØ-Þ]", suffix):
                    citation = suffix
                elif index + 1 < len(lines):
                    following = lines[index + 1].strip()
                    if following.startswith("*") and YEAR.search(following) and not LINK.search(following):
                        citation = following.strip("* ")
                rows.append({"citation": clean_citation(citation), "identifier": ident, "kind": kind,
                             "line": index + 1, "descriptive_link": True})
            continue
        line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line)
        dois = list(DOI.finditer(line))
        if dois:
            for doi_index, match in enumerate(dois):
                start = dois[doi_index - 1].end() if doi_index else 0
                before = line[start:match.start()].rsplit("; ", 1)[-1]
                prefix, separator, remainder = before.partition(": ")
                if separator and not YEAR.search(prefix) and YEAR.search(remainder):
                    before = remainder
                comma_year = re.search(r"\(((?:19|20)\d{2})(?=\s*[,;])", before)
                if comma_year:
                    author_block = before[:comma_year.start()].strip(" *`():—–-")
                    citation = f"{author_block} ({comma_year.group(1)})" if author_block else before
                else:
                    names = list(re.finditer(r"[A-ZÀ-ÖØ-Þ][\w'’\-]*(?:\s+[A-ZÀ-ÖØ-Þ][\w'’\-]*){0,3}\s*\((?:19|20)\d{2}(?=[),])", before))
                    citation = before[names[-1].start():] if names else before
                    citation = citation.strip(" *`():—–-.") or line
                rows.append({"citation": citation, "identifier": clean_identifier(match.group()), "kind": "doi", "line": index + 1})
            continue
        kind, ident = identifiers(line)
        if kind in ("arxiv", "url"):
            rows.append({"citation": clean_citation(line.strip("* ")), "identifier": ident, "kind": kind, "line": index + 1})
        elif ((in_references and re.search(r"\(\d{4}\)\.\s+\w", line)) or
              (not markdown_document and YEAR.search(line) and len(line.split()) >= 3)):
            rows.append({"citation": clean_citation(line.strip("* ")), "identifier": "", "kind": "", "line": index + 1})
    return rows


def coverage(text: str, rows: list[dict]) -> dict:
    """Count distinct DOI strings; repeated prose mentions do not create references."""
    source = set()
    excluded = set()
    for line in text.splitlines():
        for match in DOI.finditer(line):
            doi = clean_identifier(match.group()).lower()
            if (line.lstrip().startswith("*") and "corrected" in line.lower() and
                    "`" + doi + "`" in line.lower() and not LINK.search(line)):
                excluded.add(doi)
            else:
                source.add(doi)
    attached = {row["identifier"].lower() for row in rows if row["kind"] == "doi"}
    missing = sorted(source - attached)
    return {"doi_like_in_source": len(source), "attached": len(source & attached),
            "unattached": len(missing), "unattached_identifiers": missing,
            "excluded_quoted_corrections": len(excluded - attached)}


def load_references(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() != ".json":
        return extract(raw)
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("references", [])
    if not isinstance(data, list):
        raise ValueError("JSON input must be a list or an object with references")
    rows = []
    for item in data:
        if isinstance(item, str):
            citation, explicit = item, ""
        elif isinstance(item, dict):
            citation = str(item.get("citation") or item.get("text") or "")
            explicit = str(item.get("identifier") or item.get("doi") or item.get("url") or "")
        else:
            raise ValueError("each reference must be a string or object")
        kind, ident = identifiers(explicit or citation)
        rows.append({"citation": clean_citation(citation), "identifier": ident, "kind": kind})
    return rows


def normalized(value: str) -> str:
    value = html.unescape(value or "")
    if "Ã" in value or "â€" in value:
        try:
            value = value.encode("cp1252").decode("utf-8")
        except UnicodeError:
            pass
    folded = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in folded if not unicodedata.combining(c))))


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalized(a), normalized(b)).ratio()


def citation_fields(citation: str) -> dict:
    year = YEAR.search(citation)
    first = re.search(r"[\w'’\-]+", citation)
    # Titles must be explicit; a prose summary or author-year link label is not a title.
    tail = citation[year.end():].strip(" ).") if year else ""
    # A leading comma or italic span with no sentence break is venue metadata.
    venue_only = bool(re.match(r"^\s*,\s*\*[^*]+\*", tail) or
                       re.match(r"^\s*,\s*[^.?!]+$", tail) or
                       (re.match(r"^\s*\*[^*]+\*", tail) and not re.search(r"[.?!]\s+", tail)) or
                       re.match(r"^\s*vs\b", tail, re.I))
    parts = re.split(r"[.?!]\s+(?=\*?[A-Z])", tail, maxsplit=1)
    title = "" if venue_only else re.split(r"\s+[0-9]+\s*\(", parts[0], maxsplit=1)[0].strip(" *_.,?!\"“”")
    if len(title.split()) < 2:
        title = ""
    details = parts[1] if len(parts) > 1 else ""
    volume = re.search(r",\s*(\d+)\s*(?:\(|,)", details)
    pages = re.search(r",\s*(\d+)\s*[–-]\s*(\d+)(?=\s*[.,]|\s*$)", details)
    venue = details[:volume.start()] if volume else re.split(r"\.\s+", details, maxsplit=1)[0]
    venue = venue.strip(" *_.,")
    if venue_only and year:
        metadata = re.sub(r"^\s*\)\s*[,.;]?\s*", "", citation[year.end():]).strip(" *_.,")
        match = re.match(r"^(.*?)(?:,\s*(\d+)(?:\s*\([^)]*\))?)?(?:,\s*(\d+\s*[-–]\s*\d+))?\s*$", metadata)
        if match:
            venue = match.group(1).strip(" *_.,")
            volume = match.group(2)
            pages = match.group(3)
            return {"year": int(year.group()), "author": normalized(first.group()) if first else "",
                    "title": "", "venue": venue, "volume": volume or "",
                    "pages": (pages or "").replace(" ", "")}
    return {"year": int(year.group()) if year else None,
            "author": normalized(first.group()) if first else "", "title": title,
            "venue": venue,
            "volume": volume.group(1) if volume else "",
            "pages": "-".join(pages.groups()) if pages else ""}


def _reference_authors(prefix: str) -> list[str]:
    prefix = re.sub(r"\bet\s+al\.?\s*$", "", prefix, flags=re.I).strip(" ,;*&")
    # Split author groups while keeping surname/initial commas together.
    parts = re.split(r"\s*(?:&|\band\b|;)\s*|,\s*(?=[A-Z][\w'’.-]+,\s*[A-Z])", prefix)
    return [part.strip(" ,") for part in parts if part.strip(" ,")]


def _parse_reference_entry(entry: str) -> dict:
    entry = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", entry).strip()
    entry = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r"\1 \2", entry)
    year_match = re.search(r"\(((?:19|20)\d{2})([a-z])?\)\s*\.?", entry, re.I)
    prefix = entry[:year_match.start()].strip(" ,") if year_match else ""
    clean = URL.sub("", DOI.sub("", entry))
    clean = re.sub(r"\(((?:19|20)\d{2})[a-z]\)", r"(\1)", clean, flags=re.I)
    fields = citation_fields(clean)
    if re.search(r"\((?:19|20)\d{2}\)\.?\s*\*[^*]+\*\.?\s*(?:doi\s*:)?\s*$", clean, re.I):
        fields["title"] = ""
    kind, identifier = identifiers(entry)
    return {
        "authors": _reference_authors(prefix),
        "year": int(year_match.group(1)) if year_match else None,
        "suffix": (year_match.group(2) or "").lower() if year_match else "",
        "title": fields["title"],
        "doi": identifier if kind == "doi" else "",
    }


def parse_reference_list(text: str) -> list[dict]:
    """Parse bibliography entries separately from inline author-year mentions."""
    lines = text.splitlines()
    heading_re = re.compile(r"^(#+)\s+.*\b(?:references|bibliography)\b", re.I)
    active = False
    level = 0
    entries = []
    current = ""
    for raw in lines:
        line = raw.strip()
        heading = re.match(r"^(#+)\s", line)
        if heading:
            match = heading_re.match(line)
            if match:
                active, level = True, len(heading.group(1))
            elif active and len(heading.group(1)) <= level:
                active = False
            continue
        if not active or not line:
            continue
        starts_entry = bool(re.match(r"^(?:[-*+]\s+|\d+[.)]\s+)", line) or
                            re.match(r"^[^|].*\((?:19|20)\d{2}[a-z]?\)", line, re.I))
        if starts_entry:
            if current:
                entries.append(_parse_reference_entry(current))
            current = line
        elif current:
            current += " " + line
    if current:
        entries.append(_parse_reference_entry(current))
    return entries


def parse_inline_citations(text: str) -> list[dict]:
    """Find inline author-year mentions, excluding bibliography sections."""
    lines = text.splitlines(keepends=True)
    kept = []
    active = False
    level = 0
    for line in lines:
        heading = re.match(r"^(#+)\s+", line)
        if heading:
            is_refs = bool(re.match(r"^#+\s+.*\b(?:references|bibliography)\b", line, re.I))
            if is_refs:
                active, level = True, len(heading.group(1))
            elif active and len(heading.group(1)) <= level:
                active = False
        kept.append("\n" if active else line)
    searchable = "".join(kept)
    name = r"[A-Z][\w'’.-]*(?:\s+[A-Z][\w'’.-]*){0,2}"
    authors = rf"{name}(?:\s*(?:&|\band\b)\s*{name})?(?:\s+et\s+al\.?)?"
    date = r"((?:19|20)\d{2})([ab])?"
    pattern = re.compile(
        rf"(?P<paren>\(\s*(?P<pauthors>{authors})\s*,\s*(?P<pyear>{date})\s*\))"
        rf"|(?P<narrative>(?P<nauthors>{authors})\s+\(\s*(?P<nyear>{date})\s*\))"
        rf"|(?P<bare>(?P<bauthors>{authors})\s+(?P<byear>{date}))"
    )
    found = []
    for match in pattern.finditer(searchable):
        if match.group("paren"):
            author_text, year_text = match.group("pauthors"), match.group("pyear")
        elif match.group("narrative"):
            author_text, year_text = match.group("nauthors"), match.group("nyear")
        else:
            author_text, year_text = match.group("bauthors"), match.group("byear")
            if normalized(author_text) in {
                "january", "february", "march", "april", "may", "june",
                "july", "august", "september", "october", "november", "december",
            }:
                continue
        date_match = re.fullmatch(date, year_text)
        found.append({
            "authors": _reference_authors(author_text),
            "year": int(date_match.group(1)),
            "suffix": (date_match.group(2) or "").lower(),
            "citation": text[match.start():match.end()],
            "start": match.start(),
            "end": match.end(),
        })
    return found


class RegistryClient:
    def __init__(self, cache: Path, pace: float = 0.2, online: bool = True, refresh: bool = False):
        self.cache, self.pace, self.online, self.refresh = cache, pace, online, refresh
        self.last_request = 0.0

    def get(self, url: str):
        key = hashlib.sha256(url.encode()).hexdigest()
        path = self.cache / (key + ".json")
        if path.exists() and not self.refresh:
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                if cached.get("status") != 404 or time.time() - path.stat().st_mtime < 7 * 86400:
                    return cached
            except (OSError, ValueError, AttributeError):
                pass
        if not self.online:
            raise LookupError("not cached")
        # Pace guard list queries, including cursor pages and retries.
        guard_list = ((url.startswith("https://api.crossref.org/works?") and "query.author=" in url)
                      or (url.startswith("https://api.openalex.org/works?")
                          and ("authorships.author.id" in url or "search=" in url)))
        pace = max(self.pace, 1.0) if guard_list else self.pace
        for attempt in range(3):
            time.sleep(max(0, pace - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as response:
                    result = {"status": response.status, "data": json.load(response)}
                break
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    result = {"status": 404, "data": None}
                    break
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                retry_after = _retry_after_seconds(error) if error.code == 429 else 0.0
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
                retry_after = 0.0
            time.sleep(max(2 ** attempt, retry_after))
        temp_path = None
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", suffix=".tmp",
                                             dir=self.cache, delete=False) as temp:
                json.dump(result, temp)
                temp_path = Path(temp.name)
            os.replace(temp_path, path)
        except OSError:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        return result


def _retry_after_seconds(error: urllib.error.HTTPError) -> float:
    value = error.headers.get("Retry-After") if error.headers else None
    if not value:
        return 0.0
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            date = email.utils.parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 0.0


@dataclass(frozen=True)
class SameTeamGuardResult:
    complete: bool
    siblings: list[dict]
    sibling_count: int
    reason: str = ""


def _family_last_token(name: str) -> str:
    parts = normalized(name).split()
    return parts[-1] if parts else ""


def _crossref_first_family(item: dict) -> str:
    authors = item.get("author") or []
    return (_family_last_token(authors[0].get("family") or "")
            if isinstance(authors, list) and authors and isinstance(authors[0], dict) else "")


def _crossref_guard(doi: str, record: dict, year: int, client: RegistryClient) -> SameTeamGuardResult:
    """Collect Crossref siblings from at most three pages; never infer completeness."""
    authors = [str(a) for a in record.get("authors") or [] if a]
    title = str(record.get("title") or "")
    first = _family_last_token(authors[0]) if authors else ""
    coauthors = {_family_last_token(author) for author in authors[1:]}
    if not first or not title or not doi:
        return SameTeamGuardResult(False, [], 0, "missing registered metadata")
    params = {"query.author": " ".join(authors[:4]),
              "filter": f"from-pub-date:{year - 1}-01-01,until-pub-date:{year + 1}-12-31",
              "rows": "100", "select": "DOI,title,author,issued,type", "cursor": "*"}
    base = "https://api.crossref.org/works?"
    seen_dois: set[str] = set()
    seen_cursors: set[str] = set()
    siblings: list[dict] = []
    sibling_count = 0
    read = 0
    cursor = "*"
    for page in range(3):
        params["cursor"] = cursor
        url = base + urllib.parse.urlencode(params)
        try:
            answer = client.get(url)
        except Exception as error:  # any failed search is an unresolved guard, never an automatic pass
            return SameTeamGuardResult(False, siblings, sibling_count,
                                       f"lookup unavailable: {error}")
        data = answer.get("data") if isinstance(answer, dict) else None
        message = data.get("message") if isinstance(data, dict) else None
        if not isinstance(answer, dict) or answer.get("status") != 200 or not isinstance(message, dict):
            return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref answer")
        items, total = message.get("items"), message.get("total-results")
        if not isinstance(items, list) or not isinstance(total, int) or total < 0:
            return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref answer")
        read += len(items)
        for item in items:
            if not isinstance(item, dict):
                return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref item")
            candidate_authors = item.get("author") or []
            if not isinstance(candidate_authors, list):
                return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref author list")
            if _crossref_first_family(item) != first:
                continue
            if any(not isinstance(author, dict) for author in candidate_authors[1:]):
                return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref author list")
            candidate_coauthors = {_family_last_token(a.get("family") or "") for a in candidate_authors[1:]
                                   if isinstance(a, dict)}
            if coauthors and not (coauthors & candidate_coauthors):
                continue
            candidate_doi = str(item.get("DOI") or "").lower()
            if not candidate_doi:
                return SameTeamGuardResult(False, siblings, sibling_count, "candidate DOI missing")
            if candidate_doi == doi.lower() or candidate_doi in seen_dois:
                continue
            seen_dois.add(candidate_doi)
            if item.get("type") in {"dataset", "peer-review", "component", "grant"}:
                continue
            titles = item.get("title") or [""]
            if not isinstance(titles, list) or not titles or not isinstance(titles[0], str):
                return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref title")
            candidate_title = titles[0]
            if similarity(candidate_title, title) >= SAME_TEAM_VERSION_TITLE_THRESHOLD:
                continue
            issued = item.get("issued") or {}
            if not isinstance(issued, dict):
                return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref date")
            dates = issued.get("date-parts") or []
            candidate_year = dates[0][0] if dates and dates[0] else None
            sibling_count += 1
            siblings.append({"doi": candidate_doi, "title": candidate_title,
                             "year": candidate_year, "type": item.get("type")})
        if total <= read:
            return SameTeamGuardResult(True, siblings, sibling_count)
        if len(items) < 100:
            return SameTeamGuardResult(False, siblings, sibling_count, "incomplete Crossref page")
        next_cursor = message.get("next-cursor")
        if (not isinstance(next_cursor, str) or not next_cursor or
                next_cursor == cursor or next_cursor in seen_cursors):
            return SameTeamGuardResult(False, siblings, sibling_count, "cursor unavailable")
        seen_cursors.add(cursor)
        cursor = next_cursor
    return SameTeamGuardResult(False, siblings, sibling_count, "three-page limit reached")


def _openalex_id(value: str) -> str:
    """Canonicalize an OpenAlex author URL or short ID for equality and filters."""
    return str(value or "").rstrip("/").rsplit("/", 1)[-1].upper()


def _openalex_guard(doi: str, record: dict, year: int, client: RegistryClient) -> SameTeamGuardResult:
    """Read every filtered first-author work; only meta.count proves completeness."""
    try:
        target = client.get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe=""))
        if target.get("status") != 200 or not isinstance(target.get("data"), dict):
            return SameTeamGuardResult(False, [], 0, "DOI absent from OpenAlex")
        authorships = target["data"].get("authorships") or []
        first = _openalex_id((authorships[0].get("author") or {}).get("id")) if authorships else ""
        if not first:
            return SameTeamGuardResult(False, [], 0, "first OpenAlex author ID missing")
        coauthors = {_openalex_id((a.get("author") or {}).get("id")) for a in authorships[1:]}
        coauthors.discard("")
        params = {"filter": f"authorships.author.id:{first},publication_year:{year - 1}-{year + 1}",
                  "per-page": "200", "select": "doi,title,publication_year,type,authorships,primary_location", "cursor": "*"}
        seen = set()
        siblings = []
        count = pages_read = 0
        total = None
        cursor = "*"
        while True:
            params["cursor"] = cursor
            answer = client.get("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
            data = answer.get("data") if answer.get("status") == 200 else None
            meta = data.get("meta") if isinstance(data, dict) else None
            items = data.get("results") if isinstance(data, dict) else None
            page_total = meta.get("count") if isinstance(meta, dict) else None
            if not isinstance(items, list) or not isinstance(page_total, int) or page_total < 0:
                return SameTeamGuardResult(False, siblings, count, "incomplete OpenAlex answer")
            if page_total > 1000:
                return SameTeamGuardResult(False, siblings, count, "OpenAlex count above 1000")
            if total is not None and page_total != total:
                return SameTeamGuardResult(False, siblings, count, "OpenAlex count changed during paging")
            total = page_total
            for item in items:
                if not isinstance(item, dict):
                    return SameTeamGuardResult(False, siblings, count, "incomplete OpenAlex work")
                work_authors = item.get("authorships") or []
                if not isinstance(work_authors, list):
                    return SameTeamGuardResult(False, siblings, count, "incomplete OpenAlex authorships")
                work_ids = [_openalex_id((a.get("author") or {}).get("id")) for a in work_authors]
                if not work_ids or work_ids[0] != first:
                    continue
                if coauthors and not (coauthors & set(work_ids[1:])):
                    continue
                candidate_doi = str(item.get("doi") or "").lower().removeprefix("https://doi.org/")
                if not candidate_doi or candidate_doi == doi.lower() or candidate_doi in seen:
                    continue
                seen.add(candidate_doi)
                if item.get("type") in {"dataset", "erratum", "peer-review", "paratext"}:
                    continue
                title = item.get("title") or ""
                if not isinstance(title, str) or not title:
                    return SameTeamGuardResult(False, siblings, count, "incomplete OpenAlex title")
                if similarity(title, record.get("title") or "") >= SAME_TEAM_VERSION_TITLE_THRESHOLD:
                    continue
                count += 1
                source = ((item.get("primary_location") or {}).get("source") or {})
                siblings.append({"doi": candidate_doi, "title": title,
                                 "year": item.get("publication_year"), "venue": source.get("display_name") or "",
                                 "type": item.get("type")})
            # OpenAlex may include works without DOIs; count raw results instead.
            pages_read += len(items)
            if pages_read >= total:
                return SameTeamGuardResult(True, siblings, count)
            next_cursor = meta.get("next_cursor")
            if not items or not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor:
                return SameTeamGuardResult(False, siblings, count, "OpenAlex cursor unavailable")
            cursor = next_cursor
    except Exception as error:
        return SameTeamGuardResult(False, [], 0, f"OpenAlex lookup unavailable: {error}")


def same_team_guard(doi: str, record: dict, year: int, client: RegistryClient) -> SameTeamGuardResult:
    """Require complete OpenAlex author-ID scan; Crossref adds sibling evidence."""
    openalex = _openalex_guard(doi, record, year, client)
    if not openalex.complete:
        return openalex
    crossref = _crossref_guard(doi, record, year, client)
    siblings = list(openalex.siblings)
    seen = {item["doi"] for item in siblings}
    count = openalex.sibling_count
    for item in crossref.siblings:
        if item["doi"] not in seen:
            seen.add(item["doi"])
            count += 1
            siblings.append(item)
    return SameTeamGuardResult(True, siblings[:5], count)


def registry_record(doi: str, client: RegistryClient) -> tuple[str, dict | None, str]:
    encoded = urllib.parse.quote(doi, safe="")
    agency = client.get("https://doi.org/doiRA/" + encoded)
    agency_row = (agency.get("data") or [{}])[0]
    ra = (agency_row.get("RA") or "").lower()
    if ra and ra not in ("crossref", "datacite"):
        return ra, None, "unsupported registration agency: " + ra
    choices = (["Crossref"] if ra == "crossref" else ["DataCite"] if ra == "datacite"
               else ["Crossref", "DataCite"])
    answer = None
    registry = ""
    for candidate in choices:
        url = ("https://api.crossref.org/works/" if candidate == "Crossref" else
               "https://api.datacite.org/dois/") + encoded
        answer = client.get(url)
        if answer["status"] != 404:
            registry = candidate
            break
    if not registry:
        checked = ", ".join(choices)
        missing = agency_row.get("status") == "DOI does not exist"
        status = "DOI does not exist; " if missing else ""
        return checked, None, status + "not found in " + checked
    raw = answer["data"]
    if registry == "Crossref":
        m = raw.get("message", {})
        year_sources = {key: parts[0][0] for key in ("published-online", "published-print", "issued", "published")
                        if (parts := (m.get(key) or {}).get("date-parts")) and parts[0] and parts[0][0]}
        years = sorted(set(year_sources.values()))
        year = years[0] if years else None
        authors = [a.get("family") or a.get("literal") or a.get("name") for a in m.get("author") or []]
        authors = [a for a in authors if a]
        record = {"title": (m.get("title") or [""])[0], "subtitle": (m.get("subtitle") or [""])[0],
                  "author": authors[0] if authors else "", "authors": authors,
                  "year": year, "years": years, "year_sources": year_sources,
                  "venue": (m.get("container-title") or [""])[0],
                  "volume": m.get("volume"), "pages": m.get("page"), "doi": m.get("DOI", doi)}
    else:
        m = raw.get("data", {}).get("attributes", {})
        authors = [c.get("familyName") or c.get("name", "").split(",")[0] for c in m.get("creators") or []]
        authors = [a for a in authors if a]
        record = {"title": (m.get("titles") or [{}])[0].get("title", ""),
                  "author": authors[0] if authors else "", "authors": authors,
                  "year": m.get("publicationYear"), "years": [m["publicationYear"]] if m.get("publicationYear") else [],
                  "year_sources": {"publication": m["publicationYear"]} if m.get("publicationYear") else {},
                  "venue": (m.get("container") or {}).get("title", ""),
                  "volume": m.get("volume"), "pages": m.get("page"), "doi": m.get("doi", doi)}
    return registry, record, "resolved"


def _author_tokens(value: str) -> set[str]:
    stop = {"and", "the", "for", "with", "et", "al", "der", "den", "van", "von", "del", "de", "la", "le", "da", "di"}
    for original, expanded in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue")):
        value = value.replace(original, expanded)
    return {part for part in normalized(value).split() if len(part) > 1 and part not in stop}


def _venue_matches(cited: str, registered: str) -> bool:
    cited_words, registered_words = normalized(cited).split(), normalized(registered).split()
    if not cited_words or not registered_words:
        return True
    joined_cited, joined_registered = " ".join(cited_words), " ".join(registered_words)
    if joined_cited in joined_registered or joined_registered in joined_cited:
        return True
    def acronym(words):
        return "".join(w[0] for w in words if w not in {"of", "the", "and"})
    return acronym(cited_words) == acronym(registered_words) or "".join(cited_words) == acronym(registered_words)


def _venue_label_matches(cited: str, registered: str) -> bool:
    """A venue label may abbreviate its registry name, but cannot contain it as a title."""
    cited_words, registered_words = normalized(cited).split(), normalized(registered).split()
    if not cited_words or not registered_words:
        return False
    if " ".join(cited_words) in " ".join(registered_words):
        return True
    def acronym(words):
        return "".join(word[0] for word in words if word not in {"of", "the", "and"})
    return (acronym(cited_words) == acronym(registered_words) or
            "".join(cited_words) == acronym(registered_words))


def _cited_title(citation: str, record: dict) -> str:
    """Do not mistake a journal-only citation for a paper title."""
    year = YEAR.search(citation)
    if not year:
        return ""
    tail = citation[year.end():]
    # A venue inside the year parentheses is metadata, e.g. (2019, AEJ: Applied).
    parenthetical_venue = re.match(r"^\s*,[^)]*\)", tail)
    if parenthetical_venue:
        tail = tail[parenthetical_venue.end():]
    # Closing emphasis belongs to the author-year label, not the title.
    tail = re.sub(r"^\s*\)\s*[*_]*", "", tail, count=1)
    tail = re.sub(r"^\s*[.,:;—–-]\s*", "", tail, count=1).lstrip(" \t")
    venue = record.get("venue") or ""
    venue_text = re.sub(r"\s*(?:\([^()]*\)|`[^`]*`)\s*$", "", tail).strip(" *_.,")
    if venue_text and not re.search(r"[.,;]", venue_text) and venue and _venue_label_matches(venue_text, venue):
        return ""
    if re.match(r"^[^.!?]+,\s*\d+(?:\s*\(\d+\))?,\s*\d+\s*[-–]\s*\d+\s*$", tail):
        return ""
    first_word = re.match(r"\w+", tail.lstrip("*_\"'‘“("))
    if not first_word or first_word.group()[0].islower():
        return ""
    italic = re.match(r"^([*_])([^*_]+)\1", tail)
    if italic:
        title = italic.group(2).strip()
        remainder = tail[italic.end():]
    else:
        title = re.split(r"[.?!]\s+(?=[*_]*[A-Z])", tail, maxsplit=1)[0]
        remainder = ""
    title = title.strip(" *_.,?!\"'‘“”()")
    if len(title.split()) < 2:
        return ""
    venue = record.get("venue") or ""
    if title and venue and similarity(title, venue) >= 0.9:
        return ""
    if italic and re.match(r"^\s*[.,]?\s*(?:\d|doi\b|https?://)", remainder, re.I):
        return ""
    return title


def _title_score(title: str, record: dict) -> float:
    registered = record.get("title") or ""
    titles = [registered]
    if record.get("subtitle"):
        titles.append(registered + ": " + record["subtitle"])
    cited_words = normalized(title).split()
    for candidate in titles:
        words = normalized(candidate).split()
        if len(cited_words) >= 2 and words[:len(cited_words)] == cited_words:
            return 1.0
    return max((similarity(title, candidate) for candidate in titles if candidate), default=0.0)


def compare(citation: str, record: dict) -> tuple[str, list[str], str]:
    citation = URL.sub("", DOI.sub("", citation))
    fields = citation_fields(citation)
    notes = []
    year_match = re.search(r"\((?:19|20)\d{2}\)", citation)
    if not year_match and re.match(
            r"^\s*[A-Z][\w'’-]+(?:\s*(?:&|and)\s*[A-Z][\w'’-]+)?\s*(?:\(|\s+)(?:19|20)\d{2}(?=\b|[,)])",
            citation):
        year_match = YEAR.search(citation)
    author_prefix = citation[:year_match.start()].rstrip(" \t([,") if year_match else ""
    cited_authors = _author_tokens(author_prefix)
    registered_authors = set().union(*(_author_tokens(a) for a in record.get("authors") or [record.get("author", "")]))
    overlap = cited_authors & registered_authors
    first_block = re.split(r",|\s+&\s+|\s+and\s+", author_prefix, maxsplit=1)[0]
    first_cited = _author_tokens(first_block)
    first_registered = _author_tokens((record.get("authors") or [record.get("author", "")])[0])
    first_surname = normalized(first_block.split(",", 1)[0]).split()
    last_name_token = first_surname[-1] if first_surname else ""
    first_matches = bool(first_cited and first_registered and first_cited & first_registered and
                         (last_name_token in first_registered or first_cited <= first_registered))
    identity = ("SAME_WORK" if first_matches or len(overlap) >= 2 else
                "AMBIGUOUS" if overlap else
                "WRONG_WORK" if cited_authors and registered_authors else "UNCHECKED")
    year = fields["year"]
    years = [int(y) for y in (record.get("years") or [record.get("year")]) if y]
    year_detail = ""
    if year and years and year not in years:
        notes.append("YEAR_DIFFERS")
        sources = record.get("year_sources") or {}
        labelled = [f"{value} {key.removeprefix('published-')}" for key, value in sources.items()
                    if key in ("published-print", "published-online")]
        year_detail = f"cited {year}; registry " + (", ".join(labelled) if labelled else ", ".join(map(str, years)))
    title = _cited_title(citation, record or {})
    score = _title_score(title, record) if title else None
    if not title:
        notes.append("NO_TITLE")
    elif score is not None and score < 0.92:
        notes.append("TITLE_DIFFERS")
    if identity in ("UNCHECKED", "AMBIGUOUS") and score is not None and score >= 0.92:
        identity = "SAME_WORK"
    elif identity == "UNCHECKED" and year_match and score is not None and score < 0.30:
        identity = "WRONG_WORK"
    venue = record.get("venue") or ""
    if (fields["venue"] and venue and len(normalized(fields["venue"]).split()) >= 3 and
            not fields["venue"].lower().startswith("in:") and not fields["venue"].startswith("In ") and
            not _venue_matches(fields["venue"], venue)):
        notes.append("VENUE_DIFFERS")
    if fields["volume"] and record.get("volume") and fields["volume"] != str(record["volume"]):
        notes.append("VOLUME_DIFFERS")
    def expand_pages(value):
        match = re.fullmatch(r"(\d+)[-–](\d+)", str(value or "").replace(" ", ""))
        if not match:
            return str(value or "")
        start, end = match.groups()
        if len(end) < len(start):
            end = start[:len(start) - len(end)] + end
        return f"{start}-{end}"
    if fields["pages"] and record.get("pages") and expand_pages(fields["pages"]) != expand_pages(record["pages"]):
        notes.append("PAGES_DIFFER")
    if identity == "WRONG_WORK":
        basis = ("no cited author surname overlaps registry authors" if registered_authors else
                 "registry has no authors and title is substantially different")
        return identity, notes or ["OK"], basis + ("; " + year_detail if year_detail else "")
    if identity == "AMBIGUOUS":
        return identity, notes or ["OK"], "author overlap without first-author or title corroboration" + ("; " + year_detail if year_detail else "")
    if identity == "UNCHECKED":
        return identity, notes or ["OK"], "insufficient author and title evidence for identity"
    if not years:
        notes.append("YEAR_UNKNOWN")
    reason = "author overlap; " + (", ".join(notes) if notes else "citation metadata agrees")
    if score is not None and "TITLE_DIFFERS" in notes:
        reason += f" (title score {score:.2f})"
    if year_detail:
        reason += "; " + year_detail
    return identity, notes or ["OK"], reason


def _identity_tier(identity: str, citation: str, record: dict | None = None) -> str:
    """Map identity to owner-approved tier; classification remains legacy output."""
    if identity == "AMBIGUOUS":
        return "REVIEW"
    if identity != "SAME_WORK":
        return identity
    title = _cited_title(citation, record or {})
    if not title:
        return "PLAUSIBLE"
    fields = citation_fields(citation)
    years = [int(y) for y in ((record or {}).get("years") or [(record or {}).get("year")]) if y]
    score = _title_score(title, record or {})
    cited_year = fields["year"]
    year_within_tolerance = bool(cited_year and any(abs(cited_year - year) <= 1 for year in years))
    year_matches = bool(cited_year and cited_year in years)
    if (score >= 0.92 and year_within_tolerance) or (score >= 0.5 and year_matches):
        return "CONFIRMED"
    return "REVIEW"


def _cited_surnames(citation: str, *, first_for_et_al: bool = True) -> tuple[list[str], bool]:
    """Read the cited surname list before the first year, ignoring initials."""
    year = YEAR.search(citation)
    if not year:
        return [], False
    prefix = citation[:year.start()].rstrip(" \t([,")
    et_al = bool(re.search(r"\bet\s+al\.?\s*,?\s*$", prefix, re.I))
    prefix = re.sub(r"\bet\s+al\.?\s*,?\s*$", "", prefix, flags=re.I).strip()
    names = []
    for part in re.split(r"\s*(?:,|&|\band\b)\s*", prefix):
        part = re.sub(r"\s+[A-Z]{1,3}\.?$", "", part)
        surname = _family_last_token(part)
        if surname and len(surname) > 1:
            names.append(surname)
    return (names[:1] if et_al and first_for_et_al else names), et_al


def search_cited_title(citation: str, client: RegistryClient,
                       *, title: str | None = None) -> tuple[dict | None, bool]:
    """Find a cited title in either registry; return (best hit, both searches usable).

    A hit is evidence for human review, not proof that the cited DOI is wrong.
    If either lookup fails and neither finds a title, the caller must fail closed.
    """
    title = citation_fields(citation)["title"] if title is None else title
    surnames, _ = _cited_surnames(citation, first_for_et_al=False)
    if not title:
        return None, False
    query_title = title[:200]
    requests = [
        ("Crossref", "https://api.crossref.org/works?" + urllib.parse.urlencode({
            "query.bibliographic": query_title, "query.author": " ".join(surnames),
            "rows": "5", "select": "DOI,title,author,issued"})),
        ("OpenAlex", "https://api.openalex.org/works?" + urllib.parse.urlencode({
            "search": query_title, "per-page": "5",
            "select": "doi,title,publication_year,authorships"})),
    ]
    found = []
    complete = True
    for source, url in requests:
        try:
            answer = client.get(url)
            if not isinstance(answer, dict) or answer.get("status") != 200:
                raise LookupError(f"{source} title search did not succeed")
            data = answer.get("data")
            if source == "Crossref":
                message = data.get("message") if isinstance(data, dict) else None
                items = message.get("items") if isinstance(message, dict) else None
            else:
                items = data.get("results") if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise ValueError(f"{source} title search answer incomplete")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"{source} title search item incomplete")
                raw_title = item.get("title")
                if source == "Crossref" and raw_title is not None and not isinstance(raw_title, list):
                    raise ValueError(f"{source} title search title malformed")
                candidate_title = ((raw_title or [""])[0] if source == "Crossref"
                                   else raw_title or "")
                if not isinstance(candidate_title, str):
                    raise ValueError(f"{source} title search title malformed")
                score = similarity(title, candidate_title)
                if score < 0.92:
                    continue
                dates = (item.get("issued") or {}).get("date-parts") or [] if source == "Crossref" else []
                year = dates[0][0] if dates and dates[0] else None
                doi = item.get("DOI") if source == "Crossref" else item.get("doi")
                found.append((score, {"doi": clean_identifier(str(doi or "")),
                                      "title": candidate_title,
                                      "year": year if source == "Crossref" else item.get("publication_year"),
                                      "source": source}))
        except Exception:  # a missing or malformed answer cannot prove title absence
            complete = False
    return (max(found, key=lambda pair: pair[0])[1] if found else None), complete


def _apply_title_search(result: dict, citation: str, record: dict, client: RegistryClient) -> None:
    """Attach cited-title search evidence without changing the review tier yet."""
    if result["identity"] != "SAME_WORK":
        return
    title = _cited_title(citation, record)
    if not title:
        return
    if _title_score(title, record) >= 0.5:
        return
    hit, complete = search_cited_title(citation, client, title=title)
    if hit:
        result["cited_title_found"] = hit
    elif not complete:
        result["reason"] += "; title search unavailable"
    else:
        result["text_fidelity"].append("TITLE_NOT_FOUND")
        result["registry_title"] = record.get("title") or ""
        result["reason"] = ("cited title not found in Crossref or OpenAlex; DOI and authors match; "
                            "confirm which work you meant; if it is this DOI's work, use its registered title")


def _apply_author_year(result: dict, citation: str, registry: str, record: dict, client: RegistryClient) -> None:
    """Promote only fully checked title-less SAME_WORK rows; mutate the row."""
    if result["tier"] != "PLAUSIBLE" or result["identity"] != "SAME_WORK" or _cited_title(citation, record):
        return
    cited, et_al = _cited_surnames(citation)
    registered = [_family_last_token(author) for author in record.get("authors") or []]
    if not cited or not registered or not set(cited) <= set(registered):
        result["reason"] += "; cited surnames not all registered"
        return
    if et_al and cited[0] != registered[0]:
        result["reason"] += "; et al. first author differs from registry"
        return
    year = citation_fields(citation)["year"]
    try:
        registered_years = [int(value) for value in (record.get("years") or [record.get("year")]) if value]
    except (TypeError, ValueError):
        registered_years = []
    if year is None or year not in registered_years:
        result["reason"] += "; cited year does not exactly match registry"
        return
    fields = _titleless_metadata(citation)
    if fields["venue"] and record.get("venue") and not _venue_matches(fields["venue"], record["venue"]):
        result["text_fidelity"].append("VENUE_DIFFERS")
    if fields["volume"] and record.get("volume") and fields["volume"] != str(record["volume"]):
        result["text_fidelity"].append("VOLUME_DIFFERS")
    if fields["pages"] and record.get("pages") and fields["pages"].replace("–", "-") != str(record["pages"]).replace("–", "-"):
        result["text_fidelity"].append("PAGES_DIFFER")
    guard = same_team_guard(result["identifier"], record, year, client) if registry == "Crossref" else SameTeamGuardResult(False, [], 0)
    if guard.siblings:
        result["siblings"] = guard.siblings
    venue = fields["venue"]
    target_matches = bool(venue and record.get("venue") and _venue_matches(venue, record["venue"]))
    better = next((s for s in guard.siblings if venue and s.get("venue") and s.get("year") == year
                   and _venue_matches(venue, s["venue"]) and not target_matches), None)
    if better:
        result["tier"] = "REVIEW"
        result["reason"] += "; cited venue/year match a different work by the same team: " + better["title"]
        return
    differences = {"VENUE_DIFFERS", "VOLUME_DIFFERS", "PAGES_DIFFER", "YEAR_DIFFERS"}
    if differences.intersection(result["text_fidelity"]):
        return
    if not venue:
        result["tier"] = "AUTHOR_YEAR"
        result["reason"] += "; author/year agreement"
        return
    if not target_matches:
        return
    result["tier"] = "AUTHOR_YEAR"
    agreed = ["venue"] + [name for name in ("volume", "pages") if fields[name] and record.get(name)]
    result["reason"] += "; " + ", ".join(agreed) + " agree"


def _description_words(value: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "into", "versus", "against", "this", "that",
            "chapter", "springer", "link", "here", "paper", "study", "article", "doi", "www"}
    return {word for word in normalized(value).split() if len(word) >= 3 and word not in stop and not word.isdigit()}


def _titleless_metadata(citation: str) -> dict[str, str]:
    year = YEAR.search(citation)
    tail = citation[year.end():] if year else ""
    tail = re.sub(r"^\s*\)\s*[.,;]?\s*", "", tail).strip(" .,·)")
    tail = re.sub(r"\s*(?:\([^()]*\)|`[^`]*`)\s*$", "", tail)
    tail = re.sub(r"\.\s*(?:doi|https?://).*", "", tail, flags=re.I).strip(" .,·)")
    italic = re.match(r"^\*([^*]+)\*", tail)
    if italic:
        tail = italic.group(1) + tail[italic.end():]
    parts = [part.strip(" *_.,") for part in tail.split(",")]
    if italic and "," in italic.group(1):
        parts = [italic.group(1)] + [part.strip(" *_.,") for part in tail[len(italic.group(1)):].lstrip(", ").split(",") if part]
    venue = parts[0] if parts else ""
    volume = pages = ""
    for part in parts[1:]:
        if re.fullmatch(r"\d+\s*[-–]\s*\d+", part):
            pages = part.replace(" ", "")
        elif match := re.fullmatch(r"(\d+)(?:\s*\(\d+\))?", part):
            volume = match.group(1)
    return {"venue": venue, "volume": volume, "pages": pages}


def check(row: dict, client: RegistryClient, *, author_year: bool = True) -> dict:
    citation, ident, kind = clean_citation(row["citation"]), row["identifier"], row["kind"]
    result = {"citation": citation, "identifier": ident, "registry_answer": None,
              "classification": "UNRESOLVED", "identity": "UNRESOLVED", "tier": "UNRESOLVED",
              "evidence": "title_in_citation" if citation_fields(citation)["title"] else "",
              "text_fidelity": ["UNCHECKED"], "reason": ""}
    if kind == "arxiv":
        ident = "10.48550/arXiv." + ident
        result["identifier"] = ident
    if not ident or kind == "url":
        query = (citation_fields(citation)["title"] or citation)[:200]
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query.title": query, "rows": 3})
        try:
            items = client.get(url)["data"].get("message", {}).get("items", [])
        except (LookupError, urllib.error.URLError, TimeoutError, ValueError) as error:
            items = []
            result["reason"] = "title search unavailable: " + str(error)
        result["registry_answer"] = {"candidates": [{"title": (m.get("title") or [""])[0],
            "doi": m.get("DOI"), "score": round(similarity(query, (m.get("title") or [""])[0]), 3)} for m in items]}
        prefix = "ordinary URL; " if kind == "url" else ""
        result.update(classification="NO_IDENTIFIER", identity="UNCHECKED", tier="UNCHECKED",
                      reason=result["reason"] or prefix + "Crossref title candidates are suggestions only")
        return result
    try:
        registry, record, status = registry_record(ident, client)
    except (LookupError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, TypeError) as error:
        result["reason"] = "registry lookup unavailable: " + str(error)
        return result
    result["registry_answer"] = {"registry": registry, "record": record}
    if record is None:
        if status.startswith("DOI does not exist"):
            result["classification"] = result["identity"] = "NOT_FOUND"
        result["tier"] = result["identity"]
        result["reason"] = status
        return result
    if "front_matter_title" in row:
        title = row["front_matter_title"]
        score = _title_score(title, record) if title else 0.0
        if score >= 0.92:
            result.update(classification="MATCH", identity="SAME_WORK", tier="CONFIRMED",
                          evidence="front_matter_title", text_fidelity=["OK"],
                          reason="front matter title matches registered title")
        elif not title:
            result.update(classification="PARTIAL", identity="SAME_WORK", tier="TITLE_MISSING",
                          text_fidelity=["NO_TITLE"], reason="front matter DOI has no title")
        else:
            hit, complete = search_cited_title(title, client, title=title)
            tier = "REVIEW" if hit or not complete else "TITLE_WRONG"
            result.update(classification="PARTIAL", identity="SAME_WORK", tier=tier,
                          evidence="front_matter_title", text_fidelity=["TITLE_DIFFERS"],
                          reason="front matter title differs from registered title")
            if hit:
                result["cited_title_found"] = hit
        return result
    result["evidence"] = "title_in_citation" if _cited_title(citation, record) else ""
    result["identity"], result["text_fidelity"], result["reason"] = compare(citation, record)
    _apply_title_search(result, citation, record, client)
    result["tier"] = _identity_tier(result["identity"], citation, record)
    if result["tier"] == "UNCHECKED" and row.get("descriptive_link") and not citation_fields(citation)["year"]:
        shared = sorted(_description_words(citation) &
                        _description_words((record.get("title") or "") + " " + (record.get("venue") or "")))
        if len(shared) >= 2:
            result["tier"] = "DESCRIBED"
            result["reason"] = "description agrees: " + ", ".join(shared)
    if "TITLE_NOT_FOUND" in result["text_fidelity"]:
        result["tier"] = "TITLE_WRONG"
    result["classification"] = ("MISMATCH" if result["identity"] == "WRONG_WORK" else
                                "MATCH" if result["identity"] == "SAME_WORK" and result["text_fidelity"] == ["OK"] else
                                "PARTIAL")
    if author_year:
        _apply_author_year(result, citation, registry, record, client)
    return result


def _citation_key(citation: str) -> dict | None:
    parsed = parse_inline_citations(citation)
    return parsed[0] if parsed else None


def _reference_key(entry: dict) -> tuple[str, int | None, str, tuple[str, ...]]:
    authors = entry.get("authors") or []
    surnames = tuple(normalized(author.split(",", 1)[0]) for author in authors)
    return (surnames[0] if surnames else "", entry.get("year"), entry.get("suffix", ""), surnames[1:])


def _entry_matches_citation(entry: dict, citation: dict) -> bool:
    first, year, suffix, coauthors = _reference_key(entry)
    mentioned = tuple(normalized(author) for author in citation.get("authors", []))
    if not first or not mentioned or first != mentioned[0]:
        return False
    if year != citation.get("year") or suffix != citation.get("suffix", ""):
        return False
    return set(mentioned[1:]).issubset(set(coauthors))


def check_note(text: str, client: RegistryClient, rows: list[dict] | None = None) -> list[dict]:
    """Check extracted DOI rows after linking inline mentions to bibliography titles."""
    source_rows = extract(text) if rows is None else rows
    entries = parse_reference_list(text)
    bibliography_dois = {entry["doi"].casefold() for entry in entries if entry.get("doi")}
    body_dois_without_title = {
        row["identifier"].casefold() for row in source_rows
        if row.get("identifier", "").casefold() in bibliography_dois
        and not citation_fields(row["citation"])["title"]
    }
    # A DOI row in the body owns the result; its repeated bibliography entry
    # supplies title evidence and must not become a second checker row.
    source_rows = [row for row in source_rows if not (
        row.get("identifier", "").casefold() in body_dois_without_title
        and citation_fields(row["citation"])["title"]
    )]
    results = []
    for row in source_rows:
        original = check(row, client, author_year=False)
        if "line" in row:
            original["line"] = row["line"]
        if "front_matter_title" in row:
            results.append(original)
            continue
        record = (original.get("registry_answer") or {}).get("record") or {}
        original["evidence"] = "title_in_citation" if _cited_title(row["citation"], record) else ""
        if original["identity"] != "SAME_WORK" or original["evidence"]:
            results.append(original)
            continue
        mention = _citation_key(row["citation"])
        if not mention:
            answer = original.get("registry_answer") or {}
            _apply_author_year(original, row["citation"], answer.get("registry", ""),
                               answer.get("record") or {}, client)
            results.append(original)
            continue
        titled = [entry for entry in entries if entry.get("title")]
        doi_entries = [entry for entry in titled if entry.get("doi", "").casefold() == row["identifier"].casefold()]
        candidates = doi_entries or [entry for entry in titled if _entry_matches_citation(entry, mention)]
        evidence = "doi_in_list" if doi_entries else "list_entry"
        chosen = None
        if len(candidates) == 1:
            chosen = candidates[0]
        elif len(candidates) > 1:
            record = (original.get("registry_answer") or {}).get("record") or {}
            titles = [record.get("title") or ""]
            if record.get("subtitle"):
                titles.append(titles[0] + ": " + record["subtitle"])
            matches = [entry for entry in candidates if max(
                (similarity(entry["title"], title) for title in titles if title), default=0.0) >= 0.92]
            if len(matches) == 1:
                chosen = matches[0]
            else:
                original["tier"] = "REVIEW"
                original["reason"] += "; multiple reference-list entries match without a unique registry-title match"
                results.append(original)
                continue
        if chosen is None:
            answer = original.get("registry_answer") or {}
            _apply_author_year(original, row["citation"], answer.get("registry", ""),
                               answer.get("record") or {}, client)
            results.append(original)
            continue
        linked_citation = row["citation"].rstrip(" .") + ". " + chosen["title"]
        linked = check({**row, "citation": linked_citation}, client, author_year=False)
        linked["citation"] = original["citation"]
        if "line" in row:
            linked["line"] = row["line"]
        linked["linked_citation"] = linked_citation
        linked["evidence"] = evidence
        results.append(linked)
    return results


def identity_counts(rows: list[dict]) -> dict:
    rank = {"WRONG_WORK": 5, "NOT_FOUND": 4, "AMBIGUOUS": 3, "SAME_WORK": 2, "UNCHECKED": 1, "UNRESOLVED": 0}
    doi_rows = {}
    # Larger ranks are riskier; keep this explicit so duplicate DOI rows retain
    # the most concerning tier, with WRONG_WORK as the highest-risk outcome.
    doi_tiers = {}
    for row in rows:
        if str(row.get("identifier", "")).lower().startswith("10."):
            key = str(row.get("identifier", "")).lower()
            current = doi_rows.get(key)
            if current is None or rank.get(row.get("identity"), 0) > rank.get(current, 0):
                doi_rows[key] = row.get("identity", "UNRESOLVED")
            tier = row.get("tier", row.get("identity", "UNRESOLVED"))
            if (key not in doi_tiers or
                    TIER_RANK.get(tier, TIER_RANK["NOT_FOUND"]) >
                    TIER_RANK.get(doi_tiers[key], TIER_RANK["NOT_FOUND"])):
                doi_tiers[key] = tier
    def tally(values):
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return counts
    return {"mentions": tally(row.get("identity", "UNRESOLVED") for row in rows),
            "tier_mentions": tally(row.get("tier", row.get("identity", "UNRESOLVED")) for row in rows),
            "tier_distinct_dois": tally(doi_tiers.values()),
            "distinct_dois": tally(doi_rows.values()), "doi_count": len(doi_rows),
            "non_doi_entries": sum(1 for row in rows if not str(row.get("identifier", "")).lower().startswith("10."))}


def markdown(rows: list[dict]) -> str:
    def cell(value):
        return str(value or "").replace("|", "\\|").replace("\n", " ")
    out = ["| Citation | Identifier | Registry answer | Identity | Tier | Evidence | Text fidelity | Classification | Reason |",
           "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        answer = row["registry_answer"] or {}
        record = answer.get("record") or {}
        summary = answer.get("registry", "") + (": " + record.get("title", "") if record else "")
        if "candidates" in answer:
            summary = "; ".join(f"{c['title']} ({c['score']})" for c in answer["candidates"])
        out.append("| " + " | ".join(cell(v) for v in (row["citation"], row["identifier"], summary,
                        row["identity"], row.get("tier", row["identity"]), row.get("evidence", ""),
                        ", ".join(row["text_fidelity"]), row["classification"], row["reason"])) + " |")
    counts = identity_counts(rows)
    out.extend(["", f"Mention counts: {json.dumps(counts['mentions'], sort_keys=True)}",
                f"Tier mention counts: {json.dumps(counts['tier_mentions'], sort_keys=True)}",
                f"Distinct DOI counts: {json.dumps(counts['distinct_dois'], sort_keys=True)} ({counts['doi_count']} DOIs)",
                f"Tier distinct DOI counts: {json.dumps(counts['tier_distinct_dois'], sort_keys=True)}"])
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--offline", action="store_true", help="use cached answers only")
    parser.add_argument("--refresh", action="store_true", help="refresh cached registry answers")
    parser.add_argument("--pace", type=float, default=0.2, help="minimum seconds between requests")
    parser.add_argument("--exit-nonzero-on-findings", action="store_true",
                        help="exit 1 when any row is not a clean MATCH (advisory default is exit 0)")
    args = parser.parse_args(argv)
    raw_input = args.input.read_text(encoding="utf-8")
    extracted = load_references(args.input)
    source_coverage = coverage(raw_input, extracted) if args.input.suffix.lower() != ".json" else None
    client = RegistryClient(args.cache, args.pace, not args.offline, args.refresh)
    rows = (check_note(raw_input, client, extracted) if args.input.suffix.lower() != ".json" else
            [check(row, client) for row in extracted])
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.format == "json":
        print(json.dumps({"coverage": source_coverage, "counts": identity_counts(rows), "rows": rows}, indent=2, ensure_ascii=False))
    else:
        if source_coverage:
            print(f"DOIs: {source_coverage['doi_like_in_source']} in source, {source_coverage['attached']} attached, "
                  f"{source_coverage['unattached']} unattached; {source_coverage['excluded_quoted_corrections']} quoted corrections excluded.\n")
        if not rows:
            print("No references extracted.\n")
        print(markdown(rows), end="")
    if source_coverage and source_coverage["unattached"]:
        return 2
    return 1 if (not rows or (args.exit_nonzero_on_findings and any(row["classification"] != "MATCH" for row in rows))) else 0


if __name__ == "__main__":
    raise SystemExit(main())
