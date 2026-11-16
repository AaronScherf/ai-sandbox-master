"""Write data/manifest.json: source, version, access date and sha256 for every raw file (tracked; the data are not)."""
import hashlib
import json
from datetime import date

from common import RAW, ROOT

SOURCES = {
    "harveststat": {"provider": "Lee et al., HarvestStat Africa v1.2 (CC-BY-4.0)",
                    "url": "https://datadryad.org/dataset/doi:10.5061/dryad.vq83bk42w",
                    "paper": "https://doi.org/10.1038/s41597-025-05001-z",
                    "note": "downloaded in a browser by the owner; Dryad file API needs a login token"},
    "ofra": {"provider": "OFRA response-function dataset, updated Aug 2023 (Wortmann, UNL)",
             "url": "https://datadryad.org/dataset/doi:10.5061/dryad.tt6h5h1",
             "note": "xlsx supplied by the owner; Raw sheet used"},
    "acled": {"provider": "ACLED (acleddata.com), event_date 2010-01-01 to 2025-10-31 per country via API; Somalia and "
                          "Sudan exports downloaded by hand (1997-2025)",
              "url": "https://acleddata.com/api/acled/read",
              "note": "ACLED terms forbid redistribution; do not commit. Accessed 2026-11-16 (API pulls)"},
    "chirps": {"provider": "UCSB CHC CHIRPS v2.0 Africa monthly GeoTIFFs",
               "url": "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs/",
               "note": "2010-01 to 2023-12; accessed 2026-11-16"},
}
files = {}
for p in sorted(RAW.rglob("*")):
    if p.is_file():
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        files[p.relative_to(RAW).as_posix()] = {"bytes": p.stat().st_size, "sha256": h.hexdigest()}
doc = {"generated": date.today().isoformat(), "sources": SOURCES, "files": files}
(ROOT / "data" / "manifest.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
print(len(files), "files recorded")
