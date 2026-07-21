"""Tests for the shared hookbase helpers."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING
from unittest import mock

import hookbase

if TYPE_CHECKING:
    from pathlib import Path


def test_field_reads_mapping_key() -> None:
    """Field returns the value when the input is a dict with the key."""
    assert hookbase.field({"key": 7}, "key") == 7


def test_field_none_for_non_mapping() -> None:
    """Field returns None when the input is not a dict."""
    assert hookbase.field("nope", "key") is None


def test_field_none_for_missing_key() -> None:
    """Field returns None when the key is absent."""
    assert hookbase.field({"a": 1}, "b") is None


def test_run_command_returns_completed_process() -> None:
    """A command that runs returns its completed process."""
    result = hookbase.run_command([sys.executable, "-c", ""], 5)
    assert result is not None
    assert result.returncode == 0


def test_run_command_none_on_missing_executable() -> None:
    """A missing executable fails open to None."""
    assert hookbase.run_command(["no-such-binary-pythonicator-xyz"], 5) is None


def test_run_command_none_on_timeout() -> None:
    """A subprocess timeout fails open to None."""
    with mock.patch.object(
        hookbase.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd="x", timeout=1),
    ):
        assert hookbase.run_command(["anything"], 1) is None


def test_git_root_returns_toplevel(tmp_path: Path) -> None:
    """git_root resolves to the repository root."""
    subprocess.run(
        ["git", "init", str(tmp_path)], check=True, capture_output=True
    )
    assert hookbase.git_root(tmp_path) == tmp_path.resolve()


def test_git_root_none_outside_repo(tmp_path: Path) -> None:
    """git_root returns None outside any git work tree."""
    assert hookbase.git_root(tmp_path) is None


def test_git_lines_empty_on_failure(tmp_path: Path) -> None:
    """git_lines returns no lines when the git command fails."""
    assert hookbase.git_lines(["bogus-subcommand"], tmp_path) == []


def test_session_dir_from_top_level_transcript(tmp_path: Path) -> None:
    """A bare transcript path resolves to a same-named sibling dir."""
    transcript = tmp_path / "abc123.jsonl"
    assert hookbase.session_dir(transcript) == tmp_path / "abc123"


def test_session_dir_from_subagent_transcript(tmp_path: Path) -> None:
    """A subagent transcript path resolves to its parent session dir."""
    session = tmp_path / "abc123"
    transcript = session / "subagents" / "agent-xyz.jsonl"
    assert hookbase.session_dir(transcript) == session


def test_mark_session_file_then_exists(tmp_path: Path) -> None:
    """A marker written for a transcript path is then found present."""
    transcript = tmp_path / "abc123.jsonl"
    hookbase.mark_session_file(transcript, "python-touched")
    assert hookbase.session_marker_exists(transcript, "python-touched")


def test_mark_session_file_visible_from_subagent_path(tmp_path: Path) -> None:
    """A marker written via a subagent path is visible from the top-level."""
    session = tmp_path / "abc123"
    subagent_transcript = session / "subagents" / "agent-xyz.jsonl"
    hookbase.mark_session_file(subagent_transcript, "python-touched")
    top_level_transcript = tmp_path / "abc123.jsonl"
    assert hookbase.session_marker_exists(
        top_level_transcript, "python-touched"
    )


def test_session_marker_exists_false_when_absent(tmp_path: Path) -> None:
    """No marker means session_marker_exists reports False."""
    transcript = tmp_path / "abc123.jsonl"
    assert not hookbase.session_marker_exists(transcript, "python-touched")


def test_mark_session_file_fails_open_on_oserror(tmp_path: Path) -> None:
    """A mkdir failure is swallowed rather than raised."""
    transcript = tmp_path / "abc123.jsonl"
    with mock.patch.object(hookbase.Path, "mkdir", side_effect=OSError("nope")):
        hookbase.mark_session_file(transcript, "python-touched")
    assert not hookbase.session_marker_exists(transcript, "python-touched")
