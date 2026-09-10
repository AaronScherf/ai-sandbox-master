import unittest

from resume_manager.normalize import (
    ResumeParseError, extract_resume_schema, match_section_header, verify_extraction,
)

# A representative excerpt covering every section shape actually observed
# in the real resume, including the two real bugs this deterministic
# parser must not reproduce: multiple roles under one employer with no
# per-role dates (USAID), and a Thesis: line belonging to the entry
# immediately before it, back-to-back with no blank-line separator
# between two institutions.
_REAL_SHAPE_RESUME = """---
source_pdf: resume.pdf
total_pages: 2
routing: local
tags: []
---

<!-- page 1 -->

Aaron Scherf

WORK EXPERIENCE

U.S. Agency for International Development
06/2020 - 07/2025
Foreign Service Officer - Monitoring, Evaluation, Learning Team Lead (FS 3-5)
Kyiv, Ukraine

• Managed portfolio of 20 program evaluations, including leading design of a $1.5M randomized control
trial to evaluate impact and cost effectiveness of $450M credit facilitation program for small farmers.

Foreign Service Officer - Gender Equity and Program Design Officer (FS 4-9)
Bogota, Colombia

• Led the design and context research for four programs in smallholder agriculture, environmental
conservation, rural land titling, and indigenous civic society leadership.

University of California, Berkeley
08/2018 - 05/2020
Graduate Student Instructor
Berkeley, CA, USA

• MATH 10A - Methods of Mathematics: Calculus, Linear Algebra, and Combinatorics: Independently
taught 52 pre-med students across two seminars and office hours, including quiz design and grading.
• PP 297 - Stata for Public Policy Analysis: Designed and taught empirical research methods in Stata
seminar for 40 MPP and MPA students, including research support for capstone projects.

<!-- page 2 -->

EDUCATION

Georgia Institute of Technology
Master of Science in Computer Science • GPA: 3.88
Atlanta, GA, USA • 01/2022 - 12/2025
Indiana State University
Master of Science in Mathematics • GPA: 3.85
Terre Haute, IN, USA • 05/2021 - 05/2024

Thesis: Novel Omnibus Normality Test and Power Comparison with the Shapiro-Wilk

Heidelberg University
Master of Science (audited) in Economics
Heidelberg, DE • 07/2017 - 06/2018

AWARDS & SCHOLARSHIPS

Donald M. Payne Fellow ($100,000 fellowship with USAID)
05/2017
Fulbright Scholar (Research Fellow at ZEW / Heidelberg, DE)
05/2017

RESEARCH PRESENTATIONS & PUBLICATIONS

Applications of PCA for Mapping Regional Socioeconomic Vulnerability Indices
12/2019
UC Berkeley: Data for Human Mobility Lab
Integration Progress: Results from two Reallabor Surveys of Asylum Seekers
08/2018
Centre for European Economic Research (ZEW)

Published at: https://www.econstor.eu/handle/10419/231442

SKILLS

Computer Programming and
Artificial Intelligence

• Python,​ ​R,​ ​JavaScript
• Machine ​Learning

Languages and Other

• Information ​Communications ​
Technology
"""


class TestMatchSectionHeader(unittest.TestCase):
    def test_exact_header_matches(self):
        self.assertEqual(match_section_header("WORK EXPERIENCE"), "work_experience")
        self.assertEqual(match_section_header("EDUCATION"), "education")
        self.assertEqual(match_section_header("AWARDS & SCHOLARSHIPS"), "awards")
        self.assertEqual(match_section_header("RESEARCH PRESENTATIONS & PUBLICATIONS"), "publications")
        self.assertEqual(match_section_header("SKILLS"), "skills")

    def test_synonym_headers_match_via_fuzzy_ratio(self):
        self.assertEqual(match_section_header("PROFESSIONAL EXPERIENCE"), "work_experience")
        self.assertEqual(match_section_header("Job Experience"), "work_experience")
        self.assertEqual(match_section_header("Honors and Awards"), "awards")
        self.assertEqual(match_section_header("Technical Skills"), "skills")

    def test_bullet_line_is_never_a_header(self):
        self.assertIsNone(match_section_header("• Did a thing at 30% growth"))

    def test_long_line_is_never_a_header(self):
        self.assertIsNone(match_section_header("This is a much longer sentence that just happens to mention experience"))

    def test_unrelated_short_line_does_not_match(self):
        self.assertIsNone(match_section_header("Kyiv, Ukraine"))


class TestExtractResumeSchema(unittest.TestCase):
    def setUp(self):
        self.parsed = extract_resume_schema(_REAL_SHAPE_RESUME)

    def test_returns_a_dict_not_none(self):
        self.assertIsInstance(self.parsed, dict)

    def test_name_extracted_from_first_line(self):
        self.assertEqual(self.parsed["contact"]["name"], "Aaron Scherf")

    def test_missing_contact_fields_are_not_specified(self):
        self.assertEqual(self.parsed["contact"]["email"], "Not specified")
        self.assertEqual(self.parsed["contact"]["linkedin_url"], "Not specified")

    def test_multiple_roles_under_one_employer_become_separate_entries_with_shared_org(self):
        # The real bug this must not reproduce: v1's LLM once substituted
        # a role's location into its date field; this parser must
        # instead honestly report "Not specified" for a role with no
        # date of its own, never guess.
        usaid_entries = [e for e in self.parsed["work_experience"] if e["org"] == "U.S. Agency for International Development"]
        self.assertEqual(len(usaid_entries), 2)
        self.assertEqual(usaid_entries[0]["start_date"], "06/2020")
        self.assertEqual(usaid_entries[0]["end_date"], "07/2025")
        self.assertEqual(usaid_entries[1]["start_date"], "Not specified")
        self.assertEqual(usaid_entries[1]["end_date"], "Not specified")
        self.assertEqual(usaid_entries[1]["role"], "Foreign Service Officer - Gender Equity and Program Design Officer (FS 4-9)")

    def test_line_wrapped_bullet_is_joined_into_one_bullet(self):
        first_bullet = self.parsed["work_experience"][0]["bullets"][0]
        self.assertIn("randomized control trial to evaluate", first_bullet)
        self.assertNotIn("\n", first_bullet)

    def test_graduate_student_instructor_is_work_experience_not_education(self):
        # The real bug this must fix: v1's LLM miscategorized this role as
        # an "education" entry and dropped its bullets entirely.
        gsi_entries = [e for e in self.parsed["work_experience"] if e["role"] == "Graduate Student Instructor"]
        self.assertEqual(len(gsi_entries), 1)
        self.assertEqual(gsi_entries[0]["org"], "University of California, Berkeley")
        self.assertEqual(len(gsi_entries[0]["bullets"]), 2)
        self.assertNotIn("Graduate Student Instructor", [e["degree"] for e in self.parsed["education"]])

    def test_education_entries_with_no_blank_line_between_them_are_still_separated(self):
        institutions = [e["institution"] for e in self.parsed["education"]]
        self.assertIn("Georgia Institute of Technology", institutions)
        self.assertIn("Indiana State University", institutions)

    def test_gpa_split_from_degree_line(self):
        gatech = next(e for e in self.parsed["education"] if e["institution"] == "Georgia Institute of Technology")
        self.assertEqual(gatech["degree"], "Master of Science in Computer Science")
        self.assertEqual(gatech["gpa"], "3.88")

    def test_missing_gpa_is_not_specified(self):
        heidelberg = next(e for e in self.parsed["education"] if e["institution"] == "Heidelberg University")
        self.assertEqual(heidelberg["gpa"], "Not specified")

    def test_thesis_line_attaches_to_the_entry_immediately_before_it(self):
        # The real bug this must fix: v1's LLM wrote "Not specified" for
        # this thesis even though it's present in the raw text.
        indiana = next(e for e in self.parsed["education"] if e["institution"] == "Indiana State University")
        self.assertIn("Novel Omnibus Normality Test", indiana["thesis"])
        gatech = next(e for e in self.parsed["education"] if e["institution"] == "Georgia Institute of Technology")
        self.assertEqual(gatech["thesis"], "Not specified")

    def test_award_name_and_parenthetical_description_are_split(self):
        payne = next(a for a in self.parsed["awards"] if "Payne" in a["name"])
        self.assertEqual(payne["description"], "$100,000 fellowship with USAID")
        self.assertEqual(payne["date"], "05/2017")

    def test_published_at_line_attaches_to_the_publication_before_it(self):
        zew_pub = next(p for p in self.parsed["publications"] if "Integration Progress" in p["title"])
        self.assertEqual(zew_pub["link"], "https://www.econstor.eu/handle/10419/231442")
        pca_pub = next(p for p in self.parsed["publications"] if "PCA" in p["title"])
        self.assertEqual(pca_pub["link"], "Not specified")

    def test_skills_category_spanning_two_lines_is_joined(self):
        category_names = [c["category"] for c in self.parsed["skills"]]
        self.assertIn("Computer Programming and Artificial Intelligence", category_names)

    def test_comma_separated_bullet_splits_into_multiple_items(self):
        cs_category = next(c for c in self.parsed["skills"] if "Computer Programming" in c["category"])
        self.assertIn("Python", cs_category["items"])
        self.assertIn("R", cs_category["items"])
        self.assertIn("JavaScript", cs_category["items"])

    def test_single_item_bullet_is_not_split(self):
        cs_category = next(c for c in self.parsed["skills"] if "Computer Programming" in c["category"])
        self.assertIn("Machine Learning", cs_category["items"])

    def test_zero_width_space_and_wrapped_item_is_cleaned_and_joined(self):
        languages_category = next(c for c in self.parsed["skills"] if "Languages" in c["category"])
        self.assertIn("Information Communications Technology", languages_category["items"])


class TestExtractResumeSchemaFailureMode(unittest.TestCase):
    def test_unrecognized_document_returns_none_not_an_exception(self):
        self.assertIsNone(extract_resume_schema("This document has no recognizable resume structure at all."))


class TestVerifyExtraction(unittest.TestCase):
    def test_deterministically_parsed_output_always_verifies_clean(self):
        parsed = extract_resume_schema(_REAL_SHAPE_RESUME)
        from resume_manager.schema import assign_ids
        assign_ids(parsed["work_experience"], "org")
        assign_ids(parsed["education"], "institution")
        raw_text = _REAL_SHAPE_RESUME
        problems = verify_extraction(parsed, raw_text)
        self.assertEqual(problems, [])
