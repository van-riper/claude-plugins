"""Normalize a reviewer's free-form rule labels to canon categories.

The pythonic-reviewer cites rules in its own words drawn from the canon
sections. The eval maps those onto the small set of canonical judgment
categories the fixtures are labelled with, so scoring stays vocabulary-stable.
This map is expected to grow as real reviewer output reveals new phrasings.
"""

from __future__ import annotations

# Ordered (keyword, category) pairs. The first keyword found in a lowered
# label wins, so list more specific keywords first.
_KEYWORDS: list[tuple[str, str]] = [
    ("eafp", "lbyl-instead-of-eafp"),
    ("lbyl", "lbyl-instead-of-eafp"),
    ("guard", "guard-clause-missing"),
    ("early return", "guard-clause-missing"),
    ("wrap", "try-wraps-too-much"),
    ("try body", "try-wraps-too-much"),
    ("try-body", "try-wraps-too-much"),
    ("abbrev", "abbreviation-outside-scope"),
    ("magic", "magic-literal-not-named"),
    ("named constant", "magic-literal-not-named"),
    ("restate", "docstring-restates-signature"),
    ("redundant docstring", "docstring-restates-signature"),
    ("implementation", "docstring-restates-signature"),
    ("docstring", "docstring-restates-signature"),
]


def canonical(label: str) -> str | None:
    """Return the canonical category for a free-form label, or None.

    Args:
        label: The reviewer's rule or section text.

    Returns:
        The matching canonical category, or None when nothing matches.
    """
    lowered = label.lower()
    for keyword, category in _KEYWORDS:
        if keyword in lowered:
            return category
    return None
