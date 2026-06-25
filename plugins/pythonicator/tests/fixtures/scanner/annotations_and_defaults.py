"""Annotation gaps and mutable default arguments."""

from __future__ import annotations


def missing_return(value: int):
    """Return the value but omit the return annotation.

    Args:
        value: An integer.
    """
    return value


def missing_param(value, factor: int) -> int:
    """Multiply, leaving the first parameter unannotated.

    Args:
        value: The base, unannotated.
        factor: The multiplier.

    Returns:
        The product.
    """
    return value * factor


def default_list(items: list[int] = []) -> int:
    """Sum items behind a mutable list default.

    Args:
        items: Numbers to sum.

    Returns:
        Their sum.
    """
    return sum(items)


def default_dict(data: dict[str, int] = {}) -> int:
    """Count entries behind a mutable dict default.

    Args:
        data: A mapping.

    Returns:
        Its length.
    """
    return len(data)


def default_set(values: set[int] = set()) -> int:
    """Count members behind a mutable set default.

    Args:
        values: A set.

    Returns:
        Its length.
    """
    return len(values)


def annotated_none(value: int | None = None) -> int:
    """Use a None default, which is not mutable.

    Args:
        value: An optional integer.

    Returns:
        The value or zero.
    """
    return value or 0


def annotated_tuple(items: tuple[int, ...] = ()) -> int:
    """Use an empty tuple default, which is immutable.

    Args:
        items: A tuple of integers.

    Returns:
        Their sum.
    """
    return sum(items)


class Adder:
    """A small accumulator."""

    def __init__(self, start: int) -> None:
        """Store the starting value.

        Args:
            start: The initial total.
        """
        self._total = start
