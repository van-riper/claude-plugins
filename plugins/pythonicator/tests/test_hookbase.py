"""Tests for the shared hookbase helpers."""

from __future__ import annotations

import subprocess
import sys
from unittest import mock

import hookbase


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
