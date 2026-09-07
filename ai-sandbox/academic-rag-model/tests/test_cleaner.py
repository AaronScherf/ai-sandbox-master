import unittest

from audio_generator.cleaner import clean_markdown_for_speech


class TestCleanMarkdownForSpeech(unittest.TestCase):
    def test_strips_fenced_code_blocks(self):
        md = "Before.\n```python\nprint('hi')\n```\nAfter."
        result = clean_markdown_for_speech(md)
        self.assertNotIn("print", result)
        self.assertIn("Code snippet omitted", result)
        self.assertIn("Before.", result)
        self.assertIn("After.", result)

    def test_unwraps_inline_code(self):
        result = clean_markdown_for_speech("Call `foo()` to start.")
        self.assertIn("foo()", result)
        self.assertNotIn("`", result)

    def test_converts_block_latex_to_equation_prose(self):
        result = clean_markdown_for_speech("$$x^2 + y^2 = z^2$$")
        self.assertIn("Equation:", result)
        self.assertIn("x^2", result)

    def test_converts_inline_latex(self):
        result = clean_markdown_for_speech("The value is $x = 3$ here.")
        self.assertIn("x = 3", result)
        self.assertNotIn("$", result)

    def test_strips_video_notes_style_citations(self):
        md = "The eigenvalue of the matrix is 3 ([04:12](https://youtu.be/abc123&t=252s))."
        result = clean_markdown_for_speech(md)
        self.assertNotIn("04:12", result)
        self.assertNotIn("youtu.be", result)
        self.assertIn("The eigenvalue of the matrix is 3", result)

    def test_strips_remaining_markdown_syntax(self):
        result = clean_markdown_for_speech("# Heading\n\n- item one\n- item two")
        self.assertIn("Heading", result)
        self.assertIn("item one", result)
        self.assertIn("item two", result)
        self.assertNotIn("#", result)
        self.assertNotIn("- item", result)

    def test_image_markup_is_silently_dropped(self):
        result = clean_markdown_for_speech("See ![a diagram](images/fig1.png) below.")
        self.assertNotIn("fig1.png", result)
        self.assertIn("See", result)
        self.assertIn("below.", result)

    def test_normalizes_whitespace(self):
        result = clean_markdown_for_speech("Too    much\n\n\nwhitespace.")
        self.assertNotIn("  ", result)

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(clean_markdown_for_speech(""), "")

    def test_whitespace_only_input_returns_empty_string(self):
        self.assertEqual(clean_markdown_for_speech("   \n\n  "), "")
