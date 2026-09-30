import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from resume_manager.tailor import _build_entry_context
from resume_manager.user_facts import load_user_facts, validate_user_facts


_MASTER = {"work_experience": [{"id": "usaid-1", "org": "USAID", "role": "MEL Lead", "bullets": ["Built an analytics system"]}]}
_FACTS = [{
    "entry_id": "usaid-1",
    "fact": "Managed inventories and asset databases for electrical infrastructure and humanitarian equipment across more than 16 projects.",
    "required_concepts": [
        ["inventory", "inventories"], ["asset database", "asset databases"],
        ["electrical infrastructure"], ["humanitarian equipment"], ["16+ projects", "more than 16 projects"],
    ],
}]


class TestUserFacts(unittest.TestCase):
    def test_loads_and_validates_facts_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "facts.yaml")
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(_FACTS, f)
            self.assertEqual(load_user_facts(path, _MASTER), _FACTS)

    def test_unknown_entry_id_is_rejected(self):
        facts = [{**_FACTS[0], "entry_id": "unknown"}]
        with self.assertRaisesRegex(ValueError, "unknown work_experience id"):
            validate_user_facts(facts, _MASTER)

    def test_entry_scoped_fact_is_rendered_inside_its_entry_context(self):
        facts = validate_user_facts(_FACTS, _MASTER)
        context = _build_entry_context(_MASTER["work_experience"], facts)
        self.assertLess(context.index("id: usaid-1"), context.index("Managed inventories"))
        self.assertIn("user-confirmed fact (preserve accurately)", context)
        self.assertIn("coverage concepts (include each accurately)", context)
