"""Tests for the toolrunner tool-resolution helpers."""

from __future__ import annotations

from unittest import mock

import toolrunner


def test_tool_command_prefers_path() -> None:
    """A tool found on PATH resolves to a bare invocation."""
    with mock.patch.object(
        toolrunner.shutil, "which", return_value="/usr/bin/ruff"
    ):
        assert toolrunner.tool_command("ruff") == ["ruff"]


def test_tool_command_falls_back_to_uvx() -> None:
    """A tool absent from PATH runs through uvx at its floor."""
    with mock.patch.object(
        toolrunner.shutil,
        "which",
        side_effect=lambda name: "/usr/bin/uvx" if name == "uvx" else None,
    ):
        command = toolrunner.tool_command("ruff")
    floor = toolrunner.TOOL_FLOORS["ruff"]
    assert command == ["uvx", "--from", f"ruff>={floor}", "ruff"]


def test_tool_command_none_without_path_or_uvx() -> None:
    """With neither the tool nor uvx present, resolution returns None."""
    with mock.patch.object(toolrunner.shutil, "which", return_value=None):
        assert toolrunner.tool_command("ty") is None


def test_python_below_min_true_for_old() -> None:
    """An interpreter below the floor reports as below minimum."""
    with mock.patch.object(toolrunner.sys, "version_info", (3, 11, 0)):
        assert toolrunner.python_below_min() is True


def test_python_below_min_false_at_floor() -> None:
    """An interpreter at the floor reports as supported."""
    with mock.patch.object(toolrunner.sys, "version_info", (3, 12, 0)):
        assert toolrunner.python_below_min() is False
