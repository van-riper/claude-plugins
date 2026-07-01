# This module intentionally omits its docstring to trip the rule.
from __future__ import annotations


def undocumented(value: int) -> int:
    return value + 1


def _private_helper(value: int) -> int:
    return value - 1


def backtick(value: int) -> int:
    """Return ``value`` unchanged."""
    return value


def field_list(value: int) -> int:
    """Clamp the value.

    :param value: the number to clamp
    :returns: the clamped value
    """
    return max(value, 0)


def documented(value: int) -> int:
    """Return the value, unchanged.

    Args:
        value: Any integer.

    Returns:
        The same integer.
    """
    return value


def args_type_repeated(count: int) -> int:
    """Double a count.

    Args:
        count (int): The number to double.

    Returns:
        The doubled count.
    """
    return count * 2


def return_type_repeated(value: int) -> int:
    """Return the value, unchanged.

    Args:
        value: Any integer.

    Returns:
        int: The same integer.
    """
    return value
