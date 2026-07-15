"""Stop hook: sweep the session's changed Python files with ruff and ty.

When the agent tries to finish, this hook asks git which .py files changed this
session (staged, unstaged, or newly untracked), runs ruff and ty across just
those files, and blocks the stop until they are clean. The per-edit hook
(check_edit.py) has already applied the safe autofixes silently; this hook is
where anything left over is reported, once, before any judgment-review pass.

Scoping to git's changed files keeps the sweep off pre-existing debt the agent
never touched, and catches edits made by dispatched subagents too. The hook
holds no state: every stop re-derives the file list and re-runs the tools, so a
partial fix simply shrinks the next report.

Never raises: a missing git or tool fails open and lets the stop proceed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hookbase
import toolrunner

TIMEOUT_SECONDS = 60


def _git_lines(args: list[str], cwd: Path) -> list[str]:
    """Run a git command in cwd and return its non-empty stdout lines.

    Args:
        args: The git subcommand and arguments after `git`.
        cwd: The directory to run git in.

    Returns:
        Non-empty stdout lines, or an empty list if git could not run
        or exited nonzero.
    """
    result = hookbase.run_command(
        ["git", "-C", str(cwd), *args], TIMEOUT_SECONDS
    )
    if result is None or result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def _git_root(cwd: Path) -> Path | None:
    """Return the git work-tree root containing cwd, or None.

    Args:
        cwd: The directory the hook was invoked from.

    Returns:
        The repository root, or None when cwd is not in a git work tree.
    """
    lines = _git_lines(["rev-parse", "--show-toplevel"], cwd)
    return Path(lines[0]) if lines else None


def _changed_python_files(root: Path) -> list[Path]:
    """List the .py files changed this session, resolved under root.

    Args:
        root: The git repository root.

    Returns:
        Existing .py paths git reports as changed-vs-HEAD or newly
        untracked, de-duplicated and sorted.
    """
    names = _git_lines(["diff", "--name-only", "HEAD"], root)
    names += _git_lines(["ls-files", "--others", "--exclude-standard"], root)
    paths = {root / name for name in names if name.endswith(".py")}
    return sorted(path for path in paths if path.exists())


def _diagnostics(result: subprocess.CompletedProcess[str] | None) -> str:
    """Return a tool's combined output when it reported a problem.

    Args:
        result: A completed checker process, or None.

    Returns:
        The stripped stdout+stderr when the tool exited nonzero, else "".
    """
    if result is None or result.returncode == 0:
        return ""
    return (result.stdout + result.stderr).strip()


def _venv_for(path: Path) -> Path | None:
    """Find the nearest ancestor .venv directory for a changed file.

    ty resolves imports from wherever it runs, which is the repo root, not
    the subproject the file actually lives in. Pointing it at the right
    subproject's venv (`ty check --python <venv>`) fixes that without
    needing `uv run`. See toolrunner.tool_command's docstring for why a
    bare PATH lookup misses subproject venvs.

    Args:
        path: A changed .py file to locate the owning venv for.

    Returns:
        The nearest ancestor `.venv` directory, searching upward from
        path's own directory, or None if none exists.
    """
    for directory in (path.parent, *path.parent.parents):
        candidate = directory / ".venv"
        if candidate.is_dir():
            return candidate
    return None


def _group_by_venv(
    paths: list[Path],
) -> tuple[dict[Path, list[Path]], list[Path]]:
    """Split changed files by nearest ancestor .venv, for grouped ty runs.

    Args:
        paths: The changed .py files ty will check.

    Returns:
        A (grouped, unversioned) pair: grouped maps each discovered
        .venv to the files under it, so each venv gets one `ty check
        --python <venv>` call; unversioned holds files with no ancestor
        .venv, left for today's bare `ty check` fallback.
    """
    grouped: dict[Path, list[Path]] = {}
    unversioned: list[Path] = []
    for path in paths:
        venv = _venv_for(path)
        if venv is None:
            unversioned.append(path)
        else:
            grouped.setdefault(venv, []).append(path)
    return grouped, unversioned


def _sweep(paths: list[Path]) -> list[str]:
    """Run ruff and ty across the changed files and collect findings.

    Args:
        paths: The changed .py files to check.

    Returns:
        One text block per tool that still reports problems.
    """
    findings: list[str] = []
    args = [str(path) for path in paths]
    ruff = toolrunner.tool_command("ruff")
    if ruff is not None:
        ruff_out = _diagnostics(
            hookbase.run_command(
                [*ruff, "check", "--output-format", "concise", *args],
                TIMEOUT_SECONDS,
            )
        )
        if ruff_out:
            findings.append(f"ruff:\n{ruff_out}")
    ty = toolrunner.tool_command("ty")
    if ty is not None:
        ty_outs: list[str] = []
        grouped, unversioned = _group_by_venv(paths)
        for venv, group_paths in grouped.items():
            ty_outs.append(
                _diagnostics(
                    hookbase.run_command(
                        [
                            *ty,
                            "check",
                            "--output-format",
                            "concise",
                            "--python",
                            str(venv),
                            *(str(p) for p in group_paths),
                        ],
                        TIMEOUT_SECONDS,
                    )
                )
            )
        if unversioned:
            ty_outs.append(
                _diagnostics(
                    hookbase.run_command(
                        [
                            *ty,
                            "check",
                            "--output-format",
                            "concise",
                            *(str(p) for p in unversioned),
                        ],
                        TIMEOUT_SECONDS,
                    )
                )
            )
        ty_out = "\n".join(out for out in ty_outs if out)
        if ty_out:
            findings.append(f"ty:\n{ty_out}")
    return findings


def _block(findings: list[str]) -> None:
    """Write a Stop-blocking decision carrying the sweep findings.

    Args:
        findings: One text block per tool that reported problems.
    """
    body = "\n\n".join(findings)
    reason = (
        "pythonic-canon: the mechanical sweep found issues in the files you "
        "changed this session. Fix them before finishing, so the judgment "
        "review starts from a clean mechanical layer. Attempt each fix once; "
        "if a finding survives a real attempt, explain it to the user rather "
        "than retrying indefinitely.\n\n" + body
    )
    output = {"decision": "block", "reason": reason}
    sys.stdout.write(json.dumps(output))


def main() -> int:
    """Sweep the session's changed files, blocking the stop if any are dirty.

    Returns:
        Always 0; the hook fails open and never errors the stop.
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if hookbase.field(payload, "agent_id") is not None:
        return 0
    # Re-entrant stop: we already blocked once this turn, so let it finish.
    if hookbase.field(payload, "stop_hook_active"):
        return 0
    raw_cwd = hookbase.field(payload, "cwd")
    cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd else Path.cwd()
    root = _git_root(cwd)
    if root is None:
        return 0
    paths = _changed_python_files(root)
    if not paths:
        return 0
    findings = _sweep(paths)
    if findings:
        _block(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
