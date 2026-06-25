"""Locate the canon's external tools, preferring PATH then uvx.

ruff and ty are required at the versions the README and ruff.pythonicator.toml
pin. When one is absent from PATH but uv is installed, fall back to running it
through `uvx` at the same minimum version, so the hooks still work without
a separate install. This module also holds the minimum Python the plugin
targets, shared by the hooks that warn when the interpreter is older.
"""

from __future__ import annotations

import shutil
import sys

MIN_PYTHON = (3, 12)
TOOL_FLOORS = {"ruff": "0.15", "ty": "0.0.44"}


def tool_command(tool: str) -> list[str] | None:
    """Return the argv prefix that runs a tool, or None if it cannot run.

    Args:
        tool: The executable name, a key of TOOL_FLOORS.

    Returns:
        `[tool]` when it is on PATH, an equivalent `uvx` invocation when
        only uv is available, or None when neither can run it.
    """
    if shutil.which(tool):
        return [tool]
    if shutil.which("uvx"):
        return ["uvx", "--from", f"{tool}>={TOOL_FLOORS[tool]}", tool]
    return None


def python_below_min() -> bool:
    """Report whether the interpreter is below the supported floor.

    Returns:
        True when the running Python is older than MIN_PYTHON.
    """
    return sys.version_info < MIN_PYTHON
