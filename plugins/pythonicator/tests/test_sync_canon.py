"""Tests for the sync_canon freshness check."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from pathlib import Path

import sync_canon


def test_is_stale_true_when_no_canon(tmp_path: Path) -> None:
    """An empty references directory is treated as stale."""
    refs = tmp_path / "refs"
    refs.mkdir()
    with mock.patch.object(sync_canon, "REFS_DIR", refs):
        assert sync_canon.is_stale() is True


def test_is_stale_false_when_sources_absent(tmp_path: Path) -> None:
    """With a built canon but no vault sources, nothing is stale."""
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "index.md").write_text("# canon\n", encoding="utf-8")
    with (
        mock.patch.object(sync_canon, "REFS_DIR", refs),
        mock.patch.object(sync_canon, "CORE_DOC", tmp_path / "none.md"),
        mock.patch.object(sync_canon, "PYTHON_DOC", tmp_path / "gone.md"),
    ):
        assert sync_canon.is_stale() is False
