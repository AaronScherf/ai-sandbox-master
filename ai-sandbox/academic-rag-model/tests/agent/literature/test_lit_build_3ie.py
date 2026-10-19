import tempfile
import unittest
from pathlib import Path

from agent.literature.vocab import load_vocabulary
from agent.literature.vocab_data.build_3ie import build_vocabulary, main, parse_tree, sectors_vocabulary

# Minimal imitation of the explorer's markup: sector > broad group > group (with tooltip) > leaf.
def _item(marker, label, tip=None, i=0):
    t = f'<div class="__react_component_tooltip" id="info{i}"><span>{tip}</span></div>' if tip else ""
    return (f'<div class="MuiListItem-root {marker}_0"><div class="MuiListItemText-root">'
            f'<span class="MuiListItemText-primary">{label}</span></div>{t}</div>')


def _leaf(label):
    return (f'<li><div class="MuiListItem-root"><a href="https://x/taxonomy-search-detail/intervention/y/{label}">'
            f'<div><span class="MuiListItemText-primary">{label}</span></div></a>'
            f'<div class="__react_component_tooltip" id="intervention_child_search0"><span>See all studies</span></div></div></li>')


PAGE = (
    '<h4>Interventions</h4><ul><li>' + _item("sector-click", "Agriculture &amp; Forestry") + '<ul><li>'
    + _item("board-group-click", "Agricultural policy") + '<ul><li>'
    + _item("disaggregated-intervention-click", "Market policy", "Rules that affect prices", 1)
    + '<ul>' + _leaf("Export quotas") + _leaf("Import quotas") + '</ul></li></ul></li></ul></li>'
    + '<li>' + _item("sector-click", "Health") + '<ul><li>' + _item("board-group-click", "Services") + '<ul><li>'
    + _item("disaggregated-intervention-click", "Market policy", None, 2) + '<ul>' + _leaf("Import quotas")
    + '</ul></li></ul></li></ul></li></ul>'
    '<h4>Outcomes</h4><ul><li>' + _item("outcome-sector-click", "Health") + '<ul><li>'
    + _item("outcome-board-group-click", "Mortality") + '<ul>' + _leaf("Child mortality") + '</ul></li></ul></li></ul>'
)


class TestParse(unittest.TestCase):
    def test_levels_labels_and_definitions(self):
        nodes = parse_tree(PAGE, "Interventions")
        self.assertEqual([(n["level"], n["label"]) for n in nodes][:5],
                         [(1, "Agriculture & Forestry"), (2, "Agricultural policy"), (3, "Market policy"),
                          (4, "Export quotas"), (4, "Import quotas")])
        self.assertEqual(nodes[2]["definition"], "Rules that affect prices")
        self.assertEqual(nodes[3]["definition"], "")  # the 'See all studies' tooltip is not a definition

    def test_only_the_requested_tree_is_read(self):
        self.assertEqual([n["label"] for n in parse_tree(PAGE, "Outcomes")], ["Health", "Mortality", "Child mortality"])


class TestBuild(unittest.TestCase):
    def test_vocabulary_is_valid_hierarchical_and_ids_are_unique(self):
        data = build_vocabulary(parse_tree(PAGE, "Interventions"), "intervention", "test")
        with tempfile.TemporaryDirectory() as d:
            import yaml
            (Path(d) / "intervention.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
            v = load_vocabulary(Path(d) / "intervention.yaml")
        ids = [t["id"] for t in data["terms"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(v.provenance, "3ie")
        self.assertEqual(v.terms["intervention.export_quotas"].parent, "intervention.market_policy")
        # the second 'Market policy' and 'Import quotas' sit under another sector, so they get their own ids
        self.assertEqual(sum(t["label"] == "Import quotas" for t in data["terms"]), 2)
        health_leaf = [t for t in data["terms"] if t["label"] == "Import quotas"][1]
        self.assertNotEqual(health_leaf["parent"], [t for t in data["terms"] if t["label"] == "Import quotas"][0]["parent"])

    def test_sectors_vocabulary_lists_each_top_level_once(self):
        data = sectors_vocabulary(parse_tree(PAGE, "Interventions"), "test")
        self.assertEqual([t["label"] for t in data["terms"]], ["Agriculture & Forestry", "Health"])

    def test_main_writes_loadable_files(self):
        with tempfile.TemporaryDirectory() as d:
            page = Path(d) / "page.html"
            page.write_text(PAGE, encoding="utf-8")
            self.assertEqual(main([str(page), "--tree", "Interventions", "--out", str(Path(d) / "out"), "--with-sectors"]), 0)
            self.assertEqual(len(load_vocabulary(Path(d) / "out" / "intervention.yaml").terms), 9)
            self.assertEqual(len(load_vocabulary(Path(d) / "out" / "sector.yaml").terms), 2)


if __name__ == "__main__":
    unittest.main()
