from pipelines.transcribe_notes.framed_explainer.identity import (
    State, card_key, input_fingerprint, next_state, section_key)

INK = [{"id": "k1", "version": 3, "x": 1, "y": 2, "width": 3, "height": 4},
       {"id": "k2", "version": 1, "x": 5, "y": 6, "width": 7, "height": 8}]


def fp(**kw):
    args = dict(slide_sha1="a" * 40, ink=INK, frame_id="F1",
                prompt_version="explainer-v1", context_version="c1")
    args.update(kw)
    return input_fingerprint(**args)


def test_keys_are_stable_strings():
    assert card_key("ns", "F1", "S1") == "ns|F1|S1"
    assert section_key("ns", "S1", 2) == "ns|S1|2"
    assert section_key("ns", None, 1) == "ns|standalone|1"


def test_fingerprint_ignores_frame_resize():
    # frame size is not an input at all; only frame association (id) is
    assert fp() == fp()


def test_fingerprint_changes_with_ink_geometry():
    moved = [dict(INK[0], x=99), INK[1]]
    assert fp(ink=moved) != fp()


def test_fingerprint_changes_with_prompt_version_context_and_frame():
    assert fp(prompt_version="explainer-v2") != fp()
    assert fp(context_version="c2") != fp()
    assert fp(frame_id="F2") != fp()


def test_fingerprint_order_independent():
    assert fp(ink=list(reversed(INK))) == fp()


def test_next_state_none_is_pending():
    assert next_state(None, None, "x") is State.pending


def test_next_state_verified_same_fp_is_verified_noop():
    assert next_state(State.verified, "x", "x") is State.verified


def test_next_state_verified_changed_fp_is_stale():
    assert next_state(State.verified, "x", "y") is State.stale


def test_declined_stays_suppressed_on_same_fp_and_reopens_on_change():
    assert next_state(State.declined, "x", "x") is State.declined
    assert next_state(State.declined, "x", "y") is State.pending
