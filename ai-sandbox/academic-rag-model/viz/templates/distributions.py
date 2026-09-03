# ai-sandbox/academic-rag-model/viz/templates/distributions.py
"""
viz/templates/distributions.py
Compares a binomial distribution against its normal approximation --
the central visual intuition behind the central limit theorem /
de Moivre-Laplace theorem: Binomial(n, p) looks increasingly
bell-shaped and normal as n grows. Implemented with plain numpy/math
(no scipy) to avoid adding a dependency this project doesn't otherwise
use.
"""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def _binomial_pmf(n: int, p: float) -> tuple[np.ndarray, np.ndarray]:
    ks = np.arange(0, n + 1)
    pmf = np.array([math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in ks])
    return ks, pmf


def _normal_pdf(xs: np.ndarray, mean: float, std: float) -> np.ndarray:
    return (1 / (std * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((xs - mean) / std) ** 2)


def render() -> go.Figure:
    n, p = 40, 0.5
    ks, pmf = _binomial_pmf(n, p)
    mean, std = n * p, math.sqrt(n * p * (1 - p))
    xs = np.linspace(0, n, 200)
    normal = _normal_pdf(xs, mean, std)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=ks, y=pmf, name=f"Binomial(n={n}, p={p})", opacity=0.6))
    fig.add_trace(go.Scatter(x=xs, y=normal, mode="lines", name="Normal approximation"))
    fig.update_layout(title=f"Binomial(n={n}, p={p}) vs. its normal approximation -- CLT in action")
    return fig


TEMPLATE = Template(
    name="Distributions",
    keywords=["central limit theorem", "normal approximation", "binomial distribution", "distribution shape"],
    render=render,
)
