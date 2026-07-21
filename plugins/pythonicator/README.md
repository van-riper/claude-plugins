# pythonicator

A Claude Code plugin that enforces the bundled Python styleguide references as
the canonical source of truth for agentic Python development.

It bundles three coordinated parts:

- **`pythonic-canon` skill:** the always-loaded precedence + severity model,
  quick reference, and judgment checklist, plus the full canon in `references/`,
  one file per section, with the shared Audit Protocol factored into
  `audit-protocol.md`. Derived from the vault styleguide, not hand-written.
- **`check_edit.py` hook:** a `PostToolUse` hook that quietly applies
  `ruff format` and `ruff check --fix` to every `.py` you edit and reports
  nothing. Safe autofixes, every edit, for free, with no interruption.
- **`check_stop.py` hook:** a `Stop` hook that, when the agent tries to finish,
  sweeps the files git reports as changed this session with `ruff check` and
  `ty check` and blocks until they are clean. The sweep runs before any
  judgment review, so the reviewer starts from a green mechanical layer.
- **`sync_session.py` hook:** a `SessionStart` hook with fail-open steps. It
  always surfaces a reminder to invoke the `pythonic-canon` skill before
  writing Python this session, the proactive counterpart to `check_stop.py`'s
  reactive backstop. It adds advisories for an unsupported interpreter or
  missing tools, skipping those two when the repo has no Python at all, so a
  docs-only session doesn't pay for notes it can't use. Wherever the plugin
  is installed, it also snapshots `ruff.pythonicator.toml` into your config
  dir and wires `~/.config/ruff/ruff.toml` to extend that snapshot,
  prepending one line if it is missing.
- **`pythonic-reviewer` agent:** a report-only subagent for a deliberate
  end-of-work pass. It clears the mechanical rules with the static scanner, then
  audits the judgment rules Ruff and ty cannot see, following the canon's Audit
  Protocol: it reports severity-mapped, cited findings with proposed fixes and
  edits nothing. It trusts the `check_stop.py` hook for types rather than
  running its own project-wide `ty`.

## Install

Required dependencies:

- [Python](https://www.python.org/) ≥ 3.12
- [Ruff](https://docs.astral.sh/ruff/) and [ty](https://docs.astral.sh/ty/),
  either natively or as a tool with [uv](https://docs.astral.sh/uv/)

First make sure the `van-riper` marketplace is enabled, then install this plugin
with this command in the Claude Code TUI:

```text
/plugin install pythonicator@van-riper
```

### Dependency note

Native `ruff` and `ty` on `$PATH` are recommended: they are the fast path the
hooks run on every edit. If either is missing, `uv` is required instead, and
the hooks fall back to running the missing tool through `uvx` at the minimum
version it requires. If neither the tool nor `uv` is installed, a SessionStart
note names what to install. Working on the plugin itself also needs `pytest`
for the test suite.

## Where is the canon sourced from?

**NOTE:** the canon .md files in the `pythonic-canon` references folder are
sourced directly from my personal styleguides, which remain unpublished for now.
The `sync_canon` script is purely for my convenience in shipping my styleguides
with this plugin and keeping it up-to-date.

The canon documents in `references/` are generated from my vault styleguide,
which will be verified and rebuilt frequently:

```shell
python3 src/sync_canon.py          # rebuild the canon from the vault
python3 src/sync_canon.py --check  # exit nonzero if the canon is stale
```

The build strips Obsidian syntax, inlines the core rules each Python section
links to, and splits the result into per-section files. New styleguide
sections are picked up automatically.

## Moving the source files

If the vault docs move, edit the configuration block at the top of
`src/sync_canon.py` (`VAULT_DIR`, `CORE_DOC`, `PYTHON_DOC`) and rebuild.
Nothing else references those paths.

## The Ruff config is the source of truth

`ruff.pythonicator.toml` is not generated; it is the hand-maintained,
authoritative Ruff config. Both this plugin and your personal global Ruff config
extend it, so there is one place to edit and nothing to keep in sync.

The `SessionStart` hook wires your global config up for you. Wherever the
plugin is installed, it copies the installed `ruff.pythonicator.toml` into your
own config dir under the same name, then prepends one line to
`~/.config/ruff/ruff.toml` that extends it, leaving the rest untouched:

```toml
# ~/.config/ruff/ruff.toml
extend = "ruff.pythonicator.toml"

# your config options and machine-local overrides follow go below
```

The snapshot (`~/.config/ruff/ruff.pythonicator.toml`) refreshes each session
from the installed plugin, so your global lint tracks the released canon.
A rule change takes effect after you edit `ruff.pythonicator.toml`, commit,
push, and run `marketplace update`. The `extend` is a relative name, resolved
against the config's own directory, so it is identical on every machine. The
hook prepends it only once.

Because the snapshot lives in your own config dir, global lint keeps working
from the last snapshot even if you later uninstall the plugin. It simply stops
tracking new changes.

If you would rather your `ruff.toml` _be_ the canon with no local overrides,
symlink it to `ruff.pythonicator.toml` yourself. The hook detects a symlinked
`ruff.toml` and leaves it alone.

### Copying the canon into a repo

The setup above extends a copy under `~/.config/ruff/`, which is
machine-local and never checked into any repo. A project's own `ruff.toml`
or `pyproject.toml` should not `extend` that path: it will not exist on a
contributor's machine or in CI. Only a copy committed to the repo is
guaranteed to resolve everywhere the repo is cloned.

To give a repo its own portable copy, find the installed file and copy it
into the repo root:

```shell
find ~/.claude/plugins -path '*pythonicator*/ruff.pythonicator.toml' \
  | sort | head -1 | xargs -I{} cp {} ./ruff.pythonicator.toml
```

Then wire it yourself into the `ruff.toml` or `pyproject.toml` that the
repo already uses:

```toml
extend = "ruff.pythonicator.toml"
```

This step is manual and stays that way: nothing in the plugin writes to a
repo's version-controlled files on its own. A rule change reaches the repo
only when someone repeats the copy and commits the update.
