"""A bad string escape works today but is slated to become a SyntaxError; keep the package clean."""
import warnings
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[3] / "agent" / "concept_graph"


def test_no_module_in_the_package_compiles_with_a_syntax_warning():
    for path in sorted(PACKAGE.rglob("*.py")):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
