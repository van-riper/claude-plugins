"""Clean names, docs, and control flow: the judgment-tier control."""

from __future__ import annotations

OVERDUE_DAYS = 30


def sum_prices(prices: list[float]) -> float:
    """Return the total of all prices.

    Args:
        prices: The individual prices.

    Returns:
        The summed total.
    """
    return sum(prices)


def is_overdue(days_since_issue: int, grace_period_days: int) -> bool:
    """Report whether an invoice has passed its grace period.

    Args:
        days_since_issue: Days since the invoice was issued.
        grace_period_days: Allowed days before it counts as overdue.

    Returns:
        Whether the invoice is overdue.
    """
    return days_since_issue > grace_period_days
