# van-riper/claude-plugins

A personal Claude Code plugin marketplace.

## Install

```text
/plugin marketplace add van-riper/claude-plugins
```

## Plugins

- **pythonicator**: enforces the shipped Python styleguide on agentic Python
  work: a derived canon, a Ruff and ty PostToolUse hook, and a conformance
  reviewer agent. See the [README](plugins/pythonicator/README.md).
- **bash-blacklist**: blocks bash command prefixes before Claude runs them,
  configured via the `CLAUDE_BASH_BLACKLIST` environment variable. See the
  [README](plugins/bash-blacklist/README.md).

## Updating

Auto-updates are disabled by default for third-party marketplaces. To pull the
latest version, run the following command and update the plugins when prompted:

```text
/plugin marketplace update van-riper
```
