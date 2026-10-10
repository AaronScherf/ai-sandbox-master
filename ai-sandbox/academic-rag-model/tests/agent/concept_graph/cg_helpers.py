import shutil
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[3] / "agent" / "concept_graph" / "sample_data"


def copy_sample(dest: Path) -> Path:
    """Copy the sample graph into dest/graph and return that directory."""
    target = Path(dest) / "graph"
    shutil.copytree(SAMPLE, target)
    return target
