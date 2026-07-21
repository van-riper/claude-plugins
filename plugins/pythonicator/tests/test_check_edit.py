"""Tests for the check_edit PostToolUse hook."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from pathlib import Path

import check_edit


def _run_main(payload_text: str) -> tuple[int, str]:
    """Run check_edit.main with the given stdin, capturing stdout.

    Args:
        payload_text: The raw text fed to the hook on stdin.

    Returns:
        The exit code and whatever the hook wrote to stdout.
    """
    stdin = io.StringIO(payload_text)
    stdout = io.StringIO()
    with (
        mock.patch.object(check_edit.sys, "stdin", stdin),
        mock.patch.object(check_edit.sys, "stdout", stdout),
    ):
        code = check_edit.main()
    return code, stdout.getvalue()


def test_edited_python_file_accepts_existing_py(tmp_path: Path) -> None:
    """An existing .py path in the payload is returned as a Path."""
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    payload = {"tool_input": {"file_path": str(target)}}
    assert check_edit._edited_python_file(payload) == target


def test_edited_python_file_rejects_non_python(tmp_path: Path) -> None:
    """A non-.py path is rejected."""
    target = tmp_path / "notes.txt"
    target.write_text("text", encoding="utf-8")
    payload = {"tool_input": {"file_path": str(target)}}
    assert check_edit._edited_python_file(payload) is None


def test_edited_python_file_rejects_missing(tmp_path: Path) -> None:
    """A path that does not exist is rejected."""
    payload = {"tool_input": {"file_path": str(tmp_path / "gone.py")}}
    assert check_edit._edited_python_file(payload) is None


def test_edited_python_file_handles_bad_payload() -> None:
    """Malformed payloads yield None rather than raising."""
    assert check_edit._edited_python_file({}) is None
    assert check_edit._edited_python_file("string") is None
    assert check_edit._edited_python_file({"tool_input": {}}) is None


def test_main_zero_on_invalid_json() -> None:
    """Invalid JSON on stdin fails open with no output."""
    code, out = _run_main("not json at all")
    assert code == 0
    assert not out


def test_main_ignores_non_python(tmp_path: Path) -> None:
    """A non-Python edit is ignored."""
    target = tmp_path / "data.txt"
    target.write_text("x", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(target)}})
    code, out = _run_main(payload)
    assert code == 0
    assert not out


def test_main_silent_after_fixing(tmp_path: Path) -> None:
    """A Python edit runs the two fixers but writes nothing to stdout."""
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(target)}})
    with (
        mock.patch.object(
            check_edit.toolrunner, "tool_command", return_value=["ruff"]
        ),
        mock.patch.object(check_edit.hookbase, "run_command") as run,
    ):
        code, out = _run_main(payload)
    assert code == 0
    assert not out
    assert run.call_count == 2


def test_main_silent_when_tool_absent(tmp_path: Path) -> None:
    """With ruff unresolvable, the hook still writes nothing."""
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(target)}})
    with mock.patch.object(
        check_edit.toolrunner, "tool_command", return_value=None
    ):
        code, out = _run_main(payload)
    assert code == 0
    assert not out


def test_main_marks_session_on_python_edit(tmp_path: Path) -> None:
    """Editing a .py file marks the session as having touched Python."""
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    transcript = tmp_path / "session.jsonl"
    payload = json.dumps({
        "tool_input": {"file_path": str(target)},
        "transcript_path": str(transcript),
    })
    with mock.patch.object(
        check_edit.toolrunner, "tool_command", return_value=None
    ):
        _run_main(payload)
    assert check_edit.hookbase.session_marker_exists(
        transcript, check_edit.hookbase.PYTHON_TOUCHED_MARKER
    )


def test_main_no_marker_for_non_python_edit(tmp_path: Path) -> None:
    """A non-Python edit never marks the session."""
    target = tmp_path / "data.txt"
    target.write_text("x", encoding="utf-8")
    transcript = tmp_path / "session.jsonl"
    payload = json.dumps({
        "tool_input": {"file_path": str(target)},
        "transcript_path": str(transcript),
    })
    _run_main(payload)
    assert not check_edit.hookbase.session_marker_exists(
        transcript, check_edit.hookbase.PYTHON_TOUCHED_MARKER
    )
