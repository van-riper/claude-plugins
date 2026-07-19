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
- **gh-triage**: wraps `gh project` (GitHub Projects v2) with a
  Status/Type/Effort/Epic triage workflow and a recommended Active/
  Backlog/Epics view layout - scripts for creating, finding, editing,
  and archiving backlog items without retyping field/option IDs.
  See the [README](plugins/gh-triage/README.md).

## Updating

Auto-updates are disabled by default for third-party marketplaces. To pull the
latest version, run the following command and update the plugins when prompted:

```text
/plugin marketplace update van-riper
```
