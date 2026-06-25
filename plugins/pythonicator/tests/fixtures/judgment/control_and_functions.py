"""Record helpers used to exercise control-flow and function judgment."""

from __future__ import annotations


def parse_count(raw: str) -> int:
    """Return the parsed count, or zero when the field is not numeric.

    Args:
        raw: The raw field value.

    Returns:
        The parsed integer, or zero.
    """
    if raw.isdigit():
        return int(raw)
    return 0


def handle_all(items: list[str]) -> None:
    """Handle each item when the list is non-empty.

    Args:
        items: The items to handle.
    """
    if items:
        for item in items:
            _handle(item)


def store_record(record: str) -> None:
    """Validate, transform, and store a record.

    Args:
        record: The record to store.
    """
    try:
        _validate(record)
        transformed = _transform(record)
        _store(transformed)
    except ValueError:
        return


def _handle(item: str) -> None:
    """Handle one item.

    Args:
        item: The item to handle.
    """


def _validate(record: str) -> None:
    """Validate a record.

    Args:
        record: The record to check.
    """


def _transform(record: str) -> str:
    """Return a transformed record.

    Args:
        record: The record to transform.

    Returns:
        The transformed record.
    """
    return record.upper()


def _store(record: str) -> None:
    """Store a record.

    Args:
        record: The record to store.
    """
