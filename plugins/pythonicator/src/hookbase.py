"""Base helpers shared by the pythonicator hook entry points.

check_edit.py and check_stop.py both read a field from a decoded hook payload
and run external checkers as subprocesses that must fail open. Both helpers
live here so the two hooks share one implementation. This is a plain helper
module, not a base class.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

GIT_TIMEOUT_SECONDS = 60
PYTHON_TOUCHED_MARKER = "python-touched"


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


def git_lines(args: list[str], cwd: Path) -> list[str]:
    """Run a git command in cwd and return its non-empty stdout lines.

    Args:
        args: The git subcommand and arguments after `git`.
        cwd: The directory to run git in.

    Returns:
        Non-empty stdout lines, or an empty list if git could not run
        or exited nonzero.
    """
    result = run_command(["git", "-C", str(cwd), *args], GIT_TIMEOUT_SECONDS)
    if result is None or result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def git_root(cwd: Path) -> Path | None:
    """Return the git work-tree root containing cwd, or None.

    Args:
        cwd: The directory to check.

    Returns:
        The repository root, or None when cwd is not in a git work tree.
    """
    lines = git_lines(["rev-parse", "--show-toplevel"], cwd)
    return Path(lines[0]) if lines else None


def session_dir(transcript_path: Path) -> Path:
    """Return the per-session state directory for a transcript path.

    A subagent's own hook invocation carries its nested transcript path
    (`<session>/subagents/agent-*.jsonl`); the top-level hook carries
    `<session>.jsonl` next to that directory. Both forms resolve to the
    same `<session>` directory, so state written from a subagent's hook
    and read from the top-level's land in the same place.

    Args:
        transcript_path: A transcript path from any hook payload in the
            session, top-level or subagent.

    Returns:
        The per-session state directory (not guaranteed to exist).
    """
    if transcript_path.parent.name == "subagents":
        return transcript_path.parent.parent
    return transcript_path.parent / transcript_path.stem


def mark_session_file(transcript_path: Path, name: str) -> None:
    """Touch a per-session marker file, failing open on any OSError.

    Args:
        transcript_path: A transcript path from the current hook payload.
        name: The marker's file name.
    """
    try:
        directory = session_dir(transcript_path)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).touch()
    except OSError:
        pass


def session_marker_exists(transcript_path: Path, name: str) -> bool:
    """Return whether a per-session marker file has been touched.

    Args:
        transcript_path: A transcript path from the current hook payload.
        name: The marker's file name.

    Returns:
        True when the marker file exists for this session.
    """
    return (session_dir(transcript_path) / name).exists()
