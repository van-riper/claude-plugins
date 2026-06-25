"""Tests for the eval scoring core and label normalizer."""

from __future__ import annotations

import math

import aliases
import score


def test_perfect_match_scores_one() -> None:
    """A prediction on the labelled line counts as a true positive."""
    finding = score.Finding("magic-literal-not-named", 30)
    result = score.score_file([finding], [finding])
    assert result.true_positives == 1
    assert result.false_positives == 0
    assert result.false_negatives == 0
    assert math.isclose(result.precision, 1.0)
    assert math.isclose(result.recall, 1.0)


def test_match_within_line_tolerance() -> None:
    """A prediction a line or two off still matches its label."""
    predicted = [score.Finding("guard-clause-missing", 27)]
    expected = [score.Finding("guard-clause-missing", 26)]
    assert score.score_file(predicted, expected).true_positives == 1


def test_line_outside_tolerance_misses() -> None:
    """A prediction far from the label is a false positive and a miss."""
    predicted = [score.Finding("guard-clause-missing", 40)]
    expected = [score.Finding("guard-clause-missing", 26)]
    result = score.score_file(predicted, expected)
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.false_negatives == 1


def test_category_mismatch_misses() -> None:
    """Same line but a different category does not match."""
    predicted = [score.Finding("guard-clause-missing", 30)]
    expected = [score.Finding("magic-literal-not-named", 30)]
    result = score.score_file(predicted, expected)
    assert result.true_positives == 0
    assert result.false_positives == 1
    assert result.false_negatives == 1


def test_finding_on_clean_is_false_positive() -> None:
    """A finding where there is no label drops precision."""
    predicted = [score.Finding("magic-literal-not-named", 10)]
    result = score.score_file(predicted, [])
    assert result.false_positives == 1
    assert math.isclose(result.precision, 0.0)


def test_silence_on_clean_is_perfect() -> None:
    """No findings against no labels scores a perfect 1.0."""
    result = score.score_file([], [])
    assert math.isclose(result.precision, 1.0)
    assert math.isclose(result.recall, 1.0)
    assert math.isclose(result.f1, 1.0)


def test_each_label_consumed_once() -> None:
    """Two predictions on one label yield one hit and one false positive."""
    predicted = [
        score.Finding("magic-literal-not-named", 30),
        score.Finding("magic-literal-not-named", 30),
    ]
    expected = [score.Finding("magic-literal-not-named", 30)]
    result = score.score_file(predicted, expected)
    assert result.true_positives == 1
    assert result.false_positives == 1


def test_total_sums_per_file_scores() -> None:
    """Total adds the counts across files."""
    summed = score.total([score.Score(1, 2, 3), score.Score(4, 5, 6)])
    assert summed.true_positives == 5
    assert summed.false_positives == 7
    assert summed.false_negatives == 9


def test_canonical_maps_known_phrasings() -> None:
    """The normalizer maps reviewer phrasings to canon categories."""
    assert aliases.canonical("LBYL pre-check") == "lbyl-instead-of-eafp"
    assert aliases.canonical("magic number 30") == "magic-literal-not-named"
    assert aliases.canonical("abbreviated parameter") == (
        "abbreviation-outside-scope"
    )


def test_canonical_returns_none_for_unknown() -> None:
    """An unrecognized label maps to None."""
    assert aliases.canonical("some unrelated note") is None
