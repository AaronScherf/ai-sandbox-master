"""What each converted file in a course is (role, format, offering), decided once per course. See
docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md."""
from .classify import (classify_course, classify_file, classify_path, date_from_stem, load_catalog,  # noqa: F401
                       load_decisions, record_decision)
from .model import AUTHORITY, DECIDABLE, FORMATS, ROLES, Catalog, CatalogError, Material, normalize, rag_twin  # noqa: F401
