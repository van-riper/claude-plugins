"""Tests for the audit_scan static tier."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import audit_scan
import labels

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCANNER_DIR = FIXTURES / "scanner"
CLEAN_DIR = FIXTURES / "clean"

_OVER_NESTED_SRC = '''"""Module."""


def deep(values: list[int]) -> int:
    """Walk too deep."""
    for first in values:
        for second in range(first):
            for third in range(second):
                if third:
                    return third
    return 0
'''

_SHALLOW_SRC = '''"""Module."""


def shallow(values: list[int]) -> int:
    """Walk to the limit, not past it."""
    for first in values:
        for second in range(first):
            if second:
                return second
    return 0
'''

_SPHINX_LITERAL_SRC = '''"""Module."""


def clamp(value: int) -> int:
    """Return ``value`` clamped."""
    return value
'''

_SPHINX_FIELD_SRC = '''"""Module."""


def clamp(value: int) -> int:
    """Clamp the value.

    :param value: the number
    :returns: the clamped value
    """
    return value
'''

_PLAIN_DOCSTRING_SRC = '''"""Module."""


def clamp(value: int) -> int:
    """Return the value, unchanged.

    Args:
        value: Any integer.

    Returns:
        The same integer.
    """
    return value
'''

_ARGS_TYPE_REPEATED_SRC = '''"""Module."""


def double(count: int) -> int:
    """Double a count.

    Args:
        count (int): The number to double.
    """
    return count * 2
'''

_RETURN_TYPE_REPEATED_SRC = '''"""Module."""


def clamp(value: int) -> int:
    """Return the value, unchanged.

    Returns:
        int: The same integer.
    """
    return value
'''

_PROSE_TYPE_RESTATED_SRC = '''"""Module."""


def total(prices: list[float]) -> float:
    """Add up the prices.

    Args:
        prices: A list of floats.

    Returns:
        A float.
    """
    return sum(prices)
'''


def _rules(src: str) -> set[str]:
    """Return the set of rule keys the scanner reports for source.

    Args:
        src: The Python source to scan.

    Returns:
        The distinct rule keys reported.
    """
    return {finding.rule for finding in audit_scan.scan_source(src)}


def _py_files(directory: Path) -> list[Path]:
    """Return the Python fixtures directly under a directory, sorted.

    Args:
        directory: The fixture directory to list.

    Returns:
        The `.py` files in name order.
    """
    return sorted(directory.glob("*.py"))


def _expected(fixture: Path) -> Counter[tuple[str, int]]:
    """Return a fixture's labelled findings as a multiset.

    Args:
        fixture: The scanner fixture to look up in the label table.

    Returns:
        A multiset of the (rule, line) pairs the scanner should report.

    Raises:
        KeyError: If the fixture has no entry in the label table.
    """
    if fixture.name not in labels.SCANNER:
        message = f"no label entry for fixture {fixture.name}"
        raise KeyError(message)
    return Counter(labels.SCANNER[fixture.name])


def test_scanner_corpus_matches_labels() -> None:
    """Each scanner fixture's findings equal its external label file."""
    failures: list[str] = []
    for fixture in _py_files(SCANNER_DIR):
        expected = _expected(fixture)
        findings = audit_scan.scan_source(fixture.read_text(encoding="utf-8"))
        actual = Counter((item.rule, item.line) for item in findings)
        if actual != expected:
            failures.append(
                f"{fixture.name}: {sorted(actual.elements())} != "
                f"{sorted(expected.elements())}"
            )
    assert not failures, "\n".join(failures)


def test_clean_corpus_has_no_findings() -> None:
    """Every conforming fixture yields zero findings."""
    offenders: list[str] = []
    for fixture in _py_files(CLEAN_DIR):
        findings = audit_scan.scan_source(fixture.read_text(encoding="utf-8"))
        if findings:
            offenders.append(f"{fixture.name}: {[f.rule for f in findings]}")
    assert not offenders, "\n".join(offenders)


def test_scan_tree_aggregates_corpus() -> None:
    """scan_tree returns coherent whole-tree metrics for the corpus."""
    result = audit_scan.scan_tree(SCANNER_DIR)
    aggregate = result["aggregate"]
    labelled_clean = sum(
        1 for findings in labels.SCANNER.values() if not findings
    )
    assert aggregate["total_files"] == len(_py_files(SCANNER_DIR))
    assert aggregate["total_files"] == len(labels.SCANNER)
    assert aggregate["files_clean"] == labelled_clean
    assert aggregate["by_severity"]["blocker"] >= 1


def test_over_nested_flagged() -> None:
    """A function nested five deep trips the over-nested rule."""
    assert "over-nested" in _rules(_OVER_NESTED_SRC)


def test_nesting_at_limit_not_flagged() -> None:
    """A function nested four deep stays within the limit."""
    assert "over-nested" not in _rules(_SHALLOW_SRC)


def test_sphinx_double_backtick_flagged() -> None:
    """A double-backtick inline literal trips the sphinx-markup rule."""
    assert "sphinx-markup" in _rules(_SPHINX_LITERAL_SRC)


def test_sphinx_field_list_flagged() -> None:
    """A reST field list trips the sphinx-markup rule."""
    assert "sphinx-markup" in _rules(_SPHINX_FIELD_SRC)


def test_plain_google_docstring_not_flagged() -> None:
    """A plain Google docstring does not trip sphinx-markup."""
    assert "sphinx-markup" not in _rules(_PLAIN_DOCSTRING_SRC)


def test_args_type_repeated_flagged() -> None:
    """An Args entry echoing its parameter's exact annotation is flagged."""
    assert "docstring-repeats-type" in _rules(_ARGS_TYPE_REPEATED_SRC)


def test_return_type_repeated_flagged() -> None:
    """A Returns line leading with the exact return annotation is flagged."""
    assert "docstring-repeats-type" in _rules(_RETURN_TYPE_REPEATED_SRC)


def test_prose_type_restatement_not_flagged() -> None:
    """A type restated in prose, not exact annotation text, is not flagged.

    Free-form restating like "a list of floats" is a judgment call; only an
    exact echo of the annotation text is mechanically decidable.
    """
    assert "docstring-repeats-type" not in _rules(_PROSE_TYPE_RESTATED_SRC)


def test_unparseable_flagged() -> None:
    """A file that fails to parse yields a single unparseable blocker.

    Kept inline rather than as an on-disk fixture: a broken `.py` fights
    every tool that touches it (linters, formatters, editor hooks).
    """
    findings = audit_scan.scan_source("def broken(value: int) -> int\n")
    assert [item.rule for item in findings] == ["unparseable"]


def test_known_gap_bare_typing_alias_escapes_legacy_typing() -> None:
    """KNOWN GAP: a bare `List` alias (no `typing.` prefix) is not flagged.

    legacy-typing requires a `typing.` qualifier for List/Dict/Tuple/Set,
    so an unqualified `from typing import List` usage slips through. This
    locks the current behaviour; flip it when the detector is widened.
    """
    src = (
        '"""Module."""\n'
        "from typing import List\n\n\n"
        "def total(values: List[int]) -> int:\n"
        '    """Sum the values."""\n'
        "    return sum(values)\n"
    )
    assert "legacy-typing" not in _rules(src)


def test_known_gap_tuple_except_escapes_broad_except() -> None:
    """KNOWN GAP: an `except (Exception, ...)` tuple is not flagged.

    broad_except inspects only a bare handler or a single Name, so a tuple
    of exception types is skipped even when it contains Exception. Flip
    this when the check learns to look inside except tuples.
    """
    src = (
        '"""Module."""\n\n\n'
        "def guard(value: int) -> int:\n"
        '    """Divide safely."""\n'
        "    try:\n"
        "        return 1 // value\n"
        "    except (Exception, ValueError):\n"
        "        return 0\n"
    )
    assert "broad-except" not in _rules(src)
