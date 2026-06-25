"""Tests for the sync_session SessionStart hook."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from pathlib import Path

import sync_session


def test_python_note_none_when_supported() -> None:
    """No note when the interpreter meets the floor."""
    with mock.patch.object(
        sync_session.toolrunner, "python_below_min", return_value=False
    ):
        assert sync_session._python_note() is None


def test_python_note_names_floor_when_old() -> None:
    """The note names the target floor when the interpreter is old."""
    with mock.patch.object(
        sync_session.toolrunner, "python_below_min", return_value=True
    ):
        note = sync_session._python_note()
    assert note is not None
    assert "3.12" in note


def test_tools_note_none_when_all_present() -> None:
    """No note when both tools resolve."""
    with mock.patch.object(
        sync_session.toolrunner, "tool_command", return_value=["tool"]
    ):
        assert sync_session._tools_note() is None


def test_tools_note_lists_both_missing() -> None:
    """Both tools missing produces a plural note naming each."""
    with mock.patch.object(
        sync_session.toolrunner, "tool_command", return_value=None
    ):
        note = sync_session._tools_note()
    assert note is not None
    assert "ruff and ty are unavailable" in note


def test_tools_note_names_single_missing() -> None:
    """One tool missing produces a singular note for just that tool."""
    with mock.patch.object(
        sync_session.toolrunner,
        "tool_command",
        side_effect=lambda tool: ["ruff"] if tool == "ruff" else None,
    ):
        note = sync_session._tools_note()
    assert note is not None
    assert "ty is unavailable" in note


def test_emit_session_notes_combines() -> None:
    """Multiple notes join into one additionalContext block."""
    out = io.StringIO()
    with mock.patch.object(sync_session.sys, "stdout", out):
        sync_session._emit_session_notes(["first", "second"])
    payload = json.loads(out.getvalue())
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert context == "first\n\nsecond"


def test_emit_session_notes_empty_writes_nothing() -> None:
    """No notes means no output at all."""
    out = io.StringIO()
    with mock.patch.object(sync_session.sys, "stdout", out):
        sync_session._emit_session_notes([])
    assert not out.getvalue()


def test_installed_base_finds_match(tmp_path: Path) -> None:
    """The marketplace glob returns the installed canon config."""
    plugin_dir = tmp_path / "mkt" / "plugins" / "pythonicator"
    plugin_dir.mkdir(parents=True)
    base = plugin_dir / "ruff.pythonicator.toml"
    base.write_text("line-length = 80\n", encoding="utf-8")
    with mock.patch.object(sync_session, "MARKETPLACES", tmp_path):
        assert sync_session._installed_base() == base


def test_installed_base_none_when_absent(tmp_path: Path) -> None:
    """No installed config yields None."""
    with mock.patch.object(sync_session, "MARKETPLACES", tmp_path):
        assert sync_session._installed_base() is None


def test_refresh_snapshot_writes_banner_and_base(tmp_path: Path) -> None:
    """The snapshot is the banner followed by the base content."""
    base = tmp_path / "base.toml"
    base.write_text("line-length = 80\n", encoding="utf-8")
    snapshot = tmp_path / "out" / "ruff.pythonicator.toml"
    with mock.patch.object(sync_session, "SNAPSHOT", snapshot):
        sync_session._refresh_snapshot(base)
    text = snapshot.read_text(encoding="utf-8")
    assert text.startswith(sync_session.SNAPSHOT_BANNER)
    assert "line-length = 80" in text


def test_ensure_extend_creates_config(tmp_path: Path) -> None:
    """An absent ruff.toml is created with the extend line and parents."""
    config = tmp_path / "ruff" / "ruff.toml"
    snapshot = tmp_path / "ruff" / "ruff.pythonicator.toml"
    with (
        mock.patch.object(sync_session, "RUFF_USER_CONFIG", config),
        mock.patch.object(sync_session, "SNAPSHOT", snapshot),
    ):
        sync_session._ensure_extend()
    text = config.read_text(encoding="utf-8")
    assert 'extend = "ruff.pythonicator.toml"' in text
    assert sync_session.EXTEND_MARKER in text


def test_ensure_extend_is_idempotent(tmp_path: Path) -> None:
    """Running twice leaves a single extend line."""
    config = tmp_path / "ruff" / "ruff.toml"
    snapshot = tmp_path / "ruff" / "ruff.pythonicator.toml"
    with (
        mock.patch.object(sync_session, "RUFF_USER_CONFIG", config),
        mock.patch.object(sync_session, "SNAPSHOT", snapshot),
    ):
        sync_session._ensure_extend()
        sync_session._ensure_extend()
    assert config.read_text(encoding="utf-8").count("extend = ") == 1


def test_ensure_extend_preserves_user_content(tmp_path: Path) -> None:
    """Existing config content is kept below the prepended extend line."""
    config = tmp_path / "ruff" / "ruff.toml"
    config.parent.mkdir(parents=True)
    config.write_text("line-length = 100\n", encoding="utf-8")
    snapshot = tmp_path / "ruff" / "ruff.pythonicator.toml"
    with (
        mock.patch.object(sync_session, "RUFF_USER_CONFIG", config),
        mock.patch.object(sync_session, "SNAPSHOT", snapshot),
    ):
        sync_session._ensure_extend()
    text = config.read_text(encoding="utf-8")
    assert "line-length = 100" in text
    assert text.index("extend = ") < text.index("line-length = 100")


def test_ensure_extend_leaves_symlink(tmp_path: Path) -> None:
    """A symlinked ruff.toml is left untouched."""
    snapshot = tmp_path / "ruff" / "ruff.pythonicator.toml"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("line-length = 80\n", encoding="utf-8")
    config = tmp_path / "ruff" / "ruff.toml"
    config.symlink_to(snapshot)
    with (
        mock.patch.object(sync_session, "RUFF_USER_CONFIG", config),
        mock.patch.object(sync_session, "SNAPSHOT", snapshot),
    ):
        sync_session._ensure_extend()
    assert config.is_symlink()
    assert sync_session.EXTEND_MARKER not in config.read_text(encoding="utf-8")
