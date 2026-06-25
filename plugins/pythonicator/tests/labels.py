"""Ground-truth scanner findings for the corpus fixtures.

Maps each scanner fixture filename to the (rule, line) findings the static
tier must report. Kept apart from the fixture sources so a fixture can be
handed to the reviewer as a leak-free eval input while this table stays the
grader's answer key. Authored from the canon, not from scanner output, so
the corpus test asserts intent rather than echoing the implementation.
"""

from __future__ import annotations

# Fixture filename -> the (rule, line) findings the scanner must report.
# legacy-typing, broad-except, and missing-module-docstring are whole-file
# checks the scanner pins to line 1; the rest point at the offending line.
SCANNER: dict[str, list[tuple[str, int]]] = {
    "typing_and_excepts.py": [
        ("legacy-typing", 1),  # the Optional and Union aliases
        ("broad-except", 1),  # `except Exception` in guard()
    ],
    "annotations_and_defaults.py": [
        ("missing-annotation", 6),  # missing_return lacks a return type
        ("missing-annotation", 15),  # missing_param leaves value bare
        ("mutable-default", 28),  # default_list uses []
        ("mutable-default", 40),  # default_dict uses {}
        ("mutable-default", 52),  # default_set uses set()
    ],
    "docstrings_and_markup.py": [
        ("missing-module-docstring", 1),  # the module opens with a comment
        ("missing-public-docstring", 5),  # undocumented has no docstring
        ("sphinx-markup", 14),  # backtick uses double backticks
        ("sphinx-markup", 19),  # field_list uses :param: and :returns:
    ],
    "nesting.py": [
        ("over-nested", 6),  # too_deep nests five deep
        ("over-nested", 23),  # deep_async nests five deep
    ],
    "identifiers.py": [
        ("cryptic-identifier", 6),  # the ab parameter
        ("cryptic-identifier", 6),  # the xy parameter, same line
        ("cryptic-identifier", 59),  # zz on the private _private
    ],
    "edge_blanking.py": [],  # rule-like text lives only in strings/comments
}

# Judgment-tier ground truth for the reviewer eval, keyed by fixture name.
# These are canon rules the scanner cannot decide; each entry is
# (category, line, severity) and the line points at the offending construct.
JUDGMENT: dict[str, list[tuple[str, int, str]]] = {
    "naming_and_docs.py": [
        ("abbreviation-outside-scope", 6, "warning"),
        ("docstring-restates-signature", 7, "warning"),
        ("magic-literal-not-named", 30, "blocker"),
    ],
    "control_and_functions.py": [
        ("lbyl-instead-of-eafp", 15, "warning"),
        ("guard-clause-missing", 26, "warning"),
        ("try-wraps-too-much", 37, "warning"),
    ],
    "conforming.py": [],
}
