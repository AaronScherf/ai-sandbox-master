"""One-off builder for openalex_taxonomy.yaml: the OpenAlex domain / field / subfield lists.

Usage: python -m agent.literature.reference_data.build_openalex
Fetches /domains, /fields and /subfields from api.openalex.org once and writes the committed YAML, with the
retrieval date. Tests never touch the network.
"""

import datetime
import json
import urllib.request
from pathlib import Path

import yaml

API = "https://api.openalex.org"
OUT = Path(__file__).with_name("openalex_taxonomy.yaml")
USER_AGENT = "academic-rag-model-taxonomy-builder/1.0"


def _fetch(entity: str) -> list[dict]:
    results: list[dict] = []
    page = 1
    while True:
        url = f"{API}/{entity}?per-page=200&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        batch = data.get("results", [])
        results.extend(batch)
        if len(results) >= data.get("meta", {}).get("count", 0) or not batch:
            return results
        page += 1


def _short(openalex_id: str) -> str:
    return openalex_id.rstrip("/").rsplit("/", 1)[-1]


def build() -> dict:
    domains = {_short(d["id"]): d["display_name"] for d in _fetch("domains")}
    fields, field_domain = {}, {}
    for f in _fetch("fields"):
        fid = _short(f["id"])
        fields[fid] = f["display_name"]
        field_domain[fid] = _short(f["domain"]["id"])
    subfields, subfield_field = {}, {}
    for s in _fetch("subfields"):
        sid = _short(s["id"])
        subfields[sid] = s["display_name"]
        subfield_field[sid] = _short(s["field"]["id"])
    return {
        "retrieved": datetime.date.today().isoformat(),
        "source": f"{API}/domains, /fields, /subfields",
        "domains": domains,
        "fields": {fid: {"label": label, "domain": field_domain[fid]} for fid, label in fields.items()},
        "subfields": {sid: {"label": label, "field": subfield_field[sid]} for sid, label in subfields.items()},
    }


def main() -> None:
    data = build()
    OUT.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"{len(data['domains'])} domains, {len(data['fields'])} fields, {len(data['subfields'])} subfields -> {OUT}")


if __name__ == "__main__":
    main()
