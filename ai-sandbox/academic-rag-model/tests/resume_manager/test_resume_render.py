import os
import tempfile
import unittest

from resume_manager.render import build_typst, render_resume_pdf

_RESUME = {
    "contact": {
        "name": "Aaron Scherf", "location": "USA", "email": "a@x.com",
        "linkedin_url": "https://linkedin.com/in/a", "github_url": "https://github.com/a",
        "website_url": "https://a.dev",
    },
    "work_experience": [{
        "org": "Acme", "role": "Engineer", "location": "NYC",
        "start_date": "2020", "end_date": "Present", "bullets": ["Did a thing"],
    }],
    "education": [{
        "institution": "State U", "degree": "BS", "gpa": "3.9", "location": "TX",
        "start_date": "2016", "end_date": "2020", "thesis": None,
    }],
    "awards": [{"name": "Award", "description": "For doing things", "date": "2019"}],
    "publications": [{"title": "A Paper", "date": "2021", "venue": "A Venue", "link": None}],
    "skills": [{"category": "Programming", "items": ["Python", "R"]}],
}


class TestBuildTypst(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(build_typst(_RESUME), build_typst(_RESUME))

    def test_includes_every_category(self):
        typst_text = build_typst(_RESUME)
        for expected in ["Aaron Scherf", "Acme", "State U", "Award", "A Paper", "Python"]:
            self.assertIn(expected, typst_text)

    def test_missing_optional_category_is_omitted_cleanly(self):
        resume = {**_RESUME, "publications": []}
        typst_text = build_typst(resume)
        self.assertNotIn("Research Presentations", typst_text)

    def test_contact_line_is_centered(self):
        typst_text = build_typst(_RESUME)
        self.assertIn("#align(center)[a\\@x.com", typst_text)

    def test_contact_line_omits_location(self):
        # Confirmed real preference (2026-09-26): dropped so the contact
        # line fits on one line under the name.
        typst_text = build_typst(_RESUME)
        self.assertNotIn("USA", typst_text)

    def test_not_specified_contact_fields_render_as_blank(self):
        # Real, confirmed request (2026-09-10): a genuinely-missing field
        # should render as nothing at all, not the literal placeholder
        # text -- the placeholder is only meant for the YAML data layer.
        resume = {
            **_RESUME,
            "contact": {
                "name": "Aaron Scherf", "location": "Not specified", "email": "Not specified",
                "linkedin_url": "Not specified", "github_url": "Not specified", "website_url": "Not specified",
            },
        }
        typst_text = build_typst(resume)
        self.assertNotIn("Not specified", typst_text)
        self.assertIn("Aaron Scherf", typst_text)

    def test_work_experience_heading_uses_job_heading_with_right_aligned_dates(self):
        # Confirmed real feedback (2026-09-26): dates as trailing "(...)"
        # text made long titles wrap to two lines -- moving them into a
        # right-aligned column frees width for the title itself.
        typst_text = build_typst(_RESUME)
        self.assertIn("#job-heading([Acme], [Engineer], [2020 – Present])", typst_text)

    def test_work_experience_with_both_dates_not_specified_omits_the_date_argument(self):
        resume = {**_RESUME, "work_experience": [{
            "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "Not specified", "end_date": "Not specified", "bullets": ["Did a thing"],
        }]}
        typst_text = build_typst(resume)
        self.assertNotIn("Not specified", typst_text)
        self.assertIn("#job-heading([Acme], [Engineer], none)", typst_text)

    def test_consecutive_bullets_in_one_entry_form_a_single_list_block(self):
        # Real bug (2026-09-26): joining every bullet with a blank line
        # made Typst treat each one as its own separate one-item list,
        # producing visibly uneven spacing vs. a single grouped list.
        resume = {**_RESUME, "work_experience": [{
            "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present",
            "bullets": ["First bullet", "Second bullet", "Third bullet"],
        }]}
        typst_text = build_typst(resume)
        self.assertIn("- First bullet\n- Second bullet\n- Third bullet", typst_text)

    def test_multiple_awards_form_a_single_list_block(self):
        resume = {**_RESUME, "awards": [
            {"name": "Award One", "description": "", "date": "2019"},
            {"name": "Award Two", "description": "", "date": "2020"},
        ]}
        typst_text = build_typst(resume)
        self.assertIn("- Award One (2019)\n- Award Two (2020)", typst_text)

    def test_education_not_specified_gpa_and_thesis_render_as_blank(self):
        resume = {**_RESUME, "education": [{
            "institution": "State U", "degree": "BS", "gpa": "Not specified", "location": "TX",
            "start_date": "2016", "end_date": "2020", "thesis": "Not specified",
        }]}
        typst_text = build_typst(resume)
        self.assertNotIn("Not specified", typst_text)
        self.assertNotIn("GPA:", typst_text)
        self.assertNotIn("Thesis:", typst_text)
        self.assertIn("BS", typst_text)

    def test_publication_not_specified_link_renders_as_blank(self):
        resume = {**_RESUME, "publications": [
            {"title": "A Paper", "date": "2021", "venue": "A Venue", "link": "Not specified"},
        ]}
        typst_text = build_typst(resume)
        self.assertNotIn("Not specified", typst_text)
        self.assertNotIn("#link(", typst_text)

    def test_publication_link_uses_typst_link_syntax(self):
        resume = {**_RESUME, "publications": [
            {"title": "A Paper", "date": "2021", "venue": "A Venue", "link": "https://example.com/x"},
        ]}
        typst_text = build_typst(resume)
        self.assertIn('#link("https://example.com/x")[link]', typst_text)

    def test_bullet_with_dollar_and_hash_is_escaped(self):
        # Real content from the actual resume ("$1.5M", "$450M") would
        # otherwise open Typst math mode or code mode.
        resume = {**_RESUME, "work_experience": [{
            "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present",
            "bullets": ["Raised $1.5M and tagged #priority items"],
        }]}
        typst_text = build_typst(resume)
        self.assertIn(r"Raised \$1.5M and tagged \#priority items", typst_text)

    def test_email_at_sign_is_escaped(self):
        typst_text = build_typst(_RESUME)
        self.assertIn(r"a\@x.com", typst_text)

    def test_shared_date_sub_role_displays_carried_forward_range(self):
        # Real, confirmed case: multiple roles under one employer share a
        # single printed date range against only the first-listed role
        # (the actual resume's three-USAID-roles case). The sub-role's own
        # "Not specified" dates should display the employer's shared range
        # instead of no date at all.
        resume = {**_RESUME, "work_experience": [
            {
                "org": "USAID", "role": "Lead", "location": "Kyiv",
                "start_date": "06/2020", "end_date": "07/2025", "bullets": ["First role"],
            },
            {
                "org": "USAID", "role": "Officer", "location": "Bogota",
                "start_date": "Not specified", "end_date": "Not specified", "bullets": ["Second role"],
            },
        ]}
        typst_text = build_typst(resume)
        self.assertIn("#job-heading([USAID], [Lead], [06/2020 – 07/2025])", typst_text)
        self.assertIn("#job-heading([USAID], [Officer], [06/2020 – 07/2025])", typst_text)
        self.assertNotIn("Not specified", typst_text)

    def test_shared_date_carry_forward_resets_on_new_employer(self):
        resume = {**_RESUME, "work_experience": [
            {
                "org": "USAID", "role": "Lead", "location": "Kyiv",
                "start_date": "06/2020", "end_date": "07/2025", "bullets": ["First role"],
            },
            {
                "org": "Berkeley", "role": "Instructor", "location": "Berkeley",
                "start_date": "Not specified", "end_date": "Not specified", "bullets": ["Second role"],
            },
        ]}
        typst_text = build_typst(resume)
        self.assertIn("#job-heading([USAID], [Lead], [06/2020 – 07/2025])", typst_text)
        # Different org, no real dates of its own -- no range to carry.
        self.assertIn("#job-heading([Berkeley], [Instructor], none)", typst_text)

    def test_tighter_tier_produces_smaller_sizes(self):
        from resume_manager.render import _DENSITY_TIERS
        spacious = build_typst(_RESUME, _DENSITY_TIERS[0])
        tight = build_typst(_RESUME, _DENSITY_TIERS[-1])
        self.assertIn(_DENSITY_TIERS[0]["body_size"], spacious)
        self.assertIn(_DENSITY_TIERS[-1]["body_size"], tight)
        self.assertNotEqual(spacious, tight)

    def test_education_awards_publications_skills_are_non_breakable_blocks(self):
        # Spec §13a: these sections must move to the next page as one
        # atomic unit rather than splitting mid-section.
        typst_text = build_typst(_RESUME)
        for heading in ["== Education", "== Awards", "== Research Presentations", "== Skills"]:
            self.assertIn(f"#block(breakable: false)[\n{heading}", typst_text)

    def test_work_experience_is_not_wrapped_non_breakable(self):
        # Spec §13a: Work Experience must stay breakable/flowing -- its
        # length is deliberately grown by tailor_resume.py's fill loop
        # (§13b) to use available space, unlike the other sections.
        typst_text = build_typst(_RESUME)
        self.assertNotIn("#block(breakable: false)[\n== Work Experience", typst_text)

    def test_force_page_break_before_static_defaults_to_off(self):
        # Direct build_typst callers (every existing test above, and any
        # future one) get today's behavior unchanged unless they opt in.
        typst_text = build_typst(_RESUME)
        self.assertNotIn("#pagebreak()", typst_text)

    def test_force_page_break_before_static_inserts_a_break_before_the_first_static_section(self):
        # 2026-09-28 layout fix: Work Experience should get first claim on
        # page 1, with Education (or whichever static section is first
        # present) starting fresh on the next page, rather than the two
        # competing for the same page-fit budget.
        typst_text = build_typst(_RESUME, force_page_break_before_static=True)
        self.assertIn("#pagebreak()\n\n#block(breakable: false)[\n== Education", typst_text)

    def test_force_page_break_before_static_uses_whichever_static_section_is_first_present(self):
        resume = {**_RESUME, "education": []}
        typst_text = build_typst(resume, force_page_break_before_static=True)
        self.assertIn("#pagebreak()\n\n#block(breakable: false)[\n== Awards", typst_text)

    def test_force_page_break_before_static_is_skipped_with_no_work_experience(self):
        # Nothing to push to a second page relative to -- a page break here
        # would just leave a blank first page.
        resume = {**_RESUME, "work_experience": []}
        typst_text = build_typst(resume, force_page_break_before_static=True)
        self.assertNotIn("#pagebreak()", typst_text)

    def test_force_page_break_before_static_is_skipped_with_no_static_sections(self):
        resume = {**_RESUME, "education": [], "awards": [], "publications": [], "skills": []}
        typst_text = build_typst(resume, force_page_break_before_static=True)
        self.assertNotIn("#pagebreak()", typst_text)


class TestNonBreakableSectionRegression(unittest.TestCase):
    _EDUCATION = [
        {
            "institution": "Columbia University", "degree": "PhD in Sustainable Development",
            "gpa": None, "location": "New York, NY, USA", "start_date": "08/2026",
            "end_date": "Present", "thesis": None,
        },
        {
            "institution": "Georgia Institute of Technology", "degree": "Master of Science in Computer Science",
            "gpa": "3.88", "location": "Atlanta, GA, USA", "start_date": "01/2022",
            "end_date": "12/2025", "thesis": None,
        },
        {
            "institution": "Indiana State University", "degree": "Master of Science in Mathematics",
            "gpa": "3.85", "location": "Terre Haute, IN, USA", "start_date": "05/2021",
            "end_date": "05/2024", "thesis": None,
        },
    ]

    def test_education_section_does_not_split_across_a_forced_page_break(self):
        # Real, confirmed defect (2026-09-26): with enough Work Experience
        # content to push Education right up against a page boundary,
        # Education used to split -- some institutions on page 1, the
        # rest on page 2. Calibrated against this exact real template:
        # 37 filler bullets in one Work Experience entry reproduces the
        # split on the pre-fix code.
        resume = {
            "contact": {"name": "Test Person", "email": "a@x.com"},
            "work_experience": [{
                "org": "Acme", "role": "Engineer", "location": "NYC",
                "start_date": "2020", "end_date": "Present",
                "bullets": [
                    f"Filler bullet number {i} with some descriptive padding text to take up space."
                    for i in range(37)
                ],
            }],
            "education": self._EDUCATION,
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Resume.pdf")
            render_resume_pdf(resume, output_path, target_pages=50)  # never trigger tier-shrink

            from pypdf import PdfReader
            texts = [page.extract_text() for page in PdfReader(output_path).pages]
            pages_with_institution = [
                i for i, t in enumerate(texts)
                if any(entry["institution"] in t for entry in self._EDUCATION)
            ]
            self.assertEqual(len(set(pages_with_institution)), 1, "Education split across more than one page")
            for entry in self._EDUCATION:
                self.assertIn(entry["institution"], texts[pages_with_institution[0]])


class TestRenderResumePdf(unittest.TestCase):
    def test_writes_a_non_empty_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path)

            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))

    def test_also_writes_the_typst_source_alongside_the_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path)

            typst_path = os.path.join(tmp, "Tailored_Resume.typ")
            self.assertTrue(os.path.exists(typst_path))
            with open(typst_path, encoding="utf-8") as f:
                self.assertIn("Aaron Scherf", f.read())

    def test_small_resume_fits_within_target_pages_at_the_default_tier(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path, target_pages=2)

            from pypdf import PdfReader
            self.assertLessEqual(len(PdfReader(output_path).pages), 2)

    def test_education_starts_on_a_fresh_page_when_target_pages_is_at_least_two(self):
        # 2026-09-28 layout fix: with a real target of 2+ pages, Education
        # must never share a page with Work Experience, regardless of how
        # short Work Experience turns out to be -- it gets pushed to
        # whatever page follows, guaranteed by an explicit page break
        # rather than hoping the page-fit numbers work out.
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(_RESUME, output_path, target_pages=2)

            from pypdf import PdfReader
            texts = [page.extract_text() for page in PdfReader(output_path).pages]
            work_experience_pages = {i for i, t in enumerate(texts) if "Acme" in t}
            education_pages = {i for i, t in enumerate(texts) if "State U" in t}
            self.assertTrue(work_experience_pages)
            self.assertTrue(education_pages)
            self.assertTrue(work_experience_pages.isdisjoint(education_pages))

    def test_overflowing_content_steps_down_to_a_tighter_tier(self):
        # A huge number of long bullets can't possibly fit one page even
        # at the tightest tier -- render_resume_pdf should still produce
        # a valid PDF (using the tightest tier) rather than raising or
        # looping forever.
        huge_resume = {**_RESUME, "work_experience": [{
            "org": "Acme", "role": "Engineer", "location": "NYC",
            "start_date": "2020", "end_date": "Present",
            "bullets": [f"Bullet number {i} with some real descriptive text in it" for i in range(80)],
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "Tailored_Resume.pdf")

            render_resume_pdf(huge_resume, output_path, target_pages=1)

            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "rb") as f:
                self.assertTrue(f.read(5).startswith(b"%PDF"))
            with open(os.path.join(tmp, "Tailored_Resume.typ"), encoding="utf-8") as f:
                typst_source = f.read()
            from resume_manager.render import _DENSITY_TIERS
            self.assertIn(_DENSITY_TIERS[-1]["body_size"], typst_source)
