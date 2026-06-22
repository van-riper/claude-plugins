"""Tests for the audit_scan static tier."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import audit_scan

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


def _rules(src: str) -> set[str]:
    """Return the set of rule keys the scanner reports for source."""
    return {finding.rule for finding in audit_scan.scan_source(src)}


def test_scan_tree_counts_violations() -> None:
    """The scanner separates the clean file from the messy one."""
    fixtures = Path(__file__).resolve().parent / "fixtures"
    result = audit_scan.scan_tree(fixtures)

    aggregate = result["aggregate"]
    assert aggregate["total_files"] == 2
    assert aggregate["files_clean"] == 1

    by_path = {Path(f["path"]).name: f for f in result["files"]}
    assert by_path["clean.py"]["count"] == 0
    messy_rules = {f["rule"] for f in by_path["messy.py"]["findings"]}
    assert "legacy-typing" in messy_rules
    assert "broad-except" in messy_rules
    assert "missing-module-docstring" in messy_rules
    assert by_path["messy.py"]["path"] == "messy.py"


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
