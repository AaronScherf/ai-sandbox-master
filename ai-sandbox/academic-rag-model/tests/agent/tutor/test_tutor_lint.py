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


from agent.tutor.claims import parse_recognizer
from agent.tutor.lint import check_form

BLOCKED = {"C3": parse_recognizer({"all": [["independen*"], ["multipl*", "product", "joint", "together"]], "window": 14})}
STATEMENT2 = ("The probability of an alternative a being considered is gamma which is independent of the "
              "probability of any other alternative being considered together here.")


class TestDisclosure(unittest.TestCase):
    def test_unreached_claim_is_rejected_by_id_only(self):
        draft = "Since each item is considered independently, how would you express the probability of all those events together?"
        v = lint(draft, blocked_claims=BLOCKED)
        self.assertEqual(codes(v), {"REVEALS_CLAIM"})
        self.assertIn("C3", v[0].detail)
        self.assertNotIn("independen", v[0].detail)        # the recognizer words must not leak through the message

    def test_neutral_question_passes_with_blocked_claims(self):
        self.assertEqual(lint("What have you tried so far?", blocked_claims=BLOCKED), [])

    def test_no_blocked_claims_means_no_disclosure_check(self):
        self.assertEqual(lint("The events are independent so multiply them together."), [])

    def test_quoting_the_problem_statement_is_not_a_reveal(self):
        quote = "As written, independent of the probability of any other alternative being considered together, correct?"
        self.assertEqual(lint(quote, statement=STATEMENT2, blocked_claims=BLOCKED), [])
        paraphrase = "These are independent, so how do they combine together?"
        self.assertIn("REVEALS_CLAIM", codes(lint(paraphrase, statement=STATEMENT2, blocked_claims=BLOCKED)))


class TestQuestionForm(unittest.TestCase):
    LAST = "I think the alternative needs to be considered and have the highest utility"

    def form(self, text):
        return lint(text, form=True, last_student_text=self.LAST)

    def test_good_forms_pass(self):
        self.assertEqual(self.form("What else has to happen for that alternative to be chosen?"), [])
        self.assertEqual(self.form("You said the alternative needs the highest utility. What else has to happen?"), [])

    def test_two_questions_rejected(self):
        self.assertIn("QUESTION_FORM", codes(self.form("What do you mean? And why does it matter?")))

    def test_word_cap_rejected(self):
        self.assertIn("QUESTION_FORM", codes(self.form(" ".join(["word"] * 70) + "?")))

    def test_second_statement_rejected(self):
        self.assertIn("QUESTION_FORM", codes(self.form("You are right. That is the idea. What next?")))

    def test_statement_must_echo_the_student(self):
        reason = check_form("Items have prices. What do you think?", self.LAST)
        self.assertIn("own words", reason)

    def test_form_is_off_by_default(self):
        self.assertEqual(lint("Two questions? Really? Yes, " + "word " * 80), [])
