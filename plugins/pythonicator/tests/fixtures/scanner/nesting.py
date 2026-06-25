"""Nesting depth: the over-nested rule and its boundary cases."""

from __future__ import annotations


def too_deep(values: list[int]) -> int:
    """Nest one level past the limit.

    Args:
        values: Numbers to walk.

    Returns:
        A found value or zero.
    """
    for first in values:
        for second in range(first):
            for third in range(second):
                if third:
                    return third
    return 0


async def deep_async(values: list[int]) -> int:
    """Nest past the limit inside an async function.

    Args:
        values: Numbers to walk.

    Returns:
        A found value or zero.
    """
    for first in values:
        for second in range(first):
            for third in range(second):
                if third:
                    return third
    return 0


def at_limit(values: list[int]) -> int:
    """Nest exactly to the limit, not past it.

    Args:
        values: Numbers to walk.

    Returns:
        A found value or zero.
    """
    for first in values:
        for second in range(first):
            if second:
                return second
    return 0


def long_elif(value: int) -> int:
    """Use a long if/elif chain, which flattens to one level.

    Args:
        value: The selector.

    Returns:
        A mapped integer.
    """
    if value == 1:
        return 10
    elif value == 2:
        return 20
    elif value == 3:
        return 30
    elif value == 4:
        return 40
    elif value == 5:
        return 50
    else:
        return 0


def with_and_match(value: int, items: list[int]) -> int:
    """Exercise with and match blocks without exceeding the limit.

    Args:
        value: A selector.
        items: A context list.

    Returns:
        A small integer.
    """
    with open("/dev/null", encoding="utf-8") as handle:
        handle.write(str(value))
    match value:
        case 1:
            return 1
        case _:
            return len(items)


def outer(values: list[int]) -> int:
    """Hold a nested function that is audited as its own unit.

    Args:
        values: Numbers to sum.

    Returns:
        The inner result.
    """

    def inner(rows: list[int]) -> int:
        """Total the rows, nesting shallowly in its own scope.

        Args:
            rows: Numbers to total.

        Returns:
            Their sum.
        """
        total = 0
        for row in rows:
            if row:
                total += row
        return total

    return inner(values)
