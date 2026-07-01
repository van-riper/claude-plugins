"""Base helpers shared by the pythonicator hook entry points.

check_edit.py and check_stop.py both read a field from a decoded hook payload
and run external checkers as subprocesses that must fail open. Both helpers
live here so the two hooks share one implementation. This is a plain helper
module, not a base class.
"""

from __future__ import annotations

import subprocess
from typing import cast


def field(mapping: object, key: str) -> object:
    """Read one key from a value that may or may not be a mapping.

    Args:
        mapping: A decoded JSON value, possibly a dict.
        key: The key to read.

    Returns:
        The value at the key when mapping is a dict, else None.
    """
    if not isinstance(mapping, dict):
        return None
    return cast("dict[str, object]", mapping).get(key)


def run_command(
    command: list[str], timeout: int
) -> subprocess.CompletedProcess[str] | None:
    """Run a command with a timeout, failing open to None.

    Args:
        command: The full argv to run.
        timeout: Seconds to allow before giving up.

    Returns:
        The completed process (stdout and stderr captured as text), or
        None if it could not run or timed out.
    """
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
