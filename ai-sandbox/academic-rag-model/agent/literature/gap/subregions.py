"""Country -> UN M49 subregion, for the gap analysis's notion of an adjacent country. Names come from countries.yaml."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ..transcript import normalize
from ..vocab import DATA_DIR

DEFAULT_PATH = Path(__file__).with_name("country_subregions.yaml")
_DEFAULT_COUNTRIES = DATA_DIR / "countries.yaml"
_cache: dict[tuple, "Subregions"] = {}


@dataclass
class Subregions:
    by_code: dict[str, str]  # ISO alpha-2 code -> subregion
    names: dict[str, str]  # ISO alpha-2 code -> country name

    def region_of(self, code: str) -> str | None:
        return self.by_code.get(code.upper())

    def members(self, subregion: str) -> frozenset[str]:
        return frozenset(c for c, r in self.by_code.items() if r == subregion)

    def codes_for_name(self, text: str) -> list[str]:
        key = normalize(text)
        return sorted(c for c, name in self.names.items() if normalize(name) == key)


def _rows(path) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["countries"]


def load_subregions(path=None, countries_path=None) -> Subregions:
    key = (str(path or DEFAULT_PATH), str(countries_path or _DEFAULT_COUNTRIES))
    if key not in _cache or (path or countries_path):  # a caller-supplied (test) path is always read fresh
        _cache[key] = Subregions({r["code"]: r["subregion"] for r in _rows(key[0])},
                                 {r["code"]: r["name"] for r in _rows(key[1])})
    return _cache[key]
