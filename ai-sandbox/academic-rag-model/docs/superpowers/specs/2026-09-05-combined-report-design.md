# Combined Report: Text + Citations + Visualization in One Document

Brainstormed and approved with the user 2026-09-05. Builds on
`docs/superpowers/specs/2026-09-02-visualization-agent-design.md` and
`docs/superpowers/specs/2026-09-03-viz-ollama-retry-hardening-design.md`
(`viz/`) and the existing `rag/rag_agent.py` (spec:
`docs/superpowers/specs/2026-08-30-rag-agent-design.md`). This is the
"combined report" item flagged as the next design conversation in the
visualization sub-agent's status doc since 2026-09-03.

## 1. Problem & goals

`answer_question()` already produces everything a report needs, but as
three disconnected pieces: a synthesized text `answer`, a `citations`
list, and an optional `visualization` (a `VizResult` pointing at a
standalone `.html` file) when `visualize=True`. Both existing consumers
(`rag_agent.py`'s own REPL and `indexer/index_search.py ask`) just print
the answer, then the citations, then a bare `visualization: <path>`
line -- nothing stitches these into one document a student would
actually want to open or hand someone.

**Goal:** give `answer_question()` an opt-in way to produce one
self-contained HTML file combining the question, the answer text, the
citations, and (when present) the interactive Plotly visualization --
open it in a browser, the plot is fully manipulable, nothing else needs
to travel with it.

**Non-goals**
- Switching visualization libraries (matplotlib, Bokeh, etc.) --
  considered and rejected 2026-09-05: matplotlib can't preserve the
  interactivity (zoom/pan/hover) that's the point of embedding a plot
  at all, and introducing a second library for no functional gain isn't
  worth the added templates/prompt-tuning cost. Plotly stays.
- Including full conversation history in the report. A report is built
  from one `answer_question()` call's own question/answer/citations/
  visualization -- `history` is a separate cross-call concern the
  report doesn't touch.
- A print-friendly/PDF export path (e.g., via Plotly's `kaleido`
  static-export). Raised as a possible future direction, not built here
  -- HTML is the only target format.
- Any change to the local example store (`viz/example_store.py`) or to
  the retry-hardening/timeout logic in `viz/llm_fallback.py`'s
  generation loop. This pass touches only how the *finished* Plotly
  output gets rendered (fragment vs. full document) and how it's
  combined with the rest of an answer.
- Reusing the raw retrieved-passage excerpts in the report's citation
  list. The report's citations section shows the same citation strings
  already printed today (`c.citation` / `c.path` / `c.root`), not the
  underlying passage text -- a formatting layer over data already
  produced, not a new content source.

## 2. Architecture

**New module:** `rag/report_builder.py`. `rag_agent.answer_question()`
is already the one place holding all three pieces (answer, citations,
visualization) after computing them, so it's the natural call site --
no new orchestration layer needed above it.

```python
def build_report(
    question: str, answer: str, citations: list[Citation],
    visualization: VizResult | None, output_path: str,
) -> str | None:
    """Writes one self-contained HTML file combining question, answer,
    citations, and (if given) the visualization's embedded fragment.
    Never raises past its caller -- any failure is logged as a WARNING
    and this returns None, leaving the rest of the answer untouched."""
```

`AnswerResult` (in `rag_agent.py`) gains one new field:

```python
@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]
    history: list[Turn]
    visualization: VizResult | None = None
    report_path: str | None = None  # new
```

`answer_question()` gains one new parameter, **independent** of
`visualize` (confirmed with the user 2026-09-05): `report: bool =
False`. `report=True` with `visualize=False` -- or with `visualize=True`
but the fallback degraded to `None` -- still produces a valid report
containing just the question, answer, and citations; the visualization
section is simply omitted. Every existing caller (both current
consumers, and anything else calling `answer_question()` today)
defaults to `report=False` and sees zero behavior change.

## 3. Making the plot embeddable: fragment vs. full document

Both viz tiers currently call Plotly's `write_html(path,
include_plotlyjs="inline")`, which always renders a **full standalone
HTML document** (`<html><head>...<body>...</body></html>`) -- there is
no way to drop that document directly into a larger page. Fixing this
requires touching both tiers, but only code this project authors
itself, never model-generated code:

- `viz/viz_agent.py`'s template path: change from writing directly via
  `fig.write_html(output_path, include_plotlyjs="inline")` to rendering
  the fragment string first (`fig.to_html(include_plotlyjs="inline",
  full_html=False)`), then writing a *wrapped* version of that fragment
  to `output_path` (see below), while also returning the raw fragment.
- `viz/llm_fallback.py`'s subprocess postamble -- the fixed line this
  project appends after the model's own generated script, never
  anything the model itself writes -- changes from
  `fig.write_html({path!r}, include_plotlyjs='inline')` to
  `fig.write_html({path!r}, include_plotlyjs='inline', full_html=False)`.
  This means the on-disk **cache** (`.cache/<hash>.html`) now stores
  fragments, not full documents; the cache-hit path in
  `generate_via_llm()` (today a raw `shutil.copyfile`, returning
  `VizResult` without ever reading the cached file's content) must
  instead read the cached fragment's text, write a *wrapped* version to
  `output_path`, and pass the fragment text through as `fragment_html`
  on the returned `VizResult` -- a cache hit must populate
  `fragment_html` exactly like a fresh generation does, not leave it
  empty.

`VizResult` (in `viz/viz_agent.py`) gains one new field:

```python
@dataclass
class VizResult:
    html_path: str
    title: str
    source: str  # "template" | "llm_fallback"
    fragment_html: str  # new -- the raw embeddable <div>/<script> fragment,
        # plotly.js inlined; html_path's file is this fragment wrapped in a
        # minimal standalone <html><body> shell, unchanged for direct-open use
```

A small helper, `_wrap_fragment(fragment: str) -> str`, lives in
`viz/viz_agent.py` and produces the minimal standalone shell
(`<html><body>{fragment}</body></html>`) used by both tiers when
writing to `output_path` -- `llm_fallback.py` imports it from there,
matching the existing dependency direction (`llm_fallback.py` already
imports `VizResult` from `viz_agent.py`, never the reverse). One
rendering path (fragment), two thin consumers (a wrapped file for
direct opening, the raw fragment for report embedding). `report_builder.build_report()`
takes `visualization.fragment_html` directly from the `VizResult` it
already has -- it never reads `html_path`'s file back off disk or
re-parses anything out of it.

Interactivity is fully preserved: `full_html=False` only drops the
outer document scaffolding (`<html><head><body>`), not
`include_plotlyjs="inline"` or the actual `Plotly.newPlot(...)` call
with the real data -- those are what make a Plotly output interactive
(zoom, pan, hover, legend toggling), and neither depends on the
surrounding document tags.

## 4. Report content and file format

One HTML file, no external dependencies (no CDN link, no template
engine, no CSS framework) -- plain f-string interpolation into a
minimal structure, matching the "no paid API, no external service"
style already used throughout `viz/`:

```
<h1>{question}</h1>
<p>{answer, HTML-escaped}</p>
<h2>Citations</h2>
<ul>
  <li>[{root}] {path} ({citation})</li>
  ...
</ul>
<h2>Visualization</h2>          <- section omitted entirely if visualization is None
{visualization.fragment_html}
```

`answer` is HTML-escaped (`html.escape()`, stdlib) before interpolation
-- it's LLM-generated free text that could coincidentally contain
characters HTML would otherwise interpret as markup. Citation fields
(`path`, `citation`, `root`) are escaped the same way.

**File location:** a new sibling tree, `<academic_hub_root>/.reports/<course>/<slug>.html`
-- parallel to the existing `.viz/<course>/` tree, keeping "a rendered
plot artifact" and "a combined document artifact" as distinct kinds of
output (confirmed with the user 2026-09-05) rather than mixing them in
one directory. Needs a new `.gitignore` entry (`**/.reports/`,
mirroring the existing `**/.viz/` entry) -- generated, corpus-derived
content, same IP posture as `.viz/`. The filename slug reuses the same
slugification logic `viz_agent.py` already has (`_slugify`, keyed on
the question text) -- duplicated as a small private helper in
`report_builder.py` rather than extracted into a new shared module, to
avoid `report_builder.py` needing to import anything from `viz/` at all
(a `report=True, visualize=False` caller shouldn't pull in `viz/`'s
heavier dependencies, matching the existing lazy-import boundary
`viz_agent.py:55` already documents for the same reason).

## 5. CLI integration

Both existing consumers get a new `--report` flag, independent of
`--visualize`, printing a `report: <path>` line the same way
`visualization: <path>` prints today:

- `rag/rag_agent.py`'s `main()` (the REPL)
- `indexer/index_search.py`'s `ask` subcommand

## 6. Error handling

`build_report()` never raises past its caller, matching the
project-wide convention already established for `generate_via_llm()`
and the template path (`viz_agent.py`'s own try/except around
`match_template`). Any failure -- a disk write error, an unexpected
`None`/malformed field -- is caught, logged as
`WARNING: report generation failed (...)`, and `report_path` comes back
`None` on `AnswerResult`. A report is additive: its failure must never
affect `answer`, `citations`, or `visualization`.

## 7. Testing

New `tests/test_report_builder.py`:
- All three pieces present: the written file contains the question,
  the answer text, each citation's fields, and the visualization's
  fragment content (e.g., asserting a distinctive substring from a
  fake fragment appears verbatim).
- `visualization=None`: report writes cleanly, no "Visualization"
  section present.
- HTML-escaping: an answer/citation field containing `<`/`&` is
  escaped in the output, not interpreted as markup.
- Write failure (e.g., an unwritable path): `build_report()` returns
  `None`, does not raise.

Existing tests updated for the `full_html=False` switch:
- `tests/test_llm_fallback.py` / template tests: assertions checking
  for `<html`/`<body` tags move from the fragment-producing internals
  to the wrapped-output-path assertions; a new assertion confirms the
  *cached* file (fragment) lacks a top-level `<html>` tag while the
  final `output_path` file (wrapped) has one.
- `viz_agent.py` template-path tests: assert `VizResult.fragment_html`
  is populated and is a strict substring of the wrapped `html_path`
  file's content.

`rag_agent.py` tests gain cases for `report=True` (with and without
`visualize`), asserting `AnswerResult.report_path` is set and the file
exists, and a `report=False` (default) case confirming zero behavior
change from today.

No new end-to-end/real-Ollama test -- consistent with this project's
established convention, real validation happens as a manual run
recorded honestly in a status-doc update.
