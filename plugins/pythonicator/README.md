# pythonicator

A local Claude Code plugin that enforces the personal Python styleguide as the
canonical source of truth for agentic Python work.

It bundles three coordinated parts:

- **`pythonic-canon` skill** — the always-loaded precedence + severity model,
  quick reference, and judgment checklist, plus the full canon in `references/`,
  one file per section, with the shared Audit Protocol factored into
  `audit-protocol.md`. Derived from the vault styleguide, not hand-written.
- **`check_edit.py` hook** — a `PostToolUse` hook that runs `ruff format`,
  `ruff check --fix`, and `ty check` on every `.py` you edit, feeding anything
  unresolved back as context. Mechanical conformance, every edit, for free.
- **`pythonic-reviewer` agent** — a report-only subagent for a deliberate
  end-of-work pass. It runs a whole-project `ty` gate, then audits the judgment
  rules ruff and ty cannot see, following the canon's Audit Protocol: it reports
  severity-mapped, cited findings with proposed fixes and edits nothing.

## Install

The plugin is local; nothing is published. From Claude Code:

```text
/plugin marketplace add ~/.claude/plugins/local/pythonicator
/plugin install pythonicator
```

The skill, hook, and agent register automatically. No `settings.json` edit is
needed.

## The canon is generated

`references/` and `ruff.base.toml` are built from two sources of truth:

- the vault styleguide: `~/org/Styleguide/Styleguide.md` and
  `~/org/Styleguide/Python Styleguide.md`
- the enforced ruff config: `~/.config/ruff/ruff.toml`

After editing any of those, rebuild:

```shell
python3 hooks/sync_canon.py          # rebuild the canon and mirror the ruff config
python3 hooks/sync_canon.py --check  # exit nonzero if the canon is stale
```

The build strips Obsidian syntax, inlines the core rules each Python section
links to, splits the result into per-section files, and copies the ruff config
to `ruff.base.toml`. New styleguide sections are picked up automatically.

## Moving the source files

If the vault docs or the ruff config move, edit the configuration block at the
top of `hooks/sync_canon.py` (`VAULT_DIR`, `CORE_DOC`, `PYTHON_DOC`,
`RUFF_CONFIG`) and rebuild. Nothing else references those paths.

## Linting this plugin

`ruff.toml` extends the mirrored `ruff.base.toml` and ignores the rules that do
not fit standalone hook scripts. The plugin's own Python is held to the same
canon it enforces.
