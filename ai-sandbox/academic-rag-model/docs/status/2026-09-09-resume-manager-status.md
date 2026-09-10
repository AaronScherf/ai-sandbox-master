# Resume Manager: Real End-to-End Validation and Revision History

Start here for what happened and where things stand. `resume_manager/`
(spec: `docs/superpowers/specs/2026-09-09-resume-manager-design.md`, plan:
`docs/superpowers/plans/2026-09-09-resume-manager-plan.md`) went through
three real design revisions in a single day, each driven by a concrete bug
found by actually running the bootstrap against the user's real resume —
not by anticipating problems in the abstract. The short version: v1's
freeform-Markdown master format let an LLM guess wrong; Revision 2's
structured schema fixed that but its own first real run took over 90
minutes and needed five separate fixes just to parse the model's YAML
output, then *still* produced two further real content bugs; Revision 3
replaced the LLM extraction step entirely with deterministic parsing,
fixing every one of those bugs at the root and dropping bootstrap runtime
to about 1.5 seconds with zero API calls.

## What shipped

- **v1** (10 tasks): PDF → freeform-Markdown master resume
  (`resume_master.md`) via one local-LLM reformat call, then whole-document
  LLM tailoring, fact-diff validation, and `xhtml2pdf` rendering.
- **Revision 2** (10 tasks, same count, different modules): master resume
  becomes a structured YAML schema (`resume_master.yaml` — `contact`,
  `work_experience`, `education`, `awards`, `publications`, `skills`, each
  with named fields); tailoring restricted to Work Experience selection +
  bullet rewrites, with the LLM never emitting a metadata field at all —
  `tailor.py`'s own code reconstructs the tailored resume from master data,
  so date/org/location fabrication became structurally impossible rather
  than something to detect after the fact.
- **Revision 3** (1 task, `normalize.py` rewritten): bootstrap extraction
  (raw PDF text → `resume_master.yaml`) becomes deterministic, section-
  aware parsing — fuzzy section-header matching (`rapidfuzz`) against known
  synonyms, plus explicit per-section line-shape rules. No LLM call, no
  network, no sampling variance for the bootstrap. Tailoring (still
  inherently a language task) is unaffected and still uses local Ollama.

## Real-run timeline, in order

### 1. v1's only real run: a role's location silently took the place of its dates

**Symptom:** the master resume's Markdown heading for two of three USAID
sub-roles showed the role's *location* where its `(dates)` were supposed
to go — e.g. `### U.S. Agency for International Development — Foreign
Service Officer - Program Officer Rotations (FS 5-12) (Washington, DC,
USA)`, no date range at all.

**Root cause:** the real resume prints one date range against the
*employer* line, covering three sequential sub-roles, not one per role.
v1's format asked the LLM to freely author one Markdown heading per entry
with a single `(<dates>)` slot; when a role had no date of its own to put
there, the model substituted the role's location instead of leaving the
slot honestly empty or flagging the gap. v1's fact-diff verification was
built to catch fabricated/dropped *entries and metrics*, not a malformed
*field within* an otherwise-plausible-looking entry, so it didn't catch
this.

**Fix:** not a tighter regex — a structural one. Revision 2 replaced the
single freeform heading with named fields (`org`, `role`, `location`,
`start_date`, `end_date`), so there's no ambiguous slot left for the model
to misuse. See the design spec's §1 item 4.

### 2. Revision 2's first bootstrap attempt: clean bullets flagged as "defective"

**Symptom:** `python -m resume_manager.convert_resume` failed immediately:
`page(s) [1, 2] ... look defective under local extraction`.

**Root cause:** `page_looks_defective()`'s "unexpected character"
allowlist (`notes/transcribe_notes.py`) was tuned for LaTeX math lecture
notes and had never needed to recognize an ordinary bullet character
(U+2022) or a zero-width space (U+200B) — both completely legitimate in
any bulleted document, neither corrupted. A resume's 16-62 bullets per
page trivially exceeded the "more than a handful of unexpected
characters" threshold.

**Fix:** added `•` and the zero-width space to `_ALLOWED_EXTRA_CHARS` —
additive, same precedent as the earlier Apache FOP/XEP fix for journal
articles, benefiting every pipeline that reuses this shared check, not
just `resume_manager`. Regression tests added to
`tests/test_transcribe_notes.py`.

### 3-7. Revision 2's extraction call: five formatting/normalization fixes to trust the LLM's output at all

Once the resume PDF's raw text extracted cleanly, getting a *reliable,
correctly-parsed* structured extraction out of the local LLM took five
more real, evidence-driven fixes — all found by actually running the
bootstrap repeatedly, not anticipated:

1. **Bare `-` as a missing-value placeholder broke YAML.** The model
   sometimes wrote `location: -` meaning "no value," which `yaml.safe_load`
   rejects (a bare `-` is a sequence-item marker, not a scalar, at that
   position). Fixed in a new shared `resume_manager/llm_yaml.py` (used by
   both `normalize.py` and `tailor.py`): quote the placeholder before
   parsing rather than fail and retry the whole slow CPU-only Ollama call.
2. **An unquoted value that itself contains `": "` broke YAML.** A real
   publication venue, `UC Berkeley: Data for Human Mobility Lab`, is
   genuine content — but YAML treats any unescaped `": "` inside an
   unquoted scalar as introducing a nested mapping key. Fixed in the same
   `llm_yaml.py`, confirmed not to falsely match `https://...` values
   (colon immediately followed by `/`, not whitespace — already
   unambiguous).
3. **Line-wrapped raw text made correctly-joined content look "invented."**
   The source PDF line-wraps mid-sentence (`"...randomized control\ntrial
   to evaluate..."`); the LLM correctly joined it into flowing prose with a
   single space, but a literal substring check against the raw text flagged
   this as fabricated on nearly every bullet and degree line (31 false
   positives on one real run). Fixed by normalizing whitespace (including
   non-breaking spaces) before comparing in `schema.py`'s
   `verify_entry_fields`.
4. **Zero-width spaces embedded *within* words weren't whitespace at all.**
   The Skills section's raw text embeds U+200B between words (`"Natural
   [ZWSP]Language [ZWSP]Processing"`); U+200B is Unicode category Cf
   (format), not Zs (separator), so `\s` regexes don't match it — it
   survived the whitespace-collapse fix above untouched. Fixed by
   stripping it explicitly before normalizing.
5. **An honestly missing value needed a real, acceptable placeholder.**
   Two USAID sub-roles genuinely have no date of their own in the source
   (see bug #1), and the resume has no contact info (email/links) anywhere
   in its extracted text at all. The model writing `"Not specified"` for
   such a field is correct, honest behavior — not something to flag as
   unfindable. `verify_entry_fields` now exempts a small set of known
   placeholders (`"Not specified"`, `"N/A"`, `"Unknown"`, `"TBD"`) from the
   traceability check, the same way `"Present"` already was for `end_date`
   specifically.

Each of these five was found, reproduced, and fixed via TDD in turn — see
the individual commits (`fix(resume_manager): ...`) for full detail per
issue.

### 8. Revision 2's first *clean-verification* bootstrap run: two further real content bugs

Once all five fixes above landed, the bootstrap finally completed with a
clean verification report — but manual inspection of the actual output
(not just trusting the "verified clean" message) found two more real
problems the verification step structurally couldn't catch, because it
only checks whether an extracted *value* traces back to the source, never
whether extraction was *complete* or *correctly categorized*:

- **A Work Experience role was miscategorized as an Education entry, and
  its content was dropped.** "Graduate Student Instructor" at UC Berkeley
  (a real job, with 4 substantial teaching-duty bullets: MATH 10A, PP 297,
  DATA 100, DS 421) was filed under `education` with `degree: "Graduate
  Student Instructor"`, and all 4 bullets vanished entirely — Education
  entries have no `bullets` field in the schema, so they were simply
  nowhere.
- **A real thesis, present in the raw text, was written as `"Not
  specified"`.** Indiana State's thesis title
  ("Novel Omnibus Normality Test and Power Comparison with the
  Shapiro-Wilk") is literally in the raw extraction, immediately after
  that entry's 3 lines — but the model gave up and wrote the honest-missing
  placeholder instead of finding it.

**This is what prompted Revision 3.** Both bugs trace to the same root
cause as bug #1: the LLM had to freely *decide* section membership and
entry boundaries, not just fill in named fields — and a wrong decision
here isn't a malformed field verification can catch, it's a structurally
valid entry in the wrong place (or missing) entirely.

### 9. Revision 3: deterministic parsing, verified against the real resume

Replaced `normalize.py`'s LLM call entirely with explicit parsing rules
(fuzzy section-header matching via `rapidfuzz`, plus one function per
category matching that category's small set of real, observed line-shapes
— full detail in spec §3). Test fixture is a representative excerpt of the
*actual* resume's real raw extraction, not a synthesized approximation,
covering every line-shape and both real bugs from #8 by name.

**Real bootstrap run after Revision 3 (2026-09-09):**
```
real  0m1.485s
```
`resume_master.yaml` verified clean (defense-in-depth check, not load-
bearing anymore — every value is a substring of the raw text by
construction now). Manual inspection confirmed both bug #8 issues are
fixed: "Graduate Student Instructor" is correctly under `work_experience`
with all 4 bullets present; Indiana State's thesis is correctly captured.
Every other field across all 7 work-experience entries, 5 education
entries, 4 awards, 7 publications, and 3 skill categories matches the
source exactly.

### 10. First real tailoring run: dropped metrics and an unsupported claim

**Setup:** `python -m resume_manager.tailor_resume` against a real UN
Development Coordination Office "Economist, NO-D" posting (Jakarta),
selecting from the real `resume_master.yaml`.

**Symptom:** the automated report said `Validation: no discrepancies
flagged` — but manual inspection of the actual rewritten bullets against
their originals found real quality loss the invented-only check couldn't
see:
- The first USAID role's three bullets (with `$1.5M`, `$450M`, `20 program
  evaluations`, `$5Bn`) were compressed into two vaguer bullets, and all
  four figures disappeared.
- The DC-rotation role's award mention and tool names were dropped
  entirely: `"Won agency-wide award for developing new budget data
  processing and visualization tool using Python and Tableau, saving
  hundreds of hours of staff time..."` became `"Created a budget data
  processing and visualization tool to support SDG-related
  negotiations..."`.
- One rewrite added a claim not present in the original bullet at all:
  `"...which improved the coherence and consistency of SDG implementation
  across country offices"` — not a `%`/`$`/`x` token, so the metrics check
  had no way to flag it.

**Root cause:** the tailoring prompt only forbade *inventing* new
metrics/experience; it never required *preserving* the ones already
present, and `validate.py`'s fact-diff only checked the invented
direction, never the dropped one.

**Fix:** `validate.py`'s `validate_tailored()` is now bidirectional —
`metrics_not_traceable()` is called both ways, so a metric present in the
original bullets that doesn't survive into *any* rewritten bullet for that
entry is flagged too. `tailor.py`'s prompt gained an explicit rule to
preserve every number/named tool/named award from the original bullets
(and to never add an unsupported outcome claim), plus an instruction that
merging bullets must never lose these details.

**Re-run after the fix (same real JD, same real master resume):**
`$1.5M` and `$450M` now survive into the rewrite; `"Python and Tableau"`
now survives. The bidirectional check correctly flagged the one remaining
real drop: `$5Bn` (written as `$5B` by the metric extractor), from a
bullet whose content was dropped entirely rather than merged in. The named
award ("Won agency-wide award...") is *still* missing from the rewrite —
a real LLM instruction-following gap the prompt fix didn't fully close,
and one the automated check still can't catch on its own, since it isn't
a numeric metric. Catching a dropped *named entity* (an award title, a
tool name) rather than a dropped *number* would need a fundamentally
different mechanism than metric-token matching — recorded below as an
open item, not solved here, to keep scope proportionate to what's been
validated so far.

### 11. User review of the real tailored PDF: contact info filled in, five follow-on requests

**Contact info hand-fill confirms the intended workflow.** The user
filled in `resume_master.yaml`'s `contact` block by hand directly
(`name`, `location`, `email`, `linkedin_url`, `github_url`,
`website_url`) — exactly the workflow the design intends
(`resume_master.yaml` is a hand-maintained file the bootstrap never
overwrites once it exists). No tooling change needed; recorded here as
the open contact-info item now being real, resolved data for this user
rather than a lingering gap.

**Reviewing the actual rendered PDF (not just the YAML) surfaced a real,
new finding: repeated bullet-opening phrasing across different roles.**
From the UN Economist tailoring run (§10): the first bullet of both the
first and second USAID entries opens with nearly identical language --
`"Researches, analyzes, consolidates, and presents information and data
on emerging best practices in SDG acceleration, particularly related
to..."` and `"...including..."`. Worth noting precisely: `tailor.py`
already sends every Work Experience entry to the model in a single
prompt/single call (not one call per entry), so this isn't a case of the
model lacking context about what it already wrote elsewhere in the same
response -- it's echoing the job description's own repeated phrasing
(the JD itself opens several duty bullets with "Researches, analyzes,
consolidates and presents...") too literally across multiple resume
bullets rather than varying sentence structure. Not yet fixed; the
distinction matters for how to fix it (a stronger anti-repetition
instruction the model can act on with its existing full-response context,
rather than restructuring the prompt to add context it already has).

**Five follow-on requests from this review round, none implemented yet:**

1. **Render `"Not specified"` as blank on the PDF, not the literal
   string.** Currently a genuinely-missing field (e.g. `gpa: Not
   specified`) prints the literal placeholder text in the rendered
   resume. `resume_master.yaml`/`tailored_resume.yaml` should keep storing
   the explicit placeholder (needed for the honest-missing-value
   traceability exemption, §3-7), but `render.py`'s `build_markdown()`
   should skip a field entirely when its value is the placeholder, not
   print it.
2. **Page-limit-aware output formatting.** Already recorded as deferred in
   the design spec (§10) and above -- re-confirmed here as a real,
   standing want after seeing actual rendered output length.
3. **Cross-bullet awareness to reduce repetitive language** -- see the
   finding above. A real, reproducible example now exists to test a fix
   against (unlike a purely speculative "bullets might repeat" concern).
4. **A cover-letter generator, paired with the resume pipeline.** Already
   a non-goal for this version (design spec §1) -- re-confirmed as wanted
   as a follow-on subproject, not solved here.
5. **A back-and-forth clarifying-question model before tailoring**, similar
   to the brainstorming skill's own question-and-answer flow: let the user
   answer a few questions grounded in the job description (e.g. which
   experience to foreground, what to downplay) before the LLM selects
   entries and rewrites bullets, rather than the LLM inferring relevance
   from the JD text alone. This is a new, not-yet-designed feature --
   would need its own brainstorming pass to work out where in
   `tailor_resume.py`'s flow the questions surface and how answers get
   threaded into `tailor.py`'s prompt.

## Known, not yet fixed / open items

- **Dropped named entities (awards, tool names) aren't caught
  automatically.** `validate.py`'s bidirectional check only catches
  dropped/invented *numeric* metrics (`%`/`$`/`x` tokens). A dropped award
  title or tool name (§10) has no equivalent automated check yet — would
  need named-entity-style matching, not metric-token matching. Manual
  review of rewritten bullets is still recommended before submitting any
  real application.
- **Repeated bullet-opening phrasing across different roles** (§11) --
  reproducible real example now on record; not yet fixed.
- **`"Not specified"` renders literally on the PDF** (§11) -- a `render.py`
  fix, not yet made.
- **The deterministic parser (Revision 3) is tuned to one real resume.**
  `match_section_header()`'s synonym list and each section's line-shape
  rules are grounded in this one document. Explicitly deferred (spec §10)
  rather than guessed: broaden the synonym lists and add new line-shapes
  once a second real resume with a different layout is available to test
  against.
- **Metric-extraction regex coverage is heuristic** (`fact_diff.py`) — only
  recognizes `%`/`$`/`x`-suffixed tokens; a bullet like "reduced latency by
  half" or "team of 12" isn't caught either way. Not yet validated against
  a real tailored bullet with this kind of phrasing.
- **Page-limit-aware selection, non-Work-Experience tailoring, cover-letter
  generation, and a clarifying-question flow before tailoring** all remain
  explicitly deferred (design spec §10 for the first two; §11 above for
  the latter two, re-confirmed as real wants after real use) — none solved
  speculatively here.

## What's next

1. `render.py`: skip a field entirely when its value is the
   `"Not specified"`/placeholder sentinel, rather than printing it.
2. Reduce repeated bullet-opening phrasing across roles (§11) — candidate
   approaches: a stronger anti-repetition instruction in `tailor.py`'s
   existing single-call prompt, or a post-generation pass that checks for
   and rewrites duplicate openings.
3. Brainstorm the clarifying-question flow (§11 item 5) as its own design
   pass before implementing — where in `tailor_resume.py` questions
   surface, how answers thread into `tailor.py`'s prompt.
4. Page-limit-aware selection and a paired cover-letter generator, per the
   design spec's §10 and §11's re-confirmation.
5. Consider a named-entity-style check (award titles, tool names) if
   dropped-named-entity issues keep recurring across more real tailoring
   runs — not solved speculatively now, per §10.
6. Once a second real resume (different layout) is available, extend
   `match_section_header()`'s synonyms and `normalize.py`'s per-section
   line-shape rules to cover it, rather than speculatively generalizing
   now.
