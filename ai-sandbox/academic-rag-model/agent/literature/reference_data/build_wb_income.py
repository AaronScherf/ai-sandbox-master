"""One-off builder for wb_income_groups.csv from the World Bank historical classification workbook (OGHIST.xlsx).

Usage: python -m agent.literature.reference_data.build_wb_income PATH_TO_OGHIST.xlsx

Reads the "Country Analytical History" sheet with the standard library only. The workbook is downloaded data, so
any XML part that declares a DOCTYPE or ENTITY is refused before parsing. Columns are the calendar year of the GNI
data used (1987 to the latest); a year's group is the classification based on that year's data, published the
following July 1. The CSV is committed with its source and retrieval date in the first comment line.
"""

import csv
import datetime
import re
import sys
import xml.etree.ElementTree as ET  # nosec: guarded by _safe_xml below
import zipfile
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
OUT = Path(__file__).with_name("wb_income_groups.csv")
SOURCE = "https://datacatalogfiles.worldbank.org/ddh-published/0037712/DR0090754/OGHIST.xlsx"
SHEET_NAME = "Country Analytical History"


def _safe_xml(data: bytes) -> ET.Element:
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("refusing XML that declares a DOCTYPE or ENTITY")
    return ET.fromstring(data)


def _sheet_path(z: zipfile.ZipFile, name: str) -> str:
    workbook = _safe_xml(z.read("xl/workbook.xml"))
    rels = _safe_xml(z.read("xl/_rels/workbook.xml.rels"))
    rid = next(s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
               for s in workbook.iter(NS + "sheet") if s.get("name") == name)
    target = next(r.get("Target") for r in rels if r.get("Id") == rid)
    return "xl/" + str(target).lstrip("/").removeprefix("xl/")


def read_rows(xlsx: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(xlsx) as z:
        shared = [" ".join(t.text or "" for t in si.iter(NS + "t")).strip()
                  for si in _safe_xml(z.read("xl/sharedStrings.xml")).findall(NS + "si")]
        rows = []
        for r in _safe_xml(z.read(_sheet_path(z, SHEET_NAME))).iter(NS + "row"):
            cells = {}
            for c in r.findall(NS + "c"):
                v = c.find(NS + "v")
                col = re.match(r"[A-Z]+", c.get("r") or "")
                if v is None or v.text is None or col is None:
                    continue
                cells[col.group()] = shared[int(v.text)] if c.get("t") == "s" else v.text
            rows.append(cells)
        return rows


def build(xlsx: str) -> None:
    rows = read_rows(xlsx)
    header = next(r for r in rows if r.get("B", "").startswith("Data for calendar year"))
    year_cols = {col: val for col, val in header.items() if re.fullmatch(r"\d{4}", val)}
    with OUT.open("w", encoding="utf-8", newline="") as f:
        f.write(f"# World Bank country analytical history; source {SOURCE}; retrieved {datetime.date.today().isoformat()}; "
                "column = calendar year of the GNI data (L low, LM lower middle, UM upper middle, H high, .. none)\n")
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["iso3", "country", *year_cols.values()])
        for r in rows:
            if re.fullmatch(r"[A-Z]{3}", r.get("A", "")) and r.get("B"):
                writer.writerow([r["A"], r["B"], *(r.get(col, "..") for col in year_cols)])


if __name__ == "__main__":
    build(sys.argv[1])
    print(f"wrote {OUT}")
