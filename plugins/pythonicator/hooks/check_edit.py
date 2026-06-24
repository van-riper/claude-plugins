"""PostToolUse hook: enforce the canon's mechanical rules on an edited file.

Runs ruff (format, then safe autofixes) and ty on the Python file that was just
written or edited, and feeds any remaining findings back to the agent as
additional context. Never blocks the edit: a missing tool or unexpected error
fails open.

This is the plugin's only ruff layer. It is advisory by design, so do not pair
it with a separate blocking ruff hook on the same edit — the two produce a
confusing double signal. See the README's "Ruff: run one hook, not two".
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent))

import toolrunner

TIMEOUT_SECONDS = 30


def _run(
    command: list[str], target: Path
) -> subprocess.CompletedProcess[str] | None:
    """Run a checker command against a file.

    Args:
        command: The executable and arguments preceding the file path.
        target: The Python file to check.

    Returns:
        The completed process, or None if the tool could not be run.
    """
    try:
        return subprocess.run(
            [*command, str(target)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _field(mapping: object, key: str) -> object:
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


def _edited_python_file(payload: object) -> Path | None:
    """Extract the edited path from the hook payload when it is Python.

    Args:
        payload: The decoded PostToolUse hook JSON.

    Returns:
        The path when it names an existing `.py` file, else None.
    """
    raw = _field(_field(payload, "tool_input"), "file_path")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if path.suffix != ".py" or not path.exists():
        return None
    return path


def _diagnostics(result: subprocess.CompletedProcess[str] | None) -> str:
    """Return a tool's output when it reported a problem.

    Args:
        result: A completed checker process, or None.

    Returns:
        The combined output when the tool exited nonzero, else an empty string.
    """
    if result is None or result.returncode == 0:
        return ""
    return (result.stdout + result.stderr).strip()


def _report(target: Path, findings: list[str]) -> None:
    """Surface unresolved findings to the agent as additional context.

    Args:
        target: The file the findings refer to.
        findings: One block of text per tool that still reports problems.
    """
    body = "\n\n".join(findings)
    message = (
        f"pythonic-canon: unresolved issues remain in {target.name}. "
        f"Fix them to satisfy the canon.\n\n{body}"
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        }
    }
    sys.stdout.write(json.dumps(output))


def main() -> int:
    """Format and check the edited file, reporting anything unresolved.

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

    findings: list[str] = []
    ruff = toolrunner.tool_command("ruff")
    if ruff is not None:
        _run([*ruff, "format"], target)
        _run([*ruff, "check", "--fix"], target)
        ruff_left = _diagnostics(
            _run([*ruff, "check", "--output-format", "concise"], target)
        )
        if ruff_left:
            findings.append(f"ruff:\n{ruff_left}")
    ty = toolrunner.tool_command("ty")
    if ty is not None:
        ty_left = _diagnostics(_run([*ty, "check"], target))
        if ty_left:
            findings.append(f"ty:\n{ty_left}")

    if findings:
        _report(target, findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
