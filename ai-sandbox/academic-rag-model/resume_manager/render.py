"""
render.py
Markdown -> HTML -> styled PDF via xhtml2pdf (spec §6). Not
weasyprint -- confirmed during planning that weasyprint fails to
import on Windows without separately-installed Pango/GTK native
libraries; xhtml2pdf is pure Python and installs cleanly via pip.
"""
from __future__ import annotations

import markdown as markdown_lib
from xhtml2pdf import pisa

_CSS = """
<style>
@page {
    size: letter;
    margin: 0.6in 0.6in 0.8in 0.6in;
}
body {
    font-family: Helvetica, Arial, sans-serif;
    color: #333;
    font-size: 10.5pt;
    line-height: 1.4;
}
h1 {
    text-align: center;
    text-transform: uppercase;
    color: #111;
    font-size: 22pt;
    margin-bottom: 5px;
}
h2 {
    color: #003366;
    border-bottom: 1px solid #ccc;
    font-size: 13pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 20px;
    margin-bottom: 8px;
}
h3 {
    font-size: 11pt;
    margin-top: 10px;
    margin-bottom: 3px;
}
ul {
    margin-top: 0;
    margin-bottom: 10px;
    padding-left: 20px;
}
li {
    margin-bottom: 3px;
}
</style>
"""


def render_resume_pdf(markdown_text: str, output_path: str) -> None:
    """Renders `markdown_text` to a styled PDF at `output_path`. Raises
    if xhtml2pdf reports an error (pisa.CreatePDF's `.err` is
    non-zero) -- an application's PDF is either fully written or not
    written at all, never a silently-broken partial file."""
    html_body = markdown_lib.markdown(markdown_text)
    full_html = f"<html><head>{_CSS}</head><body>{html_body}</body></html>"
    with open(output_path, "wb") as f:
        result = pisa.CreatePDF(full_html, dest=f)
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} error(s) rendering {output_path}")
