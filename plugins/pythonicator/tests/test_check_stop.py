"""Tests for the check_stop Stop hook."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from unittest import mock

import check_stop


def _git(repo: Path, *args: str) -> None:
    """Run a git command in a repo, raising on failure.

    Args:
        repo: The repository directory.
        args: The git arguments after `git`.
    """
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path) -> None:
    """Initialize a git repo with one committed, clean file.

    Args:
        repo: The directory to turn into a repo.
    """
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@t.test")
    _git(repo, "config", "user.name", "t")
    (repo / "base.py").write_text('"""Base."""\n', encoding="utf-8")
    _git(repo, "add", "base.py")
    _git(repo, "commit", "-m", "chore: initial commit")


def _run_main(payload: dict[str, object]) -> tuple[int, str]:
    """Run check_stop.main with a payload on stdin, capturing stdout.

    Args:
        payload: The Stop hook payload to feed as JSON.

    Returns:
        The exit code and whatever the hook wrote to stdout.
    """
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    with (
        mock.patch.object(check_stop.sys, "stdin", stdin),
        mock.patch.object(check_stop.sys, "stdout", stdout),
    ):
        code = check_stop.main()
    return code, stdout.getvalue()


def test_non_git_cwd_allows_stop(tmp_path: Path) -> None:
    """A cwd outside any git repo lets the stop proceed silently."""
    code, out = _run_main({"cwd": str(tmp_path)})
    assert code == 0
    assert not out


def test_clean_repo_allows_stop(tmp_path: Path) -> None:
    """A repo with no changed .py files produces no block."""
    _init_repo(tmp_path)
    code, out = _run_main({"cwd": str(tmp_path)})
    assert code == 0
    assert not out


def test_changed_file_with_findings_blocks(tmp_path: Path) -> None:
    """When the sweep finds issues, main emits a block decision."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    with mock.patch.object(
        check_stop, "_sweep", return_value=["ruff:\nnew.py:1:1: D100 x"]
    ):
        code, out = _run_main({"cwd": str(tmp_path)})
    assert code == 0
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "new.py:1:1" in decision["reason"]


def test_changed_file_clean_allows_stop(tmp_path: Path) -> None:
    """When the sweep finds nothing, main stays silent."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    with mock.patch.object(check_stop, "_sweep", return_value=[]):
        code, out = _run_main({"cwd": str(tmp_path)})
    assert code == 0
    assert not out


def test_agent_id_skips_sweep(tmp_path: Path) -> None:
    """A payload carrying agent_id (a subagent stop) does nothing."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    with mock.patch.object(check_stop, "_sweep") as sweep:
        code, out = _run_main({"cwd": str(tmp_path), "agent_id": "sub-1"})
    assert code == 0
    assert not out
    sweep.assert_not_called()


def test_stop_hook_active_skips_sweep(tmp_path: Path) -> None:
    """A re-entrant stop (stop_hook_active) does not block again."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    with mock.patch.object(check_stop, "_sweep") as sweep:
        code, out = _run_main({"cwd": str(tmp_path), "stop_hook_active": True})
    assert code == 0
    assert not out
    sweep.assert_not_called()


def test_tools_absent_allows_stop(tmp_path: Path) -> None:
    """With neither ruff nor ty resolvable, the sweep finds nothing."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("import os\n", encoding="utf-8")
    with mock.patch.object(
        check_stop.toolrunner, "tool_command", return_value=None
    ):
        code, out = _run_main({"cwd": str(tmp_path)})
    assert code == 0
    assert not out


def test_sweep_reports_ruff_findings() -> None:
    """_sweep surfaces ruff's nonzero output as a labelled finding block."""
    completed = subprocess.CompletedProcess(
        args=["ruff"], returncode=1, stdout="f.py:1:1: F401 x\n", stderr=""
    )
    with (
        mock.patch.object(
            check_stop.toolrunner,
            "tool_command",
            side_effect=lambda name: [name] if name == "ruff" else None,
        ),
        mock.patch.object(
            check_stop.hookbase, "run_command", return_value=completed
        ),
    ):
        findings = check_stop._sweep([Path("f.py")])
    assert findings == ["ruff:\nf.py:1:1: F401 x"]


def test_venv_for_finds_nearest_ancestor(tmp_path: Path) -> None:
    """_venv_for finds a .venv in a parent directory of the changed file."""
    venv = tmp_path / "sub" / ".venv"
    venv.mkdir(parents=True)
    changed = tmp_path / "sub" / "pkg" / "mod.py"
    changed.parent.mkdir()
    changed.write_text("x = 1\n", encoding="utf-8")
    assert check_stop._venv_for(changed) == venv


def test_venv_for_missing_returns_none(tmp_path: Path) -> None:
    """_venv_for returns None when no ancestor .venv exists."""
    changed = tmp_path / "mod.py"
    changed.write_text("x = 1\n", encoding="utf-8")
    assert check_stop._venv_for(changed) is None


def test_group_by_venv_splits_grouped_and_unversioned(tmp_path: Path) -> None:
    """_group_by_venv groups files by owning venv, else unversioned."""
    venv = tmp_path / "sub" / ".venv"
    venv.mkdir(parents=True)
    in_venv = tmp_path / "sub" / "mod.py"
    in_venv.write_text("x = 1\n", encoding="utf-8")
    bare = tmp_path / "other.py"
    bare.write_text("y = 1\n", encoding="utf-8")
    grouped, unversioned = check_stop._group_by_venv([in_venv, bare])
    assert grouped == {venv: [in_venv]}
    assert unversioned == [bare]


def test_sweep_scopes_ty_to_each_files_venv(tmp_path: Path) -> None:
    """_sweep runs ty once per venv with --python, once for the rest."""
    venv = tmp_path / "sub" / ".venv"
    venv.mkdir(parents=True)
    in_venv = tmp_path / "sub" / "mod.py"
    in_venv.write_text("x = 1\n", encoding="utf-8")
    bare = tmp_path / "other.py"
    bare.write_text("y = 1\n", encoding="utf-8")
    calls = []

    def fake_run_command(cmd: list[str], _timeout: int) -> None:
        calls.append(cmd)

    with (
        mock.patch.object(
            check_stop.toolrunner,
            "tool_command",
            side_effect=lambda name: [name] if name == "ty" else None,
        ),
        mock.patch.object(
            check_stop.hookbase, "run_command", side_effect=fake_run_command
        ),
    ):
        check_stop._sweep([in_venv, bare])
    assert [
        "ty",
        "check",
        "--output-format",
        "concise",
        "--python",
        str(venv),
        str(in_venv),
    ] in calls
    assert ["ty", "check", "--output-format", "concise", str(bare)] in calls


def test_scoping_excludes_unchanged_committed_files(tmp_path: Path) -> None:
    """_changed_python_files returns changed and new .py, not clean ones."""
    _init_repo(tmp_path)
    tracked = tmp_path / "tracked.py"
    tracked.write_text("a = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.py")
    _git(tmp_path, "commit", "-m", "chore: add tracked")
    tracked.write_text("a = 2\n", encoding="utf-8")
    untracked = tmp_path / "untracked.py"
    untracked.write_text("b = 1\n", encoding="utf-8")
    result = check_stop._changed_python_files(tmp_path)
    assert set(result) == {tracked, untracked}
    assert (tmp_path / "base.py") not in result
