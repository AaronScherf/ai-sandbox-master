"""
viz/templates/spectral_decomposition.py
Illustrates the spectral theorem: a symmetric matrix's eigenvectors
form an orthogonal basis, and applying the matrix to an eigenvector
only stretches it along its own line -- no rotation. Plotting each
eigenvector alongside its own image under the matrix makes that
"stays on its own line" property directly visible.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from viz.templates import Template


def render() -> go.Figure:
    matrix = np.array([[3.0, 1.0], [1.0, 2.0]])  # symmetric -> real eigenvalues, orthogonal eigenvectors
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)

    fig = go.Figure()
    colors = ["#1f77b4", "#d62728"]
    for i in range(2):
        v = eigenvectors[:, i]
        transformed = matrix @ v
        fig.add_trace(go.Scatter(
            x=[0, v[0]], y=[0, v[1]], mode="lines+markers",
            name=f"eigenvector {i + 1} (λ={eigenvalues[i]:.2f})",
            line=dict(color=colors[i], dash="dot"),
        ))
        fig.add_trace(go.Scatter(
            x=[0, transformed[0]], y=[0, transformed[1]], mode="lines+markers",
            name=f"A · eigenvector {i + 1}",
            line=dict(color=colors[i]),
        ))
    fig.update_layout(
        title="Spectral decomposition: eigenvectors of a symmetric matrix stay on their own line under A",
        xaxis=dict(scaleanchor="y", range=[-4, 4]), yaxis=dict(range=[-4, 4]),
    )
    return fig


TEMPLATE = Template(
    name="Spectral decomposition",
    keywords=["spectral decomposition", "spectral theorem", "eigendecomposition"],
    render=render,
)
