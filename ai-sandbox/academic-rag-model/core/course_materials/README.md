# course_materials

Decides what each converted file in a course is, once per course, so pipelines read a **catalog** instead of
guessing from folder names. Courses share a small set of material kinds whose names and layouts differ; this package
weighs several independent signals per file, flags the files it is unsure of for the owner, and stores the owner's
decisions so they win on every re-run. No model or network calls. Design:
[`docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md`](../../docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md).
First user: `agent/concept_graph`.

## What a material is

| field | values |
|---|---|
| `role` | `syllabus`, `instructor`, `recitation`, `problem_set`, `exam`, `textbook`, `student_notes`, `other` |
| `format` | `slides`, `handwritten`, `typeset`, `excalidraw`, `chapter` |
| `offering` | `None` for the current offering, else the label of the `.notes_subset.json` marker above the file |
| `date` | from the file name (`2026-09-09`, or `092126` as MMDDYY) |
| `book` | textbooks only: first word of the book folder (`hansen`); a decision can rename it |
| `order` | leading number in the file name, then date, then name |

Each role belongs to an **authority** group (`Material.authority`):

| authority | roles | |
|---|---|---|
| `class` | syllabus, instructor, recitation, problem_set, exam | handed out by the class: ground truth |
| `reference` | textbook | |
| `student` | student_notes | the student's own notes or their model expansions: may contain mistakes |
| `unknown` | other | |

Mixing up roles inside `class` costs little; mixing up `class` and `student` does not. Flagging works on authority.

## Signals

| signal | votes | weight |
|---|---|---|
| frontmatter `source_excalidraw` | student_notes + excalidraw | decisive (10) |
| `chapters/NN_*` layout, or index card `doc_type: textbook` | textbook + chapter | decisive (10) |
| a textbook folder (`textbooks`, `textbooks-and-papers`) | textbook + chapter | strong (3) |
| index card `doc_type` (`problem_set`, `ta_notes`, `syllabus`, ...) | the matching role (or `handwritten` format) | strong (3) |
| `.excalidraw.` in the file name | student_notes + excalidraw | medium (2) |
| content: syllabus wording, numbered problems, exam wording, recitation wording | that role | medium (2) |
| source PDF page shape (pypdf) | landscape: `slides` **format only**; never a role | medium (2) |
| path words (`professor`, `ta`, `hw`, `exam`, `syllabus`, `slides`, ...) | that role or format | weak (1) each |
| fallback | portrait scan with few headings and short lines: `handwritten`, else `typeset` | weak (1) |

A slide deck adds its slides score to `class` (a deck is class material, whoever presented it) but picks no role;
`class` with no role votes is `instructor`. A file is **flagged** when its top authority group scores below 3 or leads
the next group by less than 2. Orientation is a convention of the courses seen so far, so on its own it never clears
review.

## Storage

- `academic-hub/.index/materials/<course>.json`: the catalog, rewritten by every `classify`.
- `academic-hub/.index/materials/<course>.decisions.json`: the owner's decisions, keyed by file path, or by folder
  path ending in `/` (applies to every file under it). A decision may set `role`, `format`, `offering`, `book`,
  `date`, `order`, or `exclude: true`. Decisions for files that no longer exist are reported and kept.

Both are shared hub state: run `classify`/`decide` from one session at a time.

## Commands

```
python -m core.course_materials.cli --hub-root <academic-hub> --course econometrics classify
python -m core.course_materials.cli --hub-root <academic-hub> --course econometrics flagged     # JSON rows
python -m core.course_materials.cli --hub-root <academic-hub> --course econometrics decide \
    "academic_notes/econometrics/class_2024/Class Notes/Hand-Written Notes" --role instructor --format handwritten
```

**Reviewing flagged files** (per the subproject rule, decisions are made on an interactive Artifact, not by editing
JSON): load the `flagged` rows into a review page's `db` collection (one row per file with its evidence, a role and
format select, Confirm / Exclude, and "apply to the whole folder"); when the owner is done, apply each row with
`decide`, then `classify` again until nothing is flagged.

## API

- `classify_course(hub_root, course, *, write=True) -> Catalog`
- `load_catalog(hub_root, course, *, refresh="if_stale" | "always" | "never") -> Catalog` (rebuilds when the course's
  files or the decisions are newer than the catalog; a corrupt file raises `CatalogError` naming it)
- `Catalog.lookup(path)`: either hub root, either slash; falls back to the nearest folder whose materials agree;
  misses are collected in `Catalog.misses`
- `Catalog.by_role(role, offering=None)`, `.flagged()`, `.offerings()`, `.book_keys()`
- `record_decision(hub_root, course, path, **fields) -> key`
- `classify_path(path) -> Material`: path-only, for files not in the catalog
