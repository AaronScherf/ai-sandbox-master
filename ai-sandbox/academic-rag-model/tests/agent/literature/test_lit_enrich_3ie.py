import hashlib

import yaml

from agent.literature.vocab_data.enrich_3ie import enrich, parse_array


def test_parse_and_enrich(tmp_path):
    bundle = r'[{InterventionSector:"Sector",BroadGroup:"Broad",InterventionGroup:"Group",Definition1:"Group definition",DisaggregatedIntervention:"Leaf",Definition:" new\x20definition "},{InterventionSector:"Other",BroadGroup:"Broad",InterventionGroup:"Other group",Definition1:"",DisaggregatedIntervention:"Leaf",Definition:"path wins"},{InterventionSector:"Sector",BroadGroup:"Broad",InterventionGroup:"Group",Definition1:"",DisaggregatedIntervention:"Missing",Definition:"unused"}][{OutcomeSector:"Sector",BroadGroup:"Broad",OutcomeGroup:"Group",Definition1:"",DisaggregatedOutcome:"Leaf",Definition:"stray\q"}]'
    assert parse_array(bundle, "InterventionSector")[0]["Definition"] == " new definition "
    assert parse_array(bundle, "OutcomeSector")[0]["Definition"] == r"stray\q"
    terms = []
    for ident, label, parent in [("sector", "Sector", None), ("broad", "Broad", "sector"),
                                 ("group", "Group", "broad"), ("leaf", "Leaf", "group"),
                                 ("other", "Other", None), ("broad2", "Broad", "other"),
                                 ("group2", "Other group", "broad2"), ("leaf2", "Leaf", "group2")]:
        term = {"id": f"intervention.{ident}", "label": label}
        if parent:
            term["parent"] = f"intervention.{parent}"
        if ident == "leaf2":
            term["definition"] = "kept"
        terms.append(term)
    src = tmp_path / "src"
    src.mkdir()
    (src / "intervention.yaml").write_text(yaml.safe_dump({"vocabulary": "intervention", "version": 1,
        "provenance": "3ie", "source": "synthetic", "terms": terms}), encoding="utf-8")
    out = tmp_path / "out"
    report = enrich(src, bundle, out, "2026-11-03")
    data = yaml.safe_load((out / "intervention.yaml").read_text(encoding="utf-8"))
    by_id = {t["id"]: t for t in data["terms"]}
    assert by_id["intervention.leaf"]["definition"] == "new definition"
    assert by_id["intervention.group"]["definition"] == "Group definition"
    assert by_id["intervention.leaf2"]["definition"] == "kept"
    assert "intervention.leaf2" in report["intervention"]["differ"]
    assert data["version"] == 2
    assert hashlib.sha256(bundle.encode()).hexdigest()[:12] in data["source"]
    assert "2026-11-03" in data["source"]
