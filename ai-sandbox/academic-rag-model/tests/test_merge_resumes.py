import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

from resume_manager.extract import DefectivePageError
from resume_manager.merge_resumes import (
    _build_master_context, _discover_unprocessed_files, _excerpt_around, _extract_raw_text, _load_manifest,
    _save_manifest, merge_one_source, merge_source_resumes,
)

_MASTER = {
    "contact": {"name": "Aaron"},
    "work_experience": [
        {"id": "acme-1", "org": "Acme", "role": "Engineer", "location": "NYC",
         "start_date": "2020", "end_date": "Present", "bullets": ["Grew revenue 30%"]},
    ],
    "education": [
        {"id": "state-u-1", "institution": "State U", "degree": "BS", "gpa": "3.9",
         "location": "TX", "start_date": "2016", "end_date": "2020", "thesis": "A Fixture Thesis"},
    ],
    "awards": [{"name": "Existing Award", "description": "d", "date": "2019"}],
    "publications": [{"title": "Existing Paper", "date": "2021", "venue": "A Venue", "link": None}],
    "skills": [],
}


class TestDiscoverUnprocessedFiles(unittest.TestCase):
    def test_new_file_is_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "resume.pdf"), "w").close()
            self.assertEqual(_discover_unprocessed_files(tmp, {}), ["resume.pdf"])

    def test_unchanged_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.pdf")
            open(path, "w").close()
            manifest = {"resume.pdf": os.path.getmtime(path)}
            self.assertEqual(_discover_unprocessed_files(tmp, manifest), [])

    def test_changed_mtime_is_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.pdf")
            open(path, "w").close()
            manifest = {"resume.pdf": os.path.getmtime(path) - 1000}
            self.assertEqual(_discover_unprocessed_files(tmp, manifest), ["resume.pdf"])

    def test_unsupported_extension_is_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "notes.txt"), "w").close()
            self.assertEqual(_discover_unprocessed_files(tmp, {}), [])

    def test_dotfiles_and_desktop_ini_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "desktop.ini"), "w").close()
            open(os.path.join(tmp, ".hidden.pdf"), "w").close()
            self.assertEqual(_discover_unprocessed_files(tmp, {}), [])

    def test_nonexistent_directory_returns_empty(self):
        self.assertEqual(_discover_unprocessed_files("/does/not/exist", {}), [])


class TestManifestRoundTrip(unittest.TestCase):
    def test_save_then_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            _save_manifest(tmp, {"a.pdf": 123.0})
            self.assertEqual(_load_manifest(tmp), {"a.pdf": 123.0})

    def test_load_missing_manifest_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_load_manifest(tmp), {})


class TestExtractRawText(unittest.TestCase):
    @patch("resume_manager.merge_resumes.extract_resume_text", return_value="pdf text")
    def test_pdf_uses_extract_resume_text(self, mock_extract):
        self.assertEqual(_extract_raw_text("resume.pdf"), "pdf text")
        mock_extract.assert_called_once_with("resume.pdf")

    def test_docx_uses_mammoth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.docx")
            open(path, "wb").close()
            mock_mammoth = MagicMock()
            mock_mammoth.convert_to_markdown.return_value = MagicMock(value="docx text")
            with patch.dict("sys.modules", {"mammoth": mock_mammoth}):
                self.assertEqual(_extract_raw_text(path), "docx text")

    def test_unsupported_extension_returns_none(self):
        self.assertIsNone(_extract_raw_text("notes.txt"))


class TestExcerptAround(unittest.TestCase):
    def test_returns_a_window_starting_at_the_needle(self):
        raw_text = "noise before it\n" + "x" * 100 + "\nAcme Corp\nEngineer\n- Did a thing." + "y" * 5000
        excerpt = _excerpt_around(raw_text, "Acme Corp", window=50)
        self.assertTrue(excerpt.startswith("Acme Corp"))
        self.assertEqual(len(excerpt), 50)

    def test_match_is_case_insensitive(self):
        raw_text = "prefix\nACME CORP\nEngineer\n- Did a thing." + "y" * 5000
        excerpt = _excerpt_around(raw_text, "Acme Corp", window=50)
        self.assertTrue(excerpt.startswith("ACME CORP"))

    def test_falls_back_to_the_full_text_when_the_needle_is_not_found(self):
        raw_text = "This document never mentions that organization at all."
        self.assertEqual(_excerpt_around(raw_text, "Nonexistent Org", window=10), raw_text)


class TestMergeOneSource(unittest.TestCase):
    def _master(self):
        return yaml.safe_load(yaml.safe_dump(_MASTER))  # deep copy

    @patch("resume_manager.merge_resumes.call_ollama", return_value=None)
    def test_ollama_failure_applies_nothing(self, mock_call):
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(len(flagged), 1)
        self.assertEqual(master, self._master())

    @patch("resume_manager.merge_resumes.call_ollama", return_value="not: [valid: yaml: at all")
    def test_malformed_yaml_applies_nothing(self, mock_call):
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(len(flagged), 1)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_traceable_new_bullet_is_added_to_existing_entry(self, mock_call):
        raw_text = "Acme Corp\nEngineer\n- Grew revenue 30%\n- Shipped a brand new feature to production."
        mock_call.return_value = yaml.safe_dump({
            "new_bullets_by_id": {"acme-1": ["Shipped a brand new feature to production."]},
        })
        master = self._master()
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(flagged, [])
        self.assertIn("Shipped a brand new feature to production.", master["work_experience"][0]["bullets"])
        self.assertEqual(len(applied), 1)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_paraphrased_new_bullet_is_added_without_a_traceability_check(self, mock_call):
        raw_text = "Acme Corp\nEngineer\n- Grew revenue 30%"
        mock_call.return_value = yaml.safe_dump({
            "new_bullets_by_id": {"acme-1": ["Drove a third more revenue than the prior year."]},
        })
        master = self._master()
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(flagged, [])
        self.assertEqual(
            master["work_experience"][0]["bullets"],
            ["Grew revenue 30%", "Drove a third more revenue than the prior year."],
        )
        self.assertTrue(any("acme-1" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_new_bullet_for_unknown_id_is_flagged_not_crashed(self, mock_call):
        mock_call.return_value = yaml.safe_dump({"new_bullets_by_id": {"nonexistent": ["Some bullet."]}})
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertTrue(any("nonexistent" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_underscore_id_resolves_to_the_hyphenated_master_id(self, mock_call):
        # Real, confirmed slip (2026-09-26): a real merge run had the LLM
        # write "university_of_california_berkeley_1" for an id the
        # master actually stores as "university-of-california-berkeley-1"
        # -- an exact-match lookup silently lost 4 otherwise-good new
        # bullets to this formatting mismatch alone.
        raw_text = "Acme Corp\nEngineer\n- Grew revenue 30%\n- Shipped a brand new feature to production."
        mock_call.return_value = yaml.safe_dump({"new_bullets_by_id": {"acme_1": ["Shipped a brand new feature to production."]}})
        master = self._master()
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(flagged, [])
        self.assertEqual(len(applied), 1)
        self.assertIn("Shipped a brand new feature to production.", master["work_experience"][0]["bullets"])

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_near_identical_bullet_is_flagged_as_duplicate_not_added(self, mock_call):
        # Real, confirmed failure (2026-09-26): a real merge run added a
        # bullet the LLM called "new" that was actually word-for-word
        # already in the master. This is the deterministic safety net
        # that catches it even when the LLM's own judgment doesn't.
        # (Master's existing bullet is "Grew revenue 30%" -- see _MASTER.)
        raw_text = "Acme Corp\nEngineer\n- Grew revenue by 30%."
        mock_call.return_value = yaml.safe_dump({
            "new_bullets_by_id": {"acme-1": ["Grew revenue by 30%."]},
        })
        master = self._master()
        original_bullets = list(master["work_experience"][0]["bullets"])
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(applied, [])
        self.assertTrue(any("duplicate" in f for f in flagged))
        self.assertEqual(master["work_experience"][0]["bullets"], original_bullets)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_reworded_duplicate_work_experience_entry_is_flagged_not_added(self, mock_call):
        # Real, confirmed failure (2026-09-26): a real merge run created 3
        # duplicate USAID work_experience entries this way -- the LLM
        # didn't recognize a slightly-reworded version of an existing
        # role/org as already present. Realistic long-form phrasing here
        # (rather than the short _MASTER fixture's own entry) matches how
        # fuzzy ratio actually behaves on real resume-length text -- a few
        # differing words in a long string still scores high similarity,
        # unlike the same few words changed in a short string.
        master = self._master()
        master["work_experience"][0]["org"] = "United States Department of Agriculture"
        master["work_experience"][0]["role"] = (
            "Program Officer for Rural Development and Agricultural Extension Services"
        )
        raw_text = (
            "United States Department of Agriculture\n"
            "Program Officer for Rural Development and Extension Services\nDC\n2018 - 2020\n"
            "- Grew revenue 30%"
        )
        mock_call.return_value = yaml.safe_dump({
            "new_work_experience": [{
                "org": "United States Department of Agriculture",
                "role": "Program Officer for Rural Development and Extension Services",
                "location": "DC", "start_date": "2018", "end_date": "2020", "bullets": ["Grew revenue 30%"],
            }],
        })
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(applied, [])
        self.assertEqual(len(master["work_experience"]), 1)
        self.assertTrue(any("duplicate" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_reworded_duplicate_education_entry_is_flagged_not_added(self, mock_call):
        master = self._master()
        master["education"][0]["institution"] = "Georgia Institute of Technology"
        master["education"][0]["degree"] = "Master of Science in Computer Science"
        raw_text = "Georgia Institute of Technology\nMaster of Science in Computer Engineering\nGA\n2020 - 2022"
        mock_call.return_value = yaml.safe_dump({
            "new_education": [{
                "institution": "Georgia Institute of Technology",
                "degree": "Master of Science in Computer Engineering", "gpa": "Not specified",
                "location": "GA", "start_date": "2020", "end_date": "2022", "thesis": "Not specified",
            }],
        })
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(applied, [])
        self.assertEqual(len(master["education"]), 1)
        self.assertTrue(any("duplicate" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_same_institution_and_gpa_with_very_different_degree_wording_is_flagged(self, mock_call):
        # Real, confirmed slip-through (2026-09-26): "Mercer University
        # Bachelor in Finance and Economics" vs "Mercer University B.B.A.
        # with Honors, Summa Cum Laude, GPA: 3.91" -- the same real degree
        # (same institution, same 3.91 GPA), but the degree wording is so
        # different that combined institution+degree text similarity
        # (48.7) was actually LOWER than some genuinely different
        # institution pairs -- institution-alone + exact GPA match is
        # the reliable signal here.
        master = self._master()
        master["education"][0]["institution"] = "Mercer University"
        master["education"][0]["degree"] = "Bachelor in Finance and Economics"
        master["education"][0]["gpa"] = "3.91"
        raw_text = "Mercer University, B.B.A. with Honors, Summa Cum Laude, GPA: 3.91"
        mock_call.return_value = yaml.safe_dump({
            "new_education": [{
                "institution": "Mercer University",
                "degree": "B.B.A. with Honors, Summa Cum Laude, GPA: 3.91", "gpa": "3.91",
                "location": "Not specified", "start_date": "Not specified", "end_date": "Not specified",
                "thesis": "Not specified",
            }],
        })
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(applied, [])
        self.assertEqual(len(master["education"]), 1)
        self.assertTrue(any("duplicate" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_same_institution_different_gpa_and_degree_is_not_flagged(self, mock_call):
        # A real, legitimate case (e.g. a Bachelor's AND a Master's from
        # the same school) must not be wrongly merged just for sharing an
        # institution -- the GPA match is what makes the Mercer case above
        # safe to flag; without it, two different real degrees stay
        # distinct entries.
        master = self._master()
        master["education"][0]["institution"] = "Mercer University"
        master["education"][0]["degree"] = "Bachelor in Finance and Economics"
        master["education"][0]["gpa"] = "3.91"
        raw_text = "Mercer University, Master of Business Administration, GPA: 3.7, 2018 - 2020"
        mock_call.return_value = yaml.safe_dump({
            "new_education": [{
                "institution": "Mercer University", "degree": "Master of Business Administration",
                "gpa": "3.7", "location": "Not specified", "start_date": "2018", "end_date": "2020",
                "thesis": "Not specified",
            }],
        })
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(len(applied), 1)
        self.assertEqual(len(master["education"]), 2)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_duplicate_award_is_flagged_not_added(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_awards": [{"name": "Existing Award", "description": "d2", "date": "2019"}],
        })
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(len(master["awards"]), 1)
        self.assertTrue(any("duplicate" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_same_date_moderately_similar_award_name_is_flagged_as_duplicate(self, mock_call):
        # Real, confirmed slip-through (2026-09-26): "Donald M. Payne
        # Fellow" vs "Donald M. Payne International Development Fellow"
        # -- the same real $100,000 fellowship, same date -- only scored
        # 62.9 name similarity on its own, under the name-only threshold,
        # and was wrongly added as a duplicate second entry. An exact date
        # match plus this name similarity should now catch it.
        master = self._master()
        master["awards"][0]["name"] = "Donald M. Payne Fellow"
        master["awards"][0]["date"] = "05/2017"
        mock_call.return_value = yaml.safe_dump({
            "new_awards": [{
                "name": "Donald M. Payne International Development Fellow",
                "description": "$100,000 graduate fellowship", "date": "05/2017",
            }],
        })
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(len(master["awards"]), 1)
        self.assertTrue(any("duplicate" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_moderately_similar_award_name_with_a_different_date_is_not_flagged(self, mock_call):
        # The date-based leniency must not fire when the date differs --
        # otherwise two genuinely different awards sharing a common word
        # (e.g. "Fellow") could get wrongly merged.
        master = self._master()
        master["awards"][0]["name"] = "Donald M. Payne Fellow"
        master["awards"][0]["date"] = "05/2017"
        raw_text = "Donald M. Payne International Development Fellow, $100,000 graduate fellowship, 05/2019"
        mock_call.return_value = yaml.safe_dump({
            "new_awards": [{
                "name": "Donald M. Payne International Development Fellow",
                "description": "$100,000 graduate fellowship", "date": "05/2019",
            }],
        })
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(len(applied), 1)
        self.assertEqual(len(master["awards"]), 2)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_duplicate_publication_is_flagged_not_added(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_publications": [{"title": "Existing Paper", "date": "2021", "venue": "Another Venue", "link": None}],
        })
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(len(master["publications"]), 1)
        self.assertTrue(any("duplicate" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_traceable_new_work_experience_entry_is_added_with_a_fresh_id(self, mock_call):
        raw_text = (
            "Globex Corporation\nAnalyst\nLA\n01/2019 - 01/2020\n"
            "- Built quarterly reports for leadership."
        )
        mock_call.return_value = yaml.safe_dump({
            "new_work_experience": [{
                "org": "Globex Corporation", "role": "Analyst", "location": "LA",
                "start_date": "01/2019", "end_date": "01/2020",
                "bullets": ["Built quarterly reports for leadership."],
            }],
        })
        master = self._master()
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(flagged, [])
        self.assertEqual(len(master["work_experience"]), 2)
        new_entry = master["work_experience"][1]
        self.assertEqual(new_entry["org"], "Globex Corporation")
        self.assertNotEqual(new_entry["id"], "acme-1")
        self.assertEqual(len(applied), 1)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_new_work_experience_id_does_not_collide_with_same_org(self, mock_call):
        # Real case (spec §12): the master already has an "Acme-1" id --
        # a new role at the same org must not reuse it.
        raw_text = "Acme Corp\nManager\nNYC\n01/2021 - 01/2022\n- Managed a small team."
        mock_call.return_value = yaml.safe_dump({
            "new_work_experience": [{
                "org": "Acme", "role": "Manager", "location": "NYC",
                "start_date": "01/2021", "end_date": "01/2022",
                "bullets": ["Managed a small team."],
            }],
        })
        master = self._master()
        merge_one_source(master, raw_text)
        ids = [e["id"] for e in master["work_experience"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("acme-2", ids)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_paraphrased_new_work_experience_entry_is_added_without_a_traceability_check(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_work_experience": [{
                "org": "Other Corp", "role": "Other Role", "location": "Nowhere",
                "start_date": "01/2019", "end_date": "01/2020", "bullets": ["Led a summarized initiative."],
            }],
        })
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text describing the same role in different words")
        self.assertEqual(flagged, [])
        self.assertEqual(len(master["work_experience"]), 2)
        self.assertTrue(any("Other Corp" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_traceable_new_education_award_and_publication_are_added(self, mock_call):
        raw_text = (
            "Some University\nMaster of Arts\n01/2015 - 01/2017\n"
            "Best Paper Award\nGiven for excellence\n2018\n"
            "A Great Paper\n2019\nSome Venue\n"
        )
        mock_call.return_value = yaml.safe_dump({
            "new_education": [{
                "institution": "Some University", "degree": "Master of Arts", "gpa": "Not specified",
                "location": "Not specified", "start_date": "01/2015", "end_date": "01/2017",
                "thesis": "Not specified",
            }],
            "new_awards": [{"name": "Best Paper Award", "description": "Given for excellence", "date": "2018"}],
            "new_publications": [{"title": "A Great Paper", "date": "2019", "venue": "Some Venue", "link": "Not specified"}],
        })
        master = self._master()
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(flagged, [])
        self.assertEqual(len(master["education"]), 2)
        self.assertEqual(len(master["awards"]), 2)
        self.assertEqual(len(master["publications"]), 2)
        self.assertEqual(len(applied), 3)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_no_new_content_returns_empty_applied_and_flagged(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_bullets_by_id": {}, "new_work_experience": [], "new_education": [],
            "new_awards": [], "new_publications": [],
        })
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(flagged, [])

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_new_entry_with_no_bullets_is_backfilled_from_a_followup_call(self, mock_call):
        mock_call.side_effect = [
            yaml.safe_dump({
                "new_work_experience": [{
                    "org": "Other Corp", "role": "Other Role", "location": "Nowhere",
                    "start_date": "01/2019", "end_date": "01/2020", "bullets": [],
                }],
            }),
            yaml.safe_dump({"bullets": ["Did the first thing.", "Did the second thing."]}),
        ]
        master = self._master()
        raw_text = "y" * 5000 + "\nOther Corp\nOther Role\n- Did the first thing.\n- Did the second thing."
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(flagged, [])
        self.assertEqual(mock_call.call_count, 2)
        new_entry = next(e for e in master["work_experience"] if e["org"] == "Other Corp")
        self.assertEqual(new_entry["bullets"], ["Did the first thing.", "Did the second thing."])
        self.assertTrue(any("backfilled" in a for a in applied))
        # Real, confirmed memory problem (2026-09-27): this narrowly-scoped
        # follow-up call was sending the entire source document, forcing
        # Ollama to size its context window for the whole thing on every
        # such call in a run -- real enough to exhaust system memory. It
        # must only receive an excerpt around the role it's targeting.
        backfill_prompt = mock_call.call_args_list[-1].args[0]
        self.assertNotIn("y" * 5000, backfill_prompt)
        self.assertIn("Other Corp", backfill_prompt)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_new_entry_still_empty_after_failed_backfill_is_flagged(self, mock_call):
        mock_call.side_effect = [
            yaml.safe_dump({
                "new_work_experience": [{
                    "org": "Other Corp", "role": "Other Role", "location": "Nowhere",
                    "start_date": "01/2019", "end_date": "01/2020", "bullets": [],
                }],
            }),
            "not valid yaml: [",
        ]
        master = self._master()
        _applied, flagged = merge_one_source(master, "raw text")
        new_entry = next(e for e in master["work_experience"] if e["org"] == "Other Corp")
        self.assertEqual(new_entry.get("bullets"), [])
        self.assertTrue(any("still has no bullets" in f for f in flagged))

    def test_build_master_context_flags_blank_education_fields_and_shows_real_ones(self):
        master = self._master()
        master["education"][0]["thesis"] = None
        context = _build_master_context(master)
        self.assertIn("gpa: 3.9", context)
        self.assertIn("thesis: (blank -- fill in under new_field_updates_by_id if this document states it)", context)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_existing_entry_with_empty_bullets_is_backfilled_even_if_llm_ignores_it(self, mock_call):
        # Real, confirmed gap (2026-09-27): a re-run against a master that
        # already has a blank-bullets entry from an earlier run is not
        # reliably caught by the main comparison call alone -- the model
        # can simply omit the entry from its response entirely. This must
        # not depend on the main call proposing anything for it.
        master = self._master()
        master["work_experience"][0]["bullets"] = []
        mock_call.side_effect = [
            yaml.safe_dump({
                "new_work_experience": [], "new_education": [], "new_awards": [], "new_publications": [],
            }),
            yaml.safe_dump({"bullets": ["Recovered bullet one.", "Recovered bullet two."]}),
        ]
        applied, flagged = merge_one_source(master, "raw text describing Acme in detail")
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(master["work_experience"][0]["bullets"], ["Recovered bullet one.", "Recovered bullet two."])
        self.assertTrue(any("backfilled" in a and "acme-1" in a for a in applied))
        self.assertEqual(flagged, [])

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_existing_entry_stays_empty_when_backfill_finds_nothing(self, mock_call):
        master = self._master()
        master["work_experience"][0]["bullets"] = []
        mock_call.side_effect = [
            yaml.safe_dump({
                "new_work_experience": [], "new_education": [], "new_awards": [], "new_publications": [],
            }),
            yaml.safe_dump({"bullets": []}),
        ]
        applied, _flagged = merge_one_source(master, "raw text")
        self.assertEqual(master["work_experience"][0]["bullets"], [])
        self.assertFalse(any("backfilled" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_field_update_fills_a_genuinely_blank_field(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_field_updates_by_id": {"state-u-1": {"thesis": "A Thesis About Something"}},
        })
        master = self._master()
        master["education"][0]["thesis"] = None
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(flagged, [])
        self.assertEqual(master["education"][0]["thesis"], "A Thesis About Something")
        self.assertTrue(any("state-u-1.thesis" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_field_update_is_skipped_when_field_already_has_a_real_value(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_field_updates_by_id": {"state-u-1": {"gpa": "4.0"}},
        })
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(applied, [])
        self.assertEqual(master["education"][0]["gpa"], "3.9")
        self.assertTrue(any("already has a real value" in f for f in flagged))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_field_update_rejects_a_proposed_placeholder_value(self, mock_call):
        # Real, confirmed bug (2026-09-27): a real merge run had the model
        # answer a blank field with the literal placeholder text "Not
        # specified" instead of omitting it -- writing that in just swaps
        # one placeholder spelling for another and must not count as a fill.
        mock_call.return_value = yaml.safe_dump({
            "new_field_updates_by_id": {"state-u-1": {"thesis": "Not specified"}},
        })
        master = self._master()
        master["education"][0]["thesis"] = None
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(flagged, [])
        self.assertIsNone(master["education"][0]["thesis"])
        self.assertFalse(any("thesis" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_existing_education_entry_with_blank_field_is_backfilled_from_a_followup_call(self, mock_call):
        # Mirrors the work_experience bullets backfill fix: the main
        # comparison call doesn't reliably re-propose a real value for an
        # existing entry's blank field, so a targeted follow-up call must
        # not depend on the main call mentioning it at all.
        mock_call.side_effect = [
            yaml.safe_dump({"new_field_updates_by_id": {}}),
            yaml.safe_dump({"thesis": "Recovered Thesis Title"}),
        ]
        master = self._master()
        master["education"][0]["thesis"] = None
        raw_text = "y" * 5000 + "\nState U\nBS\n- Thesis: Recovered Thesis Title"
        applied, flagged = merge_one_source(master, raw_text)
        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(master["education"][0]["thesis"], "Recovered Thesis Title")
        self.assertTrue(any("backfilled" in a and "state-u-1.thesis" in a for a in applied))
        self.assertEqual(flagged, [])
        # Same memory problem, same fix, for the education-field backfill.
        self.assertNotIn("y" * 5000, mock_call.call_args_list[-1].args[0])
        # Real, confirmed prompt bug (2026-09-27): a generic "{field_name}:
        # {value}" template in the prompt got echoed back literally by the
        # model instead of substituted with the real field name, silently
        # losing an otherwise-correctly-found answer. The prompt must show
        # the real requested field name as a concrete example instead.
        backfill_prompt = mock_call.call_args_list[-1].args[0]
        self.assertIn("thesis:", backfill_prompt)
        self.assertNotIn("{field_name}", backfill_prompt)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_education_field_backfill_ignores_a_placeholder_response(self, mock_call):
        mock_call.side_effect = [
            yaml.safe_dump({"new_field_updates_by_id": {}}),
            yaml.safe_dump({"thesis": "Not specified"}),
        ]
        master = self._master()
        master["education"][0]["thesis"] = None
        applied, _flagged = merge_one_source(master, "raw text")
        self.assertIsNone(master["education"][0]["thesis"])
        self.assertFalse(any("backfilled" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_new_skills_are_added_to_a_new_category(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_skills_by_category": {"Languages": ["Spanish", "French"]},
        })
        master = self._master()
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(flagged, [])
        self.assertEqual(len(master["skills"]), 1)
        self.assertEqual(master["skills"][0]["category"], "Languages")
        self.assertEqual(master["skills"][0]["items"], ["Spanish", "French"])
        self.assertTrue(any("Languages" in a for a in applied))

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_new_skills_merge_into_an_existing_similarly_named_category_without_duplicates(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_skills_by_category": {"Programming Languages": ["Python", "R"]},
        })
        master = self._master()
        master["skills"] = [{"category": "Programming Language", "items": ["Python", "SQL"]}]
        applied, flagged = merge_one_source(master, "raw text")
        self.assertEqual(flagged, [])
        self.assertEqual(len(master["skills"]), 1)
        self.assertEqual(master["skills"][0]["items"], ["Python", "SQL", "R"])
        self.assertTrue(any("'R']" in a for a in applied))


class TestMergeSourceResumes(unittest.TestCase):
    def _setup(self, tmp):
        source_dir = os.path.join(tmp, "source_resumes")
        os.makedirs(source_dir, exist_ok=True)
        master_path = os.path.join(tmp, "resume_master.yaml")
        with open(master_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(_MASTER, f)
        return source_dir, master_path

    def test_no_files_to_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir, master_path = self._setup(tmp)
            result = merge_source_resumes(source_dir, master_path)
            self.assertIn("No new or changed", result)

    @patch("resume_manager.merge_resumes.call_ollama", return_value=None)
    def test_processes_a_file_writes_master_report_and_manifest(self, mock_call):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir, master_path = self._setup(tmp)
            with open(os.path.join(source_dir, "extra.pdf"), "w") as f:
                f.write("placeholder")

            with patch("resume_manager.merge_resumes.extract_resume_text", return_value="some raw text"):
                result = merge_source_resumes(source_dir, master_path)

            self.assertIn("Processed 1 source file", result)
            report_path = os.path.join(tmp, "resume_master.merge_report.txt")
            self.assertTrue(os.path.exists(report_path))
            with open(os.path.join(source_dir, ".processed_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertIn("extra.pdf", manifest)
            master_md_path = os.path.join(tmp, "resume_master.md")
            self.assertTrue(os.path.exists(master_md_path))
            with open(master_md_path, encoding="utf-8") as f:
                self.assertIn("resume-master-yaml-hash:", f.read())

    def test_defective_page_error_is_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_dir, master_path = self._setup(tmp)
            with open(os.path.join(source_dir, "bad.pdf"), "w") as f:
                f.write("placeholder")

            with patch(
                "resume_manager.merge_resumes.extract_resume_text",
                side_effect=DefectivePageError("page 1 looks defective"),
            ):
                result = merge_source_resumes(source_dir, master_path)

            self.assertIn("Processed 1 source file", result)
            with open(os.path.join(tmp, "resume_master.merge_report.txt"), encoding="utf-8") as f:
                report = f.read()
            self.assertIn("skipped", report)
            self.assertIn("bad.pdf", report)

    @patch("resume_manager.merge_resumes.call_ollama")
    def test_a_second_run_does_not_reprocess_an_unchanged_file(self, mock_call):
        mock_call.return_value = yaml.safe_dump({
            "new_bullets_by_id": {}, "new_work_experience": [], "new_education": [],
            "new_awards": [], "new_publications": [],
        })
        with tempfile.TemporaryDirectory() as tmp:
            source_dir, master_path = self._setup(tmp)
            with open(os.path.join(source_dir, "extra.pdf"), "w") as f:
                f.write("placeholder")

            with patch("resume_manager.merge_resumes.extract_resume_text", return_value="some raw text"):
                merge_source_resumes(source_dir, master_path)
                second_result = merge_source_resumes(source_dir, master_path)

            self.assertIn("No new or changed", second_result)
            self.assertEqual(mock_call.call_count, 1)

    def test_a_crash_partway_through_persists_the_files_already_processed(self):
        # Real gap this fixes (2026-09-26): a kill/crash while processing
        # the 2nd of several files used to lose the 1st file's already-
        # applied changes too, since everything was only written once at
        # the very end. Now each file's result is persisted immediately.
        with tempfile.TemporaryDirectory() as tmp:
            source_dir, master_path = self._setup(tmp)
            with open(os.path.join(source_dir, "aaa_first.pdf"), "w") as f:
                f.write("placeholder")
            with open(os.path.join(source_dir, "bbb_second.pdf"), "w") as f:
                f.write("placeholder")

            def _merge_side_effect(master, raw_text, model=None):
                if "aaa_first" in raw_text:
                    return (["added something from the first file"], [])
                raise RuntimeError("simulated crash processing the second file")

            with patch("resume_manager.merge_resumes.extract_resume_text", side_effect=lambda p: p), \
                 patch("resume_manager.merge_resumes.merge_one_source", side_effect=_merge_side_effect):
                with self.assertRaises(RuntimeError):
                    merge_source_resumes(source_dir, master_path)

            with open(os.path.join(source_dir, ".processed_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertIn("aaa_first.pdf", manifest)
            self.assertNotIn("bbb_second.pdf", manifest)
            with open(os.path.join(tmp, "resume_master.merge_report.txt"), encoding="utf-8") as f:
                report = f.read()
            self.assertIn("added something from the first file", report)
