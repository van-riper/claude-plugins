"""Tests for the check_edit PostToolUse hook."""

from __future__ import annotations

import io
import json
import subprocess
from typing import TYPE_CHECKING
from unittest import mock

if TYPE_CHECKING:
    from pathlib import Path

import check_edit


def _completed(
    code: int, out: str, err: str
) -> subprocess.CompletedProcess[str]:
    """Build a completed process for the diagnostics helper.

    Args:
        code: The process return code.
        out: Captured stdout.
        err: Captured stderr.

    Returns:
        A completed process carrying those values.
    """
    return subprocess.CompletedProcess(
        args=["tool"], returncode=code, stdout=out, stderr=err
    )


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


def test_field_reads_mapping_key() -> None:
    """_field returns the value when the input is a dict with the key."""
    assert check_edit._field({"key": 7}, "key") == 7


def test_field_none_for_non_mapping() -> None:
    """_field returns None when the input is not a dict."""
    assert check_edit._field("nope", "key") is None


def test_field_none_for_missing_key() -> None:
    """_field returns None when the key is absent."""
    assert check_edit._field({"a": 1}, "b") is None


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


def test_diagnostics_empty_on_success() -> None:
    """A zero exit code produces no diagnostics."""
    assert not check_edit._diagnostics(_completed(0, "ignored", ""))


def test_diagnostics_reports_output_on_failure() -> None:
    """A nonzero exit code returns the combined, stripped output."""
    assert check_edit._diagnostics(_completed(1, "bad\n", "err")) == "bad\nerr"


def test_diagnostics_none_is_empty() -> None:
    """A missing process yields no diagnostics."""
    assert not check_edit._diagnostics(None)


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


def test_main_silent_when_tools_absent(tmp_path: Path) -> None:
    """With neither tool resolvable, the hook reports nothing."""
    target = tmp_path / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(target)}})
    with mock.patch.object(
        check_edit.toolrunner, "tool_command", return_value=None
    ):
        code, out = _run_main(payload)
    assert code == 0
    assert not out
