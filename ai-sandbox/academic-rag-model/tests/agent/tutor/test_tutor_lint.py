import unittest

from agent.tutor.lint import extract_symbols, lint_glossary, lint_message, symbol_hits

STATEMENT = "Choice overload suggests a consumer may walk away. Let $d$ be the default and $p(d, A)$ the probability of $\\Gamma$."
SOLUTION = "The probability of walking away equals one minus the total probability of choosing any listed alternative from the set."


def codes(violations):
    return {v.code for v in violations}


def lint(text, **kw):
    base = dict(state="WORKING", hint_level=0)
    base.update(kw)
    return lint_message(text, **base)


class TestSymbols(unittest.TestCase):
    def test_extract_symbols(self):
        self.assertEqual(extract_symbols(STATEMENT), {"d", "p", "\\Gamma"})

    def test_symbol_hits(self):
        self.assertEqual(symbol_hits("so d is chosen", {"d", "p"}), ["d"])
        self.assertEqual(symbol_hits("a standard result", {"d", "p"}), [])  # no match inside words
        self.assertEqual(symbol_hits("the Γ set", {"\\Gamma"}), ["\\Gamma"])  # unicode form of a latex command


class TestLintMessage(unittest.TestCase):
    def test_benign_feedback_passes(self):
        self.assertEqual(lint("Good, that holds. What does your definition say about the boundary?"), [])

    def test_launch_requires_verbatim_text(self):
        launch = "Question 1. Do the thing.\n\nHow would you like to approach this problem?"
        self.assertEqual(lint(launch, state="LAUNCH", allowed_exact=[launch]), [])
        self.assertEqual(lint(launch.replace("\n\n", "  "), state="LAUNCH", allowed_exact=[launch]), [])  # whitespace-insensitive
        v = lint(launch + " Assume the first option is better.", state="LAUNCH", allowed_exact=[launch])
        self.assertIn("LAUNCH_NOT_VERBATIM", codes(v))

    def test_technique_blocked_unless_student_named_it_or_level_three(self):
        draft = "Suppose, for the sake of contradiction, that f is concave."
        self.assertIn("TECHNIQUE", codes(lint(draft)))
        self.assertIn("TECHNIQUE", codes(lint(draft, hint_level=2)))
        self.assertEqual(codes(lint(draft, hint_level=3)) & {"TECHNIQUE"}, set())
        self.assertEqual(codes(lint(draft, student_text="maybe I can use contradiction")) & {"TECHNIQUE"}, set())

    def test_notation_bridge_after_define(self):
        v = lint("Choice overload raises the chance of d.", statement=STATEMENT, after_define=True)
        self.assertIn("NOTATION_BRIDGE", codes(v))
        ok = lint("Choice overload is when many options make a person less likely to choose anything.", statement=STATEMENT, after_define=True)
        self.assertEqual(ok, [])

    def test_sealed_overlap(self):
        draft = "Notice it equals one minus the total probability of choosing any item."
        self.assertIn("SEALED_OVERLAP", codes(lint(draft, sealed_solution=SOLUTION)))
        self.assertEqual(lint("What does the probability of walking away depend on?", sealed_solution=SOLUTION), [])

    def test_single_verbatim_six_word_run_from_sealed_solution_is_caught(self):
        draft = "Notice that it equals one minus the total probability here, think about why."
        self.assertIn("SEALED_OVERLAP", codes(lint(draft, sealed_solution=SOLUTION)))

    def test_leading_subquestion_list_blocked_while_working(self):
        draft = "Consider:\n1. What happens when x is negative?\n2. What happens when x is positive?"
        self.assertIn("SUBQUESTION_LIST", codes(lint(draft)))
        self.assertEqual(codes(lint(draft, hint_level=3)) & {"SUBQUESTION_LIST"}, set())

    def test_verified_requires_checkin_and_forbids_next_part(self):
        v = lint("Correct.", state="VERIFIED")
        self.assertIn("CHECKIN_MISSING", codes(v))
        ok = lint("Correct. Do you have any lingering questions, or are you ready to move on?", state="VERIFIED")
        self.assertEqual(ok, [])
        bad = lint("Correct. Ready for Question 2?", state="VERIFIED", forbidden_patterns=[r"\bQuestion 2\b"])
        self.assertIn("NEXT_PART_REFERENCE", codes(bad))

    def test_latex_in_chat_blocked(self):
        self.assertIn("LATEX_IN_CHAT", codes(lint("Is $x \\succeq y$ transitive?")))
        self.assertEqual(lint("Is x ≽ y transitive?"), [])


class TestLintGlossary(unittest.TestCase):
    def test_definition_using_problem_notation_rejected(self):
        v = lint_glossary({"choice overload": "Choice overload means d is chosen more often."}, [STATEMENT])
        self.assertEqual(codes(v), {"GLOSSARY_NOTATION"})

    def test_backreference_rejected(self):
        v = lint_glossary({"choice overload": "See part 1 for how this works."}, [STATEMENT])
        self.assertEqual(codes(v), {"GLOSSARY_BACKREF"})

    def test_clean_definition_and_unrelated_term_pass(self):
        g = {"choice overload": "A finding that many options can make people choose nothing.", "lattice": "A poset with joins and meets."}
        self.assertEqual(lint_glossary(g, [STATEMENT]), [])
