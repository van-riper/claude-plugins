# bash-blacklist

Blocks specific bash commands before Claude runs them, via a `PreToolUse` hook.

## Install

Required dependencies:

- [Python](https://www.python.org/) ≥ 3.7

First make sure the `van-riper` marketplace is enabled, then install this plugin
with this command in the Claude Code TUI:

```text
/plugin install bash-blacklist@van-riper
```

## Setup

Set `CLAUDE_BASH_BLACKLIST` to a bash array literal string in your environment:

```sh
export CLAUDE_BASH_BLACKLIST='(
  "git pull"
  "git push"
)'
```

> **Note:** bash does not export arrays to subprocesses, so this must be
> set as a string containing array literal syntax. The single quotes are
> required to prevent the shell from interpreting the parentheses.

## Matching

Each entry is treated as a prefix. `"git push"` blocks `git push`,
`git push --force origin main`, and any other invocation starting
with those words. Exact matches (no arguments) are also blocked.

## Warnings

If `CLAUDE_BASH_BLACKLIST` is not set or is not a valid bash array,
Claude will receive a warning message explaining the issue and the
command will be allowed to proceed.
