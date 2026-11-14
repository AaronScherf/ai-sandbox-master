"""Conservative, read-only bibliographic checks against DOI registration agencies.

Run: python -m tools.reference_checker references.md --format markdown
     python -m tools.reference_checker references.json --format json
JSON input may be a list of citation strings or objects with citation and identifier.
The default response cache is gitignored. DOI/arXiv ids go to registries;
references without an identifier send an extracted title or at most 200
characters of citation text to Crossref for candidate search. Source files stay local.
"""
from __future__ import annotations

import argparse
import difflib
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
from pathlib import Path

USER_AGENT = "ReferenceChecker/1.0 (bibliographic metadata validation)"
DOI = re.compile(r"10\.\d{4,9}/[^\s\]\[{}\"']+", re.I)
ARXIV = re.compile(r"(?:arxiv(?:\.org/(?:abs|pdf)/|:|\s+))(\d{4}\.\d{4,5}(?:v\d+)?|[a-z.\-]+/\d{7}(?:v\d+)?)", re.I)
URL = re.compile(r"https?://[^\s\])]+", re.I)
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
LINK = re.compile(r"\[([^]]+)\]\((https?://.*?)\)(?=\s|$|[.,;])")
SOURCE_TAG = re.compile(r"\s*\*{0,2}\[(?:VERIFIED|UNVERIFIED|ABSTRACT-ONLY)\]\*{0,2}", re.I)


def clean_citation(value: str) -> str:
    return SOURCE_TAG.sub("", value).strip()


def clean_identifier(value: str) -> str:
    """Keep balanced DOI parentheses, including Wiley SICI, and trim prose punctuation."""
    value = urllib.parse.unquote(html.unescape(value.strip()))
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    while value and value[-1] in ".,;:!?)]>`":
        end = value[-1]
        if end == ")" and value.count(")") <= value.count("("):
            break
        if end == ">" and value.count(">") <= value.count("<"):
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
    markdown_document = bool(re.search(r"^#{1,6}\s", text, re.M))
    lines = text.splitlines()
    reference_headings = [i for i, line in enumerate(lines)
                          if re.match(r"^#{1,6}\s+.*\b(?:references|bibliography)\b", line, re.I)]
    in_references = False
    reference_level = 0
    for index, raw in enumerate(lines):
        line = raw.strip()
        heading = re.match(r"^(#+)\s", line)
        if heading:
            if index in reference_headings:
                in_references, reference_level = True, len(heading.group(1))
            elif in_references and len(heading.group(1)) <= reference_level:
                in_references = False
            continue
        if not line:
            continue
        bullet = bool(re.match(r"(?:[-*+]\s+|\d+[.)]\s+)", line))
        table = line.startswith("|") and not re.match(r"^\|?\s*[-:| ]+\|", line)
        if reference_headings and not in_references:
            continue
        if markdown_document and not (bullet or table):
            continue
        if markdown_document and not reference_headings and not (table or (bullet and (LINK.search(line) or DOI.search(line)))):
            continue
        if table:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            author_year = re.compile(r"\b[A-Z][\w'’.-]*(?:\s+[A-Z][\w'’.-]*){0,4}\s*\((?:19|20)\d{2}\)")
            citation = next((cell.split("<br>", 1)[0].strip(" *`_") for cell in cells
                             if author_year.search(DOI.sub("", cell))), "")
            if not citation:
                citation = next((cell.split("<br>", 1)[0].strip(" *`_") for cell in cells
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
                        part = part.split("<br>", 1)[0]
                        part = LINK.sub(lambda m: m.group(1), part)
                        found_author_year = author_year.search(DOI.sub("", part))
                        if found_author_year:
                            candidate = part[:found_author_year.end()].strip(" |*`_")
                            break
                    rows.append({"citation": clean_citation(candidate or citation), "identifier": ident, "kind": "doi"})
                    seen.add(ident.lower())
            if not seen:
                for link in LINK.finditer(line):
                    kind, ident = identifiers(link.group(2))
                    if kind:
                        rows.append({"citation": clean_citation(citation), "identifier": ident, "kind": kind})
            continue
        links = list(LINK.finditer(line))
        if links:
            for link_index, link in enumerate(links):
                kind, ident = identifiers(link.group(2))
                if not kind:
                    continue
                citation = link.group(1)
                end = links[link_index + 1].start() if link_index + 1 < len(links) else len(line)
                suffix = line[link.end():end].lstrip(" —–-:")
                if YEAR.search(suffix) and re.match(r"[A-ZÀ-ÖØ-Þ]", suffix):
                    citation = suffix
                elif index + 1 < len(lines):
                    following = lines[index + 1].strip()
                    if following.startswith("*") and YEAR.search(following) and not LINK.search(following):
                        citation = following.strip("* ")
                rows.append({"citation": clean_citation(citation), "identifier": ident, "kind": kind})
            continue
        line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line)
        dois = list(DOI.finditer(line))
        if dois:
            for doi_index, match in enumerate(dois):
                start = dois[doi_index - 1].end() if doi_index else 0
                before = line[start:match.start()].rsplit("; ", 1)[-1]
                for segment in before.split(": "):
                    if YEAR.search(segment):
                        before = segment
                names = list(re.finditer(r"[A-ZÀ-ÖØ-Þ][\w'’\-]*(?:\s+[A-ZÀ-ÖØ-Þ][\w'’\-]*){0,3}\s*\((?:19|20)\d{2}(?=[),])", before))
                citation = (before[names[-1].start():] if names else before).strip(" *`():—–-.") or line
                rows.append({"citation": citation, "identifier": clean_identifier(match.group()), "kind": "doi"})
            continue
        kind, ident = identifiers(line)
        if kind in ("arxiv", "url"):
            rows.append({"citation": clean_citation(line.strip("* ")), "identifier": ident, "kind": kind})
        elif ((in_references and re.search(r"\(\d{4}\)\.\s+\w", line)) or
              (not markdown_document and YEAR.search(line) and len(line.split()) >= 3)):
            rows.append({"citation": clean_citation(line.strip("* ")), "identifier": "", "kind": ""})
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
                       (re.match(r"^\s*\*[^*]+\*", tail) and not re.search(r"[.?!]\s+", tail)))
    parts = re.split(r"[.?!]\s+(?=\*?[A-Z])", tail, maxsplit=1)
    title = "" if venue_only else re.split(r"\s+[0-9]+\s*\(", parts[0], maxsplit=1)[0].strip(" *_.,?!\"“”")
    if len(title.split()) < 2:
        title = ""
    details = parts[1] if len(parts) > 1 else ""
    volume = re.search(r",\s*(\d+)\s*(?:\(|,)", details)
    pages = re.search(r",\s*(\d+)\s*[–-]\s*(\d+)(?=\s*[.,]|\s*$)", details)
    venue = details[:volume.start()] if volume else re.split(r"\.\s+", details, maxsplit=1)[0]
    venue = venue.strip(" *_.,")
    return {"year": int(year.group()) if year else None,
            "author": normalized(first.group()) if first else "", "title": title,
            "venue": venue,
            "volume": volume.group(1) if volume else "",
            "pages": "-".join(pages.groups()) if pages else ""}


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
        for attempt in range(3):
            time.sleep(max(0, self.pace - (time.monotonic() - self.last_request)))
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
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(2 ** attempt)
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


def compare(citation: str, record: dict) -> tuple[str, list[str], str]:
    citation = URL.sub("", DOI.sub("", citation))
    fields = citation_fields(citation)
    notes = []
    year_match = re.search(r"\((?:19|20)\d{2}\)", citation)
    author_prefix = citation[:year_match.start()] if year_match else ""
    cited_authors = _author_tokens(author_prefix)
    registered_authors = set().union(*(_author_tokens(a) for a in record.get("authors") or [record.get("author", "")]))
    overlap = cited_authors & registered_authors
    first_block = re.split(r",|\s+&\s+|\s+and\s+", author_prefix, maxsplit=1)[0]
    first_cited = _author_tokens(first_block)
    first_registered = _author_tokens((record.get("authors") or [record.get("author", "")])[0])
    first_matches = bool(first_cited and first_registered and first_cited & first_registered and
                         (sorted(first_cited)[-1] in first_registered or first_cited <= first_registered))
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
    title = fields["title"]
    registry_titles = [record.get("title") or ""]
    if record.get("subtitle"):
        registry_titles.append(registry_titles[0] + ": " + record["subtitle"])
    score = max(similarity(title, candidate) for candidate in registry_titles) if title else None
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


def check(row: dict, client: RegistryClient) -> dict:
    citation, ident, kind = clean_citation(row["citation"]), row["identifier"], row["kind"]
    result = {"citation": citation, "identifier": ident, "registry_answer": None,
              "classification": "UNRESOLVED", "identity": "UNRESOLVED", "text_fidelity": ["UNCHECKED"], "reason": ""}
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
        result.update(classification="NO_IDENTIFIER", identity="UNCHECKED",
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
        result["reason"] = status
        return result
    result["identity"], result["text_fidelity"], result["reason"] = compare(citation, record)
    result["classification"] = ("MISMATCH" if result["identity"] == "WRONG_WORK" else
                                "MATCH" if result["identity"] == "SAME_WORK" and result["text_fidelity"] == ["OK"] else
                                "PARTIAL")
    return result


def identity_counts(rows: list[dict]) -> dict:
    rank = {"WRONG_WORK": 5, "NOT_FOUND": 4, "AMBIGUOUS": 3, "SAME_WORK": 2, "UNCHECKED": 1, "UNRESOLVED": 0}
    doi_rows = {}
    for row in rows:
        if row.get("kind") == "doi" or str(row.get("identifier", "")).lower().startswith("10."):
            key = str(row.get("identifier", "")).lower()
            current = doi_rows.get(key)
            if current is None or rank.get(row.get("identity"), 0) > rank.get(current, 0):
                doi_rows[key] = row.get("identity", "UNRESOLVED")
    def tally(values):
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return counts
    return {"mentions": tally(row.get("identity", "UNRESOLVED") for row in rows),
            "distinct_dois": tally(doi_rows.values()), "doi_count": len(doi_rows),
            "non_doi_entries": sum(1 for row in rows if not (row.get("kind") == "doi" or str(row.get("identifier", "")).lower().startswith("10.")))}


def markdown(rows: list[dict]) -> str:
    def cell(value):
        return str(value or "").replace("|", "\\|").replace("\n", " ")
    out = ["| Citation | Identifier | Registry answer | Identity | Text fidelity | Classification | Reason |",
           "|---|---|---|---|---|---|---|"]
    for row in rows:
        answer = row["registry_answer"] or {}
        record = answer.get("record") or {}
        summary = answer.get("registry", "") + (": " + record.get("title", "") if record else "")
        if "candidates" in answer:
            summary = "; ".join(f"{c['title']} ({c['score']})" for c in answer["candidates"])
        out.append("| " + " | ".join(cell(v) for v in (row["citation"], row["identifier"], summary,
                        row["identity"], ", ".join(row["text_fidelity"]), row["classification"], row["reason"])) + " |")
    counts = identity_counts(rows)
    out.extend(["", f"Mention counts: {json.dumps(counts['mentions'], sort_keys=True)}",
                f"Distinct DOI counts: {json.dumps(counts['distinct_dois'], sort_keys=True)} ({counts['doi_count']} DOIs)"])
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--cache", type=Path, default=Path(__file__).resolve().parents[1] / ".reference_checker_cache")
    parser.add_argument("--offline", action="store_true", help="use cached answers only")
    parser.add_argument("--refresh", action="store_true", help="refresh cached registry answers")
    parser.add_argument("--pace", type=float, default=0.2, help="minimum seconds between requests")
    parser.add_argument("--exit-nonzero-on-findings", action="store_true",
                        help="exit 1 when any row is not a clean MATCH (advisory default is exit 0)")
    args = parser.parse_args(argv)
    extracted = load_references(args.input)
    source_coverage = coverage(args.input.read_text(encoding="utf-8"), extracted) if args.input.suffix.lower() != ".json" else None
    client = RegistryClient(args.cache, args.pace, not args.offline, args.refresh)
    rows = [check(row, client) for row in extracted]
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
