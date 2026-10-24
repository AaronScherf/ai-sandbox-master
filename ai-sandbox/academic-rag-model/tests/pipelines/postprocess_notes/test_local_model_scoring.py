import unittest

from pipelines.postprocess_notes.local_model_scoring import _local_zscores


class TestLocalZscores(unittest.TestCase):
    """
    Covers the TODO-0060 calibration fix: a page-stdev floor on each
    token's local-neighborhood stdev, added because raising the raw
    z-score threshold alone (see postprocess_notes.py's
    _CAUSAL_ZSCORE_THRESHOLD comment and
    docs/status/postprocess_notes/2026-08-27-notes-postprocessing-status.md)
    never found a clean cutoff on real terse/symbolic math-heavy notes.
    Only the pure-math core is tested here (no model dependency) --
    everything else in this module touches transformers/torch and is
    deliberately not unit-tested locally, per the module docstring.
    """

    def test_short_symbolic_window_correct_word_is_no_longer_an_extreme_outlier(self):
        # Representative of the real false positive against Practice
        # Sheet.md: a page with some ordinary surprisal variety elsewhere
        # (other words, numbers, punctuation -- `diverse`), plus a run of
        # highly predictable, uniform symbolic tokens (digits, operators,
        # single-letter variables all scoring identically low to GPT-2)
        # immediately surrounding one ordinary-but-slightly-less-common
        # English word ("Let"-like, surprisal 3.5 against neighbors at
        # 0.8). Old behavior (pure local stdev): the immediate
        # neighborhood is perfectly uniform (stdev == 0), so the division
        # blows up -- matching the documented unbounded-feeling z=11.60
        # for "Let" and z=5.91-6.27 for "subject", neither of which any
        # fixed threshold in a reasonable range could separate from a
        # real anomaly (see the status doc). The page-stdev floor pulls
        # this back under any reasonable threshold (5.0) by measuring the
        # word against the page's actual register, not an artificially
        # uniform immediate neighborhood.
        diverse = [1.0, 2.0, 5.0, 3.0, 6.0, 1.5, 4.0, 2.5, 5.5, 1.0]
        symbolic_run = [0.8] * 10
        surprisal = diverse + symbolic_run + [3.5] + symbolic_run
        target_index = len(diverse) + len(symbolic_run)
        z_scores = _local_zscores(surprisal, window=10)
        self.assertLess(z_scores[target_index], 5.0)

    def test_genuine_anomaly_still_clears_the_threshold(self):
        # A real substitution bug: surprisal far outside the page's own
        # range, not just slightly above a locally-uniform neighborhood.
        # The page-stdev floor must not mask this -- the whole point of
        # the fix is to stop *manufactured* z-scores, not to blunt real
        # ones.
        surprisal = [2.0, 2.2, 1.8, 2.1, 1.9, 14.0, 2.0, 2.3, 1.7, 2.0, 2.1]
        z_scores = _local_zscores(surprisal, window=10)
        self.assertGreater(z_scores[5], 5.0)

    def test_uniform_surprisal_everywhere_yields_zero_zscore(self):
        surprisal = [2.0] * 20
        z_scores = _local_zscores(surprisal, window=10)
        self.assertTrue(all(z == 0.0 for z in z_scores))

    def test_fewer_than_four_neighbors_yields_zero_zscore(self):
        # Matches the pre-existing edge case for the very start/end of a
        # short page or a small `window` -- too little context to judge
        # anything, so no flag rather than a noisy one.
        surprisal = [1.0, 1.0, 9.0]
        z_scores = _local_zscores(surprisal, window=1)
        self.assertEqual(z_scores, [0.0, 0.0, 0.0])

    def test_empty_surprisal_list_returns_empty_list(self):
        self.assertEqual(_local_zscores([]), [])

    def test_single_token_page_returns_zero(self):
        self.assertEqual(_local_zscores([5.0]), [0.0])

    def test_min_stdev_fraction_of_zero_matches_old_local_only_behavior(self):
        # Sanity check that the floor is the only behavior change: with
        # min_stdev_fraction=0.0, this reproduces the pre-fix formula
        # exactly (local mean/stdev only), including the oversized
        # z-score the fix exists to curb.
        diverse = [1.0, 2.0, 5.0, 3.0, 6.0, 1.5, 4.0, 2.5, 5.5, 1.0]
        symbolic_run = [0.8] * 10
        surprisal = diverse + symbolic_run + [3.5] + symbolic_run
        target_index = len(diverse) + len(symbolic_run)
        old_behavior = _local_zscores(surprisal, window=10, min_stdev_fraction=0.0)
        self.assertGreater(old_behavior[target_index], 5.0)


if __name__ == "__main__":
    unittest.main()
