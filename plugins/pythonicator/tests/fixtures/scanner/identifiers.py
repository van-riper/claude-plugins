"""Cryptic identifiers and the exempt short names."""

from __future__ import annotations


def cryptic(ab: int, xy: int) -> int:
    """Take two cryptically named parameters.

    Args:
        ab: A short name.
        xy: Another short name.

    Returns:
        Their sum.
    """
    return ab + xy


def loop_vars(i: int, j: int, k: int) -> int:
    """Take the exempt loop-style names.

    Args:
        i: First index.
        j: Second index.
        k: Third index.

    Returns:
        Their sum.
    """
    return i + j + k


def handler_vars(e: int, f: int) -> int:
    """Take the exempt error and file names.

    Args:
        e: An error code.
        f: A file handle id.

    Returns:
        Their sum.
    """
    return e + f


def descriptive(count: int, total: int) -> int:
    """Take descriptive names, which are fine.

    Args:
        count: How many.
        total: The running total.

    Returns:
        Their sum.
    """
    return count + total


def _private(zz: int) -> int:
    return zz * 2
