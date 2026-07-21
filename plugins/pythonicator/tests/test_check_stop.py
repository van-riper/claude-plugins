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


def _transcript(tmp_path: Path, entries: list[list[dict[str, object]]]) -> Path:
    """Write a JSONL transcript of assistant messages to tmp_path.

    Args:
        tmp_path: The directory to write the transcript into.
        entries: One `message.content` list per line.

    Returns:
        The path to the written transcript file.
    """
    path = tmp_path / "transcript.jsonl"
    lines = [
        json.dumps({"message": {"content": content}}) for content in entries
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_skill_invoked_finds_bare_and_namespaced_call(tmp_path: Path) -> None:
    """_skill_invoked matches both bare and plugin-namespaced skill names."""
    bare = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": "pythonic-canon"},
                }
            ]
        ],
    )
    namespaced = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": "pythonicator:pythonic-canon"},
                }
            ]
        ],
    )
    assert check_stop._skill_invoked(bare, "pythonic-canon")
    assert check_stop._skill_invoked(namespaced, "pythonic-canon")


def test_skill_invoked_false_when_absent(tmp_path: Path) -> None:
    """_skill_invoked returns False when no matching call appears."""
    transcript = _transcript(
        tmp_path, [[{"type": "tool_use", "name": "Edit", "input": {}}]]
    )
    assert not check_stop._skill_invoked(transcript, "pythonic-canon")


def test_skill_invoked_fails_open_on_missing_transcript(tmp_path: Path) -> None:
    """_skill_invoked treats an unreadable transcript as invoked."""
    assert check_stop._skill_invoked(
        tmp_path / "missing.jsonl", "pythonic-canon"
    )


def test_stop_blocks_when_skill_never_invoked(tmp_path: Path) -> None:
    """Changed Python plus no skill invocation blocks the stop."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    transcript = _transcript(tmp_path, [])
    with mock.patch.object(check_stop, "_sweep", return_value=[]):
        code, out = _run_main({
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        })
    assert code == 0
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "pythonic-canon skill" in decision["reason"]


def test_stop_silent_when_skill_invoked(tmp_path: Path) -> None:
    """Changed Python plus a skill invocation stays silent."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    transcript = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": "pythonic-canon"},
                }
            ]
        ],
    )
    with mock.patch.object(check_stop, "_sweep", return_value=[]):
        code, out = _run_main({
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        })
    assert code == 0
    assert not out


def test_agent_dispatched_finds_bare_and_namespaced_call(
    tmp_path: Path,
) -> None:
    """_agent_dispatched matches both bare and plugin-namespaced types."""
    bare = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": "pythonic-reviewer"},
                }
            ]
        ],
    )
    namespaced = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {
                        "subagent_type": "pythonicator:pythonic-reviewer"
                    },
                }
            ]
        ],
    )
    assert check_stop._agent_dispatched(bare, "pythonic-reviewer")
    assert check_stop._agent_dispatched(namespaced, "pythonic-reviewer")


def test_agent_dispatched_false_when_absent(tmp_path: Path) -> None:
    """_agent_dispatched returns False when no matching dispatch appears."""
    transcript = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": "general-purpose"},
                }
            ]
        ],
    )
    assert not check_stop._agent_dispatched(transcript, "pythonic-reviewer")


def test_any_agent_dispatched_true_when_present(tmp_path: Path) -> None:
    """_any_agent_dispatched is True when any Agent call appears."""
    transcript = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": "general-purpose"},
                }
            ]
        ],
    )
    assert check_stop._any_agent_dispatched(transcript)


def test_any_agent_dispatched_false_when_absent(tmp_path: Path) -> None:
    """_any_agent_dispatched is False with no Agent call, or unreadable."""
    transcript = _transcript(
        tmp_path, [[{"type": "tool_use", "name": "Edit", "input": {}}]]
    )
    assert not check_stop._any_agent_dispatched(transcript)
    assert not check_stop._any_agent_dispatched(tmp_path / "missing.jsonl")


def test_stop_blocks_when_subagents_used_without_reviewer(
    tmp_path: Path,
) -> None:
    """Subagent-written Python without a reviewer dispatch blocks."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    transcript = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": "general-purpose"},
                }
            ],
            [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": "pythonic-canon"},
                }
            ],
        ],
    )
    with mock.patch.object(check_stop, "_sweep", return_value=[]):
        code, out = _run_main({
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        })
    assert code == 0
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "pythonic-reviewer" in decision["reason"]


def test_stop_silent_when_subagents_used_with_reviewer(
    tmp_path: Path,
) -> None:
    """A pythonic-reviewer dispatch satisfies subagent-written Python."""
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    transcript = _transcript(
        tmp_path,
        [
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": "general-purpose"},
                }
            ],
            [
                {
                    "type": "tool_use",
                    "name": "Agent",
                    "input": {"subagent_type": "pythonic-reviewer"},
                }
            ],
        ],
    )
    with mock.patch.object(check_stop, "_sweep", return_value=[]):
        code, out = _run_main({
            "cwd": str(tmp_path),
            "transcript_path": str(transcript),
        })
    assert code == 0
    assert not out


def test_stop_blocks_on_marker_when_python_already_committed(
    tmp_path: Path,
) -> None:
    """Python touched and committed away still blocks without the skill.

    A workflow that commits after every task (e.g. subagent-driven
    development) leaves no working-tree diff by the time Stop fires, so
    the judgment check must not depend solely on git diff.
    """
    _init_repo(tmp_path)
    (tmp_path / "new.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "new.py")
    _git(tmp_path, "commit", "-m", "feat: add new module")
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("", encoding="utf-8")
    check_stop.hookbase.mark_session_file(
        transcript, check_stop.hookbase.PYTHON_TOUCHED_MARKER
    )
    code, out = _run_main({
        "cwd": str(tmp_path),
        "transcript_path": str(transcript),
    })
    assert code == 0
    decision = json.loads(out)
    assert decision["decision"] == "block"
    assert "pythonic-canon skill" in decision["reason"]


def test_stop_silent_when_no_marker_and_git_diff_clean(
    tmp_path: Path,
) -> None:
    """A clean repo with no session marker stays silent."""
    _init_repo(tmp_path)
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("", encoding="utf-8")
    code, out = _run_main({
        "cwd": str(tmp_path),
        "transcript_path": str(transcript),
    })
    assert code == 0
    assert not out


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
