"""Precision/recall scoring for reviewer findings against judgment labels.

Pure and deterministic: it takes the reviewer's normalized findings and the
labelled ground truth and reports how well they agree. The non-deterministic
part (running the reviewer) lives elsewhere; this is the grader.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LINE_TOLERANCE = 2


@dataclass(frozen=True)
class Finding:
    """One normalized finding.

    Attributes:
        category: The canonical judgment category.
        line: The 1-based line the finding points at.
    """

    category: str
    line: int


@dataclass(frozen=True)
class Score:
    """Aggregate match counts for a set of predictions.

    Attributes:
        true_positives: Predictions matched to a label.
        false_positives: Predictions with no matching label.
        false_negatives: Labels with no matching prediction.
    """

    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        """Return precision, or 1.0 when nothing was predicted."""
        predicted = self.true_positives + self.false_positives
        return self.true_positives / predicted if predicted else 1.0

    @property
    def recall(self) -> float:
        """Return recall, or 1.0 when there was nothing to find."""
        actual = self.true_positives + self.false_negatives
        return self.true_positives / actual if actual else 1.0

    @property
    def f1(self) -> float:
        """Return the harmonic mean of precision and recall."""
        total_rate = self.precision + self.recall
        if not total_rate:
            return 0.0
        return 2 * self.precision * self.recall / total_rate


def _take_match(
    prediction: Finding,
    candidates: list[Finding],
    line_tolerance: int,
) -> Finding | None:
    """Return the first candidate matching a prediction, or None.

    Args:
        prediction: The prediction to match.
        candidates: The unconsumed expected findings.
        line_tolerance: Allowed line distance for a match.

    Returns:
        The matching candidate, or None when none qualifies.
    """
    for candidate in candidates:
        same_category = candidate.category == prediction.category
        near_line = abs(candidate.line - prediction.line) <= line_tolerance
        if same_category and near_line:
            return candidate
    return None


def score_file(
    predicted: list[Finding],
    expected: list[Finding],
    line_tolerance: int = DEFAULT_LINE_TOLERANCE,
) -> Score:
    """Match predictions to expected findings for one file.

    A prediction matches an expected finding when they share a category and
    their lines fall within line_tolerance. Each label is consumed by at
    most one prediction.

    Args:
        predicted: The reviewer's normalized findings.
        expected: The labelled ground-truth findings.
        line_tolerance: Allowed line distance for a match.

    Returns:
        The true/false positive and false negative counts.
    """
    remaining = list(expected)
    true_positives = 0
    for prediction in predicted:
        match = _take_match(prediction, remaining, line_tolerance)
        if match is not None:
            remaining.remove(match)
            true_positives += 1
    false_positives = len(predicted) - true_positives
    return Score(true_positives, false_positives, len(remaining))


def total(scores: list[Score]) -> Score:
    """Sum per-file scores into one aggregate.

    Args:
        scores: The per-file scores.

    Returns:
        The summed score across every file.
    """
    return Score(
        sum(item.true_positives for item in scores),
        sum(item.false_positives for item in scores),
        sum(item.false_negatives for item in scores),
    )
