from agent.concept_graph.ipguard import IP_RUN_WORDS, check_prose, longest_shared_run

PASSAGE = ("A preorder is a binary relation that is reflexive and transitive and nothing more, so ties between "
           "different elements are allowed.")


def test_the_limit_is_eight_words():
    assert IP_RUN_WORDS == 8


def test_copied_run_of_eight_words_is_caught():
    text = "Remember that a binary relation that is reflexive and transitive and so on."
    n, run = longest_shared_run(text, [PASSAGE])
    assert n >= 8 and "binary relation that is reflexive and transitive and" in run
    msgs = check_prose({"explanation": text}, [PASSAGE])
    assert len(msgs) == 1 and "explanation" in msgs[0]


def test_seven_shared_words_is_allowed():
    text = "It's a binary relation that is reflexive and then something different follows."
    n, _ = longest_shared_run(text, [PASSAGE])
    assert n == 7
    assert check_prose({"explanation": text}, [PASSAGE]) == []


def test_punctuation_and_case_differences_do_not_hide_a_copy():
    text = "BINARY RELATION, that is: reflexive -- and transitive; and nothing more!"
    assert check_prose({"gist": text}, [PASSAGE])


def test_a_paraphrase_with_the_same_vocabulary_passes():
    text = "Two properties define it: every element relates to itself, and comparisons chain together."
    assert check_prose({"explanation": text}, [PASSAGE]) == []


def test_check_prose_checks_every_field_it_is_given_and_skips_empty_ones():
    copied = "binary relation that is reflexive and transitive and nothing more"
    msgs = check_prose({"gist": "", "explanation": "fine words entirely different", "example": copied}, [PASSAGE])
    assert len(msgs) == 1 and msgs[0].startswith("example")


def test_no_passages_means_nothing_to_compare():
    assert check_prose({"explanation": "anything at all goes here today"}, []) == []
    assert longest_shared_run("some text here", []) == (0, "")
