"""Tests for the bash-blacklist PreToolUse hook."""

from __future__ import annotations

import io
import json
import os
from typing import TYPE_CHECKING
from unittest import mock

import bash_blacklist as bb

if TYPE_CHECKING:
    from collections.abc import Callable

BLACKLIST = '("git push" "rm -rf")'


def run_hook(stdin_text: str, blacklist: str | None) -> str:
    """Run the hook with a stdin payload and blacklist, capturing stdout.

    Args:
        stdin_text: The raw text fed to the hook on stdin.
        blacklist: The CLAUDE_BASH_BLACKLIST value, or None to leave it unset.

    Returns:
        Whatever the hook wrote to stdout.
    """
    environment = {} if blacklist is None else {bb.ENV_VAR: blacklist}
    stdin = io.StringIO(stdin_text)
    stdout = io.StringIO()
    with (
        mock.patch.dict(os.environ, environment, clear=True),
        mock.patch.object(bb.sys, "stdin", stdin),
        mock.patch.object(bb.sys, "stdout", stdout),
    ):
        bb.main()
    return stdout.getvalue()


def payload(command: object) -> str:
    """Return a hook payload wrapping the given command value."""
    return json.dumps({"tool_input": {"command": command}})


def captured(call: Callable[[], None]) -> str:
    """Return what a zero-argument callable writes to a patched stdout."""
    stdout = io.StringIO()
    with mock.patch.object(bb.sys, "stdout", stdout):
        call()
    return stdout.getvalue()


def test_load_blacklist_parses() -> None:
    """A well-formed bash array literal parses into tokenized prefixes."""
    cases = [
        ('("git push" "rm -rf")', [["git", "push"], ["rm", "-rf"]]),
        ("  ('git')  ", [["git"]]),
        ("()", []),
        ('("a b" "c")', [["a", "b"], ["c"]]),
    ]
    for raw, expected in cases:
        assert bb.load_blacklist(raw) == expected, raw


def test_load_blacklist_rejects() -> None:
    """Anything that is not a bash array literal yields None."""
    rejected = ["", "git push", '("oops)', '"git push"', "[1, 2]", "(no end"]
    for raw in rejected:
        assert bb.load_blacklist(raw) is None, raw


def test_tokenize() -> None:
    """A shell line tokenizes with operators kept and quotes preserved."""
    cases = [
        ("git push", ["git", "push"]),
        ("a && b || c", ["a", "&&", "b", "||", "c"]),
        ("cat x | grep y", ["cat", "x", "|", "grep", "y"]),
        ("echo 'git push'", ["echo", "'git push'"]),
        ("(git push)", ["(", "git", "push", ")"]),
        ("", []),
    ]
    for line, expected in cases:
        assert bb.tokenize(line) == expected, line


def test_tokenize_unbalanced_quote_falls_back() -> None:
    """An unbalanced quote degrades to a plain whitespace split."""
    assert bb.tokenize("echo 'oops") == ["echo", "'oops"]


def test_split_commands() -> None:
    """A compound command splits into per-segment token lists."""
    cases = [
        ("git push", [["git", "push"]]),
        ("echo hi && git push", [["echo", "hi"], ["git", "push"]]),
        ("a || b", [["a"], ["b"]]),
        ("a | b", [["a"], ["b"]]),
        ("a ; b", [["a"], ["b"]]),
        ("a & b", [["a"], ["b"]]),
        ("(git push)", [["git", "push"]]),
        ("echo $(git push)", [["echo", "$"], ["git", "push"]]),
        ("ls\ngit push", [["ls"], ["git", "push"]]),
        ("echo 'a && b'", [["echo", "'a && b'"]]),
        ("", []),
        ("   \n  \n", []),
    ]
    for command, expected in cases:
        assert bb.split_commands(command) == expected, command


def test_is_assignment() -> None:
    """Only a NAME=value token reads as a leading shell assignment."""
    cases = [
        ("FOO=bar", True),
        ("FOO=", True),
        ("PATH=/usr/bin:/bin", True),
        ("_x=1", True),
        ("git", False),
        ("=bar", False),
        ("1abc=x", False),
        ("--flag", False),
        ("a.b=c", False),
        ("", False),
    ]
    for token, expected in cases:
        assert bb.is_assignment(token) is expected, token


def test_find_blocked_prefix() -> None:
    """A segment is blocked only when it starts with a full prefix."""
    blacklist = [["git", "push"], ["rm", "-rf"]]
    cases = [
        (["git", "push"], "git push"),
        (["git", "push", "origin", "main"], "git push"),
        (["rm", "-rf", "/"], "rm -rf"),
        (["FOO=bar", "git", "push"], "git push"),
        (["A=1", "B=2", "git", "push"], "git push"),
        (["git", "status"], None),
        (["git"], None),
        (["git", "push-mirror"], None),
        (["echo", "git", "push"], None),
        ([], None),
    ]
    for words, expected in cases:
        assert bb.find_blocked_prefix(words, blacklist) == expected, words


def test_find_blocked_prefix_empty_blacklist() -> None:
    """An empty blacklist blocks nothing."""
    assert bb.find_blocked_prefix(["git", "push"], []) is None


def test_find_blocked_prefix_returns_first() -> None:
    """The first matching prefix in the blacklist is the one reported."""
    blacklist = [["git", "push"], ["git", "push", "origin"]]
    assert bb.find_blocked_prefix(["git", "push", "origin"], blacklist) == (
        "git push"
    )


def test_emit_writes_single_json_line() -> None:
    """Emit writes exactly one newline-terminated JSON object."""
    text = captured(lambda: bb.emit({"k": "v"}))
    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert json.loads(text) == {"k": "v"}


def test_warn_prefixes_message() -> None:
    """Warn tags the advisory with the plugin name."""
    text = captured(lambda: bb.warn("hello"))
    assert json.loads(text)["systemMessage"] == "bash-blacklist: hello"


def test_deny_emits_deny_decision() -> None:
    """Deny produces a PreToolUse deny decision naming the prefix."""
    output = json.loads(captured(lambda: bb.deny("git push")))
    decision = output["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"] == "blocked command: git push"


def test_main_blocks() -> None:
    """A command whose segment matches a prefix is denied."""
    commands = [
        "git push origin main",
        "FOO=bar git push",
        "echo hi && git push",
        "cat f | git push",
        "ls\ngit push",
        "(git push)",
        "echo $(git push)",
        "rm -rf /tmp/x",
    ]
    for command in commands:
        output = json.loads(run_hook(payload(command), BLACKLIST))
        decision = output["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny", command


def test_main_blocks_first_matching_segment() -> None:
    """The earliest matching segment determines the reported prefix."""
    output = json.loads(run_hook(payload("rm -rf / && git push"), BLACKLIST))
    reason = output["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason == "blocked command: rm -rf"


def test_main_allows() -> None:
    """A command with no matching segment passes silently."""
    commands = [
        "git status",
        "echo 'git push'",
        "git push-mirror origin",
        "ls -la",
        "echo git push",
    ]
    for command in commands:
        assert not run_hook(payload(command), BLACKLIST), command


def test_main_warns_when_unset() -> None:
    """An unset blacklist produces an advisory, not a block."""
    output = json.loads(run_hook(payload("ls"), None))
    assert "is not set" in output["systemMessage"]


def test_main_warns_on_malformed_blacklist() -> None:
    """A malformed blacklist produces an advisory, not a block."""
    output = json.loads(run_hook(payload("ls"), "not-an-array"))
    assert "must be a bash array literal" in output["systemMessage"]


def test_main_silent_on_bad_payload() -> None:
    """Malformed or empty payloads fail open with no output."""
    payloads = [
        "this is not json",
        "[1, 2, 3]",
        '{"tool_input": {}}',
        '{"tool_input": "string"}',
        '{"tool_input": {"command": ""}}',
        '{"tool_input": {"command": 42}}',
    ]
    for stdin_text in payloads:
        assert not run_hook(stdin_text, BLACKLIST), stdin_text


def test_main_silent_on_empty_blacklist() -> None:
    """An empty blacklist array blocks nothing."""
    assert not run_hook(payload("git push"), "()")
