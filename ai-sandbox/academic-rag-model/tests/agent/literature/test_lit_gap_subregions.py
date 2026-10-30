import tempfile
import unittest
from pathlib import Path

import yaml

from agent.literature.gap.subregions import DEFAULT_PATH, load_subregions
from agent.literature.vocab import is_country, load_countries
from gap_helpers import write_toy_tables

UNPLACED = {"AQ", "UM"}  # the standard places neither; documented in country_subregions.yaml


class TestSubregions(unittest.TestCase):
    def test_every_code_in_countries_yaml_has_a_subregion(self):
        table = load_subregions()
        missing = {c for c in load_countries() if table.region_of(c) is None}
        self.assertEqual(missing, UNPLACED)

    def test_every_subregion_code_is_a_valid_country(self):
        table = load_subregions()
        self.assertTrue(table.by_code)
        self.assertTrue(all(is_country(c) for c in table.by_code))

    def test_somalia_neighbours(self):
        table = load_subregions()
        self.assertEqual(table.region_of("SO"), "Eastern Africa")
        self.assertIn("KE", table.members("Eastern Africa"))
        self.assertNotIn("NG", table.members("Eastern Africa"))

    def test_name_lookup_is_case_and_space_insensitive(self):
        self.assertEqual(load_subregions().codes_for_name("  somalia "), ["SO"])
        self.assertEqual(load_subregions().codes_for_name("Atlantis"), [])

    def test_toy_table_loads_from_a_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            subregions, countries = write_toy_tables(tmp)
            table = load_subregions(subregions, countries)
        self.assertEqual(table.members("Western Africa"), frozenset({"NG", "GH"}))
        self.assertEqual(table.codes_for_name("kenya"), ["KE"])
        self.assertEqual(table.region_of("KE"), "Eastern Africa")

    def test_names_come_from_countries_yaml_and_the_table_holds_none(self):
        rows = yaml.safe_load(Path(DEFAULT_PATH).read_text(encoding="utf-8"))["countries"]
        self.assertTrue(rows)
        self.assertTrue(all(set(r) == {"code", "subregion"} for r in rows))
        self.assertEqual(load_subregions().names["SO"], "Somalia")


if __name__ == "__main__":
    unittest.main()
