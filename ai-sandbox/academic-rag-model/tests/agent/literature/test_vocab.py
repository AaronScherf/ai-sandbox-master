import os
import tempfile
import unittest

import yaml

from agent.literature.vocab import (
    PROVENANCES, Vocabulary, VocabularyError, is_country, load_countries, load_vocab_dir, load_vocabulary,
    validate_vocabulary,
)


def _data(**kw):
    base = {
        "vocabulary": "intervention", "version": 1, "provenance": "provisional", "source": "test fixture",
        "terms": [
            {"id": "intervention.social_protection", "label": "Social protection"},
            {"id": "intervention.cash_transfer", "label": "Cash transfer", "parent": "intervention.social_protection",
             "definition": "Money paid to households.", "aliases": ["cash transfers", "Unconditional Cash"]},
        ],
    }
    base.update(kw)
    return base


def _write(directory, name, data):
    with open(os.path.join(directory, f"{name}.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


class TestValidate(unittest.TestCase):
    def test_a_good_vocabulary_has_no_problems(self):
        self.assertEqual(validate_vocabulary(_data()), [])

    def test_problems_are_reported_in_plain_words(self):
        cases = {
            "provenance": _data(provenance="made-up"),
            "version": _data(version=0),
            "source": _data(source=""),
            "name": _data(vocabulary="Bad Name"),
        }
        for key, data in cases.items():
            with self.subTest(key=key):
                self.assertTrue(any(key in p for p in validate_vocabulary(data)), validate_vocabulary(data))

    def test_term_id_must_carry_the_vocabulary_prefix_and_be_unique(self):
        data = _data(terms=[{"id": "outcome.x", "label": "X"}, {"id": "intervention.a", "label": "A"},
                            {"id": "intervention.a", "label": "A again"}])
        problems = " | ".join(validate_vocabulary(data))
        self.assertIn("outcome.x", problems)
        self.assertIn("duplicate", problems)

    def test_parent_must_exist_and_may_not_loop(self):
        missing = _data(terms=[{"id": "intervention.a", "label": "A", "parent": "intervention.zzz"}])
        self.assertTrue(any("parent" in p for p in validate_vocabulary(missing)))
        loop = _data(terms=[{"id": "intervention.a", "label": "A", "parent": "intervention.b"},
                            {"id": "intervention.b", "label": "B", "parent": "intervention.a"}])
        self.assertTrue(any("cycle" in p for p in validate_vocabulary(loop)))

    def test_unknown_term_keys_are_refused(self):
        data = _data(terms=[{"id": "intervention.a", "label": "A", "colour": "red"}])
        self.assertTrue(any("colour" in p for p in validate_vocabulary(data)))

    def test_provenances_constant(self):
        self.assertEqual(PROVENANCES, ("3ie", "provisional", "local"))


class TestLoadAndFind(unittest.TestCase):
    def test_find_matches_id_label_and_alias_ignoring_case_and_spacing(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "intervention", _data())
            v = load_vocabulary(os.path.join(d, "intervention.yaml"))
        self.assertIsInstance(v, Vocabulary)
        for probe in ("intervention.cash_transfer", "CASH  transfer", "unconditional cash"):
            with self.subTest(probe=probe):
                self.assertEqual(v.find(probe).id, "intervention.cash_transfer")
        self.assertIsNone(v.find("vouchers"))
        self.assertTrue(v.contains("intervention.social_protection"))
        self.assertFalse(v.contains("Social protection"))

    def test_invalid_file_raises_with_every_problem(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "intervention", _data(provenance="nope", version=0))
            with self.assertRaises(VocabularyError) as ctx:
                load_vocabulary(os.path.join(d, "intervention.yaml"))
        self.assertIn("provenance", str(ctx.exception))
        self.assertIn("version", str(ctx.exception))

    def test_file_stem_must_equal_vocabulary_name(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "wrongname", _data())
            with self.assertRaises(VocabularyError):
                load_vocab_dir(d)

    def test_load_vocab_dir_skips_countries_and_non_yaml(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "intervention", _data())
            _write(d, "countries", {"countries": [{"code": "SO", "name": "Somalia"}]})
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                f.write("x")
            self.assertEqual(sorted(load_vocab_dir(d)), ["intervention"])


class TestCountries(unittest.TestCase):
    def test_shipped_list_is_the_249_iso_codes(self):
        codes = load_countries()
        self.assertEqual(len(codes), 249)
        for c in ("SO", "US", "BD", "SS"):
            self.assertIn(c, codes)

    def test_is_country_is_strict_about_form(self):
        self.assertTrue(is_country("SO"))
        for bad in ("so", "SOM", "ZZ", "", None, 5, "S"):
            with self.subTest(bad=bad):
                self.assertFalse(is_country(bad))

    def test_shipped_list_agrees_with_the_standard_library_tzdata_when_present(self):
        try:
            import importlib.resources as r
            rows = (r.files("tzdata.zoneinfo") / "iso3166.tab").read_text(encoding="utf-8").splitlines()
        except Exception:
            self.skipTest("tzdata not installed")
        expected = {line.split("\t")[0] for line in rows if line and not line.startswith("#")}
        self.assertEqual(load_countries(), frozenset(expected))


if __name__ == "__main__":
    unittest.main()
