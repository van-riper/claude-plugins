"""Stop hook: sweep the session's changed Python files with ruff and ty.

When the agent tries to finish, this hook asks git which .py files changed this
session (staged, unstaged, or newly untracked), runs ruff and ty across just
those files, and blocks the stop until they are clean. The per-edit hook
(check_edit.py) has already applied the safe autofixes silently; this hook is
where anything left over is reported, once, before any judgment-review pass.

It also closes the judgment layer's enforcement gap: unlike ruff and ty, the
pythonic-canon skill only applies its naming/docstring/structure rules if the
agent chooses to invoke it, and nothing else in the session requires that. So
this hook reads the session transcript and blocks once more if Python changed
but the skill was never invoked, the same way it already blocks on dirty ruff
or ty output.

Scoping to git's changed files keeps the ruff/ty sweep off pre-existing debt
the agent never touched, and catches edits made by dispatched subagents too.
The judgment-layer check, though, can't rely on git diff alone: a workflow
that commits after every task (subagent-driven-development, for instance)
leaves no working-tree diff by the time Stop fires, silently erasing the
evidence that Python changed at all. check_edit.py's per-edit hook backs this
up with a per-session marker (hookbase.mark_session_file) touched whenever a
.py file is edited, subagent edits included, so this hook can tell "Python
changed this session" apart from "Python is dirty right now." The hook holds
no other state: every stop re-derives the file list and re-runs the tools, so
a partial fix simply shrinks the next report.

Never raises: a missing git, tool, or transcript fails open and lets the stop
proceed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hookbase
import toolrunner

TIMEOUT_SECONDS = 60


def _changed_python_files(root: Path) -> list[Path]:
    """List the .py files changed this session, resolved under root.

    Args:
        root: The git repository root.

    Returns:
        Existing .py paths git reports as changed-vs-HEAD or newly
        untracked, de-duplicated and sorted.
    """
    names = hookbase.git_lines(["diff", "--name-only", "HEAD"], root)
    names += hookbase.git_lines(
        ["ls-files", "--others", "--exclude-standard"], root
    )
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


SKILL_REMINDER = (
    "judgment skill:\nThis session edited Python but never invoked the "
    "pythonic-canon skill, so its judgment checklist (naming, docstrings, "
    "structure, complexity) was never applied. Invoke the pythonic-canon "
    "skill and walk its judgment checklist against the files you changed."
)


def _tool_uses(transcript_path: Path) -> list[dict[str, object]] | None:
    """Collect every tool_use content block in a JSONL transcript.

    Args:
        transcript_path: The session's JSONL transcript.

    Returns:
        The tool_use block dicts found, or None when the transcript
        cannot be read.
    """
    try:
        lines = transcript_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    blocks: list[dict[str, object]] = []
    for raw_line in lines:
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        content = hookbase.field(hookbase.field(entry, "message"), "content")
        if not isinstance(content, list):
            continue
        blocks.extend(
            cast("dict[str, object]", block)
            for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"
        )
    return blocks


def _skill_invoked(transcript_path: Path, skill_name: str) -> bool:
    """Return whether the transcript shows a Skill call for skill_name.

    ponytail: a Skill tool_use is a proxy for the review happening, not
    proof it was thorough; a stronger check would need to inspect what the
    agent did with the skill's content.

    Args:
        transcript_path: The session's JSONL transcript.
        skill_name: The bare skill name to look for, e.g. "pythonic-canon".

    Returns:
        True when a matching call is found or the transcript cannot be
        read (an unreadable transcript is not evidence of a skipped
        skill), else False.
    """
    blocks = _tool_uses(transcript_path)
    if blocks is None:
        return True
    for block in blocks:
        if block.get("name") != "Skill":
            continue
        skill = hookbase.field(block.get("input"), "skill")
        if isinstance(skill, str) and skill.rsplit(":", 1)[-1] == skill_name:
            return True
    return False


def _block(findings: list[str]) -> None:
    """Write a Stop-blocking decision carrying the sweep findings.

    Args:
        findings: One text block per check that reported a problem.
    """
    body = "\n\n".join(findings)
    reason = (
        "pythonic-canon: finish-blocking checks failed on the files you "
        "changed this session. Resolve each item below before finishing; "
        "attempt each once, then explain to the user rather than retrying "
        "indefinitely if it survives a real attempt.\n\n" + body
    )
    output = {"decision": "block", "reason": reason}
    sys.stdout.write(json.dumps(output))


def main() -> int:
    """Sweep the session's changed files, blocking the stop if any are dirty.

    Also blocks when Python changed but the pythonic-canon skill was never
    invoked this session, so the judgment layer gets the same enforcement
    the mechanical ruff/ty sweep already has. "Changed" is git's dirty
    working tree, or a workflow that commits after every task (subagent-
    driven-development, for instance) leaves no working-tree diff by the
    time Stop fires, so a per-edit session marker (see
    hookbase.mark_session_file) backs up the git-diff signal.

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
    root = hookbase.git_root(cwd)
    if root is None:
        return 0
    paths = _changed_python_files(root)
    findings = _sweep(paths) if paths else []
    raw_transcript = hookbase.field(payload, "transcript_path")
    if isinstance(raw_transcript, str) and raw_transcript:
        transcript = Path(raw_transcript)
        is_python_changed = bool(paths) or hookbase.session_marker_exists(
            transcript, hookbase.PYTHON_TOUCHED_MARKER
        )
        if is_python_changed and not _skill_invoked(
            transcript, "pythonic-canon"
        ):
            findings.append(SKILL_REMINDER)
    if findings:
        _block(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
