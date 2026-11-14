"""Python cluster_ink must group strokes exactly as the framer's JS clusterInk."""
import json
import os
import random
import shutil
import subprocess

import pytest

from framed_explainer_helpers import stroke
from pipelines.transcribe_notes.framed_explainer.ink import cluster_ink

RUNNER = os.path.join(os.path.dirname(__file__), "framer_cluster_runner.cjs")


def test_cluster_ink_matches_js():
    script = os.environ.get("AUTO_FRAME_SCRIPT")
    if not script or not os.path.exists(script) or not shutil.which("node"):
        pytest.skip("set AUTO_FRAME_SCRIPT to the framer script and install node")
    rng = random.Random(7)
    strokes = [stroke(f"k{i:03d}", rng.randrange(0, 3000), rng.randrange(0, 1800),
                      rng.randrange(5, 60), rng.randrange(5, 60)) for i in range(40)]
    out = subprocess.run(["node", RUNNER, script], input=json.dumps(strokes),
                         capture_output=True, text=True, check=True).stdout
    js = sorted(sorted(r) for r in json.loads(out))
    py = sorted(sorted(r.stroke_ids) for r in cluster_ink(strokes))
    assert py == js


def test_merge_fragments_matches_js():
    from pipelines.transcribe_notes.framed_explainer.ink import merge_fragments
    script = os.environ.get("AUTO_FRAME_SCRIPT")
    if not script or not os.path.exists(script) or not shutil.which("node"):
        pytest.skip("set AUTO_FRAME_SCRIPT to the framer script and install node")
    rng = random.Random(11)
    strokes = [stroke(f"k{i:03d}", rng.randrange(0, 2600), rng.randrange(0, 1500),
                      rng.randrange(5, 40), rng.randrange(5, 40)) for i in range(70)]
    out = subprocess.run(["node", RUNNER, script, "merge"], input=json.dumps(strokes),
                         capture_output=True, text=True, check=True).stdout
    js = sorted(sorted(r) for r in json.loads(out))
    py = sorted(sorted(r.stroke_ids) for r in merge_fragments(cluster_ink(strokes)))
    assert py == js
