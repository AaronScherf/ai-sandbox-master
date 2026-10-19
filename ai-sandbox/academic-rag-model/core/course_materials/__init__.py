"""What each converted file in a course is (role, format, offering), decided once per course. See
docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md."""
from .model import AUTHORITY, DECIDABLE, FORMATS, ROLES, Catalog, CatalogError, Material, normalize, rag_twin  # noqa: F401
