import csv

from agent.literature.profile import derive

LABELS = {"L": "low", "LM": "lower_middle", "UM": "upper_middle", "H": "high"}


def _rows():
    with open(derive.DATA_FILE, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def test_known_country_and_year():
    assert derive.country_income_group("Rwanda", 2015) == "low"
    assert derive.country_income_group("Germany", 2015) == "high"


def test_year_changes_group_matching_the_committed_table():
    row = next(r for r in _rows() if len({r[str(y)] for y in range(1990, 2023) if r[str(y)] in LABELS}) > 1)
    years = [y for y in range(1990, 2023) if row[str(y)] in LABELS]
    first, last = years[0], years[-1]
    assert derive.country_income_group(row["country"], first) == LABELS[row[str(first)]]
    assert derive.country_income_group(row["country"], last) == LABELS[row[str(last)]]
    assert derive.country_income_group(row["country"], first) != derive.country_income_group(row["country"], last) \
        or len({row[str(y)] for y in years}) > 1


def test_aliases_and_case_resolve_to_the_same_country():
    assert derive.country_income_group("tanzania", 2015) == derive.country_income_group("United Republic of Tanzania", 2015)
    assert derive.country_income_group("Democratic Republic of the Congo", 2015) == "low"
    assert derive.country_income_group("Vietnam", 2020) == "lower_middle"


def test_unknown_country_or_year_returns_none():
    assert derive.country_income_group("Atlantis", 2015) is None
    assert derive.country_income_group("Rwanda", None) is None
    assert derive.country_income_group("Rwanda", 1950) is None
    assert derive.country_income_group(None, 2015) is None


def test_year_after_last_available_uses_latest_year():
    assert derive.country_income_group("Rwanda", 2099) == derive.country_income_group("Rwanda", derive.LAST_YEAR)


def test_multi_country_same_group_returns_it_and_spanning_groups_returns_none():
    assert derive.country_income_group(["Rwanda", "Uganda"], 2015) == "low"
    assert derive.country_income_group(["Rwanda", "Germany"], 2015) is None
    assert derive.country_income_group(["Rwanda", "Atlantis"], 2015) is None
    assert derive.country_income_group([], 2015) is None


def test_start_year_prefers_llm_then_period_start_then_publication_year_with_approximate_flag():
    assert derive.resolve_start_year(2018, (2010, 2012), 2020) == (2018, False)
    assert derive.resolve_start_year(None, (2010, 2012), 2020) == (2010, True)
    assert derive.resolve_start_year(None, None, 2020) == (2020, True)
    assert derive.resolve_start_year(None, None, None) == (None, False)
