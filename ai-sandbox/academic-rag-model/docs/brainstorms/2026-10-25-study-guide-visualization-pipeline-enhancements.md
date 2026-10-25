# Study Guide Visualization & Formatting Retrospective: Vector Graphics, KaTeX Geometry, and Table Hygiene

**Date:** 2026-10-25  
**Scope:** Engineering review of visual and mathematical formatting across the Microeconomics study guides (`micro_stochastic_choice_demand_and_duality_study_guide.md` and `micro_expected_utility_and_risk_study_guide.md`), evaluating why initial generation patterns (ASCII box art, unescaped table pipes, raw HTML, and Mermaid graphs) broke in Obsidian and PDF exports, and establishing concrete design patterns for future study guide and visualization pipeline automation.

---

## 1. Executive Summary & Root Problem Analysis

In recent study guide synthesis passes, pipelines and LLM generation prompts relied heavily on four legacy visualization conventions:
1. **ASCII Art & Monospaced Text Boxes:** Intended as quick visual summaries of curves, trees, and decision matrices.
2. **Raw Pipe Characters in LaTeX Equations within Markdown Tables:** Writing standard mathematical set notation like `$|X| \ge 4$` or Möbius powers `$(-1)^{|B \setminus A|}$` inside table cells.
3. **Block-Level HTML Containers for Complex Layouts:** Wrapping card layouts in `<div>` tags with inline styles.
4. **Mermaid Subgraph Diagrams:** Using Mermaid `flowchart TD` to display dual mathematical problems (UMP vs. EMP).

When rendered in Obsidian and exported to vector PDF study materials, every one of these approaches suffered critical rendering failures:
* **ASCII Art:** Rendered as oversized, unstyled code blocks with fixed character widths, raw ASCII characters (`+`, `-`, `|`, `/`), and no typography. They broke on mobile, wrapped awkwardly across PDF page boundaries, and failed to leverage KaTeX math rendering.
* **Table Parsing Explosions:** The CommonMark / GitHub Flavored Markdown (GFM) table parser treats literal pipe characters (`|`) as column separators—even inside LaTeX math blocks (`$...$`). A single `$|X| \ge 4$` turned a 3-column reference table into an illegible 7-column broken grid.
* **MathJax Suppression in Raw HTML:** Obsidian's Markdown engine strictly complies with CommonMark: block-level HTML tags (`<div>...</div>`) suppress the Markdown and MathJax parser. LaTeX math formulas inside HTML remained raw, uncompiled LaTeX strings.
* **Mermaid PDF Export & Layout Fragility:** Mermaid's Dagre layout engine calculates subgraph coordinates independently, staggering side-by-side blocks unevenly. Furthermore, cross-subgraph edge labels generated floating gray bounding boxes that overlapped node headers, and Chromium's PDF print engine frequently clipped SVG bounding boxes or dropped fonts.

To resolve these issues, we developed a series of **publication-quality, 100% native Obsidian and PDF-compatible design patterns** relying on three robust technologies:
1. **Math-Enhanced Markdown Tables with Escaped Delimiters**
2. **Pure KaTeX Visual Diagrams (`$$ \boxed{\begin{array}{cc}} $$`)**
3. **Adaptive Inline Vector SVGs with Spatial Offsets & Dark/Light Halos**

---

## 2. Inventory of Problems & Implemented Solutions

The table below catalogs the visual elements encountered, the failure mode observed in Obsidian/PDF, and the permanent architectural solution implemented.

| Component / Concept | Legacy / Failed Pattern | Failure Mode in Obsidian / PDF | Implemented Vector / KaTeX Solution |
| :--- | :--- | :--- | :--- |
| **Five Classic Demand Systems** | ASCII box table with `+----+` border lines inside a code block. | Fixed monospace font; unrendered exponents (`x1^a * x2^b`) and Greek letters (`sigma`, `rho`). | **Math-Enhanced GFM Table:** Native 3-column table with inline KaTeX Greek letters, superscripts, and aligned parameters. |
| **UMP / EMP Duality Structure** | Mermaid flowchart with cross-subgraph edge and raw text labels. | Asymmetric box sizes; staggered vertical alignment; gray `DUALITY` badge overlapping EMP title; raw sans-serif font. | **Pure KaTeX Boxed Array:** Nested `\boxed{\begin{array}{c}}` inside an outer 2-column array `\begin{array}{cc}`. Guarantees 50/50 side-by-side symmetry and native vector math fonts in PDF export. |
| **Slutsky Decomposition** | 3 ASCII boxes separated by `=` and `-` signs. | Monospace characters; `dx_i / dp_j` unrendered; awkward horizontal wrapping. | **KaTeX `\underbrace` Formula + Structured Markdown Table:** Display math formula labeling each term with underbraces, accompanied by an analytical table detailing observable total, pure substitution, and wealth shift. |
| **Trapdoors & Pitfalls Matrix** | GFM table with unescaped pipes in math: `$|X| \ge 4$` and `$(-1)^{|B \setminus A|}$`. | **Table Explosion:** Parser interpreted internal pipes as column dividers, creating 4 phantom columns and splitting single cells across the table. | **Pipe-Free LaTeX Math:** Substituted literal pipes with LaTeX delimiters: `$\lvert X \rvert \ge 4$` and `$(-1)^{\lvert B \setminus A \rvert}$`. Preserved exact 3-column geometry across all 12 rows. |
| **Choice Under Risk vs. Uncertainty** | ASCII text tree with horizontal dashed branches and bullet lists. | Rigid spacing; unscaled fonts; failed to format mathematical primitives ($p \in \Delta(X)$ vs $f: S \to X$). | **KaTeX Tree Diagram:** Centered top box (`\boxed{Non-Deterministic Choice}`) with branching arrows (`\swarrow`, `\searrow`) leading to side-by-side boxed bullet lists (`\bullet`). |
| **Utility Functions & Risk Aversion** | ASCII table of CARA and CRRA families. | Plain text; awkward fractions (`rho / x`); failed to highlight economic properties. | **4-Column Markdown Reference Table:** KaTeX-formatted functional forms (exponential, power, log), distinct ARA and RRA columns, and bulleted behavioral implications. |
| **Jensen's Inequality & Risk Premium** | ASCII plot of utility curve, chord, certainty equivalent, and risk premium. | Imprecise ASCII slopes (`.---'`); unaligned projections; risk premium bracket broken across lines; no color coding. | **Inline Vector SVG + KaTeX Companion Box:** Continuous Bézier curve $u(x)$, dashed lottery chord, purple Jensen gap bracket ($u(\mathbb{E}[x]) > \mathbb{E}[u]$), emerald certainty equivalent $CE(p)$, and double-headed risk premium arrow ($\pi(p) = \mathbb{E}[x] - CE(p)$). |
| **FOSD Cumulative Step Functions** | ASCII staircase showing two step distributions $F_p(x)$ and $F_q(x)$. | Jagged step rendering; impossible to visualize the integral difference $\int [F_q - F_p] dx$; ambiguous jump points. | **Inline Vector SVG with Shaded Integral:** Dual step functions with solid jump dots, dashed vertical transitions, labeled prizes ($x_1, \dots, x_4$), and a translucent shaded polygon representing the dominance gap $\mathbb{E}_p[x] - \mathbb{E}_q[x] > 0$. |
| **The Machina Triangle** | ASCII right triangle with single sloped hypotenuse and indifference line. | No simplex shading; single slope; could not demonstrate parallel indifference curves or preference gradients. | **Inline Vector SVG:** Right-angle probability simplex, colored degenerate vertex markers ($(0,0), (1,0), (0,1)$), multiple parallel indifference curves ($m < -1$), utility gradient vector arrow, and callout card. |
| **Allais Paradox Contradiction** | ASCII triangle with two comparison chords and conflicting slopes. | Visual clutter; overlapping labels; impossible to distinguish why Choice 1 forces $m > -1.25$ and Choice 2 forces $m < -1.25$. | **Refined Inline Vector SVG with Spatial Offsets:** Parallel amber comparison chords ($m = -1.25$), contrasting flatter purple IC ($m > -1.25$) and steeper green IC ($m < -1.25$), floating pill badges with leader lines, and dark text halos (`paint-order: stroke fill;`). |
| **Prospect Theory Value Function** | ASCII S-curve with text annotations for gains and losses. | Crude curvature; could not illustrate loss aversion magnitude ($\lambda \approx 2.25$) or reference-point kink. | **Parametric Vector SVG:** True Tversky-Kahneman S-curve ($v(x) = x^{0.75}$ in gains, $-\lambda(-x)^{0.75}$ in losses), reference point indicator, and explicit symmetric $+z$ vs $-z$ projection lines proving $|v(-z)| \approx 2.25 \cdot v(+z)$. |
| **Four-Fold Pattern of Risk** | ASCII $2 \times 2$ table with dashed cell borders. | Monospace font; cluttered bullet text; unformatted inequalities ($w(p) < p$). | **Rich Markdown Table & KaTeX Matrix:** Dual representation providing both a readable Markdown table with psychological drivers and real-world examples, and a compact KaTeX $2 \times 2$ decision matrix. |

---

### 2.1 Obsidian PDF Export & DOM Sanitizer Failure Modes Matrix

During live testing in Obsidian and headless Chromium print-to-PDF export, four successive technical failure modes were uncovered and resolved. These are documented below to ensure automated generator pipelines avoid repeating them:

| Failure Mode / Defect | Trigger Condition | Engine Mechanism | Observed Result in PDF / UI | Validated Architectural Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **Print Backend Assertion Crash** | Using `<marker orient="auto-start-reverse">` or complex `<defs>` for arrowheads. | Chromium's Skia PDF backend (`SkPDFDevice`) fails to serialize reverse transformation matrices. | Export aborts abruptly; diagrams render blank; subsequent document sections are dropped. | **Native Polygons:** Replace all markers with explicit `<polygon points="..." fill="currentColor" />` tags directly in the SVG body. |
| **Premature Block Termination** | Blank / empty lines placed inside inline `<svg>` blocks. | CommonMark classifies `<svg>` as a **Type 7 HTML block**, which strictly terminates on the first empty line. | Parser splits SVG; downstream SVG tags turn into broken `<p>` tags; MathJax halts. | **Zero Blank Lines + `<div>` Wrapper:** Strip all empty lines inside `<svg>` and wrap in a Type 6 `<div style="page-break-inside: avoid; break-inside: avoid;">`. |
| **Missing Axes & Solid Black Boxes** | Defining CSS classes inside an SVG `<style>` block (e.g. `@media print`). | Obsidian's DOM sanitizer (DOMPurify) **strips all `<style>` elements** inside inline SVGs. | Stripped classes fall back to W3C defaults: `stroke: none` (axes vanish!), `fill: #000000` (cards turn into solid black boxes!). | **100% Inline Attributes + `currentColor`:** Declare all colors inline (`stroke="currentColor"`, `fill="rgba(..., 0.08)"`). |
| **Right-Margin Formula Clipping** | Single-row LaTeX display arrays exceeding 120 characters or 4 columns. | MathJax arrays do not wrap automatically; width exceeded printable paper width (~620px on Letter/A4). | Right column formula text truncated (e.g. `\textbf{Machina Resolution...}` cut off at paper edge). | **Strict 2-Column Math Budget:** Use `\begin{array}{ll}` with <65 chars per column and concise mathematical notation. |

---

## 3. Core Architectural Rules for Pipeline Automation

To ensure that automated pipelines (such as `academic-rag-model` study guide generators, flashcard exporters, and visual note summarizers) produce production-ready materials that render cleanly in Obsidian and export crisply to PDF, future agent workflows and generation code must enforce the following five principles:

### Rule 1: Eliminate ASCII Box Art from Final Deliverables
LLMs default to generating ASCII diagrams because they are easy to produce in standard text chat. However, in personal knowledge management (PKM) vaults and academic study guides, ASCII boxes are a severe anti-pattern:
* They force horizontal scrolling on mobile devices and narrow windows.
* They break across page splits during PDF export.
* They strip all semantic mathematical formatting from variables, superscripts, and Greek symbols.

**Pipeline Mandate:** Replace ASCII boxes with either (a) a structured GFM Markdown table, (b) a pure KaTeX array diagram, or (c) an inline vector SVG.

### Rule 2: Enforce Strict Table Pipe Hygiene
The GFM table specification parses raw vertical bars (`|`) as cell separators before passing the cell contents to the math compiler. Writing `$|X| \ge 4$` or `$\det(A) = |A|$` inside a table cell guarantees a corrupted table layout.

**Pipeline Mandate:** Implement a pre-commit / post-generation regex filter that sanitizes math inside Markdown table rows:
* Replace `$|` and `|$` with `$\lvert` and `\rvert$`.
* Replace internal absolute value bars with `\vert` or `\mid`.
* Alternatively, escape literal pipes as `\|` when table rows are detected.

### Rule 3: Avoid Raw HTML Block Tags for Math Content
In CommonMark and Obsidian, block-level HTML tags (`<div>`, `<section>`) create a raw HTML context that ignores Markdown formatting and disables the MathJax/KaTeX compiler. While HTML flexbox layouts provide clean responsive cards in standard web browsers, they break math rendering in Obsidian unless specialized plugins are installed.

**Pipeline Mandate:** When multi-column mathematical structures are required, use:
* **Markdown Tables:** For structured comparative data.
* **Pure KaTeX Boxed Arrays:** For connected mathematical problems (such as primal-dual formulations):
  ```latex
  $$
  \begin{array}{c@{\qquad\qquad}c}
  \boxed{\begin{array}{c} \text{\bf Left Problem} \\ \dots \end{array}}
  &
  \boxed{\begin{array}{c} \text{\bf Right Problem} \\ \dots \end{array}}
  \end{array}
  $$
  ```

### Rule 4: Use Inline SVG as the Gold Standard for Geometric Curves
For economic models that rely on geometric intuition (utility curvature, indifference maps, simplex triangles, budget sets, and probability distributions), Mermaid is too rigid and HTML is inadequate. 

Inline vector SVG `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 W H" ...>` is the optimal standard because:
1. **Zero Plugin Requirements:** Natively rendered by Obsidian Core across all platforms (Desktop, iOS, Android).
2. **First-Class Vector Graphics in PDF:** Chromium prints SVG paths and text directly as vector primitives in PDF exports, completely avoiding the blurriness of rasterized PNGs or the layout shifts of Mermaid foreignObjects.
3. **Responsive Scaling:** Using `viewBox="0 0 740 460"` and `style="width: 100%; max-width: 740px; height: auto;"` allows diagrams to scale dynamically to fit any note pane or PDF page margin.
4. **Theme Adaptability:** Setting axes and primary labels to `stroke="currentColor"` and `fill="currentColor"` ensures that diagrams render seamlessly on Obsidian Dark Mode, Light Mode, and white PDF print pages.

### Rule 5: Prevent Diagonal Label Pile-Ups via Spatial Offsetting & Halos
When lines converge on a common origin or vertex (such as indifference curves and chords emanating from $(0, 1)$ in the Machina triangle):
* **Never place multiple rotated text labels along the converging segments.** In the upper region where lines are separated by only 5–15 pixels, rotated text will overlap into an unreadable tangle.
* **Offset labels into open regions:** Place labels near the wide divergence points (e.g. at the bottom axis), in the interior of the simplex, or outside the triangle with dashed leader lines.
* **Encase text in pill badges or SVG halos:** 
  * Use a `<rect>` pill behind text with a semi-opaque background (`fill="rgba(24, 24, 27, 0.90)"`).
  * Or use an SVG text halo style:
    ```css
    .halo {
      paint-order: stroke fill;
      stroke: #18181b;
      stroke-width: 4.5px;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    ```
  This guarantees that lines passing near or behind labels never slice through the text glyphs.

### Rule 6: Immunize SVGs for PDF Export (No `<marker>` Tags; Strict Pagination Rules)
When Obsidian exports a document to PDF, it uses Chromium's headless print rasterizer and the Skia 2D PDF serialization backend (`SkPDFDevice`). This print path behaves very differently from the on-screen GPU canvas:
* **The `<marker orient="auto-start-reverse">` Bug:** While SVG 2 `auto-start-reverse` markers render fine on screen, Skia's PDF backend fails to resolve reverse transformation matrices during print vector serialization. When a marker fails, Skia aborts drawing the child elements of the `<svg>`, leaving an empty bounding box.
* **Fatal Print Stream Aborts:** If Skia encounters an unhandled vector assertion, Chromium's print compositor aborts the PDF stream immediately, truncating the export and dropping all subsequent sections.
* **Pagination Collision & Fragmentation Deadlock:** Standard SVG viewports cannot be split across page fragments. A 400px+ SVG immediately adjacent to a 180px KaTeX display equation creates a ~600px monolithic block. Without explicit CSS pagination rules, Chromium's print layout engine deadlocks or times out at page boundaries.

**Pipeline Mandate for All Generated SVGs:**
1. **Never use `<marker>` or `<defs>` for arrowheads:** Draw arrows directly as native `<polygon>` or `<path>` elements (e.g. `<polygon points="585,280 575,275 575,285" fill="currentColor" />`). Native polygons translate cleanly into standard PDF vector operators (`m ... l ... h f`) across all PDF engines.
2. **Always include CSS print pagination guards in the SVG style attribute:**
   ```xml
   style="... page-break-inside: avoid; break-inside: avoid;"
   ```
3. **Keep vertical viewports compact:** Keep diagram heights under 380px (ideally 340–360px) so the SVG and any companion KaTeX explanation card can co-exist on a single printed page.
4. **Sanitize non-ASCII Unicode glyphs in `<text>` tags:** Avoid multi-byte mathematical minus (`\u2212`) or unstyled Greek letters inside raw SVG `<text>` elements; use standard ASCII `-` or clean HTML entities to prevent headless PDF font subsetting crashes.

### Rule 7: Zero Blank Lines Inside `<svg>` & Wrap in Block-Level `<div>`
Under the CommonMark / GitHub Flavored Markdown specification, `<svg>` is categorized as a **Type 7 HTML block**, NOT a standard Type 6 block (such as `<div>` or `<table>`).
* **The Fatal Blank-Line Termination Trap:** According to the CommonMark spec, a Type 7 HTML block *terminates immediately upon encountering a blank line*.
* **Consequence of Internal Blank Lines:** When decorative blank lines exist inside an inline `<svg>` (e.g. separating axes from labels), the Markdown parser prematurely terminates the `<svg>` at the first empty line and wraps the remainder of the chart elements (`<text>`, `<polygon>`, `<line>`) into invalid HTML `<p>` paragraph tags outside the SVG canvas. The trailing `</svg>` becomes an unmatched, orphaned closing tag.
* **Impact on PDF Export:** While interactive Live Preview may forgivingly display partial or cached DOM fragments, Obsidian's clean print renderer attempts to construct a strict HTML print DOM. The broken, malformed SVG DOM causes Chromium's print pipeline to fail, rendering only the elements preceding the first blank line and then crashing before rendering adjacent MathJax display blocks.

**Pipeline Mandate for Markdown Embedding:**
1. **Never allow blank lines inside `<svg>` blocks:** Strip all empty lines between `<svg>` and `</svg>`.
2. **Always wrap `<svg>` in a block-level `<div>`:**
   ```html
   <div style="page-break-inside: avoid; break-inside: avoid;">
   <svg ...>
   ...
   </svg>
   </div>
   ```
   `<div>` is a CommonMark Type 6 HTML block, guaranteeing that the parser treats the entire container and its enclosed SVG as an atomic, unbroken HTML unit.

### Rule 8: Universal Dual-Theme Contrast Engineering & LaTeX Array Width Budgets
When authoring study materials for dual-theme PKM environments (Obsidian dark theme on screen vs. white paper print-to-PDF):
* **The Fatal Obsidian `<style>` Sanitization Trap:** In Obsidian, the DOM sanitizer (DOMPurify) strips `<style>` tags embedded inside inline SVGs. Under the W3C SVG specification, if an element relies on stripped CSS classes, its `stroke` defaults to `none` (causing axes and ticks to vanish completely!) and its `fill` defaults to `#000000` (causing callout cards, badges, and text to turn into solid black boxes with black-on-black invisible text!).
* **The Low-Contrast Trap on White Paper:** Hardcoding light slate fills (`#cbd5e1`, `#f1f5f9`) or dark text halos (`stroke: #18181b`) looks crisp in dark mode, but washes out or produces jarring dark blobs on a white PDF page.
* **The LaTeX Array Margin Overflow:** Packing long descriptive prose or wide tabular columns side-by-side inside `\boxed{\begin{array}{ll}}` (e.g. lines over 120 characters) causes the box to exceed ~650px. On standard Letter paper with 20mm margins (printable width ~600–620px), the right edge is clipped off by the paper boundary.

**Pipeline Mandate for Themes and Math Arrays:**
1. **Never Rely on `<style>` Tags or CSS Classes in Inline SVGs:**
   Every styling property must be declared as an explicit inline XML attribute on the element itself:
   * **`currentColor` as the Theme Bridge:** Set `stroke="currentColor"` and `fill="currentColor"` on all coordinate axes, arrowheads, ticks, axis labels, and primary body text. In Obsidian dark mode, `currentColor` automatically inherits light text (`#dcddde`); during PDF export, it automatically inherits pure black (`#000000`) on white paper.
   * **Theme-Neutral Translucent Fills for Cards and Badges:** For callout cards, decision boxes, and badges, never use solid dark or light fills. Instead, use soft translucent tints (`rgba(r, g, b, 0.06)` to `0.12`) paired with crisp colored borders (`#8b5cf6`, `#ef4444`, `#10b981`, `#f59e0b`). Translucent tints render beautifully on dark slate backgrounds and equally clean on bright white print paper, with zero black-box fallback risk.
   * **Clean Text Over Heavy Rectangles:** For angled annotations (such as the Machina hypotenuse), use rotated SVG text (`fill="#64748b"`) without wrapping it in an opaque rectangular container.
2. **Strict Character & Width Budget for LaTeX Companion Arrays:**
   * Limit arrays to 2 columns: `\boxed{\begin{array}{ll}...}`.
   * Enforce a strict length budget: maximum **60–65 characters per column** (~110–120 total characters across both columns per row).
   * Replace long sentences with compact mathematical notations (e.g., replace `\textbf{Machina Resolution: Fanning Out:} curves steepen toward North-West` with `\textbf{Resolution:} \; \text{Fanning Out (slope steepens NW)}`).
   * This guarantees a total box width under ~480–520px, leaving >100px of comfortable margin safety on both Letter and A4 PDF exports.

---

### Rule 9: Canonical Dual-Theme SVG & KaTeX Companion Box Blueprints

To eliminate trial-and-error in future generations, pipelines must adhere to the following verified structural templates:

#### Template A: Dual-Theme Inline Vector SVG
```html
<div style="page-break-inside: avoid; break-inside: avoid;">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 420" style="width: 100%; max-width: 740px; height: auto; display: block; margin: 16px auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <!-- Coordinate Axes: currentColor adapts dynamically (white on dark, black on light/print) -->
  <line x1="80" y1="340" x2="620" y2="340" stroke="currentColor" stroke-width="1.8" />
  <polygon points="628,340 618,335 618,345" fill="currentColor" />
  <text x="635" y="344" fill="currentColor" font-size="13" font-weight="600" font-style="italic">X Axis Label</text>
  <line x1="80" y1="340" x2="80" y2="40" stroke="currentColor" stroke-width="1.8" />
  <polygon points="80,32 75,42 85,42" fill="currentColor" />
  <text x="80" y="22" fill="currentColor" font-size="13" font-weight="600" font-style="italic" text-anchor="middle">Y Axis Label</text>
  <!-- Curves & Highlights -->
  <path d="M 80,340 C 150,200 300,100 580,70" fill="none" stroke="#3b82f6" stroke-width="2.8" />
  <!-- Decision / Summary Card: Translucent fill with crisp colored border (zero black-box risk) -->
  <rect x="480" y="70" width="230" height="200" rx="8" fill="rgba(59, 130, 246, 0.06)" stroke="#3b82f6" stroke-width="1.3" />
  <text x="595" y="95" fill="#3b82f6" font-size="13" font-weight="bold" text-anchor="middle">Card Header</text>
  <line x1="495" y1="105" x2="695" y2="105" stroke="#3b82f6" stroke-width="0.8" opacity="0.4" />
  <text x="495" y="128" fill="currentColor" font-size="12" font-weight="600">• Point One</text>
  <text x="495" y="150" fill="#64748b" font-size="11">Subtext / details</text>
  <!-- Caption Footer -->
  <text x="360" y="395" fill="currentColor" font-size="12" text-anchor="middle">
    <tspan font-weight="bold" fill="#3b82f6">Figure Title:</tspan>
    <tspan fill="#64748b"> Descriptive take-away grounded in theoretical principles.</tspan>
  </text>
</svg>
</div>
```

#### Template B: 2-Column Margin-Safe KaTeX Summary Box
```latex
$$
\boxed{\begin{array}{ll}
\rule{0pt}{14pt}\textbf{Term 1:} \; \text{Compact Math} & \textbf{Term 2:} \; \text{Compact Math} \\[4pt]
\textbf{Property 1:} \; \text{Inequality / Form} & \textbf{Property 2:} \; \text{Inequality / Form} \\[4pt]
\textbf{Implication:} \; \text{Concise theoretical outcome} & \textbf{Order Type:} \; \text{Classification} \\[3pt]
\end{array}}
$$
```

#### Template C: 9-Point Pre-Flight Generation Checklist
Before committing or writing any generated study guide or visualization file to disk, the generator or review agent must verify:
- [x] **1. No ASCII Art:** Monospaced lattice boxes replaced by GFM tables, KaTeX arrays, or vector SVGs.
- [x] **2. No Table Pipe Explosions:** All LaTeX equations in Markdown tables use `\lvert ... \rvert` or `\vert` instead of raw `|`.
- [x] **3. No Markdown in Raw Block HTML:** No LaTeX equations enclosed within `<div>` or `<section>` tags.
- [x] **4. No `<marker>` Elements:** All vector arrowheads rendered as inline `<polygon>` elements.
- [x] **5. No Internal Blank Lines in SVGs:** The SVG markup is contiguous without empty whitespace lines.
- [x] **6. Enclosed in Block `<div>`:** Each SVG is wrapped in `<div style="page-break-inside: avoid; break-inside: avoid;">`.
- [x] **7. Zero `<style>` Tags in SVGs:** Colors and dimensions declared via direct inline XML attributes to prevent DOMPurify stripping.
- [x] **8. Dynamic Contrast Inheritance:** Coordinate systems and primary text use `currentColor`; cards use translucent `rgba(...)` fills.
- [x] **9. Margin-Safe Math Arrays:** All companion display math boxes use 2-column arrays with fewer than 65 characters per column.

---

## 4. Next Steps & Pipeline Integration Roadmap

1. **Linting & Validation Hook:** Add a diagnostic check to the corpus health / validator script (`tools/lint_notes.py` or equivalent) that automatically flags:
   * Code blocks containing ASCII art boxes (`+---+` or `|   |` lattices).
   * Unescaped pipes (`|`) inside LaTeX math blocks in Markdown table lines.
   * Unrendered MathJax markers inside raw HTML tags.
   * `<marker>` or `<style>` tags embedded inside inline SVGs.
   * Blank lines occurring between `<svg>` and `</svg>`.
   * Display math arrays (`\boxed{\begin{array}}`) whose raw row strings exceed 130 characters.
2. **Reusable Vector Template Library:** Package the validated SVG generators developed in this session (`gen_pt_coords.py`, `test_machina.py`, `test_fosd.py`, `test_svg.py`) into a modular Python visualization library (`academic-rag-model/tools/visualizers/econ_svg.py`) that can be invoked programmatically during automated study guide generation.
3. **Prompt Engineering Updates:** Update the system prompts for study guide generation agents (both Gemini and Codex) to explicitly disallow ASCII art and specify the required KaTeX / SVG formatting standards.
