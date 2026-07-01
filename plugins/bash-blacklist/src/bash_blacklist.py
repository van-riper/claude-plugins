#!/usr/bin/env python3
"""PreToolUse hook: block bash command prefixes in CLAUDE_BASH_BLACKLIST."""

from __future__ import annotations

import json
import os
import shlex
import sys
from itertools import dropwhile

ENV_VAR = "CLAUDE_BASH_BLACKLIST"
USAGE = (
    "Set it to a bash array literal, e.g. "
    'CLAUDE_BASH_BLACKLIST=\'("git pull" "git push")\'.'
)

# Shell tokens that end one command and begin the next.
COMMAND_SEPARATORS = {"&&", "||", "&", "|", ";", "(", ")"}


def emit(payload: dict[str, object]) -> None:
    """Write a hook response to stdout as a single JSON line."""
    sys.stdout.write(json.dumps(payload) + "\n")


def warn(message: str) -> None:
    """Emit a non-blocking advisory to the user through the hook channel."""
    emit({"systemMessage": f"bash-blacklist: {message}"})


def deny(prefix: str) -> None:
    """Block the bash call, citing the blacklisted prefix that matched."""
    emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"blocked command: {prefix}",
        }
    })


def load_blacklist(raw: str) -> list[list[str]] | None:
    """Return the env array literal as tokenized prefixes, or None."""
    raw = raw.strip()
    if not (raw.startswith("(") and raw.endswith(")")):
        return None
    try:
        return [shlex.split(prefix) for prefix in shlex.split(raw[1:-1])]
    except ValueError:
        return None


def tokenize(line: str) -> list[str]:
    """Return a line's shell tokens, or a plain split on unbalanced quotes."""
    lexer = shlex.shlex(line, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return line.split()


def split_commands(command: str) -> list[list[str]]:
    """Return the command's segments, each a token list, split on separators.

    Newlines bound commands in shell, so each line is tokenized on its own.
    """
    commands: list[list[str]] = []
    for line in command.splitlines():
        words: list[str] = []
        for token in tokenize(line):
            if token in COMMAND_SEPARATORS:
                commands.append(words)
                words = []
            else:
                words.append(token)
        commands.append(words)
    return [words for words in commands if words]


def is_assignment(token: str) -> bool:
    """Return whether the token is a leading NAME=value shell assignment."""
    name, sep, _ = token.partition("=")
    return bool(sep) and name.isidentifier()


def find_blocked_prefix(
    words: list[str], blacklist: list[list[str]]
) -> str | None:
    """Return the blacklisted prefix the command starts with, else None."""
    command = list(dropwhile(is_assignment, words))
    for prefix in blacklist:
        if command[: len(prefix)] == prefix:
            return " ".join(prefix)
    return None


def main() -> None:
    """Read the hook payload and deny the command if a segment matches."""
    # an unconfigured guardrail should guide the user, not block silently
    raw = os.environ.get(ENV_VAR, "")
    if not raw:
        warn(f"{ENV_VAR} is not set. {USAGE}")
        return

    # a malformed setting is the user's mistake, not a command to block
    blacklist = load_blacklist(raw)
    if blacklist is None:
        warn(f"{ENV_VAR} must be a bash array literal. {USAGE}")
        return

    # the pending tool call arrives as JSON on stdin
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    # tolerate any payload shape rather than crash the tool call
    try:
        command = payload["tool_input"]["command"]
    except (TypeError, KeyError):
        return

    # an absent or non-text command has nothing to screen
    if not isinstance(command, str) or not command:
        return

    # deny on the first sub-command that leads with a blocked prefix
    for words in split_commands(command):
        prefix = find_blocked_prefix(words, blacklist)
        if prefix:
            deny(prefix)
            return


if __name__ == "__main__":
    main()
