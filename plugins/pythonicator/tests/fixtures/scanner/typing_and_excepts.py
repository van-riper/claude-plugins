"""Legacy typing aliases and overly broad except handlers."""

from __future__ import annotations

from typing import Optional, Union


def coerce(value: Optional[int]) -> int:
    """Return the value or zero.

    Args:
        value: Maybe an integer.

    Returns:
        The integer, or zero when missing.
    """
    return value or 0


def widen(value: Union[int, float]) -> float:
    """Return the value as a float.

    Args:
        value: An int or float.

    Returns:
        The value as a float.
    """
    return float(value)


def guard(value: int) -> int:
    """Divide, swallowing any error.

    Args:
        value: The divisor.

    Returns:
        The quotient, or zero on failure.
    """
    try:
        return 100 // value
    except Exception:
        return 0
