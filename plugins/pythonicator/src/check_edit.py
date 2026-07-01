"""PostToolUse hook: quietly apply ruff's safe autofixes to an edited file.

Runs `ruff format` then `ruff check --fix` on the Python file just written or
edited, and reports nothing. Whatever ruff cannot safely autofix waits for the
stop-time sweep in check_stop.py, which reports it and blocks the stop once the
work is done.

The two ruff hooks never double-signal about the same edit: this one only
fixes and never speaks, while the stop hook only reports (and blocks) and never
fires per edit. Never blocks the edit: a missing tool or unexpected error fails
open.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hookbase
import toolrunner

TIMEOUT_SECONDS = 30


def _edited_python_file(payload: object) -> Path | None:
    """Extract the edited path from the hook payload when it is Python.

    Args:
        payload: The decoded PostToolUse hook JSON.

    Returns:
        The path when it names an existing `.py` file, else None.
    """
    raw = hookbase.field(hookbase.field(payload, "tool_input"), "file_path")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if path.suffix != ".py" or not path.exists():
        return None
    return path


def main() -> int:
    """Apply ruff's format and safe autofixes to the edited file, silently.

    Returns:
        Always 0; the hook fails open so it never blocks an edit.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    target = _edited_python_file(payload)
    if target is None:
        return 0
    ruff = toolrunner.tool_command("ruff")
    if ruff is not None:
        hookbase.run_command([*ruff, "format", str(target)], TIMEOUT_SECONDS)
        hookbase.run_command(
            [*ruff, "check", "--fix", str(target)], TIMEOUT_SECONDS
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
