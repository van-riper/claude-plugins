"""Billing helpers used to exercise naming and documentation judgment."""

from __future__ import annotations


def calc_ord_total(ord_items: list[float]) -> float:
    """Loop over the items and add each price to a running total.

    Args:
        ord_items: A list of floats.

    Returns:
        A float.
    """
    total = 0.0
    for price in ord_items:
        total += price
    return total


def is_overdue(days_since_issue: int) -> bool:
    """Report whether an invoice is overdue.

    Args:
        days_since_issue: Days since the invoice was issued.

    Returns:
        Whether it is overdue.
    """
    return days_since_issue > 30
