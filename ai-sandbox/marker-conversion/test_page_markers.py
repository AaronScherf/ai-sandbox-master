import unittest

from page_markers import remap_page_markers, tag_single_page


class TestRemapPageMarkers(unittest.TestCase):
    def test_remaps_paginate_output_markers_with_offset(self):
        # Marker's literal paginate_output format: \n\n{N} + 48 dashes + \n\n
        text = "Some content.\n\n" + "3" + "-" * 48 + "\n\nMore content."
        result = remap_page_markers(text, physical_offset=150, folio_offset=None, folio_start_page=0)
        self.assertIn("<!-- page 153 -->", result)
        self.assertNotIn("-" * 48, result)

    def test_remaps_braced_page_break_marker_same_as_bare(self):
        # Marker's real output may wrap the page number in braces
        # ("{0}" rather than a bare "0") -- unverifiable from this
        # machine (no marker package installed anywhere), so the regex
        # must tolerate both forms and produce the identical result.
        bare_text = "Some content.\n\n" + "3" + "-" * 48 + "\n\nMore content."
        braced_text = "Some content.\n\n" + "{3}" + "-" * 48 + "\n\nMore content."
        bare_result = remap_page_markers(bare_text, physical_offset=150, folio_offset=None, folio_start_page=0)
        braced_result = remap_page_markers(braced_text, physical_offset=150, folio_offset=None, folio_start_page=0)
        self.assertEqual(bare_result, braced_result)
        self.assertIn("<!-- page 153 -->", braced_result)
        self.assertNotIn("-" * 48, braced_result)
        self.assertNotIn("{3}", braced_result)

    def test_adds_folio_tag_when_offset_known_and_past_front_matter(self):
        text = "\n\n" + "0" + "-" * 48 + "\n\n"
        result = remap_page_markers(text, physical_offset=150, folio_offset=10, folio_start_page=20)
        self.assertIn("<!-- page 150 -->", result)
        self.assertIn("<!-- folio 140 -->", result)

    def test_no_folio_tag_before_front_matter_end(self):
        text = "\n\n" + "0" + "-" * 48 + "\n\n"
        result = remap_page_markers(text, physical_offset=5, folio_offset=10, folio_start_page=20)
        self.assertIn("<!-- page 5 -->", result)
        self.assertNotIn("folio", result)

    def test_remaps_colliding_span_anchors_and_links(self):
        # The actual collision pattern found in Axler's real output: the
        # same id="page-1-0" recurs once per chunk because chunk-local
        # numbering restarts at 0 every time.
        text = (
            '# *[Vector Spaces](#page-14-0)*\n\n'
            '<span id="page-1-0"></span>5.15 example text here.'
        )
        result = remap_page_markers(text, physical_offset=150, folio_offset=None, folio_start_page=0)
        self.assertIn('(#page-164-0)', result)
        self.assertIn('id="page-151-0"', result)

    def test_no_anchors_present_is_a_no_op(self):
        # The Rudin (scanned) case: nothing to remap.
        text = "Plain body text with no anchors, links, or page markers at all."
        self.assertEqual(remap_page_markers(text, physical_offset=300, folio_offset=None, folio_start_page=0), text)


class TestTagSinglePage(unittest.TestCase):
    def test_prepends_page_tag(self):
        result = tag_single_page("Fallback text.", physical_page=42, folio_offset=None, folio_start_page=0)
        self.assertTrue(result.startswith("<!-- page 42 -->"))
        self.assertIn("Fallback text.", result)

    def test_prepends_page_and_folio_tag(self):
        result = tag_single_page("Fallback text.", physical_page=42, folio_offset=10, folio_start_page=0)
        self.assertTrue(result.startswith("<!-- page 42 --><!-- folio 32 -->"))


if __name__ == "__main__":
    unittest.main()
