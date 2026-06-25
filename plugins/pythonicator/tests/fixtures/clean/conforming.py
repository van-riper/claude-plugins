"""A conforming sample module that yields no scanner findings."""

from __future__ import annotations

from dataclasses import dataclass


def add(first: int, second: int) -> int:
    """Return the sum of two integers.

    Args:
        first: The first addend.
        second: The second addend.

    Returns:
        The sum.
    """
    return first + second


async def greet(name: str) -> str:
    """Return a greeting for a name.

    Args:
        name: Who to greet.

    Returns:
        The greeting line.
    """
    return f"hello {name}"


@dataclass
class Point:
    """A point in two dimensions.

    Attributes:
        x_coord: Horizontal position.
        y_coord: Vertical position.
    """

    x_coord: int
    y_coord: int


class Counter:
    """A simple incrementing counter."""

    def __init__(self, start: int) -> None:
        """Store the initial value.

        Args:
            start: The starting count.
        """
        self._value = start

    def increment(self, amount: int) -> int:
        """Add an amount and return the new value.

        Args:
            amount: How much to add.

        Returns:
            The updated value.
        """
        self._value += amount
        return self._value
