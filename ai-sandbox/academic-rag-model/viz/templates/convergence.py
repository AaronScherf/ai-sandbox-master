# ai-sandbox/academic-rag-model/viz/templates/convergence.py
"""
viz/templates/convergence.py
Plots partial sums of the alternating harmonic series
(1 - 1/2 + 1/3 - 1/4 + ...) against n, illustrating visually that the
sequence of partial sums converges (to ln 2) even though no finite
prefix of terms sums to it exactly -- the core intuition behind
convergence of an infinite series.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def render() -> go.Figure:
    n_terms = 200
    ns = np.arange(1, n_terms + 1)
    terms = ((-1.0) ** (ns + 1)) / ns
    partial_sums = np.cumsum(terms)
    limit = np.log(2)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ns, y=partial_sums, mode="lines", name="partial sum"))
    fig.add_trace(go.Scatter(
        x=[1, n_terms], y=[limit, limit], mode="lines", name="limit (ln 2)",
        line=dict(dash="dash", color="#d62728"),
    ))
    fig.update_layout(title="Partial sums of the alternating harmonic series converge to ln 2")
    return fig


TEMPLATE = Template(
    name="Series convergence",
    keywords=["convergence", "divergence", "partial sum", "alternating series", "series converges"],
    render=render,
)
