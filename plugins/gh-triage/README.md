# gh-triage

A Claude Code plugin that wraps `gh project` (GitHub Projects v2) with a
Status/Type/Effort triage workflow: scripts for creating, finding, editing, and
archiving backlog items without retyping the underlying GraphQL field/option IDs on
every call.

It bundles one skill:

- **`gh-triage` skill:** setup instructions for resolving your
  project's field/option IDs into a config file, plus `scripts/*.sh` wrappers
  around `gh project item-create`/`item-edit`/`item-list`/`item-archive` for
  the day-to-day triage loop (add an item, find an item, update its status,
  archive a placeholder, summarize the board).

## Install

Required dependencies:

- [GitHub CLI](https://cli.github.com/) (`gh`), authenticated with the
  `project` scope
- [jq](https://jqlang.org/)

First make sure the `van-riper` marketplace is enabled, then install this
plugin with this command in the Claude Code TUI:

```text
/plugin install gh-triage@van-riper
```

## Setup

This plugin ships no project-specific IDs - GitHub Projects (v2) doesn't
expose field/option names to the API, only opaque IDs, so each consuming repo
needs its own config file. See the "Setup" section of
`skills/gh-triage/SKILL.md` for the full walkthrough: run
`scripts/init-config.sh <project-num> <owner>` from your repo root to
generate `gh-triage.conf.sh` from your project's actual fields, then
review anything it couldn't match by name. `gh-triage.conf.sh.example`
is also available to fill in by hand if you'd rather not query `gh` at setup
time.
