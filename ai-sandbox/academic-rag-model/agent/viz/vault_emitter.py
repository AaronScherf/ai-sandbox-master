"""
vault_emitter.py
Decoupled Asset Injection emitter (TODO-0053; design doc:
docs/brainstorms/agent/viz/2026-10-06-interactive-plotly-obsidian-pipeline.md).

viz_agent.py already produces a bare embeddable fragment (a <div>/<script>
pair, no surrounding document tags) via VizResult.fragment_html. This module
has no Plotly dependency of its own -- it takes that fragment string, writes
it unmodified to `assets/<slug>_div.html` next to a given note in the
academic-hub vault, and builds the standardized DataviewJS snippet that
mounts it at Obsidian render time. This sidesteps the four bottlenecks the
design doc documents (Pyodide's in-memory FS, the Webpage HTML Export
plugin's iframe/transclusion deadlock, file:/// CORS on embedded iframes,
and 0px container collapse): the asset is a plain file on vault disk, and
the note's DataviewJS block injects its DOM directly into the parent note
rather than transcluding or iframing it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from agent.viz.viz_agent import VizResult, _slugify

_ASSETS_SUBDIR = "assets"
_DEFAULT_HEIGHT_PX = 360


@dataclass
class VaultAsset:
    div_path: str  # absolute filesystem path to the written assets/<slug>_div.html
    vault_relative_path: str  # posix-style path relative to academic_hub_root, for DataviewJS's app.vault.adapter
    dataview_snippet: str  # the fenced ```dataviewjs ... ``` block ready to paste into the note
    slug: str


def _dataview_snippet(vault_relative_path: str, slug: str, height_px: int) -> str:
    # Mirrors the "standardized" snippet in the design doc (§4.2): checks
    # the asset exists before reading (a missing asset degrades to a
    # visible warning in the note, not a silent blank space or a thrown
    # exception), sets an explicit pixel height on the mount container (the
    # design doc's §2.4 fix for Plotly's 0px-collapse / MathJax corruption
    # bug), and re-creates each <script> tag from the injected markup
    # because `innerHTML` does not execute script tags on its own.
    return f'''```dataviewjs
// Auto-generated Interactive Plotly Component: {slug}
const path = "{vault_relative_path}";
if (await app.vault.adapter.exists(path)) {{
    const rawHtml = await app.vault.adapter.read(path);
    const container = this.container.createEl("div", {{
        attr: {{ style: "width: 100%; height: {height_px}px; position: relative;" }}
    }});
    container.innerHTML = rawHtml;
    Array.from(container.querySelectorAll("script")).forEach(oldScript => {{
        const newScript = document.createElement("script");
        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
        oldScript.parentNode.replaceChild(newScript, oldScript);
    }});
}} else {{
    this.container.createEl("p", {{ text: "Visualization asset not found: " + path }});
}}
```'''


def emit_vault_asset(
    fragment_html: str,
    academic_hub_root: str,
    note_dir: str,
    slug: str,
    height_px: int = _DEFAULT_HEIGHT_PX,
) -> VaultAsset:
    """Writes `fragment_html` unmodified to
    `<academic_hub_root>/<note_dir>/assets/<slug>_div.html` and returns the
    `VaultAsset` describing it, including the ready-to-paste DataviewJS
    mounting snippet. `note_dir` is the note's own directory, relative to
    `academic_hub_root` (e.g. "academic_notes/econometrics/summaries") --
    the caller resolves it, matching viz_agent.generate_visualization()'s
    own convention of taking root/course as separate explicit params
    rather than this module reaching into the vault to find a note.

    `fragment_html` must already be the bare partial Plotly produces with
    `full_html=False` (no <html>/<head>/<body> wrapper) -- unlike
    viz_agent._wrap_fragment(), this module never wraps it, since the
    DataviewJS snippet injects the fragment straight into the note's own
    DOM (design doc §2.2-2.3): wrapping it in a standalone document here
    would reintroduce the iframe/CORS problem this emitter exists to avoid.
    """
    assets_dir = os.path.join(academic_hub_root, note_dir, _ASSETS_SUBDIR)
    os.makedirs(assets_dir, exist_ok=True)

    div_filename = f"{slug}_div.html"
    div_path = os.path.join(assets_dir, div_filename)
    with open(div_path, "w", encoding="utf-8") as f:
        f.write(fragment_html)

    vault_relative_path = os.path.join(note_dir, _ASSETS_SUBDIR, div_filename).replace(os.sep, "/")

    return VaultAsset(
        div_path=os.path.abspath(div_path),
        vault_relative_path=vault_relative_path,
        dataview_snippet=_dataview_snippet(vault_relative_path, slug, height_px),
        slug=slug,
    )


def emit_from_viz_result(
    viz_result: VizResult,
    academic_hub_root: str,
    note_dir: str,
    height_px: int = _DEFAULT_HEIGHT_PX,
) -> VaultAsset:
    """Convenience wrapper over `emit_vault_asset()` for the common case of
    emitting a `VizResult` straight out of `viz_agent.generate_visualization()`
    -- derives the slug from `viz_result.title` via viz_agent's own
    `_slugify()` (same slugging rule the .viz/ cache path already uses, so
    the two output locations name a given concept identically) and emits
    `viz_result.fragment_html` (the bare fragment, not the wrapped
    `html_path` file -- see VizResult's own field docstring)."""
    slug = _slugify(viz_result.title)
    return emit_vault_asset(
        fragment_html=viz_result.fragment_html,
        academic_hub_root=academic_hub_root,
        note_dir=note_dir,
        slug=slug,
        height_px=height_px,
    )
