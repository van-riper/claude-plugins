"""Tests for the sync_session SessionStart hook."""

from __future__ import annotations

import io
import json
import subprocess
from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from pathlib import Path

import sync_session


def _git(repo: Path, *args: str) -> None:
    """Run a git command in a repo, raising on failure.

    Args:
        repo: The repository directory.
        args: The git arguments after `git`.
    """
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _run_main(payload: dict[str, object]) -> str:
    """Run sync_session.main with a payload on stdin, capturing stdout.

    Args:
        payload: The SessionStart hook payload to feed as JSON.

    Returns:
        Whatever the hook wrote to stdout.
    """
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    with (
        mock.patch.object(sync_session.sys, "stdin", stdin),
        mock.patch.object(sync_session.sys, "stdout", stdout),
        mock.patch.object(sync_session, "_link_ruff_config"),
    ):
        sync_session.main()
    return stdout.getvalue()


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


def test_repo_has_python_true_for_tracked_file(tmp_path: Path) -> None:
    """A tracked .py file counts as Python present."""
    _git(tmp_path, "init")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "a.py")
    assert sync_session._repo_has_python(tmp_path)


def test_repo_has_python_true_for_untracked_file(tmp_path: Path) -> None:
    """An unstaged new .py file still counts."""
    _git(tmp_path, "init")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert sync_session._repo_has_python(tmp_path)


def test_repo_has_python_false_when_none_present(tmp_path: Path) -> None:
    """A repo with only non-Python tracked files returns False."""
    _git(tmp_path, "init")
    (tmp_path / "a.md").write_text("hi\n", encoding="utf-8")
    _git(tmp_path, "add", "a.md")
    assert not sync_session._repo_has_python(tmp_path)


def test_repo_has_python_fails_open_outside_git(tmp_path: Path) -> None:
    """A non-git directory fails open to True."""
    assert sync_session._repo_has_python(tmp_path)


def test_main_skips_env_notes_without_python(tmp_path: Path) -> None:
    """main() drops environment notes but keeps CANON_REMINDER, sans Python."""
    with (
        mock.patch.object(sync_session, "_repo_has_python", return_value=False),
        mock.patch.object(
            sync_session, "_python_note", return_value="python note"
        ),
        mock.patch.object(
            sync_session, "_tools_note", return_value="tools note"
        ),
    ):
        out = _run_main({"cwd": str(tmp_path)})
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "python note" not in context
    assert "tools note" not in context
    assert sync_session.CANON_REMINDER in context


def test_main_keeps_env_notes_with_python(tmp_path: Path) -> None:
    """main() keeps environment notes and CANON_REMINDER with Python present."""
    with (
        mock.patch.object(sync_session, "_repo_has_python", return_value=True),
        mock.patch.object(
            sync_session, "_python_note", return_value="python note"
        ),
        mock.patch.object(
            sync_session, "_tools_note", return_value="tools note"
        ),
    ):
        out = _run_main({"cwd": str(tmp_path)})
    context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "python note" in context
    assert "tools note" in context
    assert sync_session.CANON_REMINDER in context


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
