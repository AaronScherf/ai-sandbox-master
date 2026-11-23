"""Geography derivations: World Bank income group of a study country in a given year, and the intervention year."""

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[1] / "reference_data" / "wb_income_groups.csv"
GROUPS = {"L": "low", "LM": "lower_middle", "UM": "upper_middle", "H": "high"}

# Names an LLM is likely to write, mapped to the World Bank's names (normalised, see _norm).
ALIASES = {
    "democratic republic of the congo": "congo dem rep", "dr congo": "congo dem rep", "drc": "congo dem rep",
    "republic of the congo": "congo rep", "congo brazzaville": "congo rep",
    "tanzania": "tanzania", "united republic of tanzania": "tanzania",
    "vietnam": "viet nam", "laos": "lao pdr", "egypt": "egypt arab rep", "iran": "iran islamic rep",
    "russia": "russian federation", "syria": "syrian arab republic", "turkey": "turkiye", "turkiye": "turkiye",
    "gambia": "gambia the", "the gambia": "gambia the", "bahamas": "bahamas the", "the bahamas": "bahamas the",
    "yemen": "yemen rep", "venezuela": "venezuela rb", "south korea": "korea rep", "republic of korea": "korea rep",
    "north korea": "korea dem peoples rep", "kyrgyzstan": "kyrgyz republic", "slovakia": "slovak republic",
    "micronesia": "micronesia fed sts", "ivory coast": "cote d ivoire", "cape verde": "cabo verde",
    "hong kong": "hong kong sar china", "macau": "macao sar china", "macao": "macao sar china",
    "swaziland": "eswatini", "burma": "myanmar", "east timor": "timor leste", "czech republic": "czechia",
    "st lucia": "saint lucia", "united states of america": "united states", "usa": "united states",
    "uk": "united kingdom", "britain": "united kingdom", "palestine": "west bank and gaza",
}


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", folded)).strip()


@lru_cache(maxsize=1)
def _table() -> tuple[dict[str, dict[int, str]], int]:
    """({normalised name: {year: group label}}, last year in the table)."""
    with DATA_FILE.open(encoding="utf-8", newline="") as f:
        lines = [line for line in f if not line.startswith("#")]
    by_name: dict[str, dict[int, str]] = {}
    last = 0
    for row in csv.DictReader(lines):
        years = {int(k): GROUPS[v] for k, v in row.items() if k.isdigit() and v in GROUPS}
        if years:
            last = max(last, max(years))
        by_name[_norm(row["country"])] = years
    return by_name, last


LAST_YEAR = _table()[1]


def _one(country: str, year: int) -> str | None:
    by_name, last = _table()
    key = _norm(country)
    years = by_name.get(ALIASES.get(key, key))
    if years is None:
        return None
    return years.get(min(year, last))


def country_income_group(country: str | list[str] | None, year: int | None) -> str | None:
    """World Bank income group (low, lower_middle, upper_middle, high) of the country in that year, or None when
    the country or year is unknown, or the countries span more than one group. Never guesses."""
    if not country or year is None:
        return None
    names = [country] if isinstance(country, str) else list(country)
    groups = {_one(name, year) for name in names}
    return groups.pop() if len(groups) == 1 and None not in groups else None


def resolve_start_year(llm_year: int | None, study_period: tuple[int, int] | None,
                       publication_year: int | None) -> tuple[int | None, bool]:
    """The intervention start year and whether it is approximate (taken from the study period or publication)."""
    if llm_year:
        return llm_year, False
    if study_period:
        return study_period[0], True
    if publication_year:
        return publication_year, True
    return None, False
