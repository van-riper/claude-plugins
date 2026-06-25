"""Strings and comments must not trip the scanner.

This module is clean. The rule-like text below lives only in string
literals and comments, which code_only blanks before the regex checks
run, and which are never treated as docstrings.
"""

from __future__ import annotations

# Optional, Union, typing.List, except Exception, code, param all appear here.
LEGACY_NOTE = "Optional[int] and Union[int, str] and typing.List values"
EXCEPT_NOTE = "except Exception: swallow everything"
MARKUP_NOTE = ":param value: a number and ``literal`` and :returns: text"


def describe(value: int) -> int:
    """Return the value, with rule-like text only in a local string.

    Args:
        value: Any integer.

    Returns:
        The same integer.
    """
    note = "Optional and Union and except Exception and a literal and param"
    return value if note else value
