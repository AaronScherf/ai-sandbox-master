# ai-sandbox/academic-rag-model/viz/templates/gradient_descent.py
"""
viz/templates/gradient_descent.py
Illustrates gradient descent on a 2D bowl-shaped surface,
f(x, y) = x^2 + 2y^2: a contour plot of the surface plus the actual
descent path taken from a fixed starting point, so the path visibly
curves toward, then converges on, the minimum at the origin.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def _f(x, y):
    return x ** 2 + 2 * y ** 2


def _grad(x, y):
    return np.array([2 * x, 4 * y])


def render() -> go.Figure:
    xs = np.linspace(-4, 4, 100)
    ys = np.linspace(-4, 4, 100)
    zs = np.array([[_f(x, y) for x in xs] for y in ys])

    point = np.array([3.5, 3.0])
    learning_rate = 0.15
    path = [point.copy()]
    for _ in range(30):
        point = point - learning_rate * _grad(*point)
        path.append(point.copy())
    path = np.array(path)

    fig = go.Figure()
    fig.add_trace(go.Contour(x=xs, y=ys, z=zs, showscale=False, opacity=0.6, contours_coloring="lines"))
    fig.add_trace(go.Scatter(
        x=path[:, 0], y=path[:, 1], mode="lines+markers", name="gradient descent path",
        marker=dict(size=5, color="#d62728"),
    ))
    fig.update_layout(title="Gradient descent on f(x, y) = x² + 2y²: the path curves toward the minimum")
    return fig


TEMPLATE = Template(
    name="Gradient descent",
    keywords=["gradient descent", "steepest descent"],
    render=render,
)
